#!/usr/bin/env python3
"""Run one scan cycle and persist dashboard state."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from engine import clean_product_title, is_valid_event, make_session, scan_source, send_email, utc_now
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
    # Normalize older retailer card labels before filtering legacy events.
    # This removes wrappers such as "Deal," and embedded price text without
    # changing the underlying product URL or generating a new alert.
    for event in state.get("events", []):
        if event.get("type") != "news":
            event["title"] = clean_product_title(event.get("title", ""))
    for event in state.get("pending_email", []):
        if event.get("type") != "news":
            event["title"] = clean_product_title(event.get("title", ""))
    # News items are retained because a configured Pokémon news feed is already scoped.
    state["events"] = [event for event in state.get("events", []) if is_valid_event(event)]
    state["pending_email"] = [event for event in state.get("pending_email", []) if is_valid_event(event)]
    # Scrub old loose-parser product baselines too, including sources that may fail
    # this run, so historic noise cannot inflate the public tracked-products count.
    for source_state in state.get("items", {}).values():
        products = source_state.get("products")
        if isinstance(products, dict):
            for saved_item in products.values():
                if isinstance(saved_item, dict):
                    saved_item["title"] = clean_product_title(saved_item.get("title", ""))
            products = {
                key: item for key, item in products.items()
                if is_valid_event({"category": item.get("category"), "title": item.get("title", "")})
            }
            source_state["products"] = products
            source_state["last_item_count"] = len(products)
    sources = [s for s in config.get("sources", []) if s.get("enabled", True)]
    if not sources:
        raise SystemExit("No enabled sources found in config/sources.json")
    # Remove baselines for retired/disabled source IDs; otherwise old products from
    # a renamed source could appear indefinitely in the public tracked-products view.
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
                print(f"OK {source['id']}: {result['status']['items_found']} relevant item(s), {len(events)} alert(s)")
        except Exception as exc:  # one blocked source must not prevent other stores from scanning
            failures += 1
            prior = next((x for x in state.get("source_status", []) if x.get("id") == source["id"]), {})
            source_status.append({
                "id": source["id"],
                "name": source.get("name", source["id"]),
                "retailer": source.get("retailer", ""),
                "type": source.get("type", ""),
                "url": source.get("url", ""),
                "status": "error",
                "last_checked": utc_now(),
                "items_found": state.get("items", {}).get(source["id"], {}).get("last_item_count", prior.get("items_found", 0)),
                "new_alerts": 0,
                "message": f"Scan failed: {str(exc)[:240]}",
                "notes": source.get("notes", ""),
            })
            print(f"ERROR {source['id']}: {exc}", file=sys.stderr)

    state["last_checked"] = utc_now()
    state["source_status"] = source_status
    all_events = new_events + state.get("pending_email", [])
    # Deduplicate pending events by event ID while preserving order.
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
        # Do not accumulate a personal digest backlog when no personal recipient is configured.
        # Subscriber events are queued privately per active subscriber below.
        state["pending_email"] = []
        state["email_status"] = "Owner-only alert copy is not configured."
    else:
        state["pending_email"] = []
        state["email_status"] = "No new personal alerts in this scan."

    state["subscriber_delivery_status"] = dispatch_subscriber_notifications(
        new_events,
        os.environ,
        settings.get("email_digest_subject_prefix", "PokéDrop Watch"),
    )

    product_source_ids = {source["id"] for source in sources if source.get("type") in {"catalog", "product"}}
    state["summary"] = {
        "enabled_sources": len(sources),
        "successful_sources": sum(1 for x in source_status if x["status"] == "ok"),
        "failed_sources": failures,
        "warning_sources": warnings,
        "new_alerts": len(new_events),
        "tracked_products": sum(state.get("items", {}).get(source_id, {}).get("last_item_count", 0) for source_id in product_source_ids),
    }
    write_json(state_path, state)
    print(f"Finished: {len(new_events)} new alert(s), {failures} source error(s), {warnings} source(s) with no recognized Pokémon results. {state['email_status']} Subscriber delivery: {state['subscriber_delivery_status']}")
    # A partial source failure is visible in the dashboard; it should not discard successful scans.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
