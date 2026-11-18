"""Targeted retailer/news and release-date extensions for PokéDrop Watch.

Imported by run.py before importing engine functions so the same public monitor
pipeline can be retained while adding explicit PokéBeach WP fallback handling.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import engine


_DATE_KEYS = {
    # Keys are normalized through _key(), which removes underscores/case.
    "releasedate", "productreleasedate", "launchdate", "streetdate",
    "availabilitystarts", "releasedatetime", "releasedateestimate", "releasedateutc",
}
_NAME_KEYS = (
    "name", "productName", "productTitle", "title", "displayName",
    "webProductName", "itemName", "shortDescription",
)
_URL_KEYS = (
    "url", "canonicalUrl", "productUrl", "product_url", "pdpUrl",
    "seoUrl", "href", "link", "productPageUrl",
)


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _plain_text(value: Any, limit: int = 2000) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("rendered") or value.get("value") or value.get("date") or ""
    if isinstance(value, list):
        value = " ".join(str(part) for part in value)
    raw = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()[:limit]


def _normalize_date(value: Any) -> str:
    raw = _plain_text(value, 100).strip()
    if not raw:
        return ""
    iso_match = re.search(r"\b(20\d{2}-\d{1,2}-\d{1,2})(?:[T ][0-9:.+Z-]+)?\b", raw)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1)).isoformat()
        except ValueError:
            pass
    for pattern in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(raw, pattern).date().isoformat()
        except ValueError:
            continue
    return ""


def release_date_within_month(value: Any, today: date | None = None) -> bool:
    """True for a published release date within 30 days before or after today."""
    parsed = _normalize_date(value)
    if not parsed:
        return False
    try:
        released = date.fromisoformat(parsed)
    except ValueError:
        return False
    current = today or datetime.now(timezone.utc).date()
    return abs((released - current).days) <= 30


def _release_date_from_node(node: dict[str, Any]) -> str:
    for name, value in node.items():
        if _key(name) in _DATE_KEYS:
            parsed = _normalize_date(value)
            if parsed:
                return parsed
    # Retailer payloads sometimes attach the launch date to an Offer child.
    for name, value in node.items():
        if _key(name) in {"offers", "offer", "availability"} and isinstance(value, (dict, list)):
            for child in engine._walk_json(value):
                if child is node:
                    continue
                for child_name, child_value in child.items():
                    if _key(child_name) in _DATE_KEYS:
                        parsed = _normalize_date(child_value)
                        if parsed:
                            return parsed
    return ""


def _node_value(node: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for nested in ("url", "href", "value", "rendered"):
                candidate = value.get(nested)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
    return ""


def _date_lookup(payload: Any) -> tuple[dict[str, str], dict[str, str]]:
    by_title: dict[str, str] = {}
    by_url: dict[str, str] = {}
    for node in engine._walk_json(payload):
        release_date = _release_date_from_node(node)
        if not release_date:
            continue
        title = _node_value(node, _NAME_KEYS)
        raw_url = _node_value(node, _URL_KEYS)
        if title:
            by_title[engine.normalize_match_text(title)] = release_date
        if raw_url:
            absolute = urljoin("https://invalid.local/", raw_url)
            if urlparse(absolute).scheme in {"http", "https"} and urlparse(absolute).netloc != "invalid.local":
                by_url[engine.stable_url(absolute)] = release_date
    return by_title, by_url


def _apply_release_dates(products: list[dict[str, Any]], lookup: tuple[dict[str, str], dict[str, str]]) -> list[dict[str, Any]]:
    by_title, by_url = lookup
    for item in products:
        current = _normalize_date(item.get("release_date"))
        found = current or by_url.get(engine.stable_url(item.get("url", "")), "") or by_title.get(
            engine.normalize_match_text(item.get("title", "")), ""
        )
        if found:
            item["release_date"] = found
    return products


def _json_payloads(soup: BeautifulSoup):
    for script in soup.find_all("script", attrs={"type": re.compile(r"json", re.I)}):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            yield json.loads(raw.strip().strip(";"))
        except (json.JSONDecodeError, TypeError):
            continue


def _release_date_from_card_text(text: str) -> str:
    label = re.search(
        r"(?:release\s*date|street\s*date|launch\s*date|available\s+(?:on|starting))\s*[:\-]?\s*"
        r"(20\d{2}-\d{1,2}-\d{1,2}|[A-Za-z]{3,9}\s+\d{1,2},?\s+20\d{2}|\d{1,2}/\d{1,2}/20\d{2})",
        text,
        re.I,
    )
    return _normalize_date(label.group(1)) if label else ""


def _dom_date_lookup(soup: BeautifulSoup, base_url: str) -> tuple[dict[str, str], dict[str, str]]:
    by_title: dict[str, str] = {}
    by_url: dict[str, str] = {}
    attrs = ("data-release-date", "data-product-release-date", "data-launch-date", "data-street-date")
    for element in soup.find_all(True):
        raw_date = next((element.get(attr) for attr in attrs if element.get(attr)), "")
        marker = " ".join([str(element.get("id", "")), " ".join(element.get("class", []))]).lower()
        if not raw_date and re.search(r"release.?date|street.?date|launch.?date", marker):
            raw_date = element.get_text(" ", strip=True)
        parsed = _normalize_date(raw_date) or _release_date_from_card_text(element.get_text(" ", strip=True))
        if not parsed:
            continue
        for anchor in element.find_all("a", href=True):
            by_url[engine.stable_url(urljoin(base_url, anchor.get("href", "")))] = parsed
        for heading in element.find_all(["h2", "h3", "h4"]):
            title = engine.normalize_match_text(heading.get_text(" ", strip=True))
            if title:
                by_title[title] = parsed
    return by_title, by_url


_original_extract_json_products = engine.extract_json_products
_original_extract_structured_products = engine.extract_structured_products
_original_extract_catalog_links = engine.extract_catalog_links
_original_parse_rss = engine.parse_rss
_original_fetch = engine.fetch
_original_event_record = engine.event_record
_original_is_pokemon_relevant = engine.is_pokemon_relevant
_original_scan_source = engine.scan_source
_SCOPED_SCAN_ACTIVE = False


def is_pokemon_relevant_in_scoped_page(value: Any) -> bool:
    # Some filtered retailer categories return product names that omit the word
    # Pokémon (for example, a set title or a generic TCG descriptor). On a URL
    # explicitly filtered to Pokémon, the page scope itself is the relevance
    # signal. Other sources retain the strict title-based allow-list.
    if _SCOPED_SCAN_ACTIVE:
        return bool(engine.clean_text(value, 1200)) and not engine._is_noise_title(value)
    return _original_is_pokemon_relevant(value)


def scan_source_with_pokemon_scope(session, source: dict[str, Any], settings: dict[str, Any], state: dict[str, Any]):
    """Scan scoped Pokémon catalogs and surface dated releases on first baseline."""
    global _SCOPED_SCAN_ACTIVE
    scoped = bool(source.get("pokemon_scoped")) and source.get("type") in {"catalog", "product"}
    previous_state = state.get("items", {}).get(source.get("id"), {})
    previous_initialized = bool(previous_state.get("initialized"))
    source_url_changed = bool(
        previous_state.get("source_url")
        and previous_state.get("source_url") != source.get("url")
    )
    needs_baseline = not previous_initialized or source_url_changed

    was_active = _SCOPED_SCAN_ACTIVE
    if scoped:
        _SCOPED_SCAN_ACTIVE = True
        engine.is_pokemon_relevant = is_pokemon_relevant_in_scoped_page
    try:
        events, result = _original_scan_source(session, source, settings, state)
    finally:
        _SCOPED_SCAN_ACTIVE = was_active
        engine.is_pokemon_relevant = _original_is_pokemon_relevant

    # The original monitor deliberately suppresses first-seen alerts while
    # establishing a new catalog baseline. Keep that behavior for undated
    # listings, but a published release date within 30 days is specific enough
    # to surface as a New item even on the first successful scan.
    if needs_baseline and source.get("type") in {"catalog", "product"}:
        products = result.get("state", {}).get("products", {})
        for item in products.values() if isinstance(products, dict) else []:
            if not release_date_within_month(item.get("release_date")):
                continue
            events.append(engine.event_record(
                "new_item", item, source,
                detail="Published release date is within 30 days of the current date.",
            ))
    return events, result


def extract_json_products_with_dates(payload: Any, base_url: str, retailer: str):
    products = _original_extract_json_products(payload, base_url, retailer)
    return _apply_release_dates(products, _date_lookup(payload))


def extract_structured_products_with_dates(soup: BeautifulSoup, base_url: str, retailer: str):
    products = _original_extract_structured_products(soup, base_url, retailer)
    by_title: dict[str, str] = {}
    by_url: dict[str, str] = {}
    for payload in _json_payloads(soup):
        title_dates, url_dates = _date_lookup(payload)
        by_title.update(title_dates)
        by_url.update(url_dates)
    dom_title_dates, dom_url_dates = _dom_date_lookup(soup, base_url)
    by_title.update(dom_title_dates)
    by_url.update(dom_url_dates)
    return _apply_release_dates(products, (by_title, by_url))


def _extract_scoped_product_cards(soup: BeautifulSoup, base_url: str, retailer: str, limit: int):
    """Fallback for category-filtered retailers whose PDP paths are nonstandard."""
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    found: dict[str, dict[str, Any]] = {}
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor.get("href", ""))
        parsed = urlparse(href)
        host = parsed.netloc.lower().removeprefix("www.")
        path = parsed.path.lower().rstrip("/")
        if parsed.scheme not in {"http", "https"} or host != base_host or not path or path == "/":
            continue
        if any(hint in path for hint in engine.NON_PRODUCT_PATH_HINTS):
            continue
        if len([part for part in path.split("/") if part]) < 1:
            continue

        card = engine._card_ancestor(anchor)
        if card is None:
            continue
        card_text = engine.clean_text(card.get_text(" ", strip=True), 2200)
        marker = " ".join([
            " ".join(card.get("class", [])) if card.get("class") else "",
            engine.clean_text(card.get("id"), 120),
            engine.clean_text(card.get("data-testid"), 120),
            engine.clean_text(card.get("data-cy"), 120),
            engine.clean_text(card.get("data-component-type"), 120),
        ]).lower()
        marked_tile = any(token in marker for token in (
            "product", "tile", "sku-item", "productcard", "product-card", "grid-item"
        ))
        has_image = card.find("img") is not None
        has_price = engine.PRICE_RE.search(card_text) is not None
        availability = engine.normalize_availability(card_text)
        if not marked_tile and not (has_image and (has_price or availability != "unknown")):
            continue

        title = engine._card_title(card, anchor)
        if not title or engine._is_noise_title(title):
            continue
        stable = engine.stable_url(href)
        if stable in found:
            continue
        price_match = engine.PRICE_RE.search(card_text)
        price_value, currency = engine.money(price_match.group(1)) if price_match else (None, "USD")
        image_url = engine._image_from_card(card, base_url)
        sku = ""
        for attribute in ("data-product-id", "data-sku", "data-tcin", "data-item-id"):
            sku = engine.clean_text(card.get(attribute), 80)
            if sku:
                break
        found[stable] = {
            "title": title,
            "url": stable,
            "price": price_value,
            "currency": currency or "USD",
            "availability": availability,
            "image": image_url,
            "sku": sku,
            "retailer": retailer,
            "category": engine.infer_category(title),
        }
        if len(found) >= limit:
            break
    return list(found.values())


def extract_catalog_links_with_dates(soup: BeautifulSoup, base_url: str, retailer: str, limit: int):
    products = _original_extract_catalog_links(soup, base_url, retailer, limit)
    if _SCOPED_SCAN_ACTIVE and len(products) < limit:
        products.extend(_extract_scoped_product_cards(
            soup, base_url, retailer, max(0, limit - len(products))
        ))
        products = engine.deduplicate_products(products)[:limit]
    by_title: dict[str, str] = {}
    by_url: dict[str, str] = {}
    for payload in _json_payloads(soup):
        title_dates, url_dates = _date_lookup(payload)
        by_title.update(title_dates)
        by_url.update(url_dates)
    dom_title_dates, dom_url_dates = _dom_date_lookup(soup, base_url)
    by_title.update(dom_title_dates)
    by_url.update(dom_url_dates)
    return _apply_release_dates(products, (by_title, by_url))


def parse_wordpress_posts(payload: Any, source: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and payload.get("code") and payload.get("message"):
        raise ValueError(f"WordPress REST API error: {_plain_text(payload.get('message'), 240)}")
    if isinstance(payload, list):
        posts = payload
    elif isinstance(payload, dict):
        posts = payload.get("posts") or payload.get("data")
    else:
        posts = None
    if not isinstance(posts, list):
        raise ValueError("WordPress REST response did not contain a posts array.")
    items = []
    for post in posts[:50]:
        if not isinstance(post, dict):
            continue
        title = _plain_text(post.get("title"), 240)
        link = _plain_text(post.get("link") or post.get("url"), 1000)
        if not title or not link:
            continue
        excerpt = _plain_text(post.get("excerpt") or post.get("content"), 5000)
        image = ""
        embedded = post.get("_embedded") or {}
        media = embedded.get("wp:featuredmedia") if isinstance(embedded, dict) else None
        if isinstance(media, list) and media and isinstance(media[0], dict):
            image = media[0].get("source_url") or ""
        if not image:
            content_obj = post.get("content") or ""
            content_html = content_obj.get("rendered", "") if isinstance(content_obj, dict) else str(content_obj)
            match = re.search(r"<img[^>]+(?:src|data-src)=[\"']([^\"']+)", content_html, re.I)
            if match:
                image = match.group(1)
        identifier = str(post.get("id") or post.get("guid") or link)
        items.append({
            "key": hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:20],
            "title": title,
            "url": link,
            "summary": excerpt[:420],
            "published": post.get("date_gmt") or post.get("date") or "",
            "retailer": source.get("retailer") or source.get("name", "News feed"),
            "image": urljoin(source.get("url", link), image) if image else "",
            "category": "news",
        })
    return items


def parse_news_feed(payload_text: str, source: dict[str, Any]):
    stripped = payload_text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"News JSON could not be parsed: {exc}") from exc
        return parse_wordpress_posts(payload, source)
    # The /feed endpoint currently returns a well-formed <error> XML document
    # with HTTP 200, so reject it instead of treating it as an empty RSS feed.
    try:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(payload_text)
    except ET.ParseError:
        root = None
    if root is not None and root.tag.split("}")[-1].lower() in {"error", "wp_error"}:
        detail = " ".join(root.itertext()).strip()
        raise ValueError(f"Feed endpoint returned WordPress error XML: {detail[:220]}")
    if re.search(r"<error\b[^>]*>.*?wp_die|no feed available", payload_text, re.I | re.S):
        raise ValueError("Feed endpoint returned WordPress wp_die: No feed available.")
    return _original_parse_rss(payload_text, source)


def fetch_rejecting_pokebeach_error_xml(session, url: str, timeout: int):
    body, final_url = _original_fetch(session, url, timeout)
    host = urlparse(final_url).netloc.lower().removeprefix("www.")
    if host == "pokebeach.com":
        stripped = body.lstrip("\ufeff\r\n\t ")
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(stripped)
        except ET.ParseError:
            root = None
        if root is not None and root.tag.split("}")[-1].lower() in {"error", "wp_error"}:
            detail = " ".join(root.itertext()).lower()
            if "wp_die" in detail or "no feed available" in detail:
                raise ValueError("PokéBeach /feed returned WordPress wp_die: No feed available.")
        if stripped.startswith("{"):
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and payload.get("code") and payload.get("message"):
                raise ValueError(f"PokéBeach REST endpoint error: {_plain_text(payload.get('message'), 180)}")
    return body, final_url


def event_record_with_release_classification(event_type: str, item: dict[str, Any], source: dict[str, Any], previous_price: Any = None, detail: str = ""):
    if event_type == "first_seen" and release_date_within_month(item.get("release_date")):
        event_type = "new_item"
        detail = "Published release date is within 30 days of the current date."
    return _original_event_record(event_type, item, source, previous_price, detail)


# Patch only the call sites used by the existing scanner. The underlying scraper,
# state transitions, de-duplication and stock comparison stay unchanged.
engine.extract_json_products = extract_json_products_with_dates
engine.extract_structured_products = extract_structured_products_with_dates
engine.extract_catalog_links = extract_catalog_links_with_dates
engine.parse_rss = parse_news_feed
engine.fetch = fetch_rejecting_pokebeach_error_xml
engine.event_record = event_record_with_release_classification
engine.scan_source = scan_source_with_pokemon_scope
