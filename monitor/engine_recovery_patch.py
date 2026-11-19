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
    """Find a retailer field at the current level, then in nested record objects."""
    if not isinstance(node, dict):
        return ""
    for key in keys:
        if key in node:
            value = _scalar(node.get(key))
            if value:
                return value
    for child in node.values():
        if isinstance(child, dict):
            value = _pick(child, keys)
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
    # Some retailer hydration payloads expose the canonical identifier but omit
    # the URL. Synthesize only well-defined product routes (Target TCIN, Amazon ASIN).
    if not product_url and retailer_key == "target":
        tcin = _pick(node, ("tcin", "TCIN", "tcinId"))
        if tcin and re.fullmatch(r"\d{6,14}", tcin):
            product_url = _same_host_product_url(f"/p/-/A-{tcin}", base_url, retailer_key)
    if not product_url and retailer_key == "amazon":
        asin = _pick(node, ("asin", "ASIN"))
        if asin and re.fullmatch(r"[A-Z0-9]{10}", asin, re.I):
            product_url = _same_host_product_url(f"/dp/{asin}", base_url, retailer_key)
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


def _attribute_text_values(element) -> list[str]:
    values: list[str] = []
    if not getattr(element, "attrs", None):
        return values
    for key, raw in element.attrs.items():
        low = str(key).lower()
        if low in {
            "aria-label", "title", "alt", "data-product-title", "data-product-name",
            "data-item-title", "data-name", "data-qa-title", "data-testid-title",
            "data-automation-label", "data-product-description", "content",
        } or low.startswith(("data-product-title", "data-product-name", "data-item-title")):
            value = _scalar(raw, 500)
            if value:
                values.append(value)
    return values


def _candidate_score(value: str) -> int:
    normalized = engine.normalize_match_text(value)
    score = min(len(value), 200)
    if "pokemon" in normalized:
        score += 45
    if any(term in normalized for term in (
        "booster", "elite trainer", "collection", "plush", "figure", "trading card",
        "tin", "bundle", "box", "pikachu", "charizard", "eevee",
    )):
        score += 35
    if len(normalized.split()) >= 4:
        score += 12
    return score


def _nearest_product_container(element):
    fallback = element
    for parent in element.parents:
        if getattr(parent, "name", None) in {"body", "html"}:
            break
        marker = " ".join([
            " ".join(parent.get("class", [])) if parent.get("class") else "",
            engine.clean_text(parent.get("id"), 100),
            engine.clean_text(parent.get("data-testid"), 100),
            engine.clean_text(parent.get("data-automation"), 100),
            engine.clean_text(parent.get("data-cy"), 100),
            engine.clean_text(parent.get("data-qa"), 100),
        ]).lower()
        if any(token in marker for token in (
            "product", "tile", "sku-item", "search-result", "grid-item", "item-card", "productcard",
        )):
            return parent
        if fallback is element and (parent.find("img") is not None or parent.has_attr("data-product-id")
                                    or parent.has_attr("data-tcin") or parent.has_attr("data-asin")):
            text = engine.clean_text(parent.get_text(" ", strip=True), 2500)
            if len(text) <= 2200:
                fallback = parent
    return fallback


