"""Persist a readable current-article list for RSS news sources.

This wraps the existing product scanner only for RSS source entries. Catalog and
product scans continue through the existing recovery/date-aware scanner.
"""
from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlparse

import requests

import engine

_previous_scan_source = engine.scan_source


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
    return {
        "key": engine.clean_text(item.get("key"), 80) or hashlib.sha256(url.encode("utf-8")).hexdigest()[:20],
        "title": title,
        "url": url,
        "summary": engine.clean_text(item.get("summary"), 420),
        "published": engine.clean_text(item.get("published"), 100),
        "publisher": engine.clean_text(item.get("publisher") or item.get("retailer") or source.get("retailer") or source.get("name"), 100),
        "retailer": engine.clean_text(item.get("publisher") or item.get("retailer") or source.get("retailer") or source.get("name"), 100),
        "image": engine.clean_text(item.get("image"), 1200),
        "category": "news",
    }


def scan_source_with_article_archive(
    session,
    source: dict[str, Any],
    settings: dict[str, Any],
    state: dict[str, Any],
):
    """Keep current news available on the page, including the first scan."""
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

    articles = list(collected.values())[:30]
    events: list[dict[str, Any]] = []
    now = engine.utc_now()
    for article in articles:
        key = article["key"]
        if not is_baseline and key not in seen:
            events.append(engine.event_record("news", article, source))
        seen[key] = {
            "title": article["title"],
            "url": article["url"],
            "first_seen": seen.get(key, {}).get("first_seen", now),
        }

    current_state = {
        "seen": dict(list(seen.items())[-300:]),
        "articles": articles,
        "initialized": True,
        "source_url": source.get("url", ""),
        "last_success": now,
        "last_item_count": len(articles),
        "last_successful_urls": successful_urls,
    }
    elapsed_ms = int((time.monotonic() - started) * 1000)
    status_value = "ok" if articles else "warning"
    if articles:
        status_message = f"{len(articles)} recent Pokémon news article(s) loaded."
    else:
        status_message = "The feed responded, but no matching articles were returned."

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
        "items_found": len(articles),
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
