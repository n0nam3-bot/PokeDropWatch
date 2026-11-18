# Keep Admin and Notify inside the PokéDrop website

## What this corrects

The previous update intentionally redirected the browser from GitHub Pages to `script.google.com`. That contradicted the requested site navigation. This patch restores the GitHub Pages shells and embeds the Apps Script Admin and Subscribe portals in their page iframes.

When these pages load successfully, the browser address stays on:

- `https://n0nam3-bot.github.io/PokeDropWatch/admin.html`
- `https://n0nam3-bot.github.io/PokeDropWatch/notify.html`

The outer header and bottom navigation remain the same PokéDrop site shell. The actual Admin and Notify forms run in Apps Script inside each frame, so their `google.script.run` calls still work.

## Install

1. Upload this ZIP to the repository's `updates/` folder and commit it.
2. Let the existing patch workflow install the files.
3. In the existing Apps Script project, replace only `doGet(e)` and add `pokedropEmbeddedOutput_` from `backend/apps-script/doGet_REPLACEMENT.txt`.
4. Verify the Apps Script project still contains the HTML files named exactly `Admin`, `Subscribe`, and `Index`.
5. Deploy the existing web app as a **New version**, keeping its current deployment URL and execution identity. For a public GitHub Pages iframe, the web app must execute as the owner and allow **Anyone** (not a sign-in-required audience).
6. Run GitHub Actions again after the patch has been installed so it uses the corrected tests.

## Why normal browser and Incognito can differ

The redirect in the previous patch was caused by that patch's `window.location.replace()`; it was not an unavoidable Google requirement. This patch removes it.

The remaining Incognito-versus-normal-profile difference is consistent with a Google session, browser extension, cached page, or third-party-cookie restriction in the regular browser profile. A static GitHub Pages page cannot override browser privacy settings for a cross-site Google iframe. This patch refreshes the site's service-worker cache to `pokedrop-shell-v13` and fetches pages without reusing the browser HTTP cache, but it cannot change the browser's Google-cookie policy.

If the frame still shows Google's generic Drive error in the regular profile after the Apps Script redeploy:

1. In Chrome/Edge, allow third-party cookies for `n0nam3-bot.github.io` to use `script.google.com` (and Google's `googleusercontent.com` redirect domain), or add an exception for Google's Apps Script host in the browser's third-party-cookie settings.
2. Temporarily disable privacy/ad-blocking extensions for the PokéDrop site and reload.
3. Confirm the web app is deployed as **Execute as: Me** and **Who has access: Anyone**. Do not use an audience that requires Google sign-in.
4. Try signing out of extra Google accounts in that browser profile, then reload the website.

Do not clear all browser data as a first step. The fallback links on the Admin and Notify pages still open the corresponding portal directly in a new tab for troubleshooting, but the primary experience remains embedded in GitHub Pages.

## Files

- `docs/admin.html` — restores the embedded Admin portal and GitHub Pages navigation.
- `docs/notify.html` — restores the embedded Notify portal and GitHub Pages navigation.
- `docs/sw.js` — cache v13 and network-first/no-store page fetching to remove the previous redirect shell.
- `backend/apps-script/doGet_REPLACEMENT.txt` — routes both portal pages and enables iframe embedding.
- `tests/test_auth_architecture.py` — replaces four stale assertions with checks for the separate Notify page and embedded GitHub Pages shells.
