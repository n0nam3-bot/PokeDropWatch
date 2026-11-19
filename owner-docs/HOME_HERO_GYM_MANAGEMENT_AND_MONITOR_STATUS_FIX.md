# PokéDrop Watch — hero, Gym Management, Notify, guide, and scan-status fix

## What this patch changes

- Restores the original `pokeball-8bit.png` sprite in the Home hero. The previous generated grassy throw image is no longer assigned by JavaScript or precached by the service worker.
- Keeps the Home hero ball moving with a small pixel-art idle bob.
- Makes the Pallet Town / Pokédex label depend on scroll position in both directions. Scrolling back above Alerts returns the label to Pallet Town even if the URL still contains `#alerts`.
- Removes the repeated uppercase `GYM MANAGEMENT` eyebrow so Gym Management has one visible page heading.
- Gives the Notify form the same cream page background and green gradient title panel used by Gym Management, while keeping the requested single `Receive Notifications` heading and description.
- Extends Source Health with a full Gym Leader management guide: sign-in, password reset, subscriber statuses/actions, one-hour sessions, Firestore privacy, and troubleshooting context. It also explains mixed match/parser-miss/request-error summaries and stale timestamps.
- Changes the service-worker cache to `pokedrop-shell-v17` and removes the unused generated hero scene from the precache list.
- Removes an undeclared Pillow dependency from the PNG regression test. The test now checks the PNG signature, dimensions, bit depth, and RGBA color type with Python's standard library.
- Updates outdated tests so they reflect the actual embedded GitHub Pages Admin/Notify arrangement and the restored hero sprite.

## Install website patch

1. Upload this ZIP to the repository's `updates/` folder and commit it.
2. The existing `PokeDrop Watch` workflow applies the ZIP, runs tests, and then runs the scheduled source scan if all tests pass.
3. The patch does not change `Code.gs` and does not include a partial or complete backend code replacement.

## Update Google Apps Script HTML files

The Admin and Notify contents are served from the Apps Script project inside the GitHub Pages iframes, so the embedded HTML files must also be updated:

1. Open the existing Apps Script project.
2. Open `Admin.html`, select all, and replace it with the complete `backend/apps-script/Admin.html` file from this ZIP.
3. Open `Subscribe.html`, select all, and replace it with the complete `backend/apps-script/Subscribe.html` file from this ZIP.
4. Save and deploy the existing web app as a **New version**. Keep the same deployment URL, execute-as identity, and access setting.

Do not change `Code.gs`, `Index.html`, Script Properties, or Firestore rules for this patch.

## Understanding the current scan summary

A scan summary such as `3 source matches · 5 parser misses · 2 request errors` across 10 configured source groups means three source groups supplied parsed products, five returned page content without recognized products, and two could not be fetched. A catalog count such as 176 represents the products the monitor recognized and tracks; it is not a complete inventory of all store products or confirmation that each is in stock.

The workflow is scheduled every 15 minutes. It runs automated tests before the monitor. When tests fail, the scan and email-digest step is skipped and `docs/data/state.json` retains the last successful timestamp. A stale timestamp therefore means the newest scan did not finish; it does not mean the source set was checked again and found unchanged.

## Files modified / added

- `docs/page-enhancements.js`
- `docs/site-uniform.css`
- `docs/sw.js`
- `docs/SOURCE_HEALTH.html`
- `backend/apps-script/Admin.html`
- `backend/apps-script/Subscribe.html`
- `tests/test_auth_architecture.py`
- `tests/test_subscription_portal_direct.py`
- `tests/test_theme_and_page_copy.py`
- `tests/test_ui_consistency_v2.py`
- `tests/test_source_status_and_current_page_fixes.py` (new)
- `owner-docs/HOME_HERO_GYM_MANAGEMENT_AND_MONITOR_STATUS_FIX.md` (new)
