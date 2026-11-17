# PokéDrop Watch — source health and scan results

This document explains what the source badges mean. A source badge describes the **latest automated fetch and parser result**. It is not a promise that the retailer has inventory, and a successful scan does not prove every product on the retailer site was discovered.

## Status meanings

| Badge | Meaning | What it does not mean |
|---|---|---|
| `MATCHES` | The page/feed was fetched and the current parser recognized one or more Pokémon-relevant entries. | It does not mean every product was captured, or every item is in stock. |
| `NO MATCH` | The page responded, but the current parser recognized zero usable Pokémon product/feed entries. | It does not mean the retailer has no Pokémon products or that the page is empty. The markup may require a retailer-specific adapter or JavaScript rendering. |
| `ISSUE` | The request failed before the parser could scan the page, for example because of a connection timeout, blocking, TLS, DNS, or HTTP error. | It does not prove the retailer is offline for human visitors. |

## Interpreting the reported scan

The scan report shared with the project on **November 16, 2026 at 7:48 PM** showed:

- **Walmart:** `MATCHES` — 5 Pokémon listings recognized.
- **Amazon:** `MATCHES` — 68 Pokémon listings recognized.
- **Pokémon Center · Trading Card Game:** `NO MATCH`.
- **Pokémon Center · Plush:** `NO MATCH`.
- **Target:** `NO MATCH`.
- **GameStop:** `NO MATCH`.
- **Best Buy:** `ISSUE` — the scanner reported a connection failure.
- **PokéBeach:** `ISSUE` — the scanner reported a connection failure.

That explains the displayed **2/8**: two of the eight configured sources returned entries that the current parser could recognize. The 73 recognized listings are the sum of 68 Amazon and 5 Walmart items in that scan. The other six sources did not contribute recognized entries in that run.

This is a point-in-time diagnostic, not a permanent source guarantee. Retailer layouts, network protections, and feed availability can change.

## What should be improved next

1. Build and maintain retailer-specific adapters for Pokémon Center, Target, Walmart, Best Buy, GameStop, and Amazon instead of assuming a shared generic HTML layout.
2. For every adapter, record the HTTP status, final URL, content type, page title, recognized product count, and a short non-sensitive diagnostic when it fails.
3. Add fixture-based tests using saved HTML examples so parser changes can be validated without contacting retailers during each test run.
4. Only mark a source as `MATCHES` when the parser identifies actual Pokémon product titles and product URLs.
5. Keep `NO MATCH` distinct from `ISSUE`; never turn a blocked or unrecognized source into a false success.
6. Verify product title, category, price, stock state, and image independently. Missing image or unknown price should be shown as unavailable rather than guessed.

## Why products may have no image or price

The scanner can extract an image or price only when the page returns one in structured product data, product-card markup, or known metadata. Some retailer pages load these values later with JavaScript, return placeholders, or block external image hotlinks. In those cases the website uses a neutral fallback and does not invent an image or price. A retailer-specific adapter may improve coverage, but it must be tested against the retailer's actual returned markup.

## Manual diagnosis

1. Open the source URL from the dashboard.
2. Confirm the page shows Pokémon products in a normal browser.
3. Open the corresponding GitHub Actions run and expand **Scan sources and send email digest**.
4. For `NO MATCH`, inspect whether the response HTML actually contains product titles, product links, image URLs, and price metadata.
5. For `ISSUE`, inspect the complete request exception and response status.
6. Save a sanitized HTML fixture (remove account, session, cart, address, and personal data) before writing a retailer-specific parser.

Do not add an unofficial API, proxy, CAPTCHA bypass, or scraping service without checking its terms, cost, and reliability first.
