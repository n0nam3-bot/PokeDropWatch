#!/usr/bin/env python3
"""Run one scan cycle and persist dashboard state."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Install retailer/date recovery extensions before importing scanner symbols.
import engine_patch  # noqa: F401
import engine_recovery_patch  # noqa: F401
import source_diagnostics_patch  # noqa: F401 - improve GameStop PDP detection and label access blocks
import trainer_preferences_patch  # noqa: F401
import baseline_patch  # noqa: F401 - suppress stale first-seen bursts on changed catalog scopes
import news_source_patch  # noqa: F401 - persist current RSS articles for the homepage
from engine import (
    clean_product_title, deduplicate_products, is_valid_event, make_session,
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
        source_state["last_item_count"] = len(normalized_products)
    return state



def count_saved_product_records(sources: list[dict], items: dict) -> int:
    """Count distinct saved product records, including last-known records."""
    identities = set()
    for source in sources:
        if source.get("type") not in {"catalog", "product"}:
            continue
        source_state = items.get(source.get("id"), {}) if isinstance(items, dict) else {}
        products = source_state.get("products", {}) if isinstance(source_state, dict) else {}
        if not isinstance(products, dict):
            continue
        fallback_retailer = source.get("retailer_key") or normalize_match_text(
            source.get("retailer") or source.get("name") or "other"
        ).replace(" ", "-")
        for product in products.values():
            if not isinstance(product, dict):
                continue
            title = normalize_match_text(product.get("title", ""))
            retailer = product.get("retailer_key") or fallback_retailer
            retailer = normalize_match_text(retailer).replace(" ", "-")
            if title:
                identities.add((retailer, title))
    return len(identities)



OBSOLETE_EXPERIMENT_FILES = (
    "monitor/broad_source_patch.py",
    "monitor/engine_retailer_group_patch.py",
    "docs/source-groups.js",
    "docs/source-groups.css",
    "docs/RETAILER_SCAN_DESIGN.md",
    "docs/RETAILER_SCAN_HEALTH.html",
    "tests/test_conditional_retailer_routes.py",
    "docs/news.css",
)

def cleanup_obsolete_experiment_files(repo_root: Path) -> None:
    """Remove only the known, unreferenced route-rotation experiment leftovers."""
    root = repo_root.resolve()
    for relative in OBSOLETE_EXPERIMENT_FILES:
        target = (root / relative).resolve()
        if root not in target.parents:
            continue
        if target.is_file():
            target.unlink()


def refresh_public_source_health_guide(repo_root: Path) -> None:
    """Refresh the existing guide's interval, status, and saved-count explanations."""
    guide = repo_root / "docs" / "SOURCE_HEALTH.html"
    if not guide.is_file():
        return
    content = guide.read_text(encoding="utf-8")
    old_schedule = (
        "The GitHub Actions workflow is scheduled to start every 15 minutes. A scan timestamp changes only after the monitor completes and writes a new dashboard state. "
        "The workflow runs its automated tests before scanning; when a test fails, the scan and email-digest step is skipped, so the dashboard keeps showing the last successful scan time."
    )
    new_schedule = (
        "The GitHub Actions workflow is configured to start every 15 minutes. This is the intended interval, not a guarantee that GitHub will start every scheduled run exactly on time. "
        "ZIP uploads and manual workflow runs also trigger scans. The Last checked timestamp records the latest completed monitor run and identifies whether it was a scheduled check, ZIP upload, or manual run. "
        "The scan step is configured to run even when automated tests fail, so a red workflow can still have refreshed the dashboard."
    )
    content = content.replace(old_schedule, new_schedule)
    partial_row = (
        '<tr><td><span class="health-pill nomatch">PARTIAL</span></td>'
        '<td>Only some configured URLs responded or produced usable results.</td>'
        '<td>Some coverage is available, but this source was not fully checked. Failed or blocked alternate routes may hide additional listings.</td></tr>\n            '
    )
    blocked_row = (
        '<tr><td><span class="health-pill issue">BLOCKED</span></td>'
        '<td>The retailer returned an access-protection or bot-check page.</td>'
        '<td>The HTTP request may have returned a page successfully, but it did not expose usable inventory. This is not a normal parser miss.</td></tr>\n            '
    )
    no_match_marker = '<tr><td><span class="health-pill nomatch">NO MATCH</span>'
    if partial_row.splitlines()[0] not in content and no_match_marker in content:
        content = content.replace(no_match_marker, partial_row + blocked_row + no_match_marker, 1)
    content = content.replace("<strong>Listings seen</strong>", "<strong>Products tracked</strong>")
    content = content.replace(
        "The number of distinct product records in the latest saved catalog after normalization and duplicate handling.",
        "The number of distinct saved product records across retailer catalogs. This includes last-known listings when a source is blocked or its latest request fails.",
    )
    if content != guide.read_text(encoding="utf-8"):
        guide.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/sources.json")
    parser.add_argument("--state", default="docs/data/state.json")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    cleanup_obsolete_experiment_files(repo_root)
    refresh_public_source_health_guide(repo_root)
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
    state = migrate_state(state)
    sources = [s for s in config.get("sources", []) if s.get("enabled", True)]
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
                print(f"OK {source['id']}: {result['status']['items_found']} relevant item(s), {len(events)} alert(s)")
        except Exception as exc:
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
                "successful_urls": 0,
                "configured_urls": min(4, 1 + len(source.get("alternate_urls", []))),
                "message": f"All configured URLs failed: {str(exc)[:210]}",
                "notes": source.get("notes", ""),
            })
            print(f"ERROR {source['id']}: {exc}", file=sys.stderr)

    state["last_checked"] = utc_now()
    state["last_trigger"] = os.environ.get("GITHUB_EVENT_NAME", "manual/local")
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

    state["summary"] = {
        "enabled_sources": len(sources),
        "successful_sources": sum(1 for item in source_status if item["status"] == "ok"),
        "failed_sources": failures,
        "warning_sources": warnings,
        "new_alerts": len(email_events),
        "first_seen": sum(1 for event in new_events if event.get("type") == "first_seen"),
        "new_items": sum(1 for event in new_events if event.get("type") == "new_item"),
        "tracked_products": count_saved_product_records(sources, state.get("items", {})),
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
