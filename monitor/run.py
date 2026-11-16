#!/usr/bin/env python3
"""Run one scan cycle and persist dashboard state."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from engine import make_session, scan_source, send_email, utc_now


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
    })
    settings = config.get("settings", {})
    sources = [s for s in config.get("sources", []) if s.get("enabled", True)]
    if not sources:
        raise SystemExit("No enabled sources found in config/sources.json")

    session = make_session(settings.get("user_agent", "PokeDropWatch/1.0"))
    source_status = []
    new_events = []
    failures = 0
    for source in sources:
        try:
            events, result = scan_source(session, source, settings, state)
            state.setdefault("items", {})[source["id"]] = result["state"]
            source_status.append(result["status"])
            new_events.extend(events)
            print(f"OK {source['id']}: {result['status']['items_found']} item(s), {len(events)} alert(s)")
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
                "items_found": prior.get("items_found", 0),
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

    if pending_events:
        try:
            sent, message = send_email(pending_events, os.environ, settings.get("email_digest_subject_prefix", "PokéDrop Watch"))
        except Exception as exc:
            sent, message = False, f"Email send failed and will be retried: {str(exc)[:240]}"
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
    else:
        state["pending_email"] = []
        state["email_status"] = "No new alerts in this scan."

    product_source_ids = {source["id"] for source in sources if source.get("type") in {"catalog", "product"}}
    state["summary"] = {
        "enabled_sources": len(sources),
        "successful_sources": sum(1 for x in source_status if x["status"] == "ok"),
        "failed_sources": failures,
        "new_alerts": len(new_events),
        "tracked_products": sum(state.get("items", {}).get(source_id, {}).get("last_item_count", 0) for source_id in product_source_ids),
    }
    write_json(state_path, state)
    print(f"Finished: {len(new_events)} new alert(s), {failures} source failure(s). {state['email_status']}")
    # A partial source failure is visible in the dashboard; it should not discard successful scans.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
