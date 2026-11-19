#!/usr/bin/env python3
"""Run one scan cycle and persist dashboard state."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Install retailer/date recovery and primary-first conditional fallback before
# binding the scanner function. Every configured primary is checked each run.
import engine_patch  # noqa: F401
import engine_recovery_patch  # noqa: F401
import broad_source_patch  # noqa: F401
import trainer_preferences_patch  # noqa: F401
from engine import (
    clean_product_title, deduplicate_products, infer_category, is_valid_event, make_session,
    is_email_eligible_event, normalize_match_text, scan_source, send_email, utc_now,
)
from subscribers import dispatch_subscriber_notifications


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Cannot read {path}: {exc}")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def deduplicate_events(events: list[dict]) -> list[dict]:
    """Collapse duplicate alerts when the same product appears in multiple routes."""
    unique = []
    seen = set()
    for event in events:
        event_type = event.get("type", "")
        title = normalize_match_text(event.get("title", ""))
        retailer = normalize_match_text(
            event.get("retailer_key") or event.get("retailer") or event.get("source_name", "")
        )
        price = "" if event_type in {"first_seen", "new_item"} else str(event.get("price", ""))
        previous = "" if event_type in {"first_seen", "new_item"} else str(event.get("previous_price", ""))
        url = str(event.get("url", "")) if event_type == "news" else ""
        key = (event_type, retailer, title, price, previous, url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def migrate_state(state: dict) -> dict:
    """Normalize legacy events/products without declaring old listings new drops."""
    for collection_name in ("events", "pending_email"):
        for event in state.get(collection_name, []):
            if event.get("type") == "new_drop":
                event["type"] = "first_seen"
                event["summary"] = (
                    "First observed by PokéDrop Watch. Original listing and release dates are unverified."
                )
            if event.get("type") != "news":
                event["title"] = clean_product_title(event.get("title", ""))

    deduped_events = []
    seen_events = set()
    for event in state.get("events", []):
        if not is_valid_event(event):
            continue
        event_type = event.get("type", "")
        title_key = normalize_match_text(event.get("title", ""))
        retailer = normalize_match_text(event.get("retailer_key") or event.get("retailer") or event.get("source_name", ""))
        price_key = "" if event_type in {"first_seen", "new_item"} else str(event.get("price", ""))
        previous_key = "" if event_type in {"first_seen", "new_item"} else str(event.get("previous_price", ""))
        url_key = str(event.get("url", "")) if event_type == "news" else ""
        key = (event_type, retailer, title_key, price_key, previous_key, url_key)
        if key in seen_events:
            continue
        seen_events.add(key)
        deduped_events.append(event)
    state["events"] = deduped_events
    # A verified new_item has a published release date and is email-eligible.
    # Only unverified first_seen catalog discoveries are intentionally excluded.
    state["pending_email"] = [
        event for event in state.get("pending_email", [])
        if is_valid_event(event) and event.get("type") != "first_seen"
    ]

    for source_state in state.get("items", {}).values():
        products = source_state.get("products")
        if not isinstance(products, dict):
            continue
        cleaned = []
        for saved_item in products.values():
            if not isinstance(saved_item, dict):
                continue
            saved_item["title"] = clean_product_title(saved_item.get("title", ""))
            if is_valid_event({
                "category": saved_item.get("category"),
                "title": saved_item.get("title", ""),
                "pokemon_scoped": bool(saved_item.get("pokemon_scoped")),
            }):
                cleaned.append(saved_item)
        unique = deduplicate_products(cleaned)
        normalized_products = {}
        for item in unique:
            key = item.get("url") or item.get("sku") or normalize_match_text(item.get("title", ""))
            if key:
                normalized_products[key] = item
        source_state["products"] = normalized_products
        # This is the size of the retained catalogue, not the number confirmed
        # in the latest scan. Per-source current_items_found reports freshness.
        source_state["last_item_count"] = len(normalized_products)
    return state



# Histories from the earlier category-split setup are folded into the one broad
# retailer catalog where possible. This preserves product history while removing
# the old scheduled routes from the active scan list.
LEGACY_SOURCE_MERGES = {
    "pokemon-center-plush": ["pokemon-center-plush-new-releases"],
    "target-tcg": ["target-tcg-new-arrivals", "target-plush", "target-plush-new-arrivals"],
    "walmart-tcg": ["walmart-tcg-newest", "walmart-plush", "walmart-plush-newest"],
    "best-buy-pokemon-tcg": ["best-buy-pokemon-tcg-new-arrivals", "best-buy-pokemon-tcg-coming-soon"],
    "amazon-pokemon-products": ["amazon-pokemon-tcg", "amazon-pokemon-plush", "amazon-pokemon-figures"],
}
LEGACY_CATEGORIES = {
    "pokemon-center-plush-new-releases": "plush",
    "target-tcg-new-arrivals": "tcg", "target-plush": "plush", "target-plush-new-arrivals": "plush",
    "walmart-tcg-newest": "tcg", "walmart-plush": "plush", "walmart-plush-newest": "plush",
    "best-buy-pokemon-tcg-new-arrivals": "tcg", "best-buy-pokemon-tcg-coming-soon": "tcg",
    "amazon-pokemon-tcg": "tcg", "amazon-pokemon-plush": "plush", "amazon-pokemon-figures": "collectibles",
}


def merge_legacy_source_histories(state: dict, sources: list[dict]) -> None:
    items = state.setdefault("items", {})
    source_by_id = {source["id"]: source for source in sources}
    for target_id, legacy_ids in LEGACY_SOURCE_MERGES.items():
        target_source = source_by_id.get(target_id)
        if not target_source:
            continue
        target = items.setdefault(target_id, {})
        products = target.get("products") if isinstance(target.get("products"), dict) else {}
        products = dict(products)
        initialized = bool(target.get("initialized"))
        last_success_values = [str(target.get("last_success") or "")]
        for legacy_id in legacy_ids:
            legacy = items.get(legacy_id)
            if not isinstance(legacy, dict):
                continue
            initialized = initialized or bool(legacy.get("initialized"))
            last_success_values.append(str(legacy.get("last_success") or ""))
            old_products = legacy.get("products") if isinstance(legacy.get("products"), dict) else {}
            for old_key, raw_item in old_products.items():
                if not isinstance(raw_item, dict):
                    continue
                item = dict(raw_item)
                fallback_category = LEGACY_CATEGORIES.get(legacy_id, target_source.get("category", "collectibles"))
                item["category"] = item.get("category") or infer_category(item.get("title", ""), fallback_category)
                item["retailer_key"] = target_source.get("retailer_key") or target_id
                product_key = item.get("url") or item.get("sku") or old_key or normalize_match_text(item.get("title", ""))
                if not product_key:
                    continue
                previous = products.get(product_key)
                if not previous or str(item.get("last_seen", "")) >= str(previous.get("last_seen", "")):
                    products[product_key] = item
        target["products"] = products
        target["initialized"] = initialized
        target["source_url"] = target_source.get("url", target.get("source_url", ""))
        target["last_item_count"] = len(products)
        target["last_success"] = max(last_success_values, default="")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/sources.json")
    parser.add_argument("--state", default="docs/data/state.json")
    args = parser.parse_args()
    config_path, state_path = Path(args.config), Path(args.state)
    config = read_json(config_path, {})
    state = read_json(state_path, {
        "schema_version": 1,
        "last_checked": None,
        "items": {},
        "source_status": [],
        "events": [],
        "pending_email": [],
        "email_status": "Not configured",
        "subscriber_delivery_status": "Not configured",
    })
    settings = config.get("settings", {})
    sources = [s for s in config.get("sources", []) if s.get("enabled", True)]
    merge_legacy_source_histories(state, sources)
    state = migrate_state(state)
    if not sources:
        raise SystemExit("No enabled sources found in config/sources.json")
    active_source_ids = {source["id"] for source in sources}
    state["items"] = {
        source_id: source_state for source_id, source_state in state.get("items", {}).items()
        if source_id in active_source_ids
    }

    session = make_session(settings.get("user_agent", "PokeDropWatch/1.0"))
    source_status = []
    new_events = []
    failures = 0
    warnings = 0
    for source in sources:
        try:
            events, result = scan_source(session, source, settings, state)
            state.setdefault("items", {})[source["id"]] = result["state"]
            source_status.append(result["status"])
            new_events.extend(events)
            if result["status"].get("status") == "warning":
                warnings += 1
                print(f"WARNING {source['id']}: {result['status']['message']}")
            else:
                print(f"OK {source['id']}: {result['status']['items_found']} current item(s), {len(events)} alert(s)")
        except Exception as exc:
            failures += 1
            prior = next((x for x in state.get("source_status", []) if x.get("id") == source["id"]), {})
            last_known_items = state.get("items", {}).get(source["id"], {}).get("last_item_count", prior.get("items_found", 0))
            failure_message = f"Request failed: {str(exc)[:210]}"
            source_status.append({
                "id": source["id"],
                "name": source.get("name", source["id"]),
                "retailer": source.get("retailer", ""),
                "retailer_key": source.get("retailer_key", ""),
                "category": source.get("category", ""),
                "type": source.get("type", ""),
                "url": source.get("url", ""),
                "status": "error",
                "last_checked": utc_now(),
                "items_found": 0,
                "current_items_found": 0,
                "last_known_items": last_known_items,
                "new_alerts": 0,
                "successful_urls": 0,
                "configured_urls": 1 + len(source.get("alternate_urls", [])) + (1 if source.get("id") == "pokebeach-news" else 0),
                "available_urls": 1 + len(source.get("alternate_urls", [])) + (1 if source.get("id") == "pokebeach-news" else 0),
                "attempted_urls": 0,
                "message": failure_message,
                "notes": source.get("notes", ""),
            })
            print(f"ERROR {source['id']}: {exc}", file=sys.stderr)

    # Collapse duplicate product/event alerts if a broad page repeats a listing.
    new_events = deduplicate_events(new_events)
    state["last_checked"] = utc_now()
    state["source_status"] = source_status
    email_events = [event for event in new_events if is_email_eligible_event(event)]
    all_events = email_events + state.get("pending_email", [])
    pending = {}
    for event in all_events:
        pending[event["id"]] = event
    pending_events = list(pending.values())
    state["events"] = (new_events + state.get("events", []))[:int(settings.get("history_limit", 100))]

    owner_recipient_configured = bool(os.environ.get("ALERT_EMAIL", "").strip())
    if pending_events and owner_recipient_configured:
        try:
            sent, message = send_email(pending_events, os.environ, settings.get("email_digest_subject_prefix", "PokéDrop Watch"))
        except Exception as exc:
            sent, message = False, f"Email send failed and will be retried ({type(exc).__name__})."
        if sent:
            sent_ids = {event["id"] for event in pending_events}
            for event in state["events"]:
                if event.get("id") in sent_ids:
                    event["email_sent"] = True
            state["pending_email"] = []
            state["email_status"] = message
        else:
            state["pending_email"] = pending_events[:100]
            state["email_status"] = message
    elif pending_events:
        state["pending_email"] = []
        state["email_status"] = "Owner-only alert copy is not configured."
    else:
        state["pending_email"] = []
        state["email_status"] = "No new personal alerts in this scan."

    state["subscriber_delivery_status"] = dispatch_subscriber_notifications(
        email_events,
        os.environ,
        settings.get("email_digest_subject_prefix", "PokéDrop Watch"),
    )

    product_sources = {source["id"]: source for source in sources if source.get("type") in {"catalog", "product"}}
    tracked_product_keys = set()
    for source_id, source in product_sources.items():
        products = state.get("items", {}).get(source_id, {}).get("products", {})
        if not isinstance(products, dict):
            continue
        fallback_retailer = source.get("retailer_key") or source.get("retailer") or source_id
        for product in products.values():
            if not isinstance(product, dict):
                continue
            title_key = normalize_match_text(product.get("title", ""))
            retailer = normalize_match_text(product.get("retailer_key") or fallback_retailer)
            if title_key:
                tracked_product_keys.add((retailer, title_key))

    current_listings = sum(
        int(item.get("current_items_found", item.get("items_found", 0)) or 0)
        for item in source_status
        if item.get("type") in {"catalog", "product"}
    )
    state["summary"] = {
        "enabled_sources": len(sources),
        "retailer_groups": len({source.get("retailer_key") or source.get("retailer") or source["id"] for source in sources}),
        "successful_sources": sum(1 for item in source_status if item["status"] == "ok"),
        "failed_sources": failures,
        "warning_sources": warnings,
        "new_alerts": len(email_events),
        "first_seen": sum(1 for event in new_events if event.get("type") == "first_seen"),
        "new_items": sum(1 for event in new_events if event.get("type") == "new_item"),
        "tracked_products": len(tracked_product_keys),
        "current_listings_found": current_listings,
    }
    write_json(state_path, state)
    print(
        f"Finished: {len(email_events)} emailed alert(s), "
        f"{state['summary']['new_items']} new item(s), "
        f"{state['summary']['first_seen']} first-seen item(s), "
        f"{failures} source error(s), {warnings} source warning(s). {state['email_status']} "
        f"Subscriber delivery: {state['subscriber_delivery_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
