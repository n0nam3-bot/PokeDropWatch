"""Conditional retailer route failover and retailer-specific product validation.

Each configured category remains an independent source/state record. The primary
route is requested first; alternate routes are tried only when the primary is
blocked, fails, or yields no recognized current listings. Identical URLs are
fetched once per scan process and shared across category sources.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

import engine
import engine_patch
import engine_recovery_patch as recovery


# The recovery adapter is already installed by run.py. Reuse it one route at a
# time so its existing parser/date/state behavior remains the source of truth.
_BASE_SCAN = engine.scan_source
_BASE_FETCH = engine.fetch
_BASE_TITLE_ALLOWED = recovery._pokemon_title_allowed
_BASE_PRODUCT_URL = recovery._same_host_product_url
_FETCH_CACHE: dict[str, tuple[str, Any]] = {}

_GENERIC_NAV_TITLE_RE = re.compile(
    r"^(?:currently\s+refined\s+by(?:\s+category)?\s*:?.*|"
    r"refine(?:d)?\s+by.*|filters?\s*:?.*|sort(?:ed)?\s+by.*|"
    r"(?:trading|collectible)\s+card\s+games?|category\s+results?|"
    r"shop\s+all(?:\s+pokemon)?|pokemon\s+products?)$",
    re.I,
)


def _strict_title_allowed(title: str) -> bool:
    cleaned = engine.clean_product_title(title)
    if not cleaned or _GENERIC_NAV_TITLE_RE.fullmatch(cleaned.strip()):
        return False
    normalized = engine.normalize_match_text(cleaned)
    if normalized in {
        "trading card games", "trading cards", "pokemon", "pokemon products",
        "currently refined by category trading card games",
    }:
        return False
    return bool(_BASE_TITLE_ALLOWED(cleaned))


def _strict_product_url(raw_url: str, base_url: str, retailer_key: str) -> str:
    absolute = urljoin(base_url, raw_url or "")
    parsed = urlparse(absolute)
    path = parsed.path.lower().rstrip("/") or "/"
    # Exclude known retailer navigation/tracking destinations that can otherwise
    # be mistaken for a product card when category pages are Pokémon-scoped.
    if path == "/sp/track" or path.startswith("/sp/track/"):
        return ""
    if retailer_key == "gamestop" and path in {
        "/toys-games",
        "/toys-games/trading-cards",
        "/toys-games/trading-cards/trading-card-games",
    }:
        return ""
    if path in {"/search", "/browse", "/category", "/categories", "/cart", "/account", "/help"}:
        return ""
    return _BASE_PRODUCT_URL(raw_url, base_url, retailer_key)


# The recovery adapter resolves these names when extracting each candidate.
recovery._pokemon_title_allowed = _strict_title_allowed
recovery._same_host_product_url = _strict_product_url


_BASE_RETAILER_EXTRACTOR = engine.extract_retailer_products
_BASE_JSON_EXTRACTOR = engine.extract_json_products


def extract_retailer_products_strict(soup, base_url: str, retailer: str, limit: int):
    products = _BASE_RETAILER_EXTRACTOR(soup, base_url, retailer, limit)
    retailer_key = engine._retailer_key(retailer)
    accepted = []
    for item in products:
        title = engine.clean_product_title(item.get("title", ""))
        url = _strict_product_url(item.get("url", ""), base_url, retailer_key)
        if not _strict_title_allowed(title) or not url:
            continue
        item["title"] = title
        item["url"] = url
        accepted.append(item)
    return engine.deduplicate_products(accepted)[:limit]


def extract_json_products_strict(payload: Any, base_url: str, retailer: str):
    products = _BASE_JSON_EXTRACTOR(payload, base_url, retailer)
    retailer_key = engine._retailer_key(retailer)
    accepted = []
    for item in products:
        title = engine.clean_product_title(item.get("title", ""))
        url = _strict_product_url(item.get("url", ""), base_url, retailer_key)
        if not _strict_title_allowed(title) or not url:
            continue
        item["title"] = title
        item["url"] = url
        accepted.append(item)
    return engine.deduplicate_products(accepted)


engine.extract_retailer_products = extract_retailer_products_strict
engine.extract_json_products = extract_json_products_strict


def _cached_fetch(session, url: str, timeout: int):
    """Cache identical URLs for this one scan run, including failed attempts."""
    cached = _FETCH_CACHE.get(url)
    if cached:
        kind, value = cached
        if kind == "error":
            error_type, message = value
            recovery._FETCH_DIAGNOSTICS.append({
                "url": url,
                "error": f"{error_type}: {message}",
                "cached": True,
            })
            raise requests.RequestException(f"Cached {error_type}: {message}")
        body, final_url = value
        diagnostic = recovery._response_diagnostic(body, final_url)
        diagnostic["url"] = url
        diagnostic["cached"] = True
        recovery._FETCH_DIAGNOSTICS.append(diagnostic)
        return body, final_url

    try:
        body, final_url = _BASE_FETCH(session, url, timeout)
    except Exception as exc:
        message = str(exc)[:180]
        _FETCH_CACHE[url] = ("error", (type(exc).__name__, message))
        raise
    _FETCH_CACHE[url] = ("response", (body, final_url))
    return body, final_url


engine.fetch = _cached_fetch

def _utc_datetime() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _retailer_key(source: dict[str, Any]) -> str:
    value = source.get("retailer_key") or engine._retailer_key(
        str(source.get("retailer") or source.get("name") or source.get("id") or "other")
    )
    return engine.normalize_match_text(value).replace(" ", "-") or "other"


def _cooldown_record(state: dict[str, Any], retailer_key: str) -> dict[str, Any] | None:
    records = state.get("retailer_health")
    record = records.get(retailer_key) if isinstance(records, dict) else None
    if not isinstance(record, dict):
        return None
    until = _timestamp(record.get("cooldown_until"))
    if not until or until <= _utc_datetime():
        if isinstance(records, dict):
            records.pop(retailer_key, None)
        return None
    return record


def _set_retailer_cooldown(
    state: dict[str, Any], source: dict[str, Any], kind: str, minutes: int, message: str,
) -> None:
    retailer_key = _retailer_key(source)
    now = _utc_datetime()
    until = now + timedelta(minutes=max(1, min(int(minutes), 240)))
    records = state.get("retailer_health")
    if not isinstance(records, dict):
        records = {}
        state["retailer_health"] = records
    records[retailer_key] = {
        "kind": kind,
        "last_checked": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cooldown_until": until.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_id": source.get("id", ""),
        "message": message[:220],
    }


def _cooldown_result(source: dict[str, Any], state: dict[str, Any], candidates: list[str], record: dict[str, Any]):
    source_id = source["id"]
    source_state = copy.deepcopy((state.get("items") or {}).get(source_id, {}))
    products = source_state.get("products") if isinstance(source_state.get("products"), dict) else {}
    seen_articles = source_state.get("seen") if isinstance(source_state.get("seen"), dict) else {}
    retained = max(len(products), len(seen_articles), int(source_state.get("last_item_count", 0) or 0))
    until = str(record.get("cooldown_until") or "")
    kind = str(record.get("kind") or "retailer access")
    kind_label = "access protection" if kind == "access-challenge" else "request failure"
    retained_label = "article(s)" if source.get("type") == "rss" else "listing(s)"
    message = f"Skipped this category route during the retailer {kind_label} cooldown until {until}. No retailer request was made."
    if retained:
        message += f" {retained} last-known {retained_label} retained; current entries were not confirmed."
    status = {
        "id": source_id,
        "name": source.get("name", source_id),
        "retailer": source.get("retailer", ""),
        "retailer_key": _retailer_key(source),
        "category": source.get("category", "news" if source.get("type") == "rss" else "collectibles"),
        "type": source.get("type", "catalog"),
        "url": source.get("url", candidates[0] if candidates else ""),
        "response_url": "",
        "status": "warning",
        "last_checked": engine.utc_now(),
        "items_found": 0,
        "current_items_found": 0,
        "last_known_items": retained,
        "new_alerts": 0,
        "successful_urls": 0,
        "configured_urls": 0,
        "attempted_urls": 0,
        "available_urls": len(candidates),
        "http_responses": 0,
        "blocked_urls": 0,
        "failed_urls": 0,
        "skipped_urls": len(candidates),
        "skipped_due_retailer_cooldown": True,
        "cooldown_kind": kind,
        "cooldown_until": until,
        "response_health": {"successful": 0, "configured": 0, "failed": 0, "partial": True},
        "message": message[:900],
        "notes": source.get("notes", ""),
    }
    if source.get("type") in {"catalog", "product"}:
        source_state["last_item_count"] = retained
    return [], {"state": source_state, "status": status}


def _candidate_urls(source: dict[str, Any]) -> list[str]:
    candidates = [source.get("url", ""), *(source.get("alternate_urls") or [])]
    if source.get("id") == "pokebeach-news" and "wp_die" in str(source.get("notes", "")).lower():
        candidates.append("https://www.pokebeach.com/")
    result = []
    seen = set()
    for candidate in candidates:
        candidate = str(candidate or "").strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result[:8]



def select_routes_for_interval(
    sources: list[dict[str, Any]], state: dict[str, Any], settings: dict[str, Any],
) -> set[str]:
    """Select a small round-robin slice of routes for each retailer.

    Rotation is persisted in state.json, so category searches are spread across
    successive 15-minute workflow runs instead of all being requested together.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        grouped.setdefault(_retailer_key(source), []).append(source)

    rotation = state.get("retailer_route_rotation")
    if not isinstance(rotation, dict):
        rotation = {}
        state["retailer_route_rotation"] = rotation
    try:
        per_retailer = int(settings.get("retailer_routes_per_scan", 1))
    except (TypeError, ValueError):
        per_retailer = 1
    selected: set[str] = set()
    for retailer_key, routes in grouped.items():
        route_count = len(routes)
        if route_count <= 0:
            continue
        take = max(1, min(per_retailer, route_count))
        try:
            start = int(rotation.get(retailer_key, 0)) % route_count
        except (TypeError, ValueError):
            start = 0
        for offset in range(take):
            selected.add(routes[(start + offset) % route_count]["id"])
        rotation[retailer_key] = (start + take) % route_count
    return selected


