"""Private Firestore subscriber lookup and per-recipient email delivery."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Callable

from engine import is_valid_event, send_email, utc_now


def event_matches_preferences(event: dict[str, Any], subscriber: dict[str, Any]) -> bool:
    categories = subscriber.get("categories") or ["tcg", "plush", "collectibles", "games", "accessories", "news"]
    retailers = subscriber.get("retailers") or ["all"]
    category = event.get("category") or "collectibles"
    retailer = event.get("retailer_key") or "other"
    return ("all" in categories or category in categories) and ("all" in retailers or retailer in retailers)


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
    """Queue and send matching digests without placing subscriber PII in public state.

    Failed/pending delivery batches remain in the subscriber's private Firestore
    subcollection and are retried on the next scheduled workflow run.
    """
    service_json = env.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if db is None:
        if not service_json:
            return "Subscriber delivery is not configured: add FIREBASE_SERVICE_ACCOUNT_JSON."
        try:
            db = create_firestore_client(service_json)
        except Exception as exc:
            return f"Subscriber database unavailable ({type(exc).__name__})."

    site_url = env.get("PUBLIC_SITE_URL", "").strip().rstrip("/")
    manage_url = f"{site_url}/?unsubscribe=1#subscriptions" if site_url else ""
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
                # The optional owner-only digest already includes every new event.
                continue
            subscriber_ref = subscriber_snapshot.reference
            deliveries_ref = subscriber_ref.collection("deliveries")

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

            # A status-only query uses Firestore's automatic single-field index.
            for delivery_snapshot in deliveries_ref.where("status", "==", "pending").stream():
                delivery = delivery_snapshot.to_dict() or {}
                raw_events = delivery.get("events") or []
                events = [event for event in raw_events if is_valid_event(event)]
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
                        events,
                        env,
                        subject_prefix,
                        recipient=email,
                        manage_url=manage_url,
                    )
                except Exception as exc:
                    # Avoid writing SMTP exception text to public Actions logs or Firestore.
                    sent, message = False, type(exc).__name__
                if sent:
                    delivery_snapshot.reference.update({
                        "status": "sent",
                        "sent_at": utc_now(),
                        "attempts": int(delivery.get("attempts", 0)) + 1,
                        "last_error": "",
                    })
                    sent_count += 1
                else:
                    delivery_snapshot.reference.update({
                        "status": "pending",
                        "updated_at": utc_now(),
                        "attempts": int(delivery.get("attempts", 0)) + 1,
                        "last_error": str(message)[:120],
                    })
                    queued_count += 1
    except Exception as exc:
        return f"Subscriber delivery could not complete ({type(exc).__name__}); pending messages remain queued."

    if not smtp_ready and active_count:
        return f"{active_count} active subscriber(s); email credentials missing, deliveries remain queued."
    return f"{active_count} active subscriber(s); {sent_count} digest(s) sent; {queued_count} queued for retry."
