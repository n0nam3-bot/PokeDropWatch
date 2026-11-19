"""Broaden retailer hydration payload parsing without mixing sibling products.

The earlier recursive lookup walked through arrays as well as objects. When a
search response contained several products, a parent container could be
mistaken for a product by borrowing the first product's title/URL and another
product's price. This version searches the current record and nested objects,
but deliberately never crosses a list boundary. Product arrays are handled by
the scanner's normal JSON tree walk, one product record at a time.
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
    "productDescription", "product_description", "nameText", "product_title",
    "productTitleText", "displayTitle", "itemTitle",
)))
_URL_KEYS = tuple(dict.fromkeys(recovery._URL_KEYS + (
    "productURL", "productPageURL", "productDetailURL", "pdpURL", "canonicalURL",
    "productSeoUrl", "productSEOURL", "slugUrl", "productPagePath", "productPath",
    "productDetailPageUrl", "productDetailUrl", "seoPath", "urlPath", "webUrl",
    "productLinkUrl", "product_link", "pdpUrlPath", "productPageLink",
)))
_PRICE_KEYS = tuple(dict.fromkeys(recovery._PRICE_KEYS + (
    "currentPriceText", "sale_price", "listPrice", "priceAmount", "formatted_price",
    "priceDisplay", "display_price", "retailPrice", "onlinePrice", "offerPriceText",
    "current_price", "regularPrice", "offerPriceValue", "price_value",
)))
_IMAGE_KEYS = tuple(dict.fromkeys(recovery._IMAGE_KEYS + (
    "imageURL", "primaryImageUrl", "primary_image_url", "imageSrc", "imageURLLarge",
    "productImageUrl", "product_image_url", "thumbnailURL", "heroImageUrl",
    "imageUrlLarge", "main_image", "primary_image",
)))
_STOCK_KEYS = tuple(dict.fromkeys(recovery._STOCK_KEYS + (
    "onlineStock", "inStock", "isInStock", "isSellable", "availabilityText",
    "stockStatusText", "inventory_state", "onlineAvailabilityStatus",
    "is_available", "onlineAvailabilityText",
)))


def _pick_normalized(node: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Find a matching field on this record or within its nested object fields.

    Do not descend into lists: each list element is visited independently by
    engine._walk_json. This prevents cross-product field borrowing.
    """
    if not isinstance(node, dict):
        return ""
    wanted = {_normalized_key(key) for key in keys}
    for key, value in node.items():
        if _normalized_key(key) in wanted:
            found = recovery._scalar(value)
            if found:
                return found
    return ""


# The recovery extractor uses these module-level names; replacing them keeps
# the same product validation, URL allow-list, and category handling.
recovery._NAME_KEYS = _NAME_KEYS
recovery._URL_KEYS = _URL_KEYS
recovery._PRICE_KEYS = _PRICE_KEYS
recovery._IMAGE_KEYS = _IMAGE_KEYS
recovery._STOCK_KEYS = _STOCK_KEYS
recovery._pick = _pick_normalized
