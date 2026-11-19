# Retailer scan and source-health behavior

PokéDrop Watch keeps each product category as its own source record. Pokémon Center TCG and Pokémon Center Plush, for example, remain separate routes with separate product histories and alert comparisons. The public source panel groups those routes under one retailer heading so the watchlist is easier to read; grouping does not merge category data.

## Route request policy

1. Each distinct category or query scope is its own source route: TCG, plush, new arrivals, newest-first, figures, and pre-orders are not interchangeable searches and must not be skipped just because another search on the same retailer returned products.
2. The dashboard groups these source routes under one retailer while preserving separate route-level product history and health. A persisted round-robin selects one route per retailer per 15-minute workflow run by default. Three-route retailers therefore cycle across about 45 minutes; four-route retailers across about 60 minutes. Routes not selected in the current run are shown as `SCHEDULED`, including their prior check time, and do not issue a retailer request.
3. Only true equivalent backup endpoints are kept in `alternate_urls`. Those are checked after the primary endpoint fails, returns a recognized access-challenge page, or produces no parser-recognized current items. Unused fallback endpoints are not requested after a route yields matches.
4. PokéBeach's WordPress REST endpoint remains a backup to its RSS feed, and the homepage HTML route remains an explicit final fallback.
5. Identical URLs are cached within one scan process, including failures, so one URL is not repeatedly fetched by different source records in the same run. Duplicate product alerts are collapsed across routes for the same retailer.
6. If all checked endpoints for a source route are access-blocked with no usable fallback, the monitor pauses that retailer's remaining category routes for a shared 45-minute cooldown. If all endpoints for a route fail at the request layer, a 15-minute cooldown avoids repeating the same failure across the retailer's other categories.

The scanner does not try to bypass retailer bot protection. CAPTCHA, Cloudflare/Akamai, "Robot or human?", and similar challenge responses are recorded as blocked content rather than a healthy retailer page. The public dashboard labels category routes skipped by the shared retry pause as `COOLDOWN`.

## Fresh versus retained data

`current_items_found` reports products recognized in the current scan. `last_known_items` reports saved product records or news articles retained after a parser miss, a block, a cooldown skip, or a request failure. Retained products remain visible for continuity, but their presence is not evidence of current stock. `successful_urls` now counts non-challenge HTTP responses, while `http_responses`, `blocked_urls`, `failed_urls`, `attempted_urls`, and `available_urls` provide the separate transport and fallback details. A cooldown-skipped category records that no new request was made. A `SCHEDULED` route was intentionally not selected in the current rotation interval.

## Product-card filtering

Product URLs must match a retailer product route on the same host. Common navigation and tracking paths such as GameStop's broad `/toys-games` landing page and Walmart's `/sp/track` path are excluded. Generic facet labels such as "Currently Refined by Category: Trading Card Games" are rejected as titles even when a search page itself is Pokémon-scoped.

## What this change cannot fix

Conditional fallback reduces unnecessary requests and makes source health more honest; it cannot make a retailer expose data that its public page withholds from automated clients. A fully blocked retailer still needs an accessible public feed/page or an approved API before reliable current listings can be collected.
