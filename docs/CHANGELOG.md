# Changelog

All notable project changes are recorded here. Entries are ordered newest first. Dates use `YYYY-MM-DD`.

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
