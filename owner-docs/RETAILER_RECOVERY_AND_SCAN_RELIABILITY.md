# PokéDrop Watch — retailer recognition and scan reliability

## What this update changes

- Adds wider source-aware product extraction for Pokémon Center, Target, Walmart, Amazon, Best Buy, and GameStop. It examines nested hydration JSON, retailer-specific product identifiers, `data-*` title/URL fields, product-card attributes, image alt/title text, stock labels, and price fields.
- Keeps sold-out products in the catalogue so their stock transition can be compared on a later scan.
- Retains last-known catalogue rows/counts when a current page responds but no current items can be parsed. The saved count is not presented as freshly confirmed inventory.
- Marks a source **PARTIAL** when at least one configured page succeeds and at least one fails, such as `1/3 pages responded`. Products found on reachable pages are still retained. Fully successful sources remain **MATCHES**; pages that respond but expose no recognized records remain **NO MATCH**; sources whose configured pages all fail remain **ISSUE**.
- Adds compact diagnostics to help distinguish parser misses from empty client-rendered shells, response challenges, and connection failures. Public status stores response size/title, product-like link count, JSON script count, and broad error types—not response bodies or subscriber data.
- Keeps PokéBeach RSS/REST/homepage fallback handling and the existing 15-minute GitHub Actions cron.

## Install

1. Upload this ZIP to the repository's `updates/` folder and commit it. Do not unzip it manually. The existing patch installer applies the files.
2. The same ZIP contains a complete replacement `backend/apps-script/Code.gs`. To activate Trainer notification preferences, separately replace the entire `Code.gs` in the existing Apps Script project with that file, save, then choose **Deploy → Manage deployments → Edit → New version → Deploy**. Keep the existing deployment URL and Script Properties. The ZIP cannot update Google's hosted Apps Script deployment by itself.
3. Open GitHub Actions and confirm the patch is applied, tests pass, and a new monitor scan completes. Check the source list for `PARTIAL`, `NO MATCH`, and `ISSUE` states.

## Interpreting source results

- **MATCHES** — all configured pages responded and at least one relevant item/news entry was recognized.
- **PARTIAL** — some configured URLs responded and some failed. The page displays the exact response count and current recognized-item count. Parsed items from successful responses remain available.
- **NO MATCH** — pages responded, but the supported content did not expose recognizable product/news records. This does not mean the retailer has no stock.
- **ISSUE** — none of the configured pages responded successfully.

This update broadens static HTML and embedded JSON recognition. It does not execute retailer JavaScript, solve CAPTCHA/queues, or bypass anti-bot systems. A live retailer result is confirmed only when a new hosted Actions scan actually reports recognized items.
