# PokéDrop Watch — Owner setup (v1.3.0)

This guide configures the live website, private subscriber database, password-protected administrator portal, and branded email-code verification. Follow the steps in order. The website stays on GitHub Pages, Firestore remains the database, GitHub Actions runs the retailer monitor, and a small Google Apps Script project sends one-time verification codes from `pokedropwatch.notify@gmail.com`.

**No Google Sheet, Vercel, Firebase Hosting, Cloud Functions, or paid server is used.** Google Apps Script and Gmail still have their own free-use quotas; the app also enforces a conservative cap of 25 verification emails per UTC day, 3 per address per hour, and a 60-second resend cooldown.

> **Important change from v1.2:** Firebase passwordless email-link sign-in is no longer used. The old Firebase email sender and its daily email-link quota are not part of normal admin login or subscriber verification after this update is installed. Admins use a password. Visitors receive a six-digit code and enter it on the same browser page where they requested it.

## Values already known for this repository

- GitHub repository: `https://github.com/n0nam3-bot/PokeDropWatch`
- GitHub Pages origin: `https://n0nam3-bot.github.io`
- GitHub Pages website: `https://n0nam3-bot.github.io/PokeDropWatch/`
- Administrator page: `https://n0nam3-bot.github.io/PokeDropWatch/admin.html`
- Firebase project ID: `project-4868291462124176670`
- Notification email: `pokedropwatch.notify@gmail.com`

## Step 1 — Update the Firebase Firestore rules

