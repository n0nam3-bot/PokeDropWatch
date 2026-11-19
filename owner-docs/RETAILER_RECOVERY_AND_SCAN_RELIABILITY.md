# PokéDrop Watch — retailer recovery and scan reliability

## What this update changes

- Adds source-aware product-card and nested JSON extraction for Pokémon Center, Target, Walmart, Amazon, Best Buy, and GameStop product URL patterns.
- Keeps sold-out product tiles in the catalogue so their availability can be compared on later scans.
- Retains the last-known saved catalogue count when a current scan responds successfully but the parser recognizes zero items. The source still shows `NO MATCH`/warning; the old listings are explicitly described as last-known and are not treated as freshly confirmed inventory.
- Adds compact response diagnostics to parser-miss messages: HTML response size/title, product-like link count, JSON script count, and common automated-access challenge markers. No raw page body or subscriber information is written to the public state.
- Adds a PokéBeach homepage HTML article parser as a final fallback after the RSS and WordPress REST URLs. Its REST API currently returns HTTP 401 in the hosted scan, and the homepage fallback can still fail if the site changes markup or blocks the runner.
- Keeps the existing 15-minute GitHub Actions cron setting. GitHub schedule events can be delayed by GitHub; the workflow run history remains the authoritative way to confirm an actual run.

## Installation

1. Upload this ZIP to the repository's `updates/` folder and commit it. The existing patch installer applies `monitor/run.py`, `monitor/engine_recovery_patch.py`, tests, and this guide.
2. No Google Apps Script change is required.
3. The next successful monitor run will record source response diagnostics. Compare `Last checked` with the latest `PokeDrop Watch` GitHub Actions run.

## A note about scheduled runs

The existing workflow schedule remains `*/15 * * * *` (every 15 minutes). The scan step currently follows the test step, so an unrelated test failure can skip a scan. A complete replacement workflow is included separately as `owner-docs/pokedrop-watch.yml.REPLACEMENT.txt`; it adds `if: always()` to the scan step so the monitor still runs when unit tests fail. The repository patch installer intentionally blocks writes to `.github/workflows`, so that one workflow file must be replaced manually in GitHub if you want this additional safeguard.

## What this cannot guarantee

A parser cannot extract product data that the retailer does not send to the GitHub Actions runner. Best Buy connection failures and retailer anti-bot responses need to be observed in the new diagnostics. This update improves discovery and logging, but a live result cannot be guaranteed without a fresh hosted run.

## One-time workflow safeguard (recommended)

The replacement workflow above is the **entire** `.github/workflows/pokedrop-watch.yml` file. To enable it, open that path in GitHub, choose Edit, replace the full file contents with `owner-docs/pokedrop-watch.yml.REPLACEMENT.txt`, and commit. It preserves the 15-minute schedule and adds `if: always()` to the scan step. The scanner therefore still runs when the tests report a failure, as long as the runner setup and required dependencies are available. The workflow file cannot be installed by the normal patch ZIP because `scripts/apply_patch.py` intentionally blocks `.github/workflows` changes.
