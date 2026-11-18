# PokéDrop Watch — uniform pixel layout and portal polish

This update improves the outer GitHub Pages layout and replaces the two Apps Script HTML templates. It does **not** change `Code.gs`; the currently deployed complete Code.gs already provides page routing, code verification, subscriber storage, authentication, and the portal rendering helper.

## Install the GitHub Pages patch

1. Upload this ZIP to the repository's `updates/` folder and commit it.
2. Let the existing GitHub Actions update workflow apply the files and run the tests.
3. Allow GitHub Pages to finish deploying. The service worker cache is bumped to `pokedrop-shell-v16` and will request the new stylesheet, script, and hero art.

## Update the two Google Apps Script HTML templates

The GitHub workflow cannot write to Google's Apps Script project. In the existing Apps Script project:

1. Open the existing `Admin` HTML file and replace **all** its contents with `backend/apps-script/Admin.html` from this ZIP.
2. Open the existing `Subscribe` HTML file and replace **all** its contents with `backend/apps-script/Subscribe.html` from this ZIP.
3. Save and deploy the existing web app as a **New version**. Keep the same deployment URL, execute-as identity, and public access setting.

Do not change `Code.gs`, `Index.html`, Script Properties, the service account, or Firestore configuration for this update. No partial Code.gs function copy is required.

## What's included

- Shared `PKMN RBYGSC` typography and consistent top/bottom navigation dimensions across Home, Admin, Notify, and the guide page.
- A vibrant pixel-art home hero with a floating throw arc.
- Wider product cards with larger thumbnails, a dedicated price rail, and no clipping of `Price not listed`.
- Clicking a product thumbnail opens the same destination as `VIEW ITEM` / `VIEW PRODUCT`.
- One click/tap throws one page-specific ball. Holding the left mouse button for more than one second starts rapid-fire throws distributed across the screen; releasing stops the sequence.
- The Pallet Town / Pokédex label follows scroll position.
- A compact Notify form with one concise `Receive Notifications` intro and verification panel placed directly after the form that requested it.
- Gym Leader wording in the Admin tool.
- One `How it works ↗` link on Admin and Notify to the full guide, instead of a collapsible duplicate guide.
- A centered, consistent fan-made/source-repository footer and bottom navigation on the guide page.

## Verification notes

The ZIP contains the existing focused test updates plus new UI consistency tests. Local syntax/markup checks cover the new JavaScript, CSS, and Apps Script HTML. Actual Gmail delivery and live iframe behavior still depend on the current Apps Script deployment and browser session and are not claimed as verified by this file build.
