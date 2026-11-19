# Source health and retailer coverage

This page explains what the public source badges mean and how the owner diagnoses source issues. It does not promise that every retailer can be scanned automatically.

## Badge meanings

- **MATCHES** — the primary route returned usable product or news records recognized by the parser.
- **PARTIAL** — one or more routes were blocked or failed, or a fallback route was needed to find current records. Any recognized results remain visible, but the route warning is retained.
- **SCHEDULED** — this category/search route was not selected in the current round-robin interval. No request was made; its previous check time and last-known records remain visible.
- **NO MATCH** — the checked pages responded without yielding usable Pokémon product/feed entries. This is not evidence that the store has no products or stock.
- **ISSUE** — all available routes failed at the request layer. Inspect the corresponding GitHub Actions log.

The dashboard groups category and search-view routes under one retailer heading, but TCG, plush, new-arrival, newest-first, and pre-order routes keep separate histories. Distinct query scopes are separate source records and are scanned independently because each can expose different products. They are not fallbacks for one another. One route per retailer is selected in a persisted round-robin each 15-minute scan by default, so three-route retailers cycle in about 45 minutes and four-route retailers in about 60 minutes. Routes not selected in the current interval show `SCHEDULED` and include their last actual check time. Only true equivalent backup endpoints are tried conditionally when the primary endpoint fails, returns an access challenge, or produces no parser-recognized current entries. Identical URLs are cached within one scan process so a repeated URL is not fetched twice. Duplicate alerts for the same retailer/product/event are collapsed across the category routes.

## Current versus last-known listings

`current_items_found` reports products recognized from the route used in the current scan. `last_known_items` reports records retained from an earlier successful scan when current inventory could not be confirmed. Retained records are shown for continuity; they must not be treated as proof of current stock. A `SCHEDULED` route was not requested in the current interval; its previous data and timestamp are retained. `successful_urls` counts non-challenge HTTP responses, while `http_responses`, `blocked_urls`, `failed_urls`, `attempted_urls`, and `available_urls` show the transport and fallback details separately.

## What the monitor can parse

The monitor can extract publicly exposed JSON-LD Product data, embedded JSON/hydration payloads, JSON catalog responses, and HTML product cards. It looks for product title, same-retailer product URL, price, image, SKU and availability when present. It does not execute arbitrary retailer JavaScript, operate a browser, pass a CAPTCHA, bypass bot protection, or use a paid proxy/API.

Some retailers serve empty templates or require client-side JavaScript. Those will remain `NO MATCH` until an accessible public product source or retailer-specific adapter is available. Some hosts may also throttle requests. Conditional fallback reduces unnecessary requests; it does not guarantee that a retailer will expose product data.

## Owner troubleshooting

1. Open [GitHub Actions runs](https://github.com/n0nam3-bot/PokeDropWatch/actions) and select the latest `PokeDrop Watch` run.
2. Expand **Scan sources and send email digest**.
3. For `NO MATCH`, inspect the HTML/JSON actually returned by the URL and confirm it contains product titles, product links, images and prices. If the products are only inserted by JavaScript after page load, this HTTP parser cannot see them.
4. For `PARTIAL`, inspect the source tooltip and diagnostic output to see whether the primary page was blocked, an alternate was requested, or a request failed.
5. For `ISSUE`, inspect the request error. DNS, TLS, HTTP 403/429 and timeout failures are different problems; do not label them as parser failures.
6. Save a sanitized fixture (remove account, session, cart, address and personal data) and add a deterministic parser test before changing retailer-specific logic.
7. Do not add unofficial APIs, scraping proxies, CAPTCHA bypasses, or paid services without documenting their price, terms and reliability first.

## Current coverage note

Retailer coverage is determined by the latest completed scan, not by the presence of a source entry in `config/sources.json`. A retailer remains incomplete until a real scan returns recognized current products or news. A blocked response and a retained catalog do not count as a successful current-inventory check.
