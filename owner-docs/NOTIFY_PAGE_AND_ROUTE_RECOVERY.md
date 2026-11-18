# Dedicated Notify page and Google Apps Script route recovery

This update moves email enrollment off the landing page and onto `docs/notify.html`, matching the separate Admin page. The landing page no longer creates the Google Apps Script iframe, so the product watchlist and alerts load without waiting for the subscription portal.

## 1. Install the GitHub patch

Upload this ZIP into the repository's `updates/` folder and commit it. The GitHub Actions workflow installs the files and runs the tests. The previous failed Actions run was caused by an outdated test that still expected only Amazon and Walmart; the corrected test now checks all six requested retailer choices.

## 2. Update the existing Apps Script project

GitHub Actions cannot change the live Google Apps Script deployment. In the existing PokéDrop Watch Apps Script project owned by `pokedropwatch.notify@gmail.com`:

1. Open the existing HTML file **Admin** and replace its contents with `backend/apps-script/Admin.html` from the repository. This file intentionally has no second PokéDrop Watch header or duplicate branded footer.
2. Open the HTML file **Subscribe** and replace its contents with `backend/apps-script/Subscribe.html`. Create it first only if it does not exist; the file name must be exactly `Subscribe`.
3. In `Code.gs`, replace only the existing `doGet(e)` with the complete function and helper in `backend/apps-script/doGet_REPLACEMENT.txt`. Keep the other functions and Script Properties unchanged.
4. Confirm `SITE_ORIGIN` is exactly `https://n0nam3-bot.github.io` (origin only).
5. In the Apps Script editor, run `authorizeOwnerAccess()` once and approve MailApp permission if it has not already been granted.
6. Open **Deploy → Manage deployments → Edit → Version → New version → Deploy**. Keep the existing `/exec` URL and set access to **Anyone**. Do not create a second deployment unless the existing one no longer exists.

## 3. Verify the two routes before using GitHub Pages

Open each URL directly in a new browser tab while signed in to the notification mailbox:

- Admin: `https://script.google.com/macros/s/AKfycbwGfc1E_t1nj-HG5Sf5V1Y-J_cwY_PmwLIUAfbPPBVtl7mbxOhCkz5Q6BNosWmEUmVm/exec?page=admin`
- Subscribe: `https://script.google.com/macros/s/AKfycbwGfc1E_t1nj-HG5Sf5V1Y-J_cwY_PmwLIUAfbPPBVtl7mbxOhCkz5Q6BNosWmEUmVm/exec?page=subscribe`

Each URL must render its PokéDrop Watch page, not Google's generic Drive “Sorry, unable to open the file” page. If either route shows the generic Drive page, the deployed Apps Script version is not serving that HTML route yet. Recheck the HTML file name, the `doGet(e)` replacement, deployment version, and **Who has access: Anyone**. Do not keep reloading GitHub Pages until the direct Apps Script URL works.

## 4. Navigation and page behavior

- The main page has no embedded subscription iframe; it links to the dedicated Notify page.
- `docs/notify.html` has the same site header and bottom navigation as Admin, embeds the Apps Script Subscribe page, and includes a direct-open link in case Google blocks the embedded frame.
- Admin and Notify Home links use the landing page's top-level `#top` anchor.
- The service worker cache is bumped so the new page is included in the offline shell.

## Email behavior

The Subscribe form calls `requestVerificationCode` and `verifyVerificationCode` through `google.script.run` inside Apps Script. A success response is shown only after `MailApp.sendEmail` returns successfully. If the form displays an Apps Script error, check **Apps Script → Executions**, MailApp daily quota, owner authorization, and the `EMAIL_HMAC_SECRET` Script Property.