def _product_card(anchor, base_url: str, retailer: str) -> dict[str, Any] | None:
    retailer_key = engine._retailer_key(retailer)
    card = _nearest_product_container(anchor)

    url_keys = ("href", "data-product-url", "data-pdp-url", "data-url", "data-href", "data-product-link")
    raw_url = ""
    for element in (anchor, card):
        for key in url_keys:
            raw = element.get(key)
            if raw:
                raw_url = engine.clean_text(raw, 1200)
                break
        if raw_url:
            break

    def find_identifier(keys: tuple[str, ...]) -> str:
        elements = [anchor, card]
        elements.extend(card.find_all(True, limit=40))
        for element in elements:
            for key in keys:
                value = engine.clean_text(element.get(key), 100)
                if value:
                    return value
        return ""

    tcin = find_identifier(("data-tcin", "data-product-tcin", "data-item-id"))
    asin = find_identifier(("data-asin", "data-item-asin"))
    if not raw_url and retailer_key == "target" and re.fullmatch(r"\d{6,14}", tcin or ""):
        raw_url = f"/p/-/A-{tcin}"
    if not raw_url and retailer_key == "amazon" and re.fullmatch(r"[A-Z0-9]{10}", asin or "", re.I):
        raw_url = f"/dp/{asin}"
    product_url = _same_host_product_url(raw_url, base_url, retailer_key)
    if not product_url:
        return None

    title_candidates: list[str] = []
    for element in (anchor, card):
        title_candidates.extend(_attribute_text_values(element))
    for element in card.select(
        "h1,h2,h3,h4,[itemprop='name'],[data-testid*='title'],[data-qa*='title'],"
        "[class*='product-title'],[class*='productTitle'],[class*='title'],[class*='name']"
    )[:16]:
        title_candidates.extend(_attribute_text_values(element))
        title_candidates.append(engine.clean_text(element.get_text(" ", strip=True), 300))
    for image_tag in card.find_all("img")[:10]:
        title_candidates.extend(_attribute_text_values(image_tag))
    # Some cards expose their product name on a sibling button/span rather than
    # the anchor. Read only likely title/name nodes from this bounded tile.
    for element in card.find_all(["a", "span", "div", "button"], limit=60):
        title_candidates.extend(_attribute_text_values(element))

    useful: dict[str, str] = {}
    for raw in title_candidates:
        title = engine.clean_product_title(raw)
        if not _pokemon_title_allowed(title):
            continue
        key = engine.normalize_match_text(title)
        if key:
            previous = useful.get(key)
            if previous is None or len(title) > len(previous):
                useful[key] = title
    if not useful:
        return None
    title = max(useful.values(), key=_candidate_score)

    card_text = engine.clean_text(card.get_text(" ", strip=True), 4000)
    price_raw = ""
    for element in card.find_all(True):
        for attr in ("data-price", "data-current-price", "data-product-price", "data-price-value", "content"):
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
            marker = " ".join([
                str(element.get("class", "")), str(element.get("id", "")),
                str(element.get("data-testid", "")), str(element.get("data-qa", "")),
            ]).lower()
            if any(token in marker for token in ("stock", "availability", "inventory", "fulfillment")):
                availability = engine.normalize_availability(
                    element.get("aria-label") or element.get("data-availability")
                    or element.get("data-stock-status") or element.get_text(" ", strip=True)
                )
                if availability != "unknown":
                    break
    sku = find_identifier(("data-product-id", "data-sku", "data-tcin", "data-item-id", "data-asin", "data-productid"))
    if not sku:
        sku = tcin or asin
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
    candidates = list(soup.find_all("a", href=True))
    # Retailer cards occasionally expose navigation only as data-product-url/data-url.
    candidates.extend(soup.select(
        "[data-product-url], [data-pdp-url], [data-product-link], [data-url], [data-href]"
    ))
    candidates.extend(soup.select("[data-tcin], [data-asin], [data-product-id], [data-productid], [data-sku]"))
    seen_candidates: set[int] = set()
    for candidate in candidates:
        marker = id(candidate)
        if marker in seen_candidates:
            continue
        seen_candidates.add(marker)
        item = _product_card(candidate, base_url, retailer)
        if not item:
            continue
        found.setdefault(item["url"], item)
        if len(found) >= limit:
            break
    return list(found.values())


