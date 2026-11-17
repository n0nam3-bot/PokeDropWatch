# PokéDrop Watch Roadmap

The roadmap records what is implemented in the current code and what remains planned. `[x]` means implemented in the repository; `[ ]` means not implemented or still requires live setup/verification.

## Stage 1 — Core monitor and public website

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
- [x] Responsive, minimal Pokémon-themed dashboard with alert-type, item-category, retailer, and exact-title filtering.
- [x] Separate alert history from a browseable view of current tracked catalog products.
- [x] Product thumbnails from structured data, retailer card images, and RSS media metadata when exposed.
- [x] Reject generic retailer navigation/rating text and unrelated products from the Pokémon alert feed.
- [x] Distinguish sources with recognized results from pages that load but return no recognizable Pokémon items.
- [x] PWA manifest and service worker for compatible mobile browsers.
- [x] ZIP patch application with path validation and automated tests.

## Stage 2 — Subscriber applications and administration

**Status: Implemented; Firebase setup required**

- [x] Public visitor application form with category and retailer preferences.
- [x] Firebase email-link sign-in to verify ownership of the applying email address.
- [x] Pending-by-default applications; visitors cannot approve themselves.
- [x] Private administrator sign-in restricted by Firestore rules to one configured verified email.
- [x] Admin dashboard to approve, reject, suspend, reactivate, and remove records.
- [x] Subscribers can read their own status and update their preferences.
- [x] Secure unsubscribe flow requiring a fresh email link and a separate confirmation.
- [x] Firestore rules restricting subscriber records and private delivery subcollections.
- [ ] Complete live Firebase project configuration and verify with separate admin and non-admin accounts.
- [ ] Add stronger automated bot protection if application volume or abuse warrants it.

## Stage 3 — Subscriber alert delivery

**Status: Implemented; live email configuration required**

- [x] Store category and retailer preferences with each subscriber.
- [x] Match each detected event against subscriber preferences.
- [x] Send a separate email per matching active subscriber; do not expose recipient addresses.
- [x] Store pending delivery batches privately in Firestore and retry them on later scheduled runs.
- [x] Include secure preference/unsubscribe link in subscriber alert emails.
- [x] Keep subscriber identifiers and addresses out of public dashboard state.
- [ ] Configure Firebase service-account and Gmail secrets in GitHub Actions.
- [ ] Complete end-to-end verification with an approved test subscriber and a real detected event.
- [ ] Evaluate a free dedicated transactional email provider if Gmail limits become restrictive.

## Stage 4 — Retailer coverage and detection quality

**Status: In progress**

- [x] Extend watchlist through `config/sources.json` for supported source formats.
- [x] Support broad catalog pages and individual product-detail URLs.
- [ ] Add dedicated retailer adapters for stores whose product data is hidden behind JavaScript or custom page structures.
- [ ] Add automated integration checks for each configured retailer and alert when a page structure stops yielding product data.
- [ ] Improve product identity matching when the same item appears through multiple retailers or URLs.
- [ ] Add location-aware inventory checks where retailers expose a permitted public location-based source.
- [ ] Expand validated coverage for Pokémon TCG, games, toys, apparel, collectibles, and special releases.

## Stage 5 — Dashboard, reliability, and release quality

**Status: In progress**

- [x] Responsive desktop/mobile public dashboard and subscriber forms.
- [x] Separate administrator page with status filters and subscriber actions.
- [x] PWA shell cache updated for the new public/admin pages and Firebase client files.
- [x] Request timeouts and retry transient HTTP failures.
- [x] Keep individual source failures from stopping the remaining source scans.
- [x] Automated tests for parsing, stock/price transitions, subscriber matching, and ZIP patch safety.
- [ ] Add dashboard sort controls for retailer, price, and detection time.
- [ ] Add a user-managed product/keyword watchlist.
- [ ] Add product history for price and availability over time.
- [ ] Add an alert path for repeated workflow failures or missed scan cycles.
- [ ] Add integration tests against controlled sample pages for every retailer adapter.
