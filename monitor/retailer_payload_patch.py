"""Normalize retailer hydration payload keys before product extraction.

Retailers frequently change casing and underscore conventions in JSON fields.
This layer broadens field recognition without executing scripts or inventing
product URLs. Anti-bot pages remain blocked rather than being bypassed.
"""
from __future__ import annotations

import re
from typing import Any

import engine_recovery_patch as recovery


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


_NAME_KEYS = tuple(dict.fromkeys(recovery._NAME_KEYS + (
    "product_name", "productDisplayName", "product_display_name", "shortName",
    "itemDisplayName", "webProductDisplayName", "display_name", "item_name",
    "productDescription", "product_description", "nameText",
)))
_URL_KEYS = tuple(dict.fromkeys(recovery._URL_KEYS + (
    "productURL", "productPageURL", "productDetailURL", "pdpURL", "canonicalURL",
    "productSeoUrl", "productSEOURL", "slugUrl", "productPagePath", "productPath",
    "productDetailPageUrl", "productDetailUrl", "seoPath", "urlPath", "webUrl",
)))
_PRICE_KEYS = tuple(dict.fromkeys(recovery._PRICE_KEYS + (
    "currentPriceText", "sale_price", "listPrice", "priceAmount", "formatted_price",
    "priceDisplay", "display_price", "retailPrice", "onlinePrice", "offerPriceText",
)))
_IMAGE_KEYS = tuple(dict.fromkeys(recovery._IMAGE_KEYS + (
    "imageURL", "primaryImageUrl", "primary_image_url", "imageSrc", "imageURLLarge",
    "productImageUrl", "product_image_url", "thumbnailURL", "heroImageUrl",
)))
_STOCK_KEYS = tuple(dict.fromkeys(recovery._STOCK_KEYS + (
    "onlineStock", "inStock", "isInStock", "isSellable", "availabilityText",
    "stockStatusText", "inventory_state", "onlineAvailabilityStatus",
)))


def _pick_normalized(node: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Find a requested field using case/underscore-insensitive JSON keys."""
    if not isinstance(node, dict):
        return ""
    wanted = {_normalized_key(key) for key in keys}
    # Prefer fields on the current product node before descending into child
    # offer/media objects, avoiding accidental selection of unrelated metadata.
    for key, value in node.items():
        if _normalized_key(key) in wanted:
            found = recovery._scalar(value)
            if found:
                return found
    for value in node.values():
        if isinstance(value, dict):
            found = _pick_normalized(value, keys)
            if found:
                return found
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict):
                    found = _pick_normalized(child, keys)
                    if found:
                        return found
    return ""


# The existing extractor uses these module-level names; replacing them keeps
# every retailer on the same extraction path and preserves existing validation.
recovery._NAME_KEYS = _NAME_KEYS
recovery._URL_KEYS = _URL_KEYS
recovery._PRICE_KEYS = _PRICE_KEYS
recovery._IMAGE_KEYS = _IMAGE_KEYS
recovery._STOCK_KEYS = _STOCK_KEYS
recovery._pick = _pick_normalized
