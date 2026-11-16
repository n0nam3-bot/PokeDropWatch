# PokéDrop Watch Roadmap

The roadmap records what is already implemented and what remains planned. `[x]` means implemented in the current project; `[ ]` means not yet implemented.

## Stage 1 — Core monitor and dashboard

**Status: Complete**

- [x] Scheduled GitHub Actions scans (currently every 15 minutes).
- [x] Configurable catalog, product-detail, and RSS/Atom source definitions.
- [x] Product discovery from structured product data and eligible product links in returned HTML.
- [x] New-listing detection after the initial baseline scan.
- [x] Restock detection when a listing changes from out of stock to in stock or preorder.
- [x] Price-drop and price-change detection when both prices are available.
- [x] New-entry detection for configured Pokémon news feeds.
- [x] Persistent scan state and recent alert history in `docs/data/state.json`.
- [x] Per-source success/failure reporting and an overall scan summary.
- [x] Responsive dashboard with alert search and event filters.
- [x] PWA manifest and service worker for compatible mobile browsers.
- [x] Optional Gmail SMTP email digests containing product/source, price, availability, and direct link details.
- [x] ZIP patch application with path validation and automated tests.

## Stage 2 — Retailer coverage and detection quality

**Status: In progress**

- [x] Allow the watchlist to be extended through `config/sources.json` without changing the scanner for supported source formats.
- [x] Support both broad catalog pages and individual product-detail URLs.
- [ ] Add dedicated retailer adapters for stores whose product data is hidden behind JavaScript or custom page structures.
- [ ] Add automated integration checks for each configured retailer and alert when a page structure stops yielding product data.
- [ ] Improve product identity matching when the same item appears through multiple retailers or URLs.
- [ ] Add location-aware inventory checks where retailers expose a permitted public location-based source.
- [ ] Expand validated coverage for Pokémon TCG, games, toys, apparel, collectibles, and special releases.

## Stage 3 — Alert controls and delivery options

**Status: Planned**

- [x] Send optional email digests through Gmail SMTP.
- [x] Include title, retailer/source, listed price, availability, previous price when known, and product/source link in alert emails.
- [ ] Add configurable keyword and product-category filters.
- [ ] Add per-source notification controls so noisy retailers can be muted without disabling scans.
- [ ] Add quiet hours and configurable digest grouping.
- [ ] Evaluate browser push notifications and optional messaging integrations without introducing paid services.

## Stage 4 — Dashboard improvements

**Status: In progress**

- [x] Show configured source health, last scan time, listing count, and recent alerts.
- [x] Search and filter the alert feed.
- [x] Provide a responsive layout for desktop and mobile screens.
- [ ] Add sort controls for retailer, price, and detection time.
- [ ] Add a user-managed watchlist for specific products and keywords.
- [ ] Add product history so price and availability changes can be reviewed over time.
- [ ] Add clearer per-source history and last-success details.

## Stage 5 — Reliability, maintenance, and release quality

**Status: In progress**

- [x] Apply request timeouts and retry transient HTTP failures.
- [x] Keep individual source failures from stopping the remaining source scans.
- [x] Test parsing, stock transitions, price changes, and ZIP patch safety.
- [x] Reject unsafe ZIP paths and symlinks in the patch installer.
- [ ] Add integration tests against controlled sample pages for every retailer adapter.
- [ ] Add an alert path for repeated workflow failures or missed scan cycles.
- [ ] Add configurable history retention and state-file size management.
- [ ] Document a repeatable release and rollback checklist.
