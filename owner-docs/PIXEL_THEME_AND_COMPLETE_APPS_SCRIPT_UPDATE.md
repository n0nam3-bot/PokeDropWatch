# PokéDrop Watch — Pixel Theme, Alert Layout, and Complete Apps Script Update

This update corrects the alert-card image overlap, keeps prices on one line, adds the game-style pixel-ball interactions, and applies the final Notify/Admin page cleanup inside the Apps Script iframe itself.

## 1. Install the GitHub Pages patch

1. Upload this ZIP to the repository's `updates/` folder.
2. Commit the ZIP. The existing update workflow applies the files to the repository.
3. Once the update installer has run, the next monitor workflow will use the new page assets and tests.

## 2. Replace the entire Apps Script `Code.gs`

The Apps Script portal is hosted separately from GitHub Pages, so its deployed copy must be updated once.

1. Open the existing Google Apps Script project attached to the current web-app deployment.
2. Open the existing file named **Code.gs**.
3. Select all contents and replace them with the **complete file** at `backend/apps-script/Code.gs` from this ZIP.
4. Save the project.

Do not paste just `doGet(e)` or a helper function. The ZIP contains the complete backend file, including the existing email verification, rate limiting, administrator authentication, password reset, Firestore access, and subscriber-management functions.

Leave the existing Apps Script HTML files named `Admin`, `Subscribe`, and `Index` in place. The new `doGet(e)` applies the requested changes when Admin and Notify are rendered, including:

- Removing the old duplicate Admin header/footer and login hint
- Removing the old Notify `HOW IT WORKS` side panel and invisible honeypot label
- Moving the six-digit code panel directly beneath the form that requested it
- Showing the revised `Accepted the email request ...` confirmation copy
- Adding compact expandable guides for Admin and Notify
- Applying the Ultra Ball / Master Ball cursor and click-to-throw effect inside the embedded portal

The existing Script Properties (service account JSON, email secrets, administrator credentials, etc.) are not changed by replacing Code.gs.

## 3. Deploy the Apps Script change

1. Choose **Deploy → Manage deployments**.
2. Edit the existing web-app deployment and choose **New version**.
3. Keep the existing deployment URL.
4. Keep **Execute as: Me** and the public access setting **Anyone** so the portals continue to load inside the public GitHub Pages site.
5. Deploy.

No URL changes are required in `docs/admin.html` or `docs/notify.html`.

## 4. What to check

- Home shows the pixel-art Poké Ball hero sprite and continuously swaying top-bar Poké Ball.
- Scrolling to Alerts changes the location label from **PALLET TOWN** to **POKÉDEX**.
- Clicking the page throws the current page's ball sprite toward the click location.
- Notify shows the Ultra Ball, **POKÉMON CENTER**, the application form, and an expandable guide. The six-digit code panel appears immediately below the button that requested it.
- Admin shows the Master Ball, **GYM LEADER**, a clean sign-in panel, and an expandable guide.
- Alert thumbnails remain inside their image column and do not overlap the item title. Prices stay on one line.

The ZIP includes the complete replacement `Code.gs`; there are no partial-code copy/paste steps.
