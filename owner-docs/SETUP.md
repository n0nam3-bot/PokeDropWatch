# PokéDrop Watch — Owner setup and recovery guide

**Current release:** 1.4.0  
**Public website:** https://n0nam3-bot.github.io/PokeDropWatch/  
**Admin portal:** https://n0nam3-bot.github.io/PokeDropWatch/admin.html  
**GitHub repository:** https://github.com/n0nam3-bot/PokeDropWatch

This guide is for the site owner. The public site is in `docs/`; these instructions are in `owner-docs/` outside the GitHub Pages publish folder. Do not put credentials, service-account keys, or private settings in GitHub files.

## Current architecture — read before changing settings

- **GitHub Pages** serves the public site from `main` → `/docs`.
- **GitHub Actions** scans retailer search pages on a 15-minute cron and publishes public scan data to `docs/data/state.json`.
- **Firestore** is the private subscriber database. No Google Sheet is used.
- **Google Apps Script** sends verification/reset codes, handles the administrator login, and performs private subscriber operations.
- **`pokedropwatch.notify@gmail.com`** must own the Apps Script project and be the account that the web app executes as. Apps Script MailApp uses that account as the sender; the code sets the display name to `PokéDrop Watch` and Reply-To to the same mailbox.
- **Firebase Authentication is not used by v1.4.0.** The administrator signs in using the password stored as an HMAC hash in Apps Script Script Properties. There should be no Firebase `noreply@...firebaseapp.com` sign-in or password-reset email from the current admin page.

A public Firebase web API key is not an admin credential. Never put the service-account JSON, Gmail App Password, HMAC secrets, or admin password in `docs/` or any committed file.

---

## A. Verify GitHub Pages first

