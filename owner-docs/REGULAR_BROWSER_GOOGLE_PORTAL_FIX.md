# Admin and Notify: top-level Google portal deployment

## What this update changes

- Admin and Notify no longer embed Apps Script inside GitHub Pages iframes.
- Opening `admin.html` or `notify.html` navigates the current tab to the matching Apps Script route. This keeps Google as the top-level site and avoids third-party iframe cookie/session restrictions that can differ between a normal browser profile and Incognito.
- The Apps Script page itself receives one shared PokéDrop Watch header and bottom navigation. Admin and Notify are therefore still separate sections and retain the same Home / Alerts / Notify / Admin / GitHub navigation.
- The public homepage remains lightweight and links to `notify.html` only.
- The service worker cache changes to `pokedrop-shell-v12` so the new portal launch pages replace older cached versions.

## Install

1. Upload this ZIP to the repository's `updates/` folder and commit it. Let the existing patch installer apply the files.
2. Open the existing Google Apps Script project attached to the current deployment.
3. In `Code.gs`, replace only the existing `doGet(e)` function and add the companion `pokedropPortalOutput_(...)` helper from `backend/apps-script/doGet_REPLACEMENT.txt`. Do not replace the other server functions.
4. Confirm the Apps Script project contains HTML files named exactly `Admin`, `Subscribe`, and `Index`. Keep the current `Admin.html` and `Subscribe.html` contents; the shared navigation is injected by the router.
5. Save, choose **Deploy → Manage deployments → Edit → New version → Deploy**. Keep the existing deployment, execution identity, access setting, and URL.
6. Test these two URLs directly in a normal browser window:
   - `https://script.google.com/macros/s/AKfycbwGfc1E_t1nj-HG5Sf5V1Y-J_cwY_PmwLIUAfbPPBVtl7mbxOhCkz5Q6BNosWmEUmVm/exec?page=admin`
   - `https://script.google.com/macros/s/AKfycbwGfc1E_t1nj-HG5Sf5V1Y-J_cwY_PmwLIUAfbPPBVtl7mbxOhCkz5Q6BNosWmEUmVm/exec?page=subscribe`
7. After both direct links work, open the GitHub Pages Admin and Notify pages. They will redirect to those same top-level routes.

## Why the Apps Script edit is manual

The GitHub Pages updater can install repository files, but it cannot publish changes into Google's Apps Script deployment. The routing helper must be added to the existing Apps Script project and deployed as a new version.

## GitHub Actions test failures from the supplied run

The attached Actions log reports 82 tests with four failures. The failures are all stale assertions in `tests/test_auth_architecture.py`: they expect the Admin page to use an iframe, expect the subscription iframe to remain on `index.html`, and expect old navigation hrefs (`./#pageTop` and `./#subscriptions`). The current design intentionally has a separate `notify.html` launch page and uses `./#top` and `./#alerts`. This patch updates those assertions to test the current design instead of reverting the site to the old iframe structure.

The first Actions run may still finish with the old test result because the repository workflow runs its test step before installing ZIP updates. Once the updated test files have been installed by the patch step, rerun the workflow; the next run will use the corrected assertions.

## If the Google generic Drive page still appears

This update removes the cross-site iframe, the most likely cause when the same page works in Incognito but not the regular browser profile. If the direct Apps Script URL still shows Google's generic Drive error in the regular profile, the remaining issue is at the Google session/account level rather than the GitHub Pages iframe. Test the direct URL in a separate Chrome/Edge profile or sign out of extra Google accounts and sign back into the account that owns the Apps Script deployment. Do not make the web app publicly editable; it should execute as the owner with the existing intended access setting.
