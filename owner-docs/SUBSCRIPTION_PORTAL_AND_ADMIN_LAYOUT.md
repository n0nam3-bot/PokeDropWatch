# Subscription portal and admin layout update

This update removes the public signup page's cross-frame `postMessage` dependency. The email verification form now runs inside an Apps Script HTML page and invokes `requestVerificationCode` / `verifyVerificationCode` with `google.script.run`, the same direct server-call method used by the working administrator portal.

## 1. Upload the ZIP

Upload this ZIP to the repository's `updates/` folder and commit it. The existing GitHub Actions workflow will install the website files and run the repository tests.

## 2. Update the existing Apps Script project

GitHub Actions cannot edit the deployed Google Apps Script project. Open the existing PokéDrop Watch Apps Script project as `pokedropwatch.notify@gmail.com`.

1. Open the existing HTML file named **Admin** and replace its entire contents with `backend/apps-script/Admin.html` from the updated repository. This removes the second PokéDrop Watch header and duplicate footer. Do not create a second Admin file.
2. Click **+ → HTML**, create a new file named exactly **Subscribe**, and paste the complete contents of `backend/apps-script/Subscribe.html`.
3. Open `Code.gs`. Replace only the existing `doGet(e)` function with the function and helper in `backend/apps-script/doGet_REPLACEMENT.txt`. Keep all other functions and Script Properties.
4. Run `authorizeOwnerAccess()` from the Apps Script editor once and approve the MailApp permission prompt if it appears. This is required for the project owner to send verification email.
5. Go to **Deploy → Manage deployments → Edit → Version: New version → Deploy**. Keep the existing `/exec` URL and access settings.

## 3. Verify the routes

- Public signup portal: append `?page=subscribe` to the existing Apps Script `/exec` URL. The page should show the email application form.
- Admin portal: append `?page=admin` to the same URL. The embedded admin page should no longer display its own PokéDrop Watch header or duplicate branded footer; the GitHub Pages shell supplies the shared navigation.
- Public GitHub Pages signup form: the `Get Pokémon drop notifications` section embeds the new direct Apps Script form. There is no hidden signup message bridge.

## Email delivery behavior

The portal displays a success response only after `requestVerificationCode` returns `{ok:true}` from Apps Script. That server function returns success after `MailApp.sendEmail` has accepted the message for sending. If it returns an error, the portal displays that result instead of a generic cross-frame timeout. Check **Apps Script → Executions** if the returned message indicates a server-side problem; check the notification mailbox's MailApp quota and that `authorizeOwnerAccess()` has been run.

The verification code is still 6 digits, expires after 10 minutes, and must be entered on the same embedded portal page. The Firestore subscriber record is saved only after successful verification.
