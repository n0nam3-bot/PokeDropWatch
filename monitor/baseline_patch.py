"""Ensure changed or first-time catalog scopes seed quietly before alerts."""
from __future__ import annotations

import engine

_previous_scan_source = engine.scan_source


def scan_source_with_quiet_baseline(session, source, settings, state):
    previous = (state.get("items") or {}).get(source.get("id"), {})
    source_url_changed = bool(
        previous.get("source_url")
        and previous.get("source_url") != source.get("url")
    )
    needs_baseline = not bool(previous.get("initialized")) or source_url_changed
    events, result = _previous_scan_source(session, source, settings, state)
    if needs_baseline:
        # Keep explicit, date-verified new-item events; suppress unverified
        # first-seen listings when a search URL changes its scope.
        events = [event for event in events if event.get("type") != "first_seen"]
    return events, result


engine.scan_source = scan_source_with_quiet_baseline
