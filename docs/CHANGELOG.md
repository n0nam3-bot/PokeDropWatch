# Changelog

All notable project changes are recorded here. Entries are ordered newest first. Dates use `YYYY-MM-DD`.

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