1. Open [PokéDrop Watch → Pages settings](https://github.com/n0nam3-bot/PokeDropWatch/settings/pages).
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Set **Branch** to `main` and **Folder** to `/docs`; press **Save**.
4. Open the public site: https://n0nam3-bot.github.io/PokeDropWatch/.
5. Open the admin page: https://n0nam3-bot.github.io/PokeDropWatch/admin.html.

The repository's Code tab showing `README.md` is normal. Visitors use the Pages URL, not the Code tab.

## B. Firestore database and private access

1. Open [Firebase Console](https://console.firebase.google.com/project/project-4868291462124176670/overview) and verify the project ID is `project-4868291462124176670`.
2. Open [Firestore Database](https://console.firebase.google.com/project/project-4868291462124176670/firestore). If there is no database yet, choose **Create database** → **Native mode** → select a location. Firestore's location cannot be changed later.
3. Open [Firestore Rules](https://console.firebase.google.com/project/project-4868291462124176670/firestore/rules).
4. Open [`firebase/firestore.rules`](https://raw.githubusercontent.com/n0nam3-bot/PokeDropWatch/main/firebase/firestore.rules), copy the complete file, paste it into the Rules editor, and click **Publish**.
5. The deployed browser rules intentionally deny all direct browser reads and writes. Apps Script and GitHub Actions use a private service-account identity through Google IAM. Do not change the rule to public access such as `allow read, write: if true`.

### Create or confirm the service-account key

1. Open [Firebase Project Settings → Service Accounts](https://console.firebase.google.com/project/project-4868291462124176670/settings/serviceaccounts/adminsdk).
2. Click **Generate new private key** and download the JSON file. Keep it private; do not upload it to GitHub.
3. Open [Google Cloud IAM](https://console.cloud.google.com/iam-admin/iam?project=project-4868291462124176670).
4. Find the service account whose email matches `client_email` inside the JSON. Grant **Cloud Datastore User** (`roles/datastore.user`) on this project if it does not already have a role granting Firestore data access.
5. Use the exact JSON file contents in the Apps Script property `FIREBASE_SERVICE_ACCOUNT_JSON` and GitHub secret `FIREBASE_SERVICE_ACCOUNT_JSON`.

---

## C. Update the existing Apps Script backend (important)

**If you already created/deployed a PokéDrop Watch Apps Script project during v1.3 setup, update that same project. Do not create a second project and do not keep using its old deployment version.** This is a likely cause of stale Firebase messages and admin login failures: changing files in GitHub does not update the copy running on Google's servers.

1. On a phone or PC, sign in to Google as **`pokedropwatch.notify@gmail.com`**.
2. Open [Google Apps Script projects](https://script.google.com/home). Locate your existing **PokéDrop Watch Backend** project. Open it. Only when no existing project exists, create one at [New Apps Script project](https://script.google.com/home/projects/create) and name it `PokéDrop Watch Backend`.
3. In the Files panel, open `Code.gs`. Replace its entire contents with the current repository file [`backend/apps-script/Code.gs`](https://raw.githubusercontent.com/n0nam3-bot/PokeDropWatch/main/backend/apps-script/Code.gs).
4. Open the HTML file named `Index`. Replace its entire contents with [`backend/apps-script/Index.html`](https://raw.githubusercontent.com/n0nam3-bot/PokeDropWatch/main/backend/apps-script/Index.html). If it does not exist, click **+** → **HTML**, name it exactly `Index`, then paste the file contents.
5. Open **Project Settings** (gear icon). Enable **Show `appsscript.json` manifest file in editor**. Open `appsscript.json` and replace it with [`backend/apps-script/appsscript.json`](https://raw.githubusercontent.com/n0nam3-bot/PokeDropWatch/main/backend/apps-script/appsscript.json).
6. Click **Project Settings** → **Script Properties** → **Edit script properties**. Keep existing correct properties and add/update the exact names below. Never add quotes around values and never include placeholder angle brackets.

| Script Property | Value |
|---|---|
| `FIREBASE_PROJECT_ID` | `project-4868291462124176670` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Entire contents of the private service-account JSON file |
| `EMAIL_HMAC_SECRET` | New random secret, minimum 32 characters |
| `SITE_ORIGIN` | `https://n0nam3-bot.github.io` — origin only, no `/PokeDropWatch/` path |
| `EMAIL_FROM_NAME` | `PokéDrop Watch` |
| `EMAIL_REPLY_TO` | `pokedropwatch.notify@gmail.com` |
| `ADMIN_EMAIL` | Your chosen administrator email in lowercase |
| `ADMIN_PASSWORD_PEPPER` | Separate random secret, minimum 32 characters |
| `ADMIN_INITIAL_PASSWORD` | Only needed for first-time admin initialization; minimum 12 characters |

7. Click **Save script properties**. The private service-account JSON, password, and secrets stay in Script Properties only.
8. **First-time admin only:** in the Apps Script function selector, choose `initializeAdminCredentials` → **Run** and approve the prompts. The function hashes `ADMIN_INITIAL_PASSWORD` and deletes the plaintext property. Do not run this again after initialization. If you already have `ADMIN_PASSWORD_HASH`, keep it and use **Forgot password?** on the admin page to reset it with an email code.
9. In the function selector, choose `authorizeOwnerAccess` → **Run** and approve the MailApp and external-request permissions. If Google already granted these scopes, it may not prompt again.
10. **Update the deployment:** open **Deploy** → **Manage deployments**. Select the existing web app deployment, click the pencil **Edit**, choose **Version → New version**, then click **Deploy**. This updates the existing deployment URL. Copy its URL ending in `/exec`.
    - If this is the very first deployment only: **Deploy** → **New deployment** → gear → **Web app**; **Execute as: Me (`pokedropwatch.notify@gmail.com`)**; **Who has access: Anyone**; **Deploy**; copy the `/exec` URL.
11. Open [`docs/subscription-backend-config.js`](https://github.com/n0nam3-bot/PokeDropWatch/edit/main/docs/subscription-backend-config.js). Replace `PASTE_APPS_SCRIPT_WEB_APP_URL` with the copied URL, preserving the single quotes, then commit.

### Sender address and display name

The Apps Script project must be owned by `pokedropwatch.notify@gmail.com`, and the deployed web app must **Execute as Me**. The Apps Script code sends with `name: 'PokéDrop Watch'` (read from `EMAIL_FROM_NAME`) and `replyTo: 'pokedropwatch.notify@gmail.com'`. That produces a sender displayed as **PokéDrop Watch** from the notification mailbox. Setting `EMAIL_FROM_NAME` alone cannot make another Google account send as this address; the owner/execute-as account must be correct.

### Admin login and reset

- Go to https://n0nam3-bot.github.io/PokeDropWatch/admin.html.
- Enter `ADMIN_EMAIL` and the password created during initialization.
- For a reset, click **Forgot password?**, request a six-digit code, read that code in the notification mailbox, enter it on the same admin page, and set a new password of at least 12 characters.
- The code expires after 10 minutes, permits five incorrect attempts, and is single-use. The app applies a 60-second resend cooldown, three sends per address per hour, and a 25-email per UTC-day cap; Google MailApp quotas also apply.
- If you still receive a Firebase `noreply@...firebaseapp.com` email, the current v1.4 admin JavaScript is not the code being served or another Firebase application is sending it. Confirm Pages has deployed the latest `docs/admin.js`, then refresh after the new service worker activates. This application no longer imports Firebase Authentication.

---

## D. GitHub Actions email and Firestore secrets

1. Open [Repository → Settings → Secrets and variables → Actions](https://github.com/n0nam3-bot/PokeDropWatch/settings/secrets/actions).
2. Under **Repository secrets**, add/update these exact entries:

| Secret | Value |
|---|---|
| `SMTP_USERNAME` | `pokedropwatch.notify@gmail.com` |
| `SMTP_APP_PASSWORD` | Gmail App Password for this mailbox, 16 characters with spaces removed |
| `ALERT_EMAIL` | Optional mailbox to receive an additional owner-only alert copy |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Same complete private service-account JSON contents |

3. For `SMTP_APP_PASSWORD`, first enable 2-Step Verification for the notification mailbox, then open [Google App Passwords](https://myaccount.google.com/apppasswords), create one named `PokéDrop Watch GitHub`, and copy the generated value. Do not use the normal Gmail password.
4. Under **Variables**, add/update `PUBLIC_SITE_URL` with `https://n0nam3-bot.github.io/PokeDropWatch`.
5. Open [GitHub Actions workflow permissions](https://github.com/n0nam3-bot/PokeDropWatch/settings/actions). Confirm Actions are enabled and **Workflow permissions** is set to **Read and write permissions**, because the scheduled monitor commits refreshed state and applies uploaded update ZIPs.

The scheduled scan uses the cron in `.github/workflows/pokedrop-watch.yml`: `*/15 * * * *` (every 15 minutes, subject to GitHub scheduling delays). The `check_interval_minutes` entry in `config/sources.json` is descriptive; changing it does not change the actual schedule.

---

## E. Font file (PKMN RBYGSC)

The CSS is prepared to load the display font from `docs/assets/fonts/PKMN-RBYGSC.ttf`. The DaFont page is a download webpage, not a direct `.ttf` file, and the binary is not included in this patch.

1. Open [PKMN RBYGSC on DaFont](https://www.dafont.com/pkmn-rbygsc.font) and download the font archive.
2. Extract the archive and locate its `.ttf` file.
3. Upload that file to `docs/assets/fonts/` and name it exactly `PKMN-RBYGSC.ttf`.
4. Commit. The website uses the pixel font on headings/navigation/filter labels and keeps long product descriptions in a readable system font.
5. Review the font author's license for your intended use. The repository patch does not redistribute the font file.

---

## F. Source status and product labels

- **MATCHES** — at least one configured URL returned Pokémon entries the parser recognized.
- **NO MATCH** — a configured URL responded, but no supported Pokémon items were extracted. This does not mean the retailer has no stock.
- **ISSUE** — all configured URLs failed to respond successfully.
- A source can now include `alternate_urls` (up to three extra public search pages). The scanner checks the primary and alternates, then merges/deduplicates the results under the same retailer/source card. These are fallback routes, not a guarantee the retailer will allow automated access.
- The monitor does not run a full visual browser, execute arbitrary retailer JavaScript, solve queues/CAPTCHAs, or bypass anti-bot restrictions. Some retailers will still require dedicated adapters or official data feeds.
- **FIRST SEEN** means first observed by this monitor, not first listed by the seller or newly released by Pokémon. It is not sent as a new-drop email. Verified restocks require an observed stock transition; price events require values exposed by the retailer. Historical `NEW DROP` catalog events are migrated to `FIRST SEEN` during the next scheduled/manual monitor run and removed from pending alert email.
- The example 2018 Amazon marketplace listing in the owner report cannot be used as a “new drop.” Its age is not reliably available from the generic search result, so v1.4 labels first discovery as `FIRST SEEN` and avoids making a release-date claim.

To inspect results, open [Actions](https://github.com/n0nam3-bot/PokeDropWatch/actions), choose **PokéDrop Watch**, and click **Run workflow**. Read each source line in the job log and then refresh the public site. The dashboard displays the last saved scan; it does not itself trigger a retailer scan.

## G. Patch installation

For routine app changes, upload the supplied patch ZIP to the repository's `updates/` folder and commit the upload. The existing GitHub Actions workflow detects ZIP files, validates paths, and extracts changed files into the repository. It commits the updated app, then runs the monitor. The ZIP patch installer blocks `.github/workflows/`; workflow changes must be edited directly in GitHub.

**Important:** Apps Script lives on Google's servers. A ZIP containing `backend/apps-script/Code.gs` does not update the deployed web app. Whenever a patch changes `Code.gs`, `Index.html`, or `appsscript.json`, copy the changed source into the existing Apps Script project and perform **Deploy → Manage deployments → Edit → New version → Deploy**. Keep the same deployment and `/exec` URL where possible.

## H. Recovery checklist

### Admin portal says service did not load / times out
1. Check that `docs/subscription-backend-config.js` contains the current Apps Script `/exec` URL (not an editor URL and not `/dev`).
2. In Apps Script, open **Deploy → Manage deployments** and confirm the Web app is active, executes as `pokedropwatch.notify@gmail.com`, and is accessible to **Anyone**.
3. Confirm you deployed a **New version** after replacing the code and `Index.html`.
4. Open Apps Script **Executions** and inspect the latest error. Never paste service-account JSON or secrets into a public issue.

### Admin email/password rejected
1. Confirm `ADMIN_EMAIL` in Script Properties exactly matches the login email, in lowercase.
2. If this is a first-time setup, run `initializeAdminCredentials` once after adding `ADMIN_INITIAL_PASSWORD`.
3. If already initialized, do not rerun initialization. Use **Forgot password?** on the admin page and enter the code sent to the notification mailbox.
4. Check MailApp quota and Apps Script **Executions** if the reset code does not arrive.

### Website still displays Firebase sign-in or reset links
1. Confirm GitHub Pages published the latest `main` branch `/docs` build.
2. Open the admin page in a private/incognito window. The v1.4 service worker uses cache `pokedrop-shell-v8` and deletes earlier PokéDrop shell caches on activation.
3. Confirm the deployed `docs/admin.js` calls Apps Script `adminLogin` and does not import Firebase Auth.
4. Confirm the Apps Script deployment is also updated; GitHub Pages and Apps Script are two separate deployments.

### Retailers still show NO MATCH or ISSUE
1. Open Actions → latest PokéDrop Watch run → scan log.
2. `NO MATCH` means the HTML/JSON returned no recognizable product entities; `ISSUE` means all configured URLs failed.
3. Do not mark a source complete based only on an HTTP 200. A parser change needs a saved sanitized response fixture and a passing test, then a successful live scan.
