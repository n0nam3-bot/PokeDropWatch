# PokéDrop Watch — Firebase Setup

This guide configures the public subscription form, private subscriber database, administrator approval page, and subscriber email delivery. It is a one-time setup. The website remains hosted on GitHub Pages; no Vercel account, Google Sheet, paid server, or Cloud Function is required.

The intended no-cost setup uses Firebase's Spark plan, GitHub Pages/Actions, and a Gmail account for alert delivery. Free plans have quotas and provider terms can change. This is intended for a small, low-volume community, not unlimited bulk email. Do not add a billing account just to follow this guide.

## 1. Create the Firebase project

1. Open the Firebase Console and create a project for PokéDrop Watch.
2. Keep the project on the no-cost Spark plan. Analytics are not required; you may turn them off.
3. In **Build → Firestore Database**, create a database.
4. Choose a database location close to you and your expected subscribers. The location cannot be changed after creation.
5. Open the **Rules** tab. Replace the starter rules with the complete contents of `firebase/firestore.rules` from this repository.
6. In the Firebase Console rules editor, replace `replace-with-your-admin-email@example.com` with the lowercase email address that will own the site administrator account. Publish the rules there. Keep the placeholder in the public GitHub copy; do not commit your real administrator email.

Do not leave Firestore in test mode. The supplied rules make subscriber records private, permit a verified user to read only their own record, and permit only the configured verified administrator to view or change the full subscriber list.

## 2. Enable secure email sign-in

1. Open **Build → Authentication → Get started**.
2. Under **Sign-in method**, enable **Email/Password** and enable the **Email link (passwordless sign-in)** option within that provider.
3. Open **Settings → Authorized domains**.
4. Add the hostname used by GitHub Pages, normally `YOUR-GITHUB-USERNAME.github.io`. Add any custom domain separately if one is used.
5. Save the changes.

The application and unsubscribe flows use Firebase email-link sign-in. Opening the link proves access to that mailbox. The unsubscribe link then presents a separate confirmation button; the email link alone does not unsubscribe the person.

## 3. Register the website as a Firebase web app

1. Open **Project settings → General → Your apps** and add a **Web app**.
2. Register it with a name such as `PokeDrop Watch Website`. Hosting in Firebase is not required.
3. Copy the web configuration values from the Firebase SDK setup panel.
4. In this repository, open `docs/firebase-config.js` and replace the placeholders for `apiKey`, `authDomain`, `projectId`, `appId`, and `messagingSenderId` with the matching values.
5. Save and commit the file. The administrator email is deliberately not stored in public website JavaScript.

The Firebase web configuration is intended to be public in a browser application. It is not a password. The private service-account JSON in the next section must never be committed to the repository or placed in `docs/`.

## 4. Give GitHub Actions private database access

The scheduled monitor runs on GitHub's runner. It needs a private service-account credential so it can read approved subscribers and write private delivery-retry records. This key stays in GitHub Actions Secrets and is never sent to the public website.

1. In Firebase **Project settings → Service accounts**, choose **Generate new private key** and download the JSON file.
2. In GitHub, open the PokéDrop Watch repository → **Settings → Secrets and variables → Actions → New repository secret**.
3. Set the name to `FIREBASE_SERVICE_ACCOUNT_JSON`.
4. Open the downloaded JSON file and paste its entire contents as the secret value. Save it.
5. Do not upload the JSON file to the repository, an issue, a chat, or a patch ZIP. If it is ever exposed, revoke the key and generate a new one.

The monitor uses the service account only in GitHub Actions to read subscriber records with status `active` and write delivery records under each subscriber's private Firestore document.

## 5. Configure email delivery

The Firebase sign-in links are sent by Firebase Authentication. Product alert emails are sent separately by the Gmail account configured in GitHub Actions.

In GitHub → repository **Settings → Secrets and variables → Actions**, add:

| Name | Type | Value |
|---|---|---|
| `SMTP_USERNAME` | Secret | Gmail address that sends product alerts. |
| `SMTP_APP_PASSWORD` | Secret | Gmail App Password, not the normal account password. |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Secret | Full service-account JSON from step 4. |
| `ALERT_EMAIL` | Optional secret | Address for an extra owner-only copy of the alert digest. It is not required for subscriber delivery. |
| `SMTP_HOST` | Optional secret | Defaults to `smtp.gmail.com`. |
| `SMTP_PORT` | Optional secret | Defaults to `587`. |

