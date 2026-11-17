"""Deterministic public-page, product and RSS monitoring for PokéDrop Watch."""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


STOCK_IN = {"instock", "limitedavailability", "onlineonly", "presale", "preorder"}
STOCK_OUT = {"outofstock", "soldout", "discontinued", "backorder"}
PRODUCT_PATH_HINTS = (
    "/product", "/products/", "/ip/", "/dp/", "/gp/product/", "/gp/aw/d/",
    "/site/", "/p/", "/item/", "/product-detail/", "/-/a-", "/a-",
)
NON_PRODUCT_PATH_HINTS = (
    "product-reviews", "customer-reviews", "review/", "reviews/", "bestsellers",
    "offer-listing", "help/", "gp/slredirect", "cart", "wishlist",
)
POKEMON_TERMS = (
    "pokemon", "pikachu", "charizard", "charmander", "squirtle", "bulbasaur",
    "eevee", "jolteon", "vaporeon", "flareon", "mewtwo", "mew", "snorlax",
    "gengar", "lucario", "greninja", "gengar", "psyduck", "jigglypuff",
    "dragonite", "gardevoir", "umbreon", "espeon", "arcanine", "lapras",
    "ditto", "magikarp", "gyarados", "rayquaza", "mimikyu", "piplup",
    "turtwig", "chimchar", "totodile", "cyndaquil", "chikorita", "treecko",
    "torchic", "mudkip", "lugia", "ho oh", "celebi", "kyogre", "groudon",
    "dialga", "palkia", "giratina", "arceus", "zekrom", "reshiram", "kyurem",
    "xerneas", "yveltal", "solgaleo", "lunala", "zacian", "zamazenta",
    "koraidon", "miraidon", "sylveon", "glaceon", "leafeon", "vulpix",
    "ninetales", "machamp", "blastoise", "venusaur", "scizor", "heracross",
    "cinderace", "sprigatito", "fuecoco", "quaxly", "pawmi", "team rocket",
)
NOISE_TITLE_RE = re.compile(
    r"^(?:\d+\s*(?:ratings?|reviews?)|see options?|view options?|" 
    r"customer reviews?|read reviews?|sponsored|shop now|learn more|" 
    r"add to cart|buy now|quick view|view details?)$", re.I
)
PRICE_RE = re.compile(r"(?:\$|USD\s*)(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_text(value: Any, limit: int = 500) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    text = re.sub(r"\s+", " ", html.unescape(str(value))).strip()
    return text[:limit]


def clean_product_title(value: Any) -> str:
    """Remove retailer UI wrappers, price snippets and duplicated title tails."""
    text = clean_text(value, 500)
    text = re.sub(r"^(?:deal|sale|sponsored|clearance|online deal)\s*[,|:–—-]\s*", "", text, flags=re.I)
    # Some retailer product tiles expose one combined accessible label such as:
    # "Deal, Pokémon ... Surprise Box, Price Now $72.89 Was $89.99".
    tail = re.search(
        r"(?:[,|•·]\s*)?(?:price(?:\s+now)?|now|was)\s*[:=]?\s*\$\s*\d",
        text,
        flags=re.I,
    )
    if tail and tail.start() >= 10:
        text = text[:tail.start()].rstrip(" ,|•·-–—")
    text = re.sub(
        r'\s*(?:[,|•·]\s*)?(?:see options?|view options?|add to cart|quick view|\"?\d+ ratings?\"?)\s*$',
        "",
        text,
        flags=re.I,
    )
    # A few retailer accessibility labels repeat the final product phrase.
    tokens = text.split()
    for width in range(min(7, len(tokens) // 2), 1, -1):
        if [t.casefold() for t in tokens[-width:]] == [t.casefold() for t in tokens[-2*width:-width]]:
            tokens = tokens[:-width]
            break
    return clean_text(" ".join(tokens), 240)


def stable_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    # Amazon exposes the same ASIN through /dp/, /gp/product/, mobile and
    # tracking-heavy URLs. Canonicalize those to one stable product identity.
    if host.endswith("amazon.com"):
        match = re.search(r"/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:/|$)", path, re.I)
        if match:
            return f"{parsed.scheme.lower()}://{host}/dp/{match.group(1).upper()}"
    # Remove trailing retailer referral fragments while preserving product IDs.
    path = re.sub(r"/ref=[^/]+$", "", path, flags=re.I)
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def money(value: Any) -> tuple[float | None, str]:
    if value is None:
        return None, ""
    if isinstance(value, (int, float)):
        return float(value), "USD"
    match = re.search(r"(\d+(?:[,.]\d{1,2})?)", str(value).replace(",", ""))
    if not match:
        return None, ""
    try:
        return float(match.group(1)), "USD"
    except ValueError:
        return None, ""


def normalize_availability(value: Any) -> str:
    raw = clean_text(value, 120).lower()
    token = raw.rsplit("/", 1)[-1].replace(" ", "").replace("-", "").replace("_", "")
    if token in STOCK_IN:
        return "in_stock" if token not in {"presale", "preorder"} else "preorder"
    if token in STOCK_OUT:
        return "out_of_stock"
    if any(word in raw for word in ("outofstock", "sold out", "unavailable", "not available")):
        return "out_of_stock"
    if any(word in raw for word in ("instock", "in stock", "available now", "add to cart")):
        return "in_stock"
    if "preorder" in raw or "pre-order" in raw:
        return "preorder"
    return "unknown"


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def normalize_match_text(value: Any) -> str:
    text = clean_text(value, 1200).lower().replace("é", "e").replace("’", "'")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def is_pokemon_relevant(value: Any) -> bool:
    text = normalize_match_text(value)
    if not text:
        return False
    padded = f" {text} "
    return any(f" {term} " in padded for term in POKEMON_TERMS)


def is_valid_event(event: dict[str, Any]) -> bool:
    """Keep scoped Pokémon news and verified Pokémon product-title events."""
    return event.get("category") == "news" or event.get("type") == "news" or is_pokemon_relevant(event.get("title", ""))


def is_email_eligible_event(event: dict[str, Any]) -> bool:
    """Only send observable changes; first-seen listings have unverified release dates."""
    return event.get("type") in {"restock", "price_drop", "price_change", "news"}


def infer_category(title: Any, fallback: str = "collectibles") -> str:
    text = normalize_match_text(title)
    if fallback == "news":
        return "news"

    # Check unmistakable game-platform terms first. Set names such as Scarlet &
    # Violet must not be treated as video games when they appear on TCG products.
    strong_game_terms = (
        "nintendo switch", "switch game", "video game", "game software",
        "switch cartridge", "nintendo switch game", "pokemon game for switch",
    )
    tcg_terms = (
        "trading card", "pokemon tcg", "booster", "elite trainer", "etb",
        "trainer box", "card collection", "battle deck", "theme deck", "blister",
        "pokemon cards", "pokemon card game", "card sleeves", "trading cards", "tcg",
        "prismatic evolutions", "destined rivals", "journey together",
        "surprise box", "pokemon trading card game",
    )
    plush_terms = ("plush", "stuffed animal", "soft toy", "plushie")
    accessory_terms = (
        "binder", "deck box", "playmat", "sleeves", "backpack", "keychain", "key chain",
        "apparel", "shirt", "hoodie", "hat", "blanket", "wallet", "bottle",
        "accessory", "accessories", "lunch box", "pin set",
    )
    if any(term in text for term in strong_game_terms):
        return "games"
    if any(term in text for term in tcg_terms):
        return "tcg"
    if any(term in text for term in plush_terms):
        return "plush"
    if any(term in text for term in accessory_terms):
        return "accessories"
    return fallback if fallback in {"tcg", "plush", "games", "accessories", "collectibles"} else "collectibles"


def _first_image(image: Any, base_url: str = "") -> str:
    if isinstance(image, list):
        image = next((value for value in image if value), "")
    if isinstance(image, dict):
        image = (
            image.get("url") or image.get("contentUrl") or image.get("thumbnailUrl")
            or image.get("src") or image.get("large") or image.get("largeImage") or ""
        )
    value = clean_text(image, 1000)
    return urljoin(base_url, value) if value else ""


def _is_noise_title(value: Any) -> bool:
    text = clean_text(value, 240)
    return not text or bool(NOISE_TITLE_RE.fullmatch(text)) or len(text) < 10


def _card_ancestor(anchor):
    """Find the nearest bounded product tile rather than a rating/link wrapper."""
    fallback = None
    for parent in anchor.parents:
        if getattr(parent, "name", None) in {"body", "html"}:
            break
        text = clean_text(parent.get_text(" ", strip=True), 3500)
        if not text:
            continue
        classes = " ".join(parent.get("class", [])) if parent.get("class") else ""
        marker = " ".join([
            classes,
            clean_text(parent.get("id"), 120),
            clean_text(parent.get("data-testid"), 120),
            clean_text(parent.get("data-component-type"), 120),
            clean_text(parent.get("data-cy"), 120),
        ]).lower()
        marked_tile = any(token in marker for token in (
            "product", "sku-item", "search-result", "producttile", "product-tile", "grid-item"
        ))
        has_image = parent.find("img") is not None
        has_price = PRICE_RE.search(text) is not None
        if marked_tile and len(text) <= 3500:
            return parent
        if fallback is None and has_image and has_price and len(text) <= 2200:
            fallback = parent
    return fallback or anchor.parent


def _card_title(card, anchor) -> str:
    candidates: list[str] = []
    for selector in ("h2", "h3", "[data-cy*='title']", "[data-testid*='title']", "[class*='product-title']", "[class*='title-recipe']"):
        try:
            for element in card.select(selector)[:4]:
                candidates.append(clean_text(element.get_text(" ", strip=True), 240))
        except Exception:
            pass
    for image in card.find_all("img")[:5]:
        candidates.extend([
            clean_text(image.get("alt"), 240),
            clean_text(image.get("title"), 240),
        ])
    for element in card.find_all(["a", "span"], limit=45):
        if element is anchor or element.get("aria-label") or element.get("title"):
            candidates.extend([
                clean_text(element.get("aria-label"), 240),
                clean_text(element.get("title"), 240),
                clean_text(element.get_text(" ", strip=True), 240),
            ])
    useful = []
    seen = set()
    for raw_value in candidates:
        value = clean_product_title(raw_value)
        if _is_noise_title(value) or not is_pokemon_relevant(value):
            continue
        normalized = normalize_match_text(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        # Prefer descriptive product names rather than a generic CTA or short brand label.
        score = min(len(value), 180) + (35 if "pokemon" in normalized else 0)
        if any(term in normalized for term in ("booster", "plush", "figure", "elite trainer", "collection", "nintendo switch")):
            score += 25
        useful.append((score, value))
    if not useful:
        return ""
    return max(useful, key=lambda item: item[0])[1]


def _image_from_card(card, base_url: str) -> str:
    """Find a real product image while skipping lazy-load placeholders."""
    image_keys = (
        "data-a-hires", "data-old-hires", "data-image-src", "data-image-url", "data-original-src",
        "data-original", "data-lazy-src", "data-src", "src",
    )

    def usable(raw: Any) -> str:
        value = clean_text(raw, 1200)
        if not value or value.startswith(("data:", "blob:", "javascript:")):
            return ""
        low = value.lower()
        if any(token in low for token in ("spacer.gif", "transparent.gif", "pixel.gif", "1x1.gif", "placeholder.svg")):
            return ""
        absolute = urljoin(base_url, value)
        return absolute if urlparse(absolute).scheme in {"http", "https"} else ""

    for image in card.find_all("img")[:12]:
        # Amazon frequently stores its real responsive image candidates in a
        # JSON map instead of src/srcset. Select the largest declared variant.
        dynamic = image.get("data-a-dynamic-image")
        if dynamic:
            try:
                candidates = json.loads(dynamic)
                if isinstance(candidates, dict):
                    ordered = sorted(
                        candidates.items(),
                        key=lambda entry: (float(entry[1][0]) * float(entry[1][1]))
                        if isinstance(entry[1], (list, tuple)) and len(entry[1]) >= 2 else 0,
                        reverse=True,
                    )
                    for raw_url, _dimensions in ordered:
                        candidate = usable(raw_url)
                        if candidate:
                            return candidate
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        for key in image_keys:
            candidate = usable(image.get(key))
            if candidate:
                return candidate
        # srcset often contains the actual loaded image while src is a tiny placeholder.
        srcsets = [image.get("srcset", "")]
        picture = image.find_parent("picture")
        if picture is not None:
            srcsets.extend(source.get("srcset", "") for source in picture.find_all("source"))
        options: list[tuple[float, str]] = []
        for srcset in srcsets:
            for entry in clean_text(srcset, 4000).split(","):
                parts = entry.strip().split()
                if not parts:
                    continue
                candidate = usable(parts[0])
                if not candidate:
                    continue
                score = 1.0
                if len(parts) > 1:
                    descriptor = parts[1].lower()
                    number = re.search(r"([0-9.]+)", descriptor)
                    if number:
                        score = float(number.group(1)) * (1000 if descriptor.endswith("w") else 1)
                options.append((score, candidate))
        if options:
            return max(options, key=lambda item: item[0])[1]
    return ""


def extract_structured_products(soup: BeautifulSoup, base_url: str, retailer: str) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw.strip().strip(";"))
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _walk_json(payload):
            kind = node.get("@type", [])
            kinds = [kind] if isinstance(kind, str) else [str(k) for k in kind]
            if not any(k.lower().endswith("product") for k in kinds):
                continue
            name = clean_product_title(node.get("name"))
            raw_url = node.get("url") or node.get("@id") or ""
            product_url = urljoin(base_url, raw_url) if raw_url else ""
            if not name or not product_url or not is_pokemon_relevant(name):
                continue
            offers = node.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if not isinstance(offers, dict):
                offers = {}
            price, currency = money(offers.get("price") or offers.get("lowPrice"))
            availability = normalize_availability(offers.get("availability"))
            image = _first_image(node.get("image"), base_url)
            item = {
                "title": name,
                "url": stable_url(product_url),
                "price": price,
                "currency": clean_text(offers.get("priceCurrency") or currency or "USD", 8),
                "availability": availability,
                "image": image,
                "sku": clean_text(node.get("sku") or node.get("productID"), 80),
                "retailer": retailer,
            }
            item["category"] = infer_category(name)
            found[item["url"]] = item
    return list(found.values())


def _json_script_payloads(soup: BeautifulSoup) -> Iterable[Any]:
    """Read structured JSON blocks and common SPA hydration payloads safely."""
    decoder = json.JSONDecoder()
    for script in soup.find_all("script"):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw or len(raw) > 2_500_000:
            continue
        script_id = clean_text(script.get("id"), 100).lower()
        script_type = clean_text(script.get("type"), 100).lower()
        interesting = (
            "json" in script_type
            or any(token in script_id for token in ("next", "state", "apollo", "preload", "product", "data"))
            or any(token in raw[:50000].lower() for token in ("productid", "product_id", "productname", "producttitle", "sku"))
        )
        if not interesting:
            continue
        stripped = raw.strip()
        try:
            yield json.loads(stripped)
            continue
        except (json.JSONDecodeError, TypeError):
            pass
        # Support common assignments such as window.__STATE__ = {...}; without
        # evaluating JavaScript. Only JSONDecoder's strict JSON parser is used.
        for index, char in enumerate(stripped):
            if char not in "[{":
                continue
            try:
                value, _end = decoder.raw_decode(stripped[index:])
                yield value
                break
            except json.JSONDecodeError:
                continue


def _node_string(node: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return clean_text(value, 1200)
        if isinstance(value, (int, float)) and key in {"sku", "productId", "id"}:
            return str(value)
        if isinstance(value, dict):
            for nested_key in (
                "url", "src", "value", "amount", "displayValue", "formattedValue",
                "current_retail", "currentRetail", "price", "formattedPrice", "priceString", "highRes",
            ):
                nested = value.get(nested_key)
                if isinstance(nested, (str, int, float)) and str(nested).strip():
                    return clean_text(nested, 1200)
    return ""


def extract_json_products(payload: Any, base_url: str, retailer: str) -> list[dict[str, Any]]:
    """Extract product-like records from a JSON API response without executing code."""
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    found: dict[str, dict[str, Any]] = {}
    name_keys = ("name", "productName", "productTitle", "title", "displayName", "webProductName", "itemName", "shortDescription")
    url_keys = ("url", "canonicalUrl", "productUrl", "product_url", "pdpUrl", "seoUrl", "href", "link", "productPageUrl")
    price_keys = ("price", "currentPrice", "current_retail", "currentRetail", "salePrice", "offerPrice", "priceValue", "unitPrice", "displayPrice", "formattedPrice")
    image_keys = ("image", "imageUrl", "primaryImage", "thumbnail", "thumbnailUrl", "largeImage", "src", "image_url", "heroImage")
    for node in _walk_json(payload):
        title = clean_product_title(_node_string(node, name_keys))
        if not title or _is_noise_title(title) or not is_pokemon_relevant(title):
            continue
        raw_url = _node_string(node, url_keys)
        if not raw_url:
            continue
        product_url = urljoin(base_url, raw_url)
        parsed = urlparse(product_url)
        host = parsed.netloc.lower().removeprefix("www.")
        if parsed.scheme not in {"http", "https"} or not host:
            continue
        if not (host == base_host or host.endswith("." + base_host)):
            continue
        path = parsed.path.lower()
        retailer_key = _retailer_key(retailer)
        target_product = retailer_key == "target" and bool(re.search(r"/-/a-\d+", path, re.I))
        bestbuy_product = retailer_key == "best-buy" and "/site/" in path and bool(re.search(r"\.p(?:/|$)", path, re.I))
        gamestop_product = retailer_key == "gamestop" and "/pokemon/" in path and len([part for part in path.split("/") if part]) >= 2
        if not (target_product or bestbuy_product or gamestop_product or any(hint in path for hint in PRODUCT_PATH_HINTS) or re.search(r"/(?:sku/|product/)[a-z0-9-]+", path)):
            continue
        price_raw = _node_string(node, price_keys)
        price, currency = money(price_raw)
        image_value = next((node.get(key) for key in image_keys if node.get(key)), "")
        image = _first_image(image_value, base_url)
        availability = normalize_availability(_node_string(node, ("availability", "availabilityStatus", "stockStatus", "inventoryStatus", "fulfillmentStatus")))
        sku = _node_string(node, ("sku", "productId", "tcin", "itemId", "id"))
        item = {
            "title": title,
            "url": stable_url(product_url),
            "price": price,
            "currency": clean_text(node.get("currency") or node.get("priceCurrency") or currency or "USD", 8),
            "availability": availability,
            "image": image,
            "sku": sku[:80],
            "retailer": retailer,
            "category": infer_category(title),
        }
        found[item["url"]] = item
    return list(found.values())


def extract_embedded_products(soup: BeautifulSoup, base_url: str, retailer: str) -> list[dict[str, Any]]:
    """Extract product entities from retailer SPA hydration JSON (no JS execution)."""
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    found: dict[str, dict[str, Any]] = {}
    name_keys = ("name", "productName", "productTitle", "title", "displayName", "webProductName", "itemName", "shortDescription")
    url_keys = ("url", "canonicalUrl", "productUrl", "product_url", "pdpUrl", "seoUrl", "href", "link")
    price_keys = ("price", "currentPrice", "salePrice", "offerPrice", "priceValue", "unitPrice", "displayPrice")
    image_keys = ("image", "imageUrl", "primaryImage", "thumbnail", "thumbnailUrl", "largeImage", "src", "image_url", "heroImage")
    for payload in _json_script_payloads(soup):
        for item in extract_json_products(payload, base_url, retailer):
            found[item["url"]] = item
    return list(found.values())


def deduplicate_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse repeated tiles for the same exact product title at one retailer."""
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    def quality(item: dict[str, Any]) -> int:
        return (
            (4 if item.get("image") else 0)
            + (3 if item.get("price") is not None else 0)
            + (2 if item.get("availability") not in {None, "unknown"} else 0)
            + (1 if item.get("sku") else 0)
            + min(len(clean_text(item.get("title"))), 240) // 60
        )
    for item in products:
        title_key = normalize_match_text(item.get("title", ""))
        retailer_key = _retailer_key(item.get("retailer", ""))
        if not title_key:
            continue
        key = (retailer_key, title_key)
        current = selected.get(key)
        if current is None or quality(item) > quality(current):
            selected[key] = item
    return list(selected.values())


def extract_catalog_links(soup: BeautifulSoup, base_url: str, retailer: str, limit: int) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor.get("href", ""))
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"}:
            continue
        host = parsed.netloc.lower().removeprefix("www.")
        if host and not (host == base_host or host.endswith("." + base_host)):
            continue
        path = parsed.path.lower()
        if any(hint in path for hint in NON_PRODUCT_PATH_HINTS):
            continue
        retailer_key = _retailer_key(retailer)
        target_product = retailer_key == "target" and bool(re.search(r"/-/a-\d+", path, re.I))
        bestbuy_product = retailer_key == "best-buy" and "/site/" in path and bool(re.search(r"\.p(?:/|$)", path, re.I))
        gamestop_product = retailer_key == "gamestop" and "/pokemon/" in path and len([part for part in path.split("/") if part]) >= 2
        if not (target_product or bestbuy_product or gamestop_product or any(hint in path for hint in PRODUCT_PATH_HINTS)):
            continue

        card = _card_ancestor(anchor)
        title = _card_title(card, anchor)
        if not title:
            continue
        stable = stable_url(href)
        if stable in found:
            continue
        card_text = clean_text(card.get_text(" ", strip=True), 2200)
        price_match = PRICE_RE.search(card_text)
        price_value, currency = money(price_match.group(1)) if price_match else (None, "USD")
        availability = normalize_availability(card_text)
        image_url = _image_from_card(card, base_url)
        found[stable] = {
            "title": title,
            "url": stable,
            "price": price_value,
            "currency": currency or "USD",
            "availability": availability,
            "image": image_url,
            "sku": "",
            "retailer": retailer,
            "category": infer_category(title),
        }
        if len(found) >= limit:
            break
    return list(found.values())

def extract_retailer_products(soup: BeautifulSoup, base_url: str, retailer: str, limit: int) -> list[dict[str, Any]]:
    """Combine retailer structured data, SPA payloads and product-tile links."""
    products: list[dict[str, Any]] = []
    products.extend(extract_structured_products(soup, base_url, retailer))
    products.extend(extract_embedded_products(soup, base_url, retailer))
    products.extend(extract_catalog_links(soup, base_url, retailer, limit))
    products = [item for item in products if is_pokemon_relevant(item.get("title", "")) and not _is_noise_title(item.get("title", ""))]
    return deduplicate_products(products)[:limit]


def enrich_prices_from_page(soup: BeautifulSoup, products: list[dict[str, Any]]) -> None:
    # Structured data above is preferred. This catches simple product detail pages.
    meta_price = soup.find("meta", attrs={"property": "product:price:amount"}) or soup.find("meta", attrs={"itemprop": "price"})
    meta_currency = soup.find("meta", attrs={"property": "product:price:currency"}) or soup.find("meta", attrs={"itemprop": "priceCurrency"})
    if meta_price and products:
        val, _ = money(meta_price.get("content"))
        if val is not None:
            products[0]["price"] = val
            products[0]["currency"] = clean_text(meta_currency.get("content") if meta_currency else "USD", 8)


def parse_product_page(html_text: str, url: str, retailer: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text, "html.parser")
    products = extract_structured_products(soup, url, retailer)
    if products:
        return products[0]
    title = clean_text((soup.find("meta", property="og:title") or {}).get("content") if soup.find("meta", property="og:title") else soup.title.get_text(" ", strip=True) if soup.title else url, 240)
    desc = soup.find("meta", attrs={"name": "description"})
    body_text = clean_text(soup.get_text(" ", strip=True), 12000).lower()
    price = None
    currency = "USD"
    price_meta = soup.find("meta", attrs={"property": "product:price:amount"}) or soup.find("meta", attrs={"itemprop": "price"})
    if price_meta:
        price, _ = money(price_meta.get("content"))
    if price is None:
        match = PRICE_RE.search(body_text)
        if match:
            price, _ = money(match.group(1))
    availability = "unknown"
    for selector in [
        {"itemprop": "availability"},
        {"class": re.compile(r"availability|stock|inventory", re.I)},
        {"id": re.compile(r"availability|stock|inventory", re.I)},
    ]:
        tag = soup.find(attrs=selector)
        if tag:
            availability = normalize_availability(tag.get("href") or tag.get("content") or tag.get_text(" ", strip=True))
            if availability != "unknown":
                break
    if availability == "unknown":
        if any(p in body_text for p in ("out of stock", "sold out", "currently unavailable", "temporarily unavailable")):
            availability = "out_of_stock"
        elif any(p in body_text for p in ("add to cart", "in stock", "available now")):
            availability = "in_stock"
        elif "pre-order" in body_text or "preorder" in body_text:
            availability = "preorder"
    image_tag = soup.find("meta", property="og:image")
    return {
        "title": title or clean_text(desc.get("content") if desc else url, 240),
        "url": stable_url(url),
        "price": price,
        "currency": currency,
        "availability": availability,
        "image": urljoin(url, clean_text(image_tag.get("content") if image_tag else "", 1000)),
        "sku": "",
        "retailer": retailer,
        "category": infer_category(title, "collectibles"),
    }


def parse_rss(xml_text: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"RSS/XML could not be parsed: {exc}") from exc
    entries = root.findall(".//item")
    if not entries:
        entries = [el for el in root.iter() if el.tag.split("}")[-1].lower() == "entry"]
    items = []
    for entry in entries[:50]:
        values: dict[str, str] = {}
        image_url = ""
        encoded_content = ""
        for child in list(entry):
            key = child.tag.split("}")[-1].lower()
            if key == "link":
                val = child.attrib.get("href") or child.text or ""
            elif key in {"content", "encoded"}:
                val = "".join(child.itertext())
                encoded_content += " " + val
            else:
                val = "".join(child.itertext())
            values.setdefault(key, clean_text(val, 5000))
            if key in {"thumbnail", "content"} and child.attrib.get("url"):
                image_url = child.attrib.get("url")
            if key == "enclosure" and child.attrib.get("type", "").startswith("image/"):
                image_url = child.attrib.get("url", "")
        if not image_url and encoded_content:
            image_match = re.search(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)', encoded_content, re.I)
            if image_match:
                image_url = image_match.group(1)
        title = values.get("title", "")
        link = values.get("link", "")
        if not title or not link:
            continue
        summary = values.get("description") or values.get("summary") or values.get("content", "")
        identifier = values.get("guid") or values.get("id") or link
        items.append({
            "key": hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:20],
            "title": title[:240],
            "url": urljoin(source["url"], link),
            "summary": re.sub(r"<[^>]+>", " ", summary)[:420],
            "published": values.get("pubdate") or values.get("published") or values.get("updated") or "",
            "retailer": source.get("retailer") or source.get("name", "News feed"),
            "image": urljoin(source["url"], image_url) if image_url else "",
            "category": "news",
        })
    return items

def make_session(user_agent: str) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=2, connect=2, read=2, backoff_factor=1.0, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=frozenset(["GET"]))
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    effective_agent = user_agent if user_agent and "PokeDropWatch/" not in user_agent else (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    session.headers.update({
        "User-Agent": effective_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml;q=0.8,*/*;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    return session


def fetch(session: requests.Session, url: str, timeout: int) -> tuple[str, str]:
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if not any(kind in content_type for kind in ("text/html", "xml", "text/plain", "application/json", "+json")):
        raise ValueError(f"Unsupported response type: {content_type or 'unknown'}")
    return response.text, response.url


def price_text(item: dict[str, Any]) -> str:
    val = item.get("price")
    if val is None:
        return "Price not published on the monitored page"
    currency = item.get("currency") or "USD"
    symbol = "$" if currency.upper() == "USD" else f"{currency} "
    return f"{symbol}{float(val):,.2f}"


def _retailer_key(value: str) -> str:
    value = clean_text(value, 100).lower()
    value = value.replace("pokémon", "pokemon")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "other"


def event_record(event_type: str, item: dict[str, Any], source: dict[str, Any], previous_price: Any = None, detail: str = "") -> dict[str, Any]:
    identity = f"{source['id']}|{item.get('url')}|{event_type}|{item.get('price')}|{utc_now()}"
    retailer = item.get("retailer") or source.get("retailer") or source.get("name", "Source")
    category = item.get("category") or infer_category(item.get("title", ""), source.get("category") or ("news" if source.get("type") == "rss" else "collectibles"))
    return {
        "id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:18],
        "type": event_type,
        "title": clean_product_title(item.get("title") or source.get("name", "Pokémon item")),
        "url": item.get("url") or source["url"],
        "retailer": retailer,
        "retailer_key": source.get("retailer_key") or _retailer_key(retailer),
        "category": category,
        "source_name": source.get("name", "Source"),
        "source_id": source["id"],
        "price": item.get("price"),
        "currency": item.get("currency") or "USD",
        "previous_price": previous_price,
        "availability": item.get("availability", "unknown"),
        "image": item.get("image", ""),
        "release_date": clean_text(item.get("release_date") or item.get("datePublished") or "", 40),
        "summary": clean_text(item.get("summary") or detail, 420),
        "detected_at": utc_now(),
        "email_sent": False,
    }


def scan_source(session: requests.Session, source: dict[str, Any], settings: dict[str, Any], state: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.monotonic()
    source_id = source["id"]
    old_source_state = state.setdefault("items", {}).get(source_id, {})
    url = source["url"]
    # A changed primary URL represents a new search scope. Establish a fresh
    # baseline instead of announcing every pre-existing result as a new drop.
    if old_source_state.get("source_url") and old_source_state.get("source_url") != url:
        old_source_state = {}
    current_source_state: dict[str, Any] = dict(old_source_state)
    events: list[dict[str, Any]] = []
    timeout = int(settings.get("request_timeout_seconds", 25))
    kind = source["type"]
    candidate_urls = list(dict.fromkeys([url, *source.get("alternate_urls", [])]))[:4]
    fetch_errors: list[str] = []
    successful_urls: list[str] = []
    collected_products: list[dict[str, Any]] = []
    collected_entries: list[dict[str, Any]] = []
    best_final_url = url
    for candidate_url in candidate_urls:
        try:
            body, final_url = fetch(session, candidate_url, timeout)
            successful_urls.append(candidate_url)
        except Exception as exc:
            fetch_errors.append(f"{candidate_url}: {type(exc).__name__}: {str(exc)[:120]}")
            continue

        if kind == "rss":
            try:
                parsed_entries = parse_rss(body, {**source, "url": final_url})
            except Exception:
                parsed_entries = []
            collected_entries.extend(parsed_entries)
            if parsed_entries:
                best_final_url = final_url
        elif kind in {"catalog", "product"}:
            retailer = source.get("retailer", source.get("name", "Retailer"))
            if kind == "product":
                parsed_products = [parse_product_page(body, final_url, retailer)]
            else:
                try:
                    direct_payload = json.loads(body)
                except (json.JSONDecodeError, TypeError):
                    direct_payload = None
                if direct_payload is not None:
                    parsed_products = extract_json_products(direct_payload, final_url, retailer)
                else:
                    soup = BeautifulSoup(body, "html.parser")
                    parsed_products = extract_retailer_products(
                        soup, final_url, retailer,
                        int(settings.get("max_items_per_catalog", 100)),
                    )
            collected_products.extend(parsed_products)
            if parsed_products:
                best_final_url = final_url
        else:
            raise ValueError(f"Unsupported source type: {kind}")

    if not successful_urls:
        raise requests.RequestException("All configured source URLs failed. " + " | ".join(fetch_errors))

    if kind == "rss":
        entries_by_key = {item["key"]: item for item in collected_entries}
        entries = list(entries_by_key.values())
        seen = current_source_state.get("seen", {})
        if not current_source_state.get("initialized"):
            for item in entries:
                seen[item["key"]] = {"title": item["title"], "url": item["url"], "first_seen": utc_now()}
        else:
            for item in entries:
                if item["key"] not in seen:
                    events.append(event_record("news", item, source))
                    seen[item["key"]] = {"title": item["title"], "url": item["url"], "first_seen": utc_now()}
        current_source_state = {"seen": dict(list(seen.items())[-250:]), "initialized": True}
        count = len(entries)
    elif kind in {"catalog", "product"}:
        for item in collected_products:
            item["title"] = clean_product_title(item.get("title", ""))
        products = deduplicate_products([
            item for item in collected_products
            if is_pokemon_relevant(item.get("title", "")) and not _is_noise_title(item.get("title", ""))
        ])
        products = products[:int(settings.get("max_items_per_catalog", 100))]
        for item in products:
            item["category"] = infer_category(item.get("title", ""), source.get("category", "collectibles"))
            item["retailer_key"] = source.get("retailer_key") or _retailer_key(item.get("retailer") or source.get("retailer") or source.get("name", "Other"))
        previous_items = {
            key: value for key, value in current_source_state.get("products", {}).items()
            if is_pokemon_relevant(value.get("title", "")) and not _is_noise_title(value.get("title", ""))
        }
        next_items = dict(previous_items)
        for item in products:
            key = item.get("url") or item.get("sku") or normalize_match_text(item.get("title", ""))
            if not key:
                continue
            old = previous_items.get(key)
            if old is None:
                # Discovery time is not a release date or seller listing date.
                if current_source_state.get("initialized"):
                    events.append(event_record(
                        "first_seen", item, source,
                        detail="First observed by PokéDrop Watch. Original listing and release dates are unverified.",
                    ))
            else:
                was = old.get("availability", "unknown")
                now = item.get("availability", "unknown")
                if was == "out_of_stock" and now in {"in_stock", "preorder"}:
                    events.append(event_record("restock", item, source, old.get("price"), "Previously unavailable; the listing now reports availability."))
                old_price, new_price = old.get("price"), item.get("price")
                if old_price is not None and new_price is not None and float(new_price) != float(old_price):
                    direction = "price_drop" if float(new_price) < float(old_price) else "price_change"
                    events.append(event_record(direction, item, source, old_price, "Listed price changed."))
                if was == "unknown" and now in {"in_stock", "preorder"} and old.get("availability_checked"):
                    events.append(event_record("restock", item, source, old.get("price"), "The listing now reports availability."))
            item_state = dict(item)
            item_state["first_seen_at"] = old.get("first_seen_at") if old else utc_now()
            item_state["last_seen"] = utc_now()
            item_state["availability_checked"] = item.get("availability") != "unknown"
            next_items[key] = item_state
        current_source_state = {"products": dict(list(next_items.items())[-500:]), "initialized": True}
        count = len(products)
    else:
        raise ValueError(f"Unsupported source type: {kind}")

    current_source_state["last_success"] = utc_now()
    current_source_state["source_url"] = url
    current_source_state["last_item_count"] = count
    current_source_state["last_successful_urls"] = successful_urls
    elapsed_ms = int((time.monotonic() - started) * 1000)
    status_value = "ok" if count > 0 else "warning"
    attempts_text = f"Fetched {len(successful_urls)}/{len(candidate_urls)} configured URL(s). "
    if count > 0:
        status_message = attempts_text + f"{count} relevant Pokémon listing(s) recognized."
    else:
        status_message = attempts_text + "The scan found no relevant Pokémon product/feed entries; this is not a confirmed stock scan."
    if fetch_errors and successful_urls:
        status_message += f" {len(fetch_errors)} alternate request(s) failed."
    status = {
        "id": source_id,
        "name": source.get("name", source_id),
        "retailer": source.get("retailer", ""),
        "type": kind,
        "url": url,
        "response_url": best_final_url,
        "status": status_value,
        "last_checked": utc_now(),
        "items_found": count,
        "new_alerts": len(events),
        "duration_ms": elapsed_ms,
        "message": status_message,
        "notes": source.get("notes", ""),
        "successful_urls": len(successful_urls),
        "configured_urls": len(candidate_urls),
    }
    return events, {"state": current_source_state, "status": status}


def html_email(events: list[dict[str, Any]], brand: str = "PokéDrop Watch", manage_url: str = "") -> tuple[str, str, str]:
    count = len(events)
    subject_line = f"{brand}: {count} Pokémon alert{'s' if count != 1 else ''}"
    cards_html = []
    cards_text = []
    labels = {
        "new_drop": "FIRST SEEN (RELEASE UNVERIFIED)",
        "first_seen": "FIRST SEEN (RELEASE UNVERIFIED)",
        "restock": "RESTOCK",
        "price_drop": "PRICE DROP",
        "price_change": "PRICE CHANGE",
        "news": "POKÉMON NEWS",
    }
    for event in events:
        title = clean_text(event.get("title"), 240)
        link = event.get("url", "")
        safe_link = html.escape(link, quote=True)
        kind = labels.get(event.get("type"), "UPDATE")
        price = price_text(event)
        availability = event.get("availability", "unknown").replace("_", " ").title()
        previous = event.get("previous_price")
        previous_text = f"Previous price: ${float(previous):,.2f}\n" if previous is not None else ""
        summary = clean_text(event.get("summary"), 420)
        cards_text.append(
            f"{kind}\n{title}\nStore/source: {event.get('retailer', '—')}\nPrice: {price}\nAvailability: {availability}\n{previous_text}Link: {link}\n{summary}\n"
        )
        cards_html.append(f"""
          <tr><td style="padding:18px 20px;border-bottom:1px solid #ececec">
            <div style="font:700 11px Arial,sans-serif;letter-spacing:1.2px;color:#c83232;margin-bottom:7px">{html.escape(kind)}</div>
            <div style="font:700 17px Arial,sans-serif;color:#202124;line-height:1.35;margin-bottom:8px">{html.escape(title)}</div>
            <div style="font:13px Arial,sans-serif;color:#5f6368;line-height:1.7">
              <strong>Store/source:</strong> {html.escape(clean_text(event.get('retailer')))}<br>
              <strong>Price:</strong> {html.escape(price)}<br>
              <strong>Availability:</strong> {html.escape(availability)}<br>
              {f'<strong>Previous price:</strong> ${float(previous):,.2f}<br>' if previous is not None else ''}
              {html.escape(summary)}
            </div>
            <div style="margin-top:13px"><a href="{safe_link}" style="display:inline-block;padding:10px 15px;background:#c83232;color:#fff;text-decoration:none;border-radius:7px;font:700 13px Arial,sans-serif">View item / source →</a></div>
          </td></tr>
        """)
    manage_html = (
        f'<p style="margin:10px 0 0"><a href="{html.escape(manage_url, quote=True)}" '
        'style="color:#a62e2e;font-weight:700">Manage preferences or request secure unsubscribe</a></p>'
        if manage_url else ""
    )
    manage_text = f"\nManage preferences or request secure unsubscribe: {manage_url}" if manage_url else ""
    html_body = f"""<!doctype html><html><body style="margin:0;background:#f5f5f3;padding:24px 10px">
      <table role="presentation" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;margin:0 auto;background:#fff;border:1px solid #e8e8e5;border-radius:12px;overflow:hidden">
        <tr><td style="background:#c83232;padding:20px 22px;color:#fff">
          <div style="font:800 21px Arial,sans-serif">◉ {html.escape(brand)}</div>
          <div style="font:13px Arial,sans-serif;opacity:.92;margin-top:5px">{count} new Pokémon update{'s' if count != 1 else ''} detected</div>
        </td></tr>
        {''.join(cards_html)}
        <tr><td style="padding:16px 20px;background:#fafaf8;font:12px/1.6 Arial,sans-serif;color:#777">
          Automated public-page monitor. Prices and availability can change quickly; confirm on the retailer's page before purchasing. Not affiliated with Nintendo, The Pokémon Company, or any retailer.
          {manage_html}
        </td></tr>
      </table></body></html>"""
    text_body = f"{brand}\n{count} new Pokémon update(s) detected\n\n" + "\n---\n".join(cards_text) + "\nPrices and availability can change quickly. Confirm with the retailer.\n" + manage_text + "\n"
    return subject_line, html_body, text_body


def branded_sender_header(address: str, display_name: str = "PokéDrop Watch") -> str:
    """Return an RFC-compliant From header with a readable brand name."""
    return formataddr((display_name, address.strip()))


def send_email(
    events: list[dict[str, Any]],
    env: dict[str, str],
    prefix: str = "PokéDrop Watch",
    recipient: str | None = None,
    manage_url: str = "",
) -> tuple[bool, str]:
    username = env.get("SMTP_USERNAME", "").strip()
    password = env.get("SMTP_APP_PASSWORD", "").strip()
    recipient = (recipient or env.get("ALERT_EMAIL", "")).strip()
    if not (username and password and recipient):
        return False, "Email is not configured; add SMTP_USERNAME and SMTP_APP_PASSWORD plus a recipient."
    import smtplib
    host = (env.get("SMTP_HOST") or "smtp.gmail.com").strip()
    port = int(env.get("SMTP_PORT") or "587")
    subject, html_body, text_body = html_email(events, prefix, manage_url)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = branded_sender_header(username)
    msg["Reply-To"] = username
    msg["To"] = recipient
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(host, port, timeout=25) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.send_message(msg)
    return True, "Email digest sent successfully."
