"""Targeted GameStop product-link support and clearer access-block detection.

Imported after engine_recovery_patch so the existing scanner can use the added
GameStop PDP patterns without changing other retailer URL rules. The bootstrap
imports below install the shared payload and source-health fixes into the
production monitor as well as in the unit-test process.
"""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urljoin, urlparse

import engine
import engine_recovery_patch as recovery


_ORIGINAL_SAME_HOST_PRODUCT_URL = recovery._same_host_product_url
_ORIGINAL_EXTRACT_RETAILER_DOM_PRODUCTS = recovery._extract_retailer_dom_products
_ORIGINAL_RESPONSE_DIAGNOSTIC = recovery._response_diagnostic

# Some GameStop search result cards use a slug + numeric product id URL rather
# than /p/ or /product/. Restrict this relaxation to the gamestop.com host.
_GAMESTOP_ID_PATH = re.compile(
    r"/(?:[a-z0-9][a-z0-9-]*/){1,5}(?:p)?\d{5,}(?:\.html)?/?$",
    re.I,
)
_GAMESTOP_QUERY_KEYS = ("pid", "productid", "product_id", "sku")


def same_host_product_url_with_gamestop(raw_url: str, base_url: str, retailer_key: str) -> str:
    known = _ORIGINAL_SAME_HOST_PRODUCT_URL(raw_url, base_url, retailer_key)
    if known or retailer_key != "gamestop" or not raw_url:
        return known

    absolute = urljoin(base_url, raw_url)
    parsed = urlparse(absolute)
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    host = parsed.netloc.lower().removeprefix("www.")
    if parsed.scheme not in {"http", "https"} or base_host != "gamestop.com" or host not in {
        "gamestop.com", "m.gamestop.com"
    }:
        return ""

    path = parsed.path.lower().rstrip("/")
    if path.startswith(("/search", "/search-new", "/search-old", "/account", "/cart", "/checkout")):
        return ""

    has_product_id = bool(_GAMESTOP_ID_PATH.search(parsed.path))
    if not has_product_id:
        query = parse_qs(parsed.query)
        has_product_id = any(
            value and any(re.fullmatch(r"[a-z0-9-]{5,}", part, re.I) for part in value)
            for key, value in query.items() if key.lower() in _GAMESTOP_QUERY_KEYS
        )

    return engine.stable_url(absolute) if has_product_id else ""


def extract_retailer_dom_products_with_pid(soup, base_url: str, retailer: str, limit: int):
    if engine._retailer_key(retailer) == "gamestop":
        for element in soup.select("[data-pid]"):
            if not element.get("data-product-id"):
                element["data-product-id"] = element.get("data-pid", "")
    return _ORIGINAL_EXTRACT_RETAILER_DOM_PRODUCTS(soup, base_url, retailer, limit)


def response_diagnostic_with_product_markers(body: str, url: str):
    """Include structural clues when a large retailer page parses empty."""
    diagnostic = _ORIGINAL_RESPONSE_DIAGNOSTIC(body, url)
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(body, "html.parser")
    marker_nodes = []
    for selector in (
        ".product-tile", ".product-tile-wrapper", "[data-pid]", "[data-product-id]",
        "[data-testid*='product']", "[class*='product-tile']",
    ):
        marker_nodes.extend(soup.select(selector))
    unique_markers = len({id(element) for element in marker_nodes})
    pid_count = len(soup.select("[data-pid]"))
    json_keys = []
    for script in soup.find_all("script", attrs={"type": re.compile(r"json", re.I)})[:4]:
        raw = script.string or script.get_text(" ", strip=True)
        try:
            payload = json.loads(raw) if raw else None
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict):
            json_keys.extend(str(key) for key in list(payload)[:8])
        elif isinstance(payload, list):
            json_keys.append(f"array[{len(payload)}]")
    shape = f"product markers={unique_markers}, data-pid={pid_count}"
    if json_keys:
        shape += ", JSON keys=" + "/".join(dict.fromkeys(json_keys))[:90]
    title = str(diagnostic.get("title") or "").strip()
    diagnostic["title"] = (title + "; " + shape).strip("; ")[:150]
    return diagnostic


recovery._same_host_product_url = same_host_product_url_with_gamestop
recovery._extract_retailer_dom_products = extract_retailer_dom_products_with_pid
recovery._response_diagnostic = response_diagnostic_with_product_markers
recovery._PRODUCT_PATH_RE = re.compile(
    recovery._PRODUCT_PATH_RE.pattern + r"|/(?:[a-z0-9][a-z0-9-]*/){1,5}(?:p)?\d{5,}(?:\.html)?(?:/|$)",
    re.I,
)
recovery._CHALLENGE_RE = re.compile(
    recovery._CHALLENGE_RE.pattern + r"|pardon our interruption",
    re.I,
)

# These modules must load after the GameStop hooks above. They install the
# corrected local-record JSON picker, source health states, and non-destructive
# public-page patcher. run.py already imports this diagnostics module.
import retailer_payload_patch  # noqa: F401,E402
import source_health_patch  # noqa: F401,E402
import public_ui_fixes_patch  # noqa: F401,E402
