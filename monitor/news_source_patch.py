"""Persist a growing news archive while keeping the current-feed scan lightweight.

The previous implementation replaced the archive with the latest 30 RSS items
on every scan. This version merges incoming entries with saved articles, older
news events, and the seen-index URLs. Latest Activity applies its 30-day window
in the browser; the All tracked products + Item type=News view can browse the
larger archive.
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlparse

import requests

import engine

_previous_scan_source = engine.scan_source
NEWS_ARCHIVE_LIMIT = 5000
NEWS_SEEN_LIMIT = 10000


def _local_name(tag: str) -> str:
    return str(tag or "").split("}")[-1].lower()


def _feed_publishers(body: str) -> dict[str, str]:
    """Read publisher labels from RSS source elements without trusting markup."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {}
    publishers: dict[str, str] = {}
    for entry in root.iter():
        if _local_name(entry.tag) not in {"item", "entry"}:
            continue
        link = ""
        for child in list(entry):
            if _local_name(child.tag) == "link":
                link = child.attrib.get("href") or (child.text or "").strip()
                if link:
                    break
        source = next((child for child in list(entry) if _local_name(child.tag) == "source"), None)
        publisher = engine.clean_text(" ".join(source.itertext()) if source is not None else "", 100)
        if link and publisher:
            publishers[link] = publisher
    return publishers


def _published_timestamp(value: Any) -> float:
    """Parse RSS RFC-822 and ISO-8601 dates for reliable newest-first sorting."""
    raw = engine.clean_text(value, 120)
    if not raw:
        return float("-inf")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).timestamp()


def _article_timestamp(article: dict[str, Any]) -> float:
    published = _published_timestamp(article.get("published"))
    if published != float("-inf"):
        return published
    detected = _published_timestamp(article.get("detected_at"))
    if detected != float("-inf"):
        return detected
    return _published_timestamp(article.get("first_seen"))


def _valid_feed_document(body: str) -> bool:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return False
    return _local_name(root.tag) in {"rss", "feed", "rdf"}


def _safe_article(item: dict[str, Any], source: dict[str, Any]) -> dict[str, Any] | None:
    title = engine.clean_text(item.get("title"), 240)
    url = engine.clean_text(item.get("url"), 1200)
    parsed = urlparse(url)
    if not title or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    publisher = engine.clean_text(
        item.get("publisher") or item.get("retailer") or source.get("retailer") or source.get("name"),
        100,
    )
    return {
        "key": engine.clean_text(item.get("key"), 80) or hashlib.sha256(url.encode("utf-8")).hexdigest()[:20],
        "title": title,
        "url": url,
        "summary": engine.clean_text(item.get("summary"), 420),
        "published": engine.clean_text(item.get("published"), 100),
        "publisher": publisher,
        "retailer": publisher,
        "retailer_key": "pokemon-news",
        "image": engine.clean_text(item.get("image"), 1200),
        "category": "news",
        "detected_at": engine.clean_text(item.get("detected_at") or item.get("first_seen"), 100),
    }


def _archive_from_seen(key: str, record: dict[str, Any], source: dict[str, Any]) -> dict[str, Any] | None:
    """Recover seen article URLs when an older state has no full article object."""
    if not isinstance(record, dict) or not record.get("url") or not record.get("title"):
        return None
    return _safe_article({
        "key": key,
        "title": record.get("title"),
        "url": record.get("url"),
        "publisher": record.get("publisher") or source.get("retailer") or "Pokémon News",
        "first_seen": record.get("first_seen"),
        "detected_at": record.get("first_seen"),
    }, source)


