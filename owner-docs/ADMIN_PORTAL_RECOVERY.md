# PokéDrop Watch — standalone administrator portal recovery

This change removes the administrator login/reset page from the nested cross-origin iframe message bridge. The public subscription form continues to use `Index.html`; the admin portal now runs directly inside Apps Script and calls the existing server functions with `google.script.run`.

## 1. Install the Apps Script HTML file

In the existing **PokéDrop Watch Backend** project, create a new HTML file named exactly `Admin` (Apps Script displays it as `Admin.html`). Copy the complete contents of `backend/apps-script/Admin.html` into it and save.

## 2. Update `doGet` in `Code.gs`

Replace only the existing `doGet()` function with the contents of `backend/apps-script/doGet_REPLACEMENT.txt`. Leave the rest of `Code.gs` unchanged. The default `/exec` page remains the public verification bridge; `/exec?page=admin` serves the standalone admin page.

## 3. Deploy

Choose **Deploy → Manage deployments → Edit → New version → Deploy**. Keep the existing deployment. It must execute as the Apps Script owner and be available to Anyone.

## 4. Use the admin portal

Open `https://n0nam3-bot.github.io/PokeDropWatch/admin.html`. It redirects to the standalone Apps Script admin page. The portal reports administrator authentication separately from Firestore subscriber loading, so a database permission error no longer looks like a bad password.

The existing Script Properties are still required. The admin page does not use Firebase Authentication. It calls `adminLogin`, `requestAdminPasswordReset`, `completeAdminPasswordReset`, `adminListSubscribers`, `adminUpdateSubscriber`, and `adminLogout` already defined in `Code.gs`.

## 5. Workflow test repair

The previous `run-monitor` workflow failure was caused by `tests/test_auth_architecture.py` still asserting that the service worker cache name must be `pokedrop-shell-v8`, while the installed worker was already `pokedrop-shell-v9`. This patch advances it to `pokedrop-shell-v10` and updates the test to match. The monitor step is skipped after a failed test step, which explains why no new scan ran in that job.

No Firebase data, Firestore rules, service-account key, or IAM role is modified by this patch.
