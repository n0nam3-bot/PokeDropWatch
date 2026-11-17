# Changelog

All notable project changes are recorded here. Entries are ordered newest first. Dates use `YYYY-MM-DD`.

## [1.2.1] — 2026-11-17

### Fixed
- Added the Firebase browser API-key HTTP-referrer allowlist instructions required for email-link authentication to work across both GitHub Pages and the Firebase-hosted auth action handler.
- Clarified the difference between a source parser miss (`NO MATCH`) and a fetch/connection failure (`ISSUE`), with the current scan report documented separately.
- Shortened source-card status descriptions so diagnostic copy remains readable on narrow mobile cards.
- Removed retailer wrapper text such as `Deal,` and embedded `Price Now ... Was ...` fragments from saved product titles.
- Corrected TCG category inference so a Scarlet & Violet / Prismatic Evolutions surprise box is not mislabeled as a video game unless an explicit game platform is present.

### Added
- Added `docs/SOURCE_HEALTH.md` with definitions, a point-in-time interpretation of the reported 2/8 scan, and requirements for source-specific parser work.
- Added lazy-load image fallback extraction and tests for Walmart-style title wrappers, product images, and Prismatic Evolutions category classification.

### Notes
- The API-key restriction change is made in Google Cloud Console; installing this ZIP does not change cloud project settings automatically.
- Retailer-specific catalog coverage for sources currently marked `NO MATCH` or `ISSUE` remains a separate engineering task requiring current response fixtures and verification. This release does not claim those sources are fixed.

### Tests
- Automated tests verify title normalization and corrected category inference.
- Firebase live sign-in and current retailer access remain owner-environment checks.


## [1.2.0] — 2026-11-16

### Fixed
- Tightened retailer catalog parsing to reject review counts, ratings, option links, generic calls to action, and unrelated products that were previously being mistaken for product listings.
- Added Pokémon-name relevance checks so the product feed does not treat arbitrary retailer navigation or unrelated search tiles as Pokémon drops.
- Changed source health reporting: a page that responds but produces no recognizable Pokémon product/feed entries is now marked `NO MATCH`, not `ONLINE`.
- Filtered malformed legacy product events from the public feed and cleaned non-Pokémon product records from the scanner's next saved state.

### Added
- Added retailer product image extraction from JSON-LD, product-card image attributes, RSS media thumbnails, and article image markup when available.
- Added product category inference for Pokémon TCG, plush, games, accessories/apparel, and general collectibles.
- Added separate Latest alerts and All tracked products views.
- Added dashboard filters for item category and retailer, plus an exact-title search option shared by both views.
- Added an Accessories & apparel notification category to subscription preferences and Firestore validation.
- Expanded the Amazon search from Pokémon TCG-only to Pokémon products generally, using a fresh baseline to prevent existing products from being sent as a burst of false new-drop emails.

### Notes
- Existing Firebase projects must manually republish the updated `firebase/firestore.rules` template after installing this release. Preserve the administrator email in the deployed Console rules; do not commit it to GitHub.
- Product photos are displayed only when a monitored page exposes a usable image URL; retailer hotlink restrictions can still prevent some images from loading.
- Retailer pages may block automated requests or render product tiles with JavaScript. A `NO MATCH` status is an honest signal that this scan did not verify any usable product listing.

### Tests
- Added sample tests reproducing the screenshot's `98 ratings` and `See options` false positives.
- Added tests for product thumbnails, RSS thumbnails, item categorization, Pokémon relevance, and no-match source status.


## [1.1.1] — 2026-11-16

### Changed
- Rewrote the Firebase setup guide as a click-by-click procedure with direct Firebase Console, Google Account, GitHub Pages, Actions secrets, Actions variables, and workflow links.
- Added exact field mappings for Firebase Web App configuration, exact GitHub secret/variable names, copy/paste locations, test steps, and troubleshooting for common setup errors.
- Clarified that the administrator email is entered only in the deployed Firebase Rules editor, never in public JavaScript or the committed rules file.
- Corrected the administrator-email comment in the public Firestore rules template.
- Linked the HTML and Markdown setup guides prominently from the README.

### Tests
- Confirmed all setup links, repository paths, and required configuration names are present in the guide.
- Verified the ZIP patch contains only intended repository-relative files and installs into a clean copy.
- Ran the project's automated Python test suite.

## [1.1.0] — 2026-11-16

### Added
- Added a responsive public website section for subscription applications, category/retailer preferences, account status, and secure unsubscribe confirmation.
- Added Firebase Authentication email-link sign-in and Firestore subscriber storage with administrator-only approval controls.
- Added a private administrator page to review, approve, reject, suspend, reactivate, and remove subscriber records.
- Added Firestore security rules that restrict visitors to their own verified subscriber record and reserve global management for the configured verified administrator email.
- Kept the administrator email out of public JavaScript and the committed public rules file; only the deployed Firestore rules contain the configured address.
- Added per-subscriber event filtering, separate email delivery, and private Firestore retry records in the scheduled monitor.
- Added the one-time Firebase setup guide and updated project configuration/change guidance.

### Changed
- GitHub Pages remains the public host and must publish from `main` / `/docs`; the repository README is not the website entry point.
- Gmail SMTP alerts can now be delivered to approved subscribers individually. `ALERT_EMAIL` is optional and is only an additional owner copy.
- Added category and retailer keys to source event records so preferences can be applied consistently.
- Updated the PWA service worker to fetch current site files first and use cached files only as an offline fallback, so owner-edited Firebase configuration is not hidden by stale cache.

### Tests
- Passed all 16 Python unit tests, including subscriber preference matching and separate-recipient delivery queue behavior.
- Passed JavaScript module syntax checks, Python compilation, source JSON validation, HTML-to-script element reference checks, workflow YAML parsing, and clean-copy ZIP patch installation.
- Live Firebase Authentication, Firestore rules deployment, and real SMTP delivery still require the owner's Firebase project and GitHub secrets; those external services were not falsely reported as live-tested.

## [1.0.2] — 2026-11-16

### Added
- Added `docs/CONFIGURATION_AND_CHANGE_GUIDE.md` as the canonical reference for project structure, settings, GitHub configuration, customization rules, testing, change requests, and ZIP patch releases.

### Changed
- Linked the detailed configuration and change guide from the README.

## [1.0.1] — 2026-11-16

### Changed
- Reworked the README to focus on the application's capabilities, supported source types, and the configuration required for operation.

### Added
- Added `docs/ROADMAP.md` with implementation status and checkbox tracking for each development stage.
- Added this versioned changelog, with newest changes listed first.

## [1.0.0] — 2026-11-16

### Added
- Initial PokéDrop Watch application with a responsive Pokémon-themed dashboard and PWA support.
- Scheduled GitHub Actions monitor for configured retailer catalog pages, product pages, and Pokémon news RSS/Atom feeds.
- Detection for new listings, restocks, listed price drops, and other listed price changes.
- Per-source scan status, persistent state, and recent alert history.
- Optional Gmail SMTP email digests with product/source details and direct links.
- ZIP-based installation and patch application, including archive path validation.
- Automated tests for parsing, stock/price transitions, and ZIP patch handling.
