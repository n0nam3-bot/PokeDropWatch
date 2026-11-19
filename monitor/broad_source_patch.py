"""Primary-first source scanning with conditional backups.

Each retailer is queried once per 15-minute scan. A backup URL is requested only
when the primary fails, is blocked, or produces no usable current records.
"""
from __future__ import annotations

import copy
import re
from typing import Any

import requests
import engine
import engine_recovery_patch as recovery

_BASE_SCAN = engine.scan_source


def _candidates(source: dict[str, Any]) -> list[str]:
    values = [source.get("url", ""), *(source.get("alternate_urls") or [])]
    # PokéBeach's homepage is a last-resort HTML article-list fallback. It is
    # deliberately not added to every scan unless the feed and REST endpoint fail.
    if source.get("id") == "pokebeach-news":
        values.append("https://www.pokebeach.com/")
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        url = str(value or "").strip()
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _attempt_state(state: dict[str, Any], source_id: str, candidate_url: str) -> dict[str, Any]:
    candidate_state = copy.deepcopy(state)
    old = (candidate_state.setdefault("items", {})).get(source_id)
    if isinstance(old, dict):
        # Preserve both product and RSS/article baselines across fallback URLs.
        old["source_url"] = candidate_url
    return candidate_state


def scan_source_primary_first(session, source: dict[str, Any], settings: dict[str, Any], state: dict[str, Any]):
    candidates = _candidates(source)
    if not candidates:
        raise requests.RequestException(f"No usable URL is configured for {source.get('id', 'source')}.")

    attempts: list[dict[str, Any]] = []
    best: tuple[list[dict[str, Any]], dict[str, Any], int] | None = None
    exceptions: list[str] = []
    selected = None

    for index, url in enumerate(candidates):
        candidate = dict(source)
        candidate["url"] = url
        candidate["alternate_urls"] = []
        # Prevent the older recovery adapter from auto-adding the homepage itself;
        # this adapter controls the fallback order and only attempts it on a miss.
        candidate["notes"] = str(source.get("notes", "")).replace("wp_die", "feed error")
        attempt_state = _attempt_state(state, source["id"], url)
        recovery._FETCH_DIAGNOSTICS.clear()
        try:
            events, result = _BASE_SCAN(session, candidate, settings, attempt_state)
            diagnostics = copy.deepcopy(recovery._FETCH_DIAGNOSTICS)
            status = result.get("status", {})
            count = int(status.get("items_found", 0) or 0)
            challenged = any(
                bool(item.get("challenge"))
                or bool(re.search(r"pardon our interruption|robot or human|verify you are human|access denied|request blocked|captcha", str(item.get("title", "")), re.I))
                or bool(re.search(r"(?:HTTPError|status|response)\D{0,8}(?:403|429)\b", str(item.get("error", "")), re.I))
                for item in diagnostics
            )
            attempts.append({"url": url, "ok": True, "challenge": challenged, "count": count, "diagnostics": diagnostics})

            if challenged:
                # A challenge shell is not evidence of product records, even if a
                # generic parser happens to mistake one of its links for a tile.
                saved = copy.deepcopy((state.get("items") or {}).get(source["id"], {}))
                saved_products = saved.get("products") if isinstance(saved.get("products"), dict) else {}
                saved_seen = saved.get("seen") if isinstance(saved.get("seen"), dict) else {}
                retained_count = max(len(saved_products), len(saved_seen), int(saved.get("last_item_count", 0) or 0))
                saved["last_item_count"] = retained_count
                result["state"] = saved
                status["items_found"] = 0
                status["current_items_found"] = 0
                status["last_known_items"] = retained_count
                status["access_challenge"] = True
                events = []

            if best is None or (count > 0 and not challenged):
                best = (events, result, index)
            if count > 0 and not challenged:
                selected = (events, result, index)
                break
        except Exception as exc:
            message = f"{type(exc).__name__}: {str(exc)[:180]}"
            exceptions.append(message)
            attempts.append({"url": url, "ok": False, "challenge": False, "count": 0, "error": message, "diagnostics": copy.deepcopy(recovery._FETCH_DIAGNOSTICS)})

    if selected is None:
        selected = best
    if selected is None:
        details = " | ".join(exceptions[:3]) or "No URL returned a usable response."
        raise requests.RequestException(f"All available source routes failed: {details}")

    events, result, selected_index = selected
    status = result.setdefault("status", {})
    result_state = result.setdefault("state", {})
    result_state["source_url"] = source["url"]
    count = int(status.get("items_found", 0) or 0)
    successful = sum(1 for attempt in attempts if attempt.get("ok"))
    failed = len(attempts) - successful
    blocked = sum(1 for attempt in attempts if attempt.get("challenge"))
    fallback_used = selected_index > 0 and count > 0
    all_diagnostics = [diag for attempt in attempts for diag in attempt.get("diagnostics", [])]

    status.update({
        "id": source["id"],
        "name": source.get("name", source["id"]),
        "retailer": source.get("retailer", ""),
        "retailer_key": source.get("retailer_key", ""),
        "category": source.get("category", "collectibles"),
        "type": source.get("type", "catalog"),
        "url": source["url"],
        "status": "ok" if count > 0 else "warning",
        "items_found": count,
        "current_items_found": count,
        "successful_urls": successful,
        "configured_urls": len(attempts),
        "attempted_urls": len(attempts),
        "available_urls": len(candidates),
        "failed_urls": failed,
        "blocked_urls": blocked,
        "fallback_used": fallback_used,
        "fallback_url": attempts[selected_index]["url"] if fallback_used else "",
        "access_challenge": bool(blocked),
        "response_health": {
            "successful": successful,
            "configured": len(attempts),
            "failed": failed,
            "partial": bool(failed or blocked or fallback_used),
        },
        "notes": source.get("notes", ""),
    })
    if fallback_used:
        status["message"] = f"Primary route did not yield usable entries; fallback recognized {count} current item(s)."
    elif count:
        status["message"] = f"{count} current Pokémon item(s) recognized from the primary route."
    elif blocked:
        status["message"] = "Retailer access protection blocked the checked route(s); no current entries were confirmed."
    else:
        status["message"] = "The checked route returned content, but no Pokémon entries were recognized."

    # Keep the raw transport/parser diagnostics for owner troubleshooting, but do
    # not surface a paragraph of stale-data caveats on the public homepage.
    status["attempt_diagnostics"] = [
        {key: value for key, value in item.items() if key in {"url", "error", "title", "bytes", "challenge", "product_links", "json_scripts"}}
        for item in all_diagnostics[:8]
    ]
    return events, result


engine.scan_source = scan_source_primary_first
