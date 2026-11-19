"""Retailer recovery adapters for PokéDrop Watch.

This module is imported after engine_patch and before run.py imports scanner
functions. It adds retailer-aware card/JSON extraction, a PokéBeach HTML fallback,
response diagnostics, and preservation of the last-known catalogue on parser misses.
No external service or API key is required.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import engine
import engine_patch


# Preserve the already-installed date-aware parser and fetch wrappers.
_previous_extract_retailer_products = engine.extract_retailer_products
_previous_extract_json_products = engine.extract_json_products
_previous_parse_rss = engine.parse_rss
_previous_fetch = engine.fetch
_previous_scan_source = engine.scan_source
_FETCH_DIAGNOSTICS: list[dict[str, Any]] = []

_NAME_KEYS = (
    "name", "productName", "productTitle", "title", "displayName",
    "webProductName", "itemName", "shortDescription", "description",
)
_URL_KEYS = (
    "url", "canonicalUrl", "productUrl", "product_url", "pdpUrl",
    "seoUrl", "href", "link", "productPageUrl", "productLink", "product_page_url",
)
_PRICE_KEYS = (
    "price", "currentPrice", "current_retail", "currentRetail", "salePrice",
    "offerPrice", "priceValue", "unitPrice", "displayPrice", "formattedPrice",
)
_IMAGE_KEYS = (
    "image", "imageUrl", "primaryImage", "thumbnail", "thumbnailUrl", "largeImage",
    "src", "image_url", "heroImage", "productImage", "mainImage", "imageInfo",
)
_STOCK_KEYS = (
    "availability", "availabilityStatus", "stockStatus", "inventoryStatus",
    "fulfillmentStatus", "onlineAvailability", "isAvailable",
)

_PRODUCT_PATH_RE = re.compile(
    r"(?:/ip/|/dp/|/gp/product/|/product/|/products/|/p/|/-/a-\d+|/site/.+\.p(?:/|$))",
    re.I,
)
_CHALLENGE_RE = re.compile(
    r"captcha|verify you are human|robot or human|access denied|request blocked|"
    r"unusual traffic|automated requests|just a moment|cloudflare|akamai bot",
    re.I,
)


def _scalar(value: Any, limit: int = 1200) -> str:
    """Read common scalar/structured values without evaluating retailer scripts."""
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in (
            "rendered", "value", "displayValue", "formattedValue", "formattedPrice",
            "amount", "price", "url", "href", "src", "contentUrl", "large", "highRes",
        ):
            if key in value:
                found = _scalar(value.get(key), limit)
                if found:
                    return found
        return ""
    if isinstance(value, list):
        for part in value:
            found = _scalar(part, limit)
            if found:
                return found
        return ""
    if isinstance(value, (str, int, float)):
        return engine.clean_text(value, limit)
    return ""


def _pick(node: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        if key in node:
            value = _scalar(node.get(key))
            if value:
                return value
    return ""


def _same_host_product_url(raw_url: str, base_url: str, retailer_key: str) -> str:
    if not raw_url:
        return ""
    absolute = urljoin(base_url, raw_url)
    parsed = urlparse(absolute)
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    host = parsed.netloc.lower().removeprefix("www.")
    if parsed.scheme not in {"http", "https"} or not host or not (host == base_host or host.endswith("." + base_host)):
        return ""
    path = parsed.path.lower()
    retailer_patterns = {
        "target": re.compile(r"(?:/-/a-\d+|/p/.+/-/a-\d+)", re.I),
        "walmart": re.compile(r"/ip/[^/?]+(?:/\d+)?", re.I),
        "amazon": re.compile(r"/(?:dp|gp/product)/[a-z0-9]{8,14}", re.I),
        "pokemon-center": re.compile(r"/(?:product|products)/", re.I),
        "best-buy": re.compile(r"/site/.+\.p(?:/|$)", re.I),
        "gamestop": re.compile(r"/(?:p|product)/", re.I),
    }
    specific = retailer_patterns.get(retailer_key)
    if specific and specific.search(path):
        return engine.stable_url(absolute)
    if _PRODUCT_PATH_RE.search(path):
        return engine.stable_url(absolute)
    return ""


def _pokemon_title_allowed(title: str) -> bool:
    if not title or engine._is_noise_title(title):
        return False
    # Scoped category pages are explicitly Pokémon filtered; some retailer card
    # titles omit the franchise name. Outside those pages keep the strict allow-list.
    if engine_patch._SCOPED_SCAN_ACTIVE:
        return True
    return engine.is_pokemon_relevant(title)


def _product_from_json_node(node: dict[str, Any], base_url: str, retailer: str) -> dict[str, Any] | None:
    title = engine.clean_product_title(_pick(node, _NAME_KEYS))
    if not _pokemon_title_allowed(title):
        return None
    retailer_key = engine._retailer_key(retailer)
    raw_url = _pick(node, _URL_KEYS)
    product_url = _same_host_product_url(raw_url, base_url, retailer_key)
    if not product_url:
        return None
    price_raw = _pick(node, _PRICE_KEYS)
    price, currency = engine.money(price_raw)
    image_raw = next((node.get(key) for key in _IMAGE_KEYS if node.get(key)), "")
    image = engine._first_image(image_raw, base_url)
    availability = engine.normalize_availability(_pick(node, _STOCK_KEYS))
    sku = _pick(node, ("sku", "productId", "productID", "tcin", "itemId", "item_id", "asin", "id"))
    return {
        "title": title,
        "url": product_url,
        "price": price,
        "currency": engine.clean_text(node.get("currency") or node.get("priceCurrency") or currency or "USD", 8),
        "availability": availability,
        "image": image,
        "sku": sku[:100],
        "retailer": retailer,
        "category": engine.infer_category(title),
        "release_date": engine_patch._release_date_from_node(node),
    }


def _extract_retailer_json_products(soup: BeautifulSoup, base_url: str, retailer: str, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    found: dict[str, dict[str, Any]] = {}
    for payload in engine._json_script_payloads(soup):
        for node in engine._walk_json(payload):
            item = _product_from_json_node(node, base_url, retailer)
            if item:
                found[item["url"]] = item
                if len(found) >= limit:
                    return list(found.values())
    return list(found.values())


def _product_card(anchor, base_url: str, retailer: str) -> dict[str, Any] | None:
    retailer_key = engine._retailer_key(retailer)
    product_url = _same_host_product_url(anchor.get("href", ""), base_url, retailer_key)
    if not product_url:
        return None

    card = anchor
    for parent in anchor.parents:
        if getattr(parent, "name", None) in {"body", "html"}:
            break
        marker = " ".join([
            " ".join(parent.get("class", [])) if parent.get("class") else "",
            engine.clean_text(parent.get("id"), 100),
            engine.clean_text(parent.get("data-testid"), 100),
            engine.clean_text(parent.get("data-automation"), 100),
            engine.clean_text(parent.get("data-cy"), 100),
        ]).lower()
        if any(token in marker for token in ("product", "tile", "sku-item", "search-result", "grid-item")):
            card = parent
            break
        if parent.find("img") is not None and len(engine.clean_text(parent.get_text(" ", strip=True), 2000)) <= 1800:
            card = parent
            break

    title_candidates = [
        engine.clean_text(anchor.get("title"), 240),
        engine.clean_text(anchor.get("aria-label"), 240),
        engine.clean_text(anchor.get_text(" ", strip=True), 240),
    ]
    for element in card.select("h1,h2,h3,h4,[data-testid*='title'],[class*='title'],[class*='name']")[:8]:
        title_candidates.append(engine.clean_text(element.get_text(" ", strip=True), 240))
    for image_tag in card.find_all("img")[:5]:
        title_candidates.extend([
            engine.clean_text(image_tag.get("alt"), 240),
            engine.clean_text(image_tag.get("title"), 240),
        ])
    title = next((engine.clean_product_title(candidate) for candidate in title_candidates if _pokemon_title_allowed(engine.clean_product_title(candidate))), "")
    if not title:
        return None

    card_text = engine.clean_text(card.get_text(" ", strip=True), 3000)
    price_raw = ""
    for element in card.find_all(True):
        for attr in ("data-price", "data-current-price", "data-product-price", "content"):
            raw = element.get(attr)
            if raw and (attr != "content" or element.get("itemprop") == "price"):
                price_raw = engine.clean_text(raw, 80)
                break
        if price_raw:
            break
    if not price_raw:
        match = engine.PRICE_RE.search(card_text)
        price_raw = match.group(1) if match else ""
    price, currency = engine.money(price_raw) if price_raw else (None, "USD")
    availability = engine.normalize_availability(card_text)
    if availability == "unknown":
        for element in card.find_all(True):
            marker = " ".join([str(element.get("class", "")), str(element.get("id", ""))]).lower()
            if any(token in marker for token in ("stock", "availability", "inventory", "fulfillment")):
                availability = engine.normalize_availability(
                    element.get("aria-label") or element.get("data-availability") or element.get_text(" ", strip=True)
                )
                if availability != "unknown":
                    break
    sku = ""
    for element in (card, anchor):
        for attr in ("data-product-id", "data-sku", "data-tcin", "data-item-id", "data-asin"):
            sku = engine.clean_text(element.get(attr), 100)
            if sku:
                break
        if sku:
            break
    return {
        "title": title,
        "url": product_url,
        "price": price,
        "currency": currency or "USD",
        "availability": availability,
        "image": engine._image_from_card(card, base_url),
        "sku": sku,
        "retailer": retailer,
        "category": engine.infer_category(title),
    }


def _extract_retailer_dom_products(soup: BeautifulSoup, base_url: str, retailer: str, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    found: dict[str, dict[str, Any]] = {}
    for anchor in soup.find_all("a", href=True):
        item = _product_card(anchor, base_url, retailer)
        if not item:
            continue
        found.setdefault(item["url"], item)
        if len(found) >= limit:
            break
    return list(found.values())


def extract_retailer_products_recovery(soup: BeautifulSoup, base_url: str, retailer: str, limit: int) -> list[dict[str, Any]]:
    existing = _previous_extract_retailer_products(soup, base_url, retailer, limit)
    if len(existing) >= limit:
        return existing[:limit]
    remaining = max(0, limit - len(existing))
    additions = _extract_retailer_json_products(soup, base_url, retailer, remaining)
    additions.extend(_extract_retailer_dom_products(soup, base_url, retailer, max(0, remaining - len(additions))))
    combined = engine.deduplicate_products(existing + additions)
    return combined[:limit]


def extract_json_products_recovery(payload: Any, base_url: str, retailer: str) -> list[dict[str, Any]]:
    existing = _previous_extract_json_products(payload, base_url, retailer)
    if len(existing) >= 80:
        return existing
    additions = []
    retailer_key = engine._retailer_key(retailer)
    for node in engine._walk_json(payload):
        item = _product_from_json_node(node, base_url, retailer)
        if item:
            additions.append(item)
        if len(existing) + len(additions) >= 100:
            break
    return engine.deduplicate_products(existing + additions)


def _pokebeach_html_posts(body: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    soup = BeautifulSoup(body, "html.parser")
    selectors = (
        "article h1 a[href]", "article h2 a[href]", "article h3 a[href]",
        ".entry-title a[href]", ".post-title a[href]", ".jeg_post_title a[href]",
        ".td-module-title a[href]", "a[rel='bookmark'][href]",
    )
    anchors = []
    seen_nodes = set()
    for selector in selectors:
        for anchor in soup.select(selector):
            marker = (anchor.get("href", ""), anchor.get_text(" ", strip=True))
            if marker not in seen_nodes:
                seen_nodes.add(marker)
                anchors.append(anchor)
    if not anchors:
        # Broader WordPress fallback for themes that omit article/post classes.
        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            anchor = heading.find("a", href=True)
            if not anchor:
                continue
            candidate_path = urlparse(urljoin(source.get("url", "https://www.pokebeach.com/"), anchor.get("href", ""))).path
            if not re.search(r"/20\d{2}/\d{1,2}/", candidate_path):
                continue
            marker = (anchor.get("href", ""), anchor.get_text(" ", strip=True))
            if marker not in seen_nodes:
                seen_nodes.add(marker)
                anchors.append(anchor)
    items = []
    seen_urls = set()
    for anchor in anchors[:60]:
        title = engine.clean_text(anchor.get_text(" ", strip=True) or anchor.get("title"), 240)
        url = urljoin(source.get("url", "https://www.pokebeach.com/"), anchor.get("href", ""))
        parsed = urlparse(url)
        if parsed.netloc.lower().removeprefix("www.") != "pokebeach.com":
            continue
        if not title or engine._is_noise_title(title) or not engine_patch._original_is_pokemon_relevant(title):
            continue
        url = engine.stable_url(url)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        card = anchor
        for parent in anchor.parents:
            if getattr(parent, "name", None) in {"article", "li"}:
                card = parent
                break
        excerpt = ""
        paragraph = card.find("p") if card else None
        if paragraph:
            excerpt = engine.clean_text(paragraph.get_text(" ", strip=True), 420)
        image = ""
        if card:
            image_tag = card.find("img")
            if image_tag:
                image = engine._first_image(
                    image_tag.get("src") or image_tag.get("data-src") or image_tag.get("data-lazy-src") or image_tag.get("srcset", "").split(" ")[0],
                    url,
                )
        time_tag = card.find("time") if card else None
        published = (time_tag.get("datetime") or time_tag.get_text(" ", strip=True)) if time_tag else ""
        identifier = url
        items.append({
            "key": hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:20],
            "title": title,
            "url": url,
            "summary": excerpt,
            "published": engine.clean_text(published, 80),
            "retailer": source.get("retailer") or "PokéBeach",
            "image": image,
            "category": "news",
        })
    return items


def parse_rss_with_pokebeach_html(body: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return _previous_parse_rss(body, source)
    except Exception:
        host = urlparse(source.get("url", "")).netloc.lower().removeprefix("www.")
        if host != "pokebeach.com" or not re.search(r"<html\b|<article\b|<body\b", body, re.I):
            raise
        posts = _pokebeach_html_posts(body, source)
        if posts:
            return posts
        raise ValueError("PokéBeach page responded with HTML, but no Pokémon article cards matched the known selectors.")


def _response_diagnostic(body: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(body, "html.parser")
    title = engine.clean_text(soup.title.get_text(" ", strip=True) if soup.title else "", 100)
    links = 0
    for anchor in soup.find_all("a", href=True):
        path = urlparse(urljoin(url, anchor.get("href", ""))).path
        if _PRODUCT_PATH_RE.search(path):
            links += 1
    scripts = len(soup.find_all("script", attrs={"type": re.compile(r"json", re.I)}))
    text = engine.clean_text(soup.get_text(" ", strip=True), 40000)
    challenge = bool(_CHALLENGE_RE.search(text) or _CHALLENGE_RE.search(body[:100000]))
    return {
        "url": url,
        "bytes": len(body.encode("utf-8", errors="ignore")),
        "title": title,
        "product_links": links,
        "json_scripts": scripts,
        "challenge": challenge,
    }


def fetch_with_diagnostics(session, url: str, timeout: int):
    try:
        body, final_url = _previous_fetch(session, url, timeout)
    except Exception as exc:
        _FETCH_DIAGNOSTICS.append({"url": url, "error": f"{type(exc).__name__}: {str(exc)[:140]}"})
        raise
    _FETCH_DIAGNOSTICS.append(_response_diagnostic(body, final_url))
    return body, final_url


def scan_source_with_recovery(session, source: dict[str, Any], settings: dict[str, Any], state: dict[str, Any]):
    source_for_scan = dict(source)
    if source.get("id") == "pokebeach-news" and "wp_die" in str(source.get("notes", "")).lower():
        # The checked-in source config documents the known wp_die feed failure.
        # Keeping this gated avoids changing minimal/custom PokéBeach test sources.
        alternates = list(source.get("alternate_urls", []))
        homepage = "https://www.pokebeach.com/"
        if homepage not in alternates and source.get("url") != homepage:
            alternates.append(homepage)
        source_for_scan["alternate_urls"] = alternates

    old_source_state = (state.get("items") or {}).get(source.get("id"), {})
    source_url_changed = bool(old_source_state.get("source_url") and old_source_state.get("source_url") != source.get("url"))
    old_product_count = 0 if source_url_changed else len(old_source_state.get("products", {}))
    if not source_url_changed:
        old_product_count = max(old_product_count, int(old_source_state.get("last_item_count", 0) or 0))

    _FETCH_DIAGNOSTICS.clear()
    events, result = _previous_scan_source(session, source_for_scan, settings, state)
    status = result.get("status", {})
    saved_state = result.get("state", {})

    # Preserve the last-known catalog while still reporting that this scan could
    # not parse current products. This avoids making a temporary parser miss look
    # like the retailer's inventory disappeared.
    if source.get("type") in {"catalog", "product"} and int(status.get("items_found", 0) or 0) == 0 and old_product_count:
        saved_products = saved_state.get("products", {}) if isinstance(saved_state.get("products"), dict) else {}
        retained = max(old_product_count, len(saved_products))
        saved_state["last_item_count"] = retained
        status["last_known_items"] = retained
        status["message"] = (status.get("message", "") + f" Last-known catalog retained: {retained} listing(s); this scan did not confirm current inventory.")[:480]

    # Include compact, non-sensitive diagnostics so a parser miss can be separated
    # from an anti-bot shell, empty application shell, or selector regression.
    diagnostics = [entry for entry in _FETCH_DIAGNOSTICS if "error" not in entry]
    if diagnostics and status.get("status") == "warning":
        summaries = []
        for entry in diagnostics[:3]:
            detail = f"{round(entry['bytes'] / 1024)} KB"
            if entry.get("title"):
                detail += f", title={entry['title'][:45]}"
            detail += f", product-like links={entry['product_links']}, JSON blocks={entry['json_scripts']}"
            if entry.get("challenge"):
                detail += ", access-challenge marker detected"
            summaries.append(detail)
        status["parser_diagnostics"] = summaries
        status["message"] = (status.get("message", "") + " Response diagnostics: " + " | ".join(summaries))[:900]
    return events, result


# Install adapters before run.py binds these callables from engine.
engine.extract_retailer_products = extract_retailer_products_recovery
engine.extract_json_products = extract_json_products_recovery
engine.parse_rss = parse_rss_with_pokebeach_html
engine.fetch = fetch_with_diagnostics
engine.scan_source = scan_source_with_recovery