def extract_retailer_products_recovery(soup: BeautifulSoup, base_url: str, retailer: str, limit: int) -> list[dict[str, Any]]:
    existing = _previous_extract_retailer_products(soup, base_url, retailer, limit)
    if len(existing) >= limit:
        if engine_patch._SCOPED_SCAN_ACTIVE:
            for item in existing[:limit]:
                item["pokemon_scoped"] = True
        return existing[:limit]
    remaining = max(0, limit - len(existing))
    additions = _extract_retailer_json_products(soup, base_url, retailer, remaining)
    additions.extend(_extract_retailer_dom_products(soup, base_url, retailer, max(0, remaining - len(additions))))
    combined = engine.deduplicate_products(existing + additions)
    if engine_patch._SCOPED_SCAN_ACTIVE:
        for item in combined:
            item["pokemon_scoped"] = True
    return combined[:limit]


def extract_json_products_recovery(payload: Any, base_url: str, retailer: str) -> list[dict[str, Any]]:
    existing = _previous_extract_json_products(payload, base_url, retailer)
    if len(existing) >= 80:
        if engine_patch._SCOPED_SCAN_ACTIVE:
            for item in existing:
                item["pokemon_scoped"] = True
        return existing
    additions = []
    retailer_key = engine._retailer_key(retailer)
    for node in engine._walk_json(payload):
        item = _product_from_json_node(node, base_url, retailer)
        if item:
            additions.append(item)
        if len(existing) + len(additions) >= 100:
            break
    combined = engine.deduplicate_products(existing + additions)
    if engine_patch._SCOPED_SCAN_ACTIVE:
        for item in combined:
            item["pokemon_scoped"] = True
    return combined


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

    # A source is only fully healthy when every configured page responds.
    # Retain parsed listings from reachable pages, but label 1/3 or 2/3 as PARTIAL.
    successful = int(status.get("successful_urls", 0) or 0)
    configured = int(status.get("configured_urls", 0) or 0)
    failed_diagnostics = [entry for entry in _FETCH_DIAGNOSTICS if entry.get("error")]
    partial = bool(configured and successful < configured)
    if partial:
        status["response_health"] = {
            "successful": successful,
            "configured": configured,
            "failed": max(0, configured - successful),
            "partial": True,
        }
        status["status"] = "warning"
        parsed_count = int(status.get("items_found", 0) or 0)
        if source.get("type") in {"catalog", "product"}:
            saved_products = saved_state.get("products", {}) if isinstance(saved_state.get("products"), dict) else {}
            retained = max(parsed_count, old_product_count, len(saved_products))
            if retained:
                saved_state["last_item_count"] = retained
                status["last_known_items"] = retained
                status["current_items_found"] = parsed_count
        prefix = f"PARTIAL: {successful}/{configured} configured pages responded; {max(0, configured - successful)} failed."
        if parsed_count:
            prefix += f" {parsed_count} item(s) were recognized on reachable pages."
        else:
            prefix += " No product/news items were recognized on the pages that responded."
        error_types = []
        for entry in failed_diagnostics[:3]:
            error = str(entry.get("error", ""))
            kind = error.split(":", 1)[0][:42] if error else "Request failed"
            if kind not in error_types:
                error_types.append(kind)
        if error_types:
            prefix += " Failed-page errors: " + ", ".join(error_types) + "."
        existing = str(status.get("message", ""))
        status["message"] = (prefix + " " + existing)[:900]
    elif configured:
        status["response_health"] = {
            "successful": successful,
            "configured": configured,
            "failed": 0,
            "partial": False,
        }

    # Include compact, non-sensitive diagnostics so a parser miss can be separated
    # from an anti-bot shell, empty application shell, or selector regression.
    diagnostics = [entry for entry in _FETCH_DIAGNOSTICS if "error" not in entry]
    if diagnostics and (status.get("status") == "warning" or partial):
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
        status["message"] = (status.get("message", "") + " Response diagnostics: " + " | ".join(summaries))[:1100]
    return events, result


# Install adapters before run.py binds these callables from engine.
engine.extract_retailer_products = extract_retailer_products_recovery
engine.extract_json_products = extract_json_products_recovery
engine.parse_rss = parse_rss_with_pokebeach_html
engine.fetch = fetch_with_diagnostics
engine.scan_source = scan_source_with_recovery