1. Open [Firestore Rules for this Firebase project](https://console.firebase.google.com/project/project-4868291462124176670/firestore/rules).
2. Open the repository file [firebase/firestore.rules](https://raw.githubusercontent.com/n0nam3-bot/PokeDropWatch/main/firebase/firestore.rules).
3. Copy the complete contents of the repository file.
4. Return to Firebase Console → Firestore Database → **Rules**.
5. Replace the editor contents with the copied rules.
6. Find `replace-with-your-admin-email@example.com` in the Firebase Console editor only. Replace it with the exact lowercase administrator email address you will use to sign in.
7. Tap **Publish**.

Keep the placeholder in the public GitHub file. Never commit your real administrator email to the repository. The new rules allow only the signed-in administrator account to read or change subscriber documents. Public visitors cannot query subscriber addresses.

## Step 2 — Enable Firebase Email/Password authentication

1. Open [Firebase Authentication → Sign-in method](https://console.firebase.google.com/project/project-4868291462124176670/authentication/providers).
2. If Firebase asks you to get started, tap **Get started**.
3. Select **Email/Password**.
4. Turn on the first **Email/Password** switch.
5. Save.
6. You do **not** need to enable **Email link (passwordless sign-in)**. It is no longer used by this version. You may turn that option off.
7. Open [Authentication → Settings](https://console.firebase.google.com/project/project-4868291462124176670/authentication/settings).
8. Under **Authorized domains**, make sure `n0nam3-bot.github.io` is listed. Add it if missing. Enter only the hostname, without `https://` or a path.

## Step 3 — Create the administrator password account

The administrator account must be created manually in Firebase Console so nobody can claim the admin email through the public website.

1. Open [Firebase Authentication → Users](https://console.firebase.google.com/project/project-4868291462124176670/authentication/users).
2. Search for the exact administrator email you placed in the private Firestore Rules.
3. If the account already exists from the old email-link login, select that old passwordless account and delete **only that Authentication user**. This does not delete Firestore subscriber documents.
4. Tap **Add user**.
5. Enter the administrator email address and create a strong password. Save it in your password manager.
6. Do not create a public admin-registration form. The admin account is created only in this Firebase Console.

The admin portal now uses that email and password. It does not send an email during login, so signing in on your PC stays on your PC even when you read other email on your phone.

## Step 4 — Confirm the Firebase web-app configuration

1. Open [Firebase Project Settings](https://console.firebase.google.com/project/project-4868291462124176670/settings/general).
2. Scroll to **Your apps** and select the Web app registered for PokéDrop Watch. If none exists, tap the Web `</>` icon, register `PokeDrop Watch Website`, and do not enable Firebase Hosting.
3. Copy `apiKey`, `authDomain`, `projectId`, `appId`, and `messagingSenderId` from the displayed `firebaseConfig` object.
4. Open [docs/firebase-config.js in GitHub](https://github.com/n0nam3-bot/PokeDropWatch/edit/main/docs/firebase-config.js).
5. Replace only the five placeholder values in the existing object with the matching values from Firebase.
6. Commit the change to `main`.

This web configuration is intended to be visible in the browser. Do not paste a service-account JSON/private key into this file.

### Confirm the Firebase browser API-key website restriction

Firebase password login is started by the PokéDrop Watch page, so the browser API key must allow the GitHub Pages website as a referrer. This is different from the old passwordless email-link flow: the `firebaseapp.com` action handler is no longer used for normal admin sign-in.

1. Open [Google Cloud API Credentials for this Firebase project](https://console.cloud.google.com/apis/credentials?project=project-4868291462124176670).
2. Find the browser API key whose value matches `apiKey` in `docs/firebase-config.js`. Do not edit a service-account key.
3. Tap the API key name.
4. Under **Application restrictions**, select **Websites** or **HTTP referrers**.
5. Make sure this exact pattern is in the allowlist:

   ```text
   https://n0nam3-bot.github.io/*
   ```

6. You may leave the older `https://project-4868291462124176670.firebaseapp.com/*` entry in place; it is no longer needed for the new admin login, but leaving it does not hurt. Keep any other valid patterns.
7. Save. Do not change the **API restrictions** section for this fix.

The separate Firebase Authentication → Settings → Authorized domains list must also contain `n0nam3-bot.github.io` as a hostname, as configured in Step 2.

## Step 5 — Create or download the Firebase service-account JSON

The Apps Script email service needs trusted permission to write subscriber records to Firestore. It uses a service-account key on the server side; that key must never appear in GitHub's `docs/` folder or browser JavaScript.

1. Open [Firebase Project Settings → Service Accounts](https://console.firebase.google.com/project/project-4868291462124176670/settings/serviceaccounts/adminsdk).
2. Select **Generate new private key** and confirm.
3. Keep the downloaded JSON file private. Do not upload it to the repository.
4. The same JSON may be stored in the GitHub Actions secret `FIREBASE_SERVICE_ACCOUNT_JSON` and in the Apps Script Script Property described below.
5. In [Google Cloud IAM](https://console.cloud.google.com/iam-admin/iam?project=project-4868291462124176670), find the service account whose email is the `client_email` value inside the JSON. Confirm it has permission to read and write Firestore data. If it does not, grant **Cloud Datastore User** (`roles/datastore.user`).

## Step 6 — Create the branded email-code service (no spreadsheet)

This is a standalone Apps Script project, not a Google Sheet. Create it while signed in to **`pokedropwatch.notify@gmail.com`** so verification messages are sent from the notification mailbox.

1. On the device/browser where you are signed in to `pokedropwatch.notify@gmail.com`, open [Create a Google Apps Script project](https://script.google.com/home/projects/create).
2. Name the project `PokéDrop Watch Verification`.
3. In the left **Files** panel, open `Code.gs`, select all starter code, and replace it with the complete contents of [backend/apps-script/Code.gs](https://raw.githubusercontent.com/n0nam3-bot/PokeDropWatch/main/backend/apps-script/Code.gs).
4. Tap the **+** beside Files → **HTML**. Name the file exactly `Index` (Apps Script adds `.html`).
5. Replace the new HTML file contents with [backend/apps-script/Index.html](https://raw.githubusercontent.com/n0nam3-bot/PokeDropWatch/main/backend/apps-script/Index.html).
6. In **Project Settings**, turn on **Show `appsscript.json` manifest file in editor**. Return to the Files panel, open `appsscript.json`, and replace its contents with [backend/apps-script/appsscript.json](https://raw.githubusercontent.com/n0nam3-bot/PokeDropWatch/main/backend/apps-script/appsscript.json).
7. Tap **Project Settings** (gear icon). Under **Script Properties**, choose **Add script property** and add every row below. Property names are case-sensitive.

| Property name | Exact value |
|---|---|
| `FIREBASE_PROJECT_ID` | `project-4868291462124176670` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Paste the entire contents of the private service-account JSON file as one value. Keep the opening and closing braces. |
| `EMAIL_HMAC_SECRET` | A new random secret of at least 32 characters. Generate it with a password manager. Do not reuse your Gmail password. |
| `SITE_ORIGIN` | `https://n0nam3-bot.github.io` |
| `EMAIL_FROM_NAME` | `PokéDrop Watch` |
| `EMAIL_REPLY_TO` | `pokedropwatch.notify@gmail.com` |

8. Save the Script Properties.
9. Return to the editor, select `authorizeOwnerAccess` in the function dropdown, and tap **Run**.
10. Google will ask for permission to send email and make external requests. Review and allow those permissions for your own script. If Google shows an unverified-app warning, choose **Advanced**, then **Go to PokéDrop Watch Verification (unsafe)** only after confirming you are authorizing the Apps Script project you just created.
11. Open **Deploy → New deployment**.
12. Tap the gear beside **Select type**, then choose **Web app**.
13. Set **Execute as** to **Me (`pokedropwatch.notify@gmail.com`)**.
14. Set **Who has access** to **Anyone**. The website needs to call this public endpoint; code verification, strict rate limits, and Firestore permissions protect the operations.
15. Tap **Deploy** and complete any authorization prompt.
16. Copy the Web app URL. It must end in `/exec`. Keep it private enough to avoid unnecessary sharing, but note that the URL itself is not a secret.

### Apps Script safety limits built into this project

- Six-digit code expires after 10 minutes.
- Code can be used once and is limited to five incorrect attempts.
- A new code invalidates the previous code for that address.
- At least 60 seconds between sends to the same address.
- Maximum three sends per address per hour.
- Application cap of 25 verification emails per UTC day, plus Google's own remaining-daily-quota check.
- A hidden honeypot field rejects basic automated form submissions.

Google Apps Script and Gmail have provider-level quotas too. The cap is intentionally conservative, but a free Gmail account is not an unlimited bulk-email service. If the community grows beyond these limits, use a dedicated transactional email service with a verified sending domain rather than repeatedly requesting codes.

## Step 7 — Connect the Apps Script URL to the website

1. In GitHub, open [docs/subscription-backend-config.js](https://github.com/n0nam3-bot/PokeDropWatch/edit/main/docs/subscription-backend-config.js).
2. Replace `PASTE_APPS_SCRIPT_WEB_APP_URL` with the complete `/exec` URL copied in Step 6. Keep the surrounding single quotes.
3. Commit the change to `main`.
4. Wait for GitHub Pages to deploy. Open [the PokéDrop Watch website](https://n0nam3-bot.github.io/PokeDropWatch/) and refresh it.

Do not put the service-account JSON, HMAC secret, or Gmail App Password in this file. Only the public Apps Script `/exec` URL belongs here.

## Step 8 — Configure Gmail for product-alert emails

The same mailbox sends scheduled product alerts from GitHub Actions. The code now displays the sender as **PokéDrop Watch <pokedropwatch.notify@gmail.com>** and sets the reply-to address to the notification mailbox.

1. Open [Google Account Security](https://myaccount.google.com/security) while signed in to `pokedropwatch.notify@gmail.com`.
2. Enable **2-Step Verification** if it is not already enabled.
3. Open [Google App Passwords](https://myaccount.google.com/apppasswords).
4. Create an App Password named `PokéDrop Watch GitHub`.
5. Copy the 16-character password. In GitHub, open [Repository Actions Secrets](https://github.com/n0nam3-bot/PokeDropWatch/settings/secrets/actions).
6. Add or update these repository secrets:

| Secret | Value |
|---|---|
| `SMTP_USERNAME` | `pokedropwatch.notify@gmail.com` |
| `SMTP_APP_PASSWORD` | The 16-character Google App Password, without spaces |
| `ALERT_EMAIL` | The address that should receive the owner's personal alert copy |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | The complete private service-account JSON, if not already present |

`SMTP_HOST` and `SMTP_PORT` are optional; the monitor defaults to `smtp.gmail.com` and port `587`.

## Step 9 — Publish the website through GitHub Pages

1. Open [PokéDrop Watch GitHub Pages settings](https://github.com/n0nam3-bot/PokeDropWatch/settings/pages).
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Set **Branch** to `main`.
4. Set the folder to `/docs`.
5. Tap **Save**.
6. Open [https://n0nam3-bot.github.io/PokeDropWatch/](https://n0nam3-bot.github.io/PokeDropWatch/). The GitHub repository Code tab still displays the README; the Pages URL is the actual website.

## Step 10 — Test both login and verification

1. Open [the administrator portal](https://n0nam3-bot.github.io/PokeDropWatch/admin.html) on your PC.
2. Enter the admin email and password created in Step 3. It should sign in directly without sending an email.
3. Open the public website on your phone or PC and submit a test application using an inbox you can access.
4. Check the inbox for an email displaying **PokéDrop Watch** from `pokedropwatch.notify@gmail.com`.
5. Enter the six-digit code into the website page where you submitted the application. You do not need to open a sign-in link or move sessions between devices.
6. Return to the admin portal and approve the pending application.
7. For unsubscribe testing, enter the subscriber email in the unsubscribe field, request a code, and enter the code on that page. The record should change to `unsubscribed`.

## Common problems

| What you see | What to check |
|---|---|
| Admin says invalid email/password | Firebase Authentication → Users. Confirm the admin account exists and Email/Password is enabled. Check the password. |
| Admin signs in but cannot load subscribers | Firestore → Rules. Confirm the real lowercase admin email is in the **deployed Console rules** and tap Publish. |
| Verification service does not load | Confirm `docs/subscription-backend-config.js` contains the current Apps Script `/exec` URL and that the deployment access is **Anyone**. |
| Script says a property is missing | Apps Script → Project Settings → Script Properties. Check exact spelling and save each required property. |
| Firestore read/write failed | Confirm the service account JSON is valid, the project ID matches, Firestore exists, and the service account has Cloud Datastore User access. |
| Verification email is not sent | Confirm the Apps Script deployment executes as `pokedropwatch.notify@gmail.com`, run `authorizeOwnerAccess`, and check Apps Script → Executions for the actual error. |
| Daily verification limit reached | The project cap is 25/day and Google's own Gmail/Apps Script quota also applies. Wait until the next UTC day; do not repeatedly retry. |
| Email sender still shows Firebase `noreply@...` | You are opening an old Firebase email-link message. The new app no longer sends Firebase email links. Request a fresh code after the Apps Script URL has deployed. |
| Old email-link 403 or `auth/quota-exceeded` | These relate to the retired Firebase email-link flow. Do not keep requesting those links; install this release and use password login/code verification. |
| The dashboard still shows only 2/8 retailer sources with matches | That is a separate retailer-parser/connectivity limitation, not an email setting. The source-health page reports actual matches and errors; it must be fixed with retailer-specific adapters and live tests. |

## Direct links

- [Firebase Console](https://console.firebase.google.com/project/project-4868291462124176670/overview)
- [Firestore Rules](https://console.firebase.google.com/project/project-4868291462124176670/firestore/rules)
- [Firebase Authentication Providers](https://console.firebase.google.com/project/project-4868291462124176670/authentication/providers)
- [Firebase Authentication Users](https://console.firebase.google.com/project/project-4868291462124176670/authentication/users)
- [Firebase Web App settings](https://console.firebase.google.com/project/project-4868291462124176670/settings/general)
- [Firebase Service Accounts](https://console.firebase.google.com/project/project-4868291462124176670/settings/serviceaccounts/adminsdk)
- [Google Cloud IAM](https://console.cloud.google.com/iam-admin/iam?project=project-4868291462124176670)
- [Create Apps Script project](https://script.google.com/home/projects/create)
- [Google App Passwords](https://myaccount.google.com/apppasswords)
- [GitHub Pages settings](https://github.com/n0nam3-bot/PokeDropWatch/settings/pages)
- [GitHub Actions secrets](https://github.com/n0nam3-bot/PokeDropWatch/settings/secrets/actions)
- [GitHub Actions workflow runs](https://github.com/n0nam3-bot/PokeDropWatch/actions)