def scheduled_route_status(
    source: dict[str, Any], state: dict[str, Any], previous_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an explicit no-request status for a route outside this interval's rotation."""
    source_id = source["id"]
    source_state = (state.get("items") or {}).get(source_id, {})
    products = source_state.get("products") if isinstance(source_state.get("products"), dict) else {}
    articles = source_state.get("seen") if isinstance(source_state.get("seen"), dict) else {}
    retained = max(
        len(products), len(articles),
        int(source_state.get("last_item_count", 0) or 0),
        int((previous_status or {}).get("last_known_items", 0) or 0),
    )
    last_scanned = (
        source_state.get("last_attempt") or source_state.get("last_success")
        or (previous_status or {}).get("last_checked")
    )
    noun = "article(s)" if source.get("type") == "rss" else "listing(s)"
    message = "Scheduled for a later retailer rotation. No retailer request was made."
    if last_scanned:
        message += f" Last scanned: {last_scanned}."
    else:
        message += " This route has not been scanned yet."
    if retained:
        message += f" {retained} last-known {noun} retained; current entries were not checked this interval."
    return {
        "id": source_id,
        "name": source.get("name", source_id),
        "retailer": source.get("retailer", ""),
        "retailer_key": source.get("retailer_key") or _retailer_key(source),
        "category": source.get("category", "news" if source.get("type") == "rss" else "collectibles"),
        "type": source.get("type", "catalog"),
        "url": source.get("url", ""),
        "response_url": "",
        "status": "skipped",
        "last_checked": last_scanned,
        "items_found": 0,
        "current_items_found": 0,
        "last_known_items": retained,
        "new_alerts": 0,
        "successful_urls": 0,
        "configured_urls": 0,
        "attempted_urls": 0,
        "available_urls": len(_candidate_urls(source)),
        "http_responses": 0,
        "blocked_urls": 0,
        "failed_urls": 0,
        "skipped_urls": len(_candidate_urls(source)),
        "skipped_by_rotation": True,
        "message": message[:900],
        "notes": source.get("notes", ""),
    }

def _diagnostic_counts(diagnostics: list[dict[str, Any]]) -> tuple[bool, bool]:
    transport_ok = any("error" not in entry for entry in diagnostics)
    blocked = any(bool(entry.get("challenge")) for entry in diagnostics)
    return transport_ok, blocked


def scan_source_with_conditional_routes(session, source: dict[str, Any], settings: dict[str, Any], state: dict[str, Any]):
    """Try the primary route first and use alternates only when necessary."""
    source_id = source["id"]
    candidates = _candidate_urls(source)
    if not candidates:
        raise requests.RequestException("No source URLs are configured.")

    retailer_key = _retailer_key(source)
    cooldown = _cooldown_record(state, retailer_key)
    if cooldown:
        return _cooldown_result(source, state, candidates, cooldown)

    original_state = copy.deepcopy((state.get("items") or {}).get(source_id, {}))
    attempts: list[dict[str, Any]] = []
    preferred: dict[str, Any] | None = None
    last_exception: Exception | None = None

    for route_index, candidate_url in enumerate(candidates):
        attempt_source = dict(source)
        attempt_source["url"] = candidate_url
        attempt_source["alternate_urls"] = []
        # The recovery adapter automatically appends the PokéBeach homepage when
        # this note is present. We add it explicitly as the final candidate above.
        if source_id == "pokebeach-news":
            attempt_source["notes"] = re.sub(r"wp_die", "feed endpoint", str(source.get("notes", "")), flags=re.I)

        attempt_state = copy.deepcopy(state)
        prior_for_route = copy.deepcopy(original_state)
        # Keep the existing catalogue/baseline while preventing the underlying
        # scanner from mistaking a fallback URL for a scope change.
        if prior_for_route:
            prior_for_route["source_url"] = candidate_url
        attempt_state.setdefault("items", {})[source_id] = prior_for_route

        try:
            events, result = _BASE_SCAN(session, attempt_source, settings, attempt_state)
            diagnostics = copy.deepcopy(recovery._FETCH_DIAGNOSTICS)
            transport_ok, blocked = _diagnostic_counts(diagnostics)
            if not diagnostics:
                transport_ok = bool(result.get("status", {}).get("successful_urls", 0))
            count = int(result.get("status", {}).get("items_found", 0) or 0)
            attempt = {
                "url": candidate_url,
                "events": events,
                "result": result,
                "diagnostics": diagnostics,
                "transport_ok": transport_ok,
                "blocked": blocked,
                "count": count,
                "route_index": route_index,
            }
            attempts.append(attempt)

            # A usable primary or fallback page with recognized records is the
            # preferred result. Stop here and leave all remaining alternates idle.
            if transport_ok and not blocked and count > 0:
                preferred = attempt
                break
            # Retain the first non-challenge response as the best parser result
            # when all pages are empty or later alternates fail.
            if transport_ok and not blocked and preferred is None:
                preferred = attempt
        except Exception as exc:
            last_exception = exc
            diagnostics = copy.deepcopy(recovery._FETCH_DIAGNOSTICS)
            transport_ok, blocked = _diagnostic_counts(diagnostics)
            attempts.append({
                "url": candidate_url,
                "events": [],
                "result": None,
                "diagnostics": diagnostics,
                # A parser exception after an HTTP response is not a transport
                # failure. Keep the response and parser layers distinct.
                "transport_ok": transport_ok,
                "blocked": blocked,
                "count": 0,
                "route_index": route_index,
                "error": f"{type(exc).__name__}: {str(exc)[:180]}",
            })

    if not attempts:
        raise requests.RequestException("No source routes were attempted.")

    # Select the first valid, non-challenge response. If none exists, the final
    # result still carries challenge diagnostics and last-known catalogue state.
    chosen = preferred or next(
        (attempt for attempt in reversed(attempts) if attempt.get("result") is not None),
        None,
    )
    if chosen is None:
        # A URL can return HTTP content that a feed/parser correctly rejects
        # (for example PokéBeach's wp_die XML). Do not mislabel that as a
        # connection failure or discard its diagnostics/last-known state.
        response_attempt = next(
            (attempt for attempt in attempts if attempt["transport_ok"] and not attempt["blocked"]),
            None,
        ) or next((attempt for attempt in attempts if attempt["transport_ok"]), None)
        if response_attempt is not None:
            record_map = original_state.get("seen", {}) if source.get("type") == "rss" else original_state.get("products", {})
            retained_count = max(
                len(record_map) if isinstance(record_map, dict) else 0,
                int(original_state.get("last_item_count", 0) or 0),
            )
            noun = "article(s)" if source.get("type") == "rss" else "listing(s)"
            synthetic_state = copy.deepcopy(original_state)
            synthetic_status = {
                "id": source_id,
                "name": source.get("name", source_id),
                "retailer": source.get("retailer", ""),
                "type": source.get("type", "catalog"),
                "url": source.get("url", candidates[0]),
                "response_url": response_attempt["url"],
                "status": "warning",
                "items_found": 0,
                "current_items_found": 0,
                "last_known_items": retained_count,
                "new_alerts": 0,
                "message": f"The retailer returned page content, but the parser could not interpret it. No current entries were confirmed; {retained_count} last-known {noun} retained.",
                "notes": source.get("notes", ""),
            }
            chosen = {
                **response_attempt,
                "events": [],
                "result": {"state": synthetic_state, "status": synthetic_status},
                "count": 0,
            }
        else:
            error_messages = [attempt.get("error", "") for attempt in attempts if attempt.get("error")]
            error_names = {str(attempt.get("error", "")).split(":", 1)[0] for attempt in attempts}
            network_error_names = {
                "ConnectionError", "ConnectTimeout", "ReadTimeout", "Timeout", "HTTPError",
                "RetryError", "SSLError", "ProxyError", "RequestException",
            }
            if error_names.intersection(network_error_names):
                _set_retailer_cooldown(
                    state, source, "request-failure",
                    int(settings.get("retailer_request_cooldown_minutes", 15)),
                    "All available source routes failed at the request layer.",
                )
            raise requests.RequestException(
                "All available source routes failed. " + " | ".join(error_messages[:3])
            ) from last_exception

    result = chosen["result"]
    events = chosen["events"]
    result_state = result.get("state", {})
    status = result.get("status", {})
    attempted_count = len(attempts)
    http_count = sum(1 for attempt in attempts if attempt["transport_ok"])
    blocked_count = sum(1 for attempt in attempts if attempt["blocked"])
    usable_count = sum(1 for attempt in attempts if attempt["transport_ok"] and not attempt["blocked"])
    failed_count = attempted_count - http_count
    fallback_used = chosen["route_index"] > 0
    current_count = int(chosen.get("count", 0) or 0)

    # Keep current and retained inventory distinct. A challenge/parser miss must
    # never erase prior records or imply that the retailer has no stock.
    record_noun = "article" if source.get("type") == "rss" else "listing"
    if source.get("type") in {"catalog", "product"}:
        saved_products = result_state.get("products") if isinstance(result_state.get("products"), dict) else {}
        old_products = original_state.get("products") if isinstance(original_state.get("products"), dict) else {}
        retained_count = max(
            len(saved_products),
            len(old_products),
            int(original_state.get("last_item_count", 0) or 0),
        )
        status["current_items_found"] = current_count
        if current_count == 0 and retained_count:
            result_state["last_item_count"] = retained_count
            status["last_known_items"] = retained_count
            status["message"] = (
                str(status.get("message", ""))
                + f" Last-known catalog retained: {retained_count} listing(s); this scan did not confirm current inventory."
            )[:900]
        elif current_count > 0:
            result_state["last_item_count"] = current_count
    elif source.get("type") == "rss":
        saved_articles = result_state.get("seen") if isinstance(result_state.get("seen"), dict) else {}
        old_articles = original_state.get("seen") if isinstance(original_state.get("seen"), dict) else {}
        retained_count = max(
            len(saved_articles), len(old_articles),
            int(original_state.get("last_item_count", 0) or 0),
        )
        status["current_items_found"] = current_count
        if current_count == 0 and retained_count:
            result_state["last_item_count"] = retained_count
            status["last_known_items"] = retained_count
    else:
        status["current_items_found"] = current_count

    # A challenge response is not a usable page, even when HTTP returned 200.
    # successful_urls counts non-challenge HTTP responses; parser recognition is
    # reported separately through current_items_found and the route status.
    status["successful_urls"] = usable_count
    status["configured_urls"] = attempted_count
    status["attempted_urls"] = attempted_count
    status["available_urls"] = len(candidates)
    status["http_responses"] = http_count
    status["blocked_urls"] = blocked_count
    status["failed_urls"] = failed_count
    status["fallbacks_available"] = max(0, len(candidates) - 1)
    status["fallbacks_used"] = max(0, chosen["route_index"])
    status["fallback_used"] = fallback_used
    status["response_health"] = {
        "successful": usable_count,
        "configured": attempted_count,
        "failed": failed_count + blocked_count,
        "partial": bool(blocked_count or failed_count or fallback_used),
    }

    all_diagnostics = [entry for attempt in attempts for entry in attempt.get("diagnostics", [])]
    status["parser_diagnostics"] = []
    for entry in all_diagnostics[:5]:
        if "error" in entry:
            detail = f"{entry.get('url', '')}: {str(entry['error'])[:100]}"
        else:
            detail = f"{entry.get('url', '')}: {round(int(entry.get('bytes', 0)) / 1024)} KB"
            if entry.get("title"):
                detail += f", title={str(entry['title'])[:45]}"
            detail += f", product-like links={entry.get('product_links', 0)}, JSON blocks={entry.get('json_scripts', 0)}"
            if entry.get("challenge"):
                detail += ", access-challenge page"
            if entry.get("cached"):
                detail += ", reused within this scan"
        status["parser_diagnostics"].append(detail[:220])

    if current_count > 0:
        if blocked_count:
            message = (
                f"Recovered {current_count} current {record_noun}(s) through a fallback route after "
                f"{blocked_count} route(s) returned retailer access challenges."
            )
        elif fallback_used:
            message = (
                f"Recognized {current_count} current {record_noun}(s) through a fallback route; "
                "the primary route returned no recognized entries."
            )
        else:
            message = (
                f"Primary route recognized {current_count} current {record_noun}(s). "
                f"{max(0, len(candidates) - 1)} fallback route(s) were left unused."
            )
    elif blocked_count:
        message = (
            f"Retailer access protection blocked {blocked_count} checked route(s). "
            f"No current {record_noun}s were confirmed; retained records are last-known only."
        )
    else:
        message = (
            "The checked page(s) responded, but the parser recognized no current product/news entries. "
            "This does not confirm that the retailer has no stock."
        )
    if failed_count:
        message += f" {failed_count} checked route(s) failed at the request level."
    if status.get("last_known_items"):
        retained_label = "article(s)" if source.get("type") == "rss" else "listing(s)"
        message += f" {status['last_known_items']} last-known {retained_label} retained."
    status["message"] = message[:900]

    # A primary-only successful parse is fully healthy. Any recovery attempt or
    # challenge is visible as a warning, even when a fallback produced listings.
    if current_count > 0 and not (blocked_count or failed_count or fallback_used):
        status["status"] = "ok"
    else:
        status["status"] = "warning"

    usable_urls = [
        attempt["url"] for attempt in attempts
        if attempt["transport_ok"] and not attempt["blocked"]
    ]
    if usable_urls:
        result_state["last_successful_urls"] = usable_urls
        result_state["last_success"] = result_state.get("last_success") or engine.utc_now()
    else:
        if original_state.get("last_success"):
            result_state["last_success"] = original_state["last_success"]
            result_state["last_successful_urls"] = original_state.get("last_successful_urls", [])
        else:
            result_state.pop("last_success", None)
            result_state.pop("last_successful_urls", None)

    # If no usable page was returned and at least one route was blocked, pause
    # this retailer's remaining category routes for a shared cooldown. A
    # successful non-challenge page clears any previous retailer cooldown.
    if blocked_count and usable_count == 0:
        _set_retailer_cooldown(
            state, source, "access-challenge",
            int(settings.get("retailer_block_cooldown_minutes", 45)),
            f"No usable page was returned; {blocked_count} checked route(s) returned retailer access challenges.",
        )
    else:
        health = state.get("retailer_health")
        if isinstance(health, dict):
            health.pop(retailer_key, None)

    result_state["source_url"] = source.get("url", candidates[0])
    result_state["last_attempt"] = engine.utc_now()
    status["response_url"] = chosen.get("url", status.get("response_url", source.get("url", "")))
    status["url"] = source.get("url", candidates[0])
    status["retailer_key"] = source.get("retailer_key") or engine._retailer_key(source.get("retailer", ""))
    status["category"] = source.get("category", "news" if source.get("type") == "rss" else "collectibles")
    status["notes"] = source.get("notes", "")
    status["message"] = status["message"][:900]
    return events, {"state": result_state, "status": status}


# Install after the recovery adapter and before run.py binds scan_source.
engine.scan_source = scan_source_with_conditional_routes
