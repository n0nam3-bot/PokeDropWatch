# Source health and retailer coverage

This page explains what the public source badges mean and how the owner diagnoses source issues. It does not promise that every retailer can be scanned automatically.

## Badge meanings

- **MATCHES** — at least one configured URL returned product or news records recognized by the parser.
- **NO MATCH** — one or more URLs responded, but the parser did not find usable Pokémon product/feed entries. This is not evidence that the store has no products or stock.
- **ISSUE** — all configured URLs failed at the request layer. Inspect the corresponding GitHub Actions log.

A scan can query a source's primary URL plus up to three `alternate_urls`. Results are merged and deduplicated for the retailer. The source card tooltip contains the number of successful and failed URLs.

## What the monitor can parse

The monitor can extract publicly exposed JSON-LD Product data, embedded JSON/hydration payloads, JSON catalog responses, and HTML product cards. It looks for product title, same-retailer product URL, price, image, SKU and availability when present. It does not execute arbitrary retailer JavaScript, operate a browser, pass a CAPTCHA, bypass bot protection, or use a paid proxy/API.

Some retailers serve empty templates or require client-side JavaScript. Those will remain `NO MATCH` until an accessible public product source or retailer-specific adapter is available. Some hosts may also throttle requests. Alternate URLs improve coverage only when the retailer allows those requests and exposes the product data.

## Owner troubleshooting

1. Open [GitHub Actions runs](https://github.com/n0nam3-bot/PokeDropWatch/actions) and select the latest `PokeDrop Watch` run.
2. Expand **Scan sources and send email digest**.
3. For `NO MATCH`, inspect the HTML/JSON actually returned by the URL and confirm it contains product titles, product links, images and prices. If the products are only inserted by JavaScript after page load, this HTTP parser cannot see them.
4. For `ISSUE`, inspect the request error. DNS, TLS, HTTP 403/429 and timeout failures are different problems; do not label them as parser failures.
5. Save a sanitized fixture (remove account, session, cart, address and personal data) and add a deterministic parser test before changing retailer-specific logic.
6. Do not add unofficial APIs, scraping proxies, CAPTCHA bypasses, or paid services without documenting their price, terms and reliability first.

## Current coverage note

The user's supplied scan snapshot on 2026-11-16 showed 1/8 source matches (Amazon), five parser misses, and two request errors (Best Buy and PokéBeach). This is a dated observation from that scan, not a live guarantee. The current release improves alternate-URL probing and generic JSON/product-card parsing, but it has not been live-verified against every retailer. A retailer remains incomplete until a real scan returns recognized products.
