"""Private Firestore subscriber lookup and per-recipient email delivery."""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from typing import Any, Callable

import engine
from engine import send_email, utc_now

DEFAULT_EVENT_TYPES = ["new_item", "restock", "price_drop", "news"]
MAX_ITEM_KEYWORDS = 20


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _subscriber_event_types(subscriber: dict[str, Any]) -> set[str]:
    raw = subscriber.get("event_types")
    if not isinstance(raw, list) or not raw:
        return set(DEFAULT_EVENT_TYPES)
    allowed = set(DEFAULT_EVENT_TYPES)
    # Backward compatibility: old records receive the four supported event types.
    return {str(item) for item in raw if str(item) in allowed}


def _subscriber_keywords(subscriber: dict[str, Any]) -> list[str]:
    raw = subscriber.get("item_keywords") or []
    if isinstance(raw, str):
        raw = re.split(r"[,;\n]+", raw)
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in raw[:MAX_ITEM_KEYWORDS * 2]:
        phrase = re.sub(r"\s+", " ", str(item or "")).strip()[:80]
        key = _normalize(phrase)
        if len(key) < 2 or key in seen:
            continue
        seen.add(key)
        result.append(key)
        if len(result) >= MAX_ITEM_KEYWORDS:
            break
    return result


def event_matches_preferences(event: dict[str, Any], subscriber: dict[str, Any]) -> bool:
    categories = subscriber.get("categories") or ["tcg", "plush", "collectibles", "games", "accessories", "news"]
    retailers = subscriber.get("retailers") or ["all"]
    category = event.get("category") or "collectibles"
    retailer = event.get("retailer_key") or "other"
    event_type = str(event.get("type") or "")
    if event_type not in _subscriber_event_types(subscriber):
        return False
    # News is selected as an event type, separately from the product-category
    # choices. Keep it available even if a Trainer only selected product categories.
    category_matches = event_type == "news" or "all" in categories or category in categories
    if not (category_matches and ("all" in retailers or retailer in retailers)):
        return False

    keywords = _subscriber_keywords(subscriber)
    if keywords:
        searchable = _normalize(" ".join(str(event.get(key) or "") for key in ("title", "summary", "source_name")))
        searchable_tokens = set(searchable.split())
        def keyword_matches(keyword: str) -> bool:
            if keyword in searchable:
                return True
            tokens = keyword.split()
            return bool(tokens) and all(token in searchable_tokens for token in tokens)
        if not any(keyword_matches(keyword) for keyword in keywords):
            return False
    return True


def delivery_batch_id(events: list[dict[str, Any]]) -> str:
    identifiers = sorted(str(event.get("id", "")) for event in events)
    return hashlib.sha256("|".join(identifiers).encode("utf-8")).hexdigest()[:32]


def create_firestore_client(service_account_json: str):
    """Create a Firestore client from a GitHub Actions secret containing service-account JSON."""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError as exc:
        raise RuntimeError("firebase-admin dependency is missing") from exc

    service_data = json.loads(service_account_json)
    app_name = "pokedrop-watch-actions"
    try:
        app = firebase_admin.get_app(app_name)
    except ValueError:
        app = firebase_admin.initialize_app(
            credentials.Certificate(service_data),
            options={"projectId": service_data.get("project_id")},
            name=app_name,
        )
    return firestore.client(app)


def dispatch_subscriber_notifications(
    new_events: list[dict[str, Any]],
    env: dict[str, str],
    subject_prefix: str = "PokéDrop Watch",
    *,
    db=None,
    send_func: Callable[..., tuple[bool, str]] = send_email,
) -> str:
    """Queue and send matching digests without placing subscriber PII in public state."""
    service_json = env.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if db is None:
        if not service_json:
            return "Subscriber delivery is not configured: add FIREBASE_SERVICE_ACCOUNT_JSON."
        try:
            db = create_firestore_client(service_json)
        except Exception as exc:
            return f"Subscriber database unavailable ({type(exc).__name__})."

    site_url = env.get("PUBLIC_SITE_URL", "").strip().rstrip("/")
    manage_url = f"{site_url}/notify.html" if site_url else ""
    smtp_ready = bool(env.get("SMTP_USERNAME", "").strip() and env.get("SMTP_APP_PASSWORD", "").strip())
    active_count = 0
    sent_count = 0
    queued_count = 0

    try:
        active_subscribers = db.collection("subscribers").where("status", "==", "active").stream()
        for subscriber_snapshot in active_subscribers:
            subscriber = subscriber_snapshot.to_dict() or {}
            email = str(subscriber.get("email", "")).strip()
            if not email:
                continue
            active_count += 1
            owner_copy = env.get("ALERT_EMAIL", "").strip().lower()
            if owner_copy and email.lower() == owner_copy:
                continue
            deliveries_ref = subscriber_snapshot.reference.collection("deliveries")

            matching = [event for event in new_events if event_matches_preferences(event, subscriber)]
            if matching:
                batch_id = delivery_batch_id(matching)
                batch_ref = deliveries_ref.document(batch_id)
                existing = batch_ref.get()
                if not existing.exists:
                    batch_ref.set({
                        "status": "pending",
                        "events": matching[:50],
                        "created_at": utc_now(),
                        "attempts": 0,
                    })

            for delivery_snapshot in deliveries_ref.where("status", "==", "pending").stream():
                delivery = delivery_snapshot.to_dict() or {}
                raw_events = delivery.get("events") or []
                events = [event for event in raw_events if engine.is_valid_event(event)]
                if not events:
                    delivery_snapshot.reference.update({
                        "status": "suppressed",
                        "events": [],
                        "last_error": "Batch contained no verified Pokémon product/news events; no email was sent.",
                        "updated_at": utc_now(),
                    })
                    continue
                if len(events) != len(raw_events):
                    delivery_snapshot.reference.update({"events": events, "updated_at": utc_now()})
                if not smtp_ready:
                    queued_count += 1
                    continue
                try:
                    sent, message = send_func(
                        events, env, subject_prefix, recipient=email, manage_url=manage_url,
                    )
                except Exception as exc:
                    sent, message = False, type(exc).__name__
                if sent:
                    delivery_snapshot.reference.update({
                        "status": "sent", "sent_at": utc_now(),
                        "attempts": int(delivery.get("attempts", 0)) + 1, "last_error": "",
                    })
                    sent_count += 1
                else:
                    delivery_snapshot.reference.update({
                        "status": "pending", "updated_at": utc_now(),
                        "attempts": int(delivery.get("attempts", 0)) + 1,
                        "last_error": str(message)[:120],
                    })
                    queued_count += 1
    except Exception as exc:
        return f"Subscriber delivery could not complete ({type(exc).__name__}); pending messages remain queued."

    if not smtp_ready and active_count:
        return f"{active_count} active subscriber(s); email credentials missing, deliveries remain queued."
    return f"{active_count} active subscriber(s); {sent_count} digest(s) sent; {queued_count} queued for retry."