def scan_source_with_article_archive(
    session,
    source: dict[str, Any],
    settings: dict[str, Any],
    state: dict[str, Any],
):
    """Keep a deduplicated, growing RSS archive while emitting new-article events."""
    if source.get("type") != "rss":
        return _previous_scan_source(session, source, settings, state)

    started = time.monotonic()
    source_id = source["id"]
    configured_urls = list(dict.fromkeys([source.get("url", ""), *source.get("alternate_urls", [])]))
    configured_urls = [url for url in configured_urls if url][:4]
    if not configured_urls:
        raise ValueError(f"RSS source {source_id} has no configured URL.")

    previous = (state.get("items") or {}).get(source_id, {})
    source_url_changed = bool(previous.get("source_url") and previous.get("source_url") != source.get("url"))
    if source_url_changed:
        previous = {}
    is_baseline = not bool(previous.get("initialized"))
    seen = dict(previous.get("seen", {})) if isinstance(previous.get("seen"), dict) else {}

    timeout = int(settings.get("request_timeout_seconds", 25))
    successful_urls: list[str] = []
    fetch_errors: list[str] = []
    collected: dict[str, dict[str, Any]] = {}

    for candidate_url in configured_urls:
        try:
            body, final_url = engine.fetch(session, candidate_url, timeout)
            if not _valid_feed_document(body):
                raise ValueError("Response was not a valid RSS/Atom feed document.")
            parsed = engine.parse_rss(body, {**source, "url": final_url})
            publishers = _feed_publishers(body)
            for raw_item in parsed:
                item = dict(raw_item)
                item_url = item.get("url", "")
                item["publisher"] = publishers.get(item_url, item.get("publisher") or item.get("retailer") or "")
                article = _safe_article(item, source)
                if article:
                    collected[article["key"]] = article
            successful_urls.append(candidate_url)
        except Exception as exc:
            fetch_errors.append(f"{candidate_url}: {type(exc).__name__}: {str(exc)[:140]}")

    if not successful_urls:
        detail = " | ".join(fetch_errors) or "No configured feed URL could be read."
        raise requests.RequestException(f"All configured news feed URLs failed. {detail}")

    # Rebuild from every recoverable source in the saved state before adding the
    # newest feed batch. This carries forward older articles from previous scans.
    archive_by_url: dict[str, dict[str, Any]] = {}
    for saved in previous.get("articles", []) if isinstance(previous.get("articles"), list) else []:
        article = _safe_article(saved, source) if isinstance(saved, dict) else None
        if article:
            archive_by_url[article["url"]] = article

    # Older monitor versions kept news in the main event list, not the archive.
    for saved_event in state.get("events", []):
        if not isinstance(saved_event, dict) or saved_event.get("type") != "news":
            continue
        article = _safe_article(saved_event, source)
        if article and article["url"] not in archive_by_url:
            archive_by_url[article["url"]] = article

    # Earlier archives kept only a seen index (up to 300 entries). Recover any
    # titles/URLs that are no longer in the top-30 article list.
    for key, record in seen.items():
        article = _archive_from_seen(str(key), record, source)
        if article and article["url"] not in archive_by_url:
            archive_by_url[article["url"]] = article

    events: list[dict[str, Any]] = []
    now = engine.utc_now()
    for key, article in collected.items():
        already_archived = article["url"] in archive_by_url
        if not is_baseline and key not in seen and not already_archived:
            events.append(engine.event_record("news", article, source))
        article["detected_at"] = article.get("detected_at") or now
        archive_by_url[article["url"]] = article
        old = seen.get(key, {}) if isinstance(seen.get(key), dict) else {}
        seen[key] = {
            "title": article["title"],
            "url": article["url"],
            "publisher": article["publisher"],
            "first_seen": old.get("first_seen") or now,
        }

    # Keep all collected articles up to a generous bounded archive size. This is
    # no longer limited to the 30 entries currently returned by the RSS feed.
    articles = sorted(archive_by_url.values(), key=_article_timestamp, reverse=True)[:NEWS_ARCHIVE_LIMIT]
    current_count = len(collected)
    current_state = {
        "seen": dict(list(seen.items())[-NEWS_SEEN_LIMIT:]),
        "articles": articles,
        "initialized": True,
        "source_url": source.get("url", ""),
        "last_success": now,
        "last_item_count": current_count,
        "archive_count": len(articles),
        "last_successful_urls": successful_urls,
    }
    elapsed_ms = int((time.monotonic() - started) * 1000)
    status_value = "ok" if current_count else "warning"
    if current_count:
        status_message = f"{current_count} recent Pokémon news article(s) loaded; {len(articles)} article(s) retained in the archive."
    else:
        status_message = f"The feed responded, but no matching articles were returned. {len(articles)} older article(s) remain archived."

    partial = bool(fetch_errors and successful_urls)
    if partial:
        status_message = f"PARTIAL: {len(successful_urls)}/{len(configured_urls)} feed URL(s) responded. " + status_message
        status_value = "warning"
    status = {
        "id": source_id,
        "name": source.get("name", source_id),
        "retailer": source.get("retailer", "News"),
        "type": "rss",
        "url": source.get("url", ""),
        "status": status_value,
        "last_checked": now,
        "items_found": current_count,
        "archive_count": len(articles),
        "new_alerts": len(events),
        "successful_urls": len(successful_urls),
        "configured_urls": len(configured_urls),
        "message": status_message,
        "notes": source.get("notes", ""),
        "elapsed_ms": elapsed_ms,
        "response_health": {
            "successful": len(successful_urls),
            "configured": len(configured_urls),
            "failed": len(configured_urls) - len(successful_urls),
            "partial": partial,
        },
    }
    return events, {"state": current_state, "status": status}


engine.scan_source = scan_source_with_article_archive