Gmail App Passwords require two-step verification on the Google account and may not be available for every account type or administrator policy. Gmail imposes sending limits. Start with a small, approved subscriber group and do not treat a personal Gmail mailbox as a high-volume email platform.

Also add a repository **Actions variable** (not a secret):

| Name | Value |
|---|---|
| `PUBLIC_SITE_URL` | The complete public site URL, including the repository path and trailing slash, for example `https://YOUR-GITHUB-USERNAME.github.io/REPOSITORY-NAME/`. |

The notification email uses this URL to link back to the secure preference/unsubscribe form.

## 6. Update the GitHub Actions workflow

The monitor workflow must pass the private service-account secret and public site URL to `monitor/run.py`.

Replace the existing `.github/workflows/pokedrop-watch.yml` with the workflow file supplied alongside this release. Keep the exact path and filename. The replacement continues to scan on its scheduled interval and apply ZIP updates, and adds these environment values to the monitor step:

- `FIREBASE_SERVICE_ACCOUNT_JSON: ${{ secrets.FIREBASE_SERVICE_ACCOUNT_JSON }}`
- `PUBLIC_SITE_URL: ${{ vars.PUBLIC_SITE_URL }}`

Workflow files are intentionally not installed by ordinary application patch ZIPs. This one-time workflow replacement must be made directly at `.github/workflows/pokedrop-watch.yml` in GitHub.

## 7. Publish the actual website (not the repository README)

In the GitHub repository:

1. Open **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch `main` and folder `/docs`.
4. Save.
5. Open the GitHub Pages URL shown on that page. It normally looks like `https://YOUR-GITHUB-USERNAME.github.io/REPOSITORY-NAME/`.

The repository's Code tab will still show `README.md`; that is normal. Visitors use the separate GitHub Pages URL. The website entry point is `docs/index.html`. The private admin page is `docs/admin.html` at `/REPOSITORY-NAME/admin.html`.

If the Pages URL still displays the README, verify that `docs/index.html` exists on the `main` branch and that Pages is set to `/docs`, not `/root`.

## 8. First-time administrator login

1. Open the public website and select **Administrator** in the footer, or open `/admin.html` directly.
2. Enter the same lowercase administrator email you configured privately in the deployed Firestore rules. The address is not embedded in public website code.
3. Request the secure sign-in link and open it from the same browser.
4. Firestore rules—not the browser—decide whether the verified account can manage subscriber records. A non-admin account is denied access.
5. Open **Subscriber management** to review pending applications.

Only the configured, verified administrator email can list subscriber records or approve, reject, suspend, reactivate, or remove them. A visitor cannot promote themselves by changing browser data.

## 9. Test the complete flow

1. Open the public site and submit an application using an email address you can access.
2. Open the Firebase email sign-in link. The website should show that the application is pending approval.
3. Open the administrator page using the configured admin email.
4. Approve the test application.
5. Confirm its status changes to active in the administrator list.
6. Run the GitHub Actions workflow manually once. The monitor will queue/send matching new alerts to active subscribers; it does not send historical products simply because someone was approved.
7. Test unsubscribe. Enter the subscriber email on the public page, open the secure link, and press **Confirm unsubscribe**. Confirm the admin list shows `unsubscribed`.

The first source scan establishes a baseline. It may not create a product alert until a later scan detects a change. To test email delivery immediately, use the workflow's existing test procedure or wait for a real detected change; do not edit production Firestore records to manufacture an alert.

## Privacy and operating limits

- Subscriber email addresses are stored in Firestore, not in the public `docs/data/state.json` file.
- The public browser can create only a verified pending application and can edit its own notification preferences or unsubscribe its own record.
- GitHub Actions uses the service-account secret for private delivery. Each subscriber receives an individual email; subscriber addresses are not exposed to other recipients.
- Pending email deliveries are stored in private Firestore subcollections and retried on later workflow runs.
- Firebase, GitHub Actions, and Gmail each have quotas and anti-abuse limits. The no-cost setup is practical for a small community but is not unlimited or guaranteed for large-scale distribution.
- Firebase's built-in email-link protections and a local resend cooldown reduce casual abuse. A public service that grows significantly should add stronger abuse controls and use a dedicated transactional email provider before increasing volume.
