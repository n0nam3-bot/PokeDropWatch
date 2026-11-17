# PokéDrop Watch — exact owner setup instructions

This is the click-by-click setup guide for the current v1.2 application. Follow it from top to bottom. You only need to do this once, unless you change Firebase projects, the GitHub repository, or the email-sending account.

**The website is hosted by GitHub Pages. Firebase provides the subscriber database and email-link sign-in. GitHub Actions runs the monitor. Gmail sends product-alert emails.** You do not need Vercel, Google Sheets, Firebase Hosting, Cloud Functions, or a paid server.

> **Cost note:** This setup is designed to stay on Firebase's no-cost Spark plan and the free allowances of GitHub/Gmail. Free plans have quotas and provider terms can change. Do not add a billing account or upgrade to a paid plan just to follow this guide. A free service is not unlimited email or unlimited database usage.

---

## Before you start: identify your GitHub address

Open your PokéDrop Watch repository in GitHub.

The repository address looks like:

`https://github.com/OWNER/REPOSITORY`

Write down the two parts:

- `OWNER` = your GitHub username or organization name.
- `REPOSITORY` = the repository name, without `.git`.

For example, if the repository address is `https://github.com/example-user/PokeDropWatch`, then `OWNER` is `example-user` and `REPOSITORY` is `PokeDropWatch`.

Whenever a link below contains `OWNER`, `REPOSITORY`, or `PROJECT_ID`, replace that word with your actual value before opening the link.

Your normal GitHub Pages address for a project repository is:

`https://OWNER.github.io/REPOSITORY/`

Special case: if the repository itself is named `OWNER.github.io`, the Pages address is `https://OWNER.github.io/` (there is no repository path).

The Firebase Authorized Domain is only the hostname, for example `example-user.github.io`. Do **not** include `https://`, a slash, or the repository name in that field.

---

## Step 1 — Create the Firebase project

1. Open the **[Firebase Console](https://console.firebase.google.com/)**.
2. Sign in with the Google account you will use to own the project.
3. Select **Create a project** (or **Add project**).
4. Enter the project name `PokeDrop Watch` and continue.
5. When asked about Google Analytics, choose **Disable Google Analytics**. Analytics is not used by this app.
6. Finish creating the project.
7. Keep the project on the **Spark (no-cost) plan**. Do not click Upgrade or add a billing account.
8. Find the **Project ID**: click the gear icon beside Project Overview → **Project settings** → **General** → copy the **Project ID**. Save it privately; you will use it in the direct Firebase links below.

Your project-specific Firebase Console links have this format:

- Project overview: `https://console.firebase.google.com/project/PROJECT_ID/overview`
- Firestore: `https://console.firebase.google.com/project/PROJECT_ID/firestore`
- Authentication providers: `https://console.firebase.google.com/project/PROJECT_ID/authentication/providers`
- Authentication settings: `https://console.firebase.google.com/project/PROJECT_ID/authentication/settings`
- Project settings: `https://console.firebase.google.com/project/PROJECT_ID/settings/general`
- Service accounts: `https://console.firebase.google.com/project/PROJECT_ID/settings/serviceaccounts/adminsdk`

Replace `PROJECT_ID` with the Project ID you just copied.

## Step 2 — Create the private Firestore database and publish its security rules

1. Open your project's **[Firestore Database page](https://console.firebase.google.com/)**. To go directly, use `https://console.firebase.google.com/project/PROJECT_ID/firestore` with your Project ID substituted.
2. Click **Create database**.
3. Choose **Standard edition** if the console asks which edition to use.
4. Choose **Start in production mode**. Do not choose test mode.
5. Choose a database location near you or the majority of your expected visitors. **The location cannot be changed after the database is created.**
6. Finish creating the database.
7. Open the **Rules** tab.
8. In a separate browser tab, open this rules file from your repository: `https://raw.githubusercontent.com/OWNER/REPOSITORY/main/firebase/firestore.rules` (replace `OWNER` and `REPOSITORY`). This opens the raw text of the exact rules file.
9. Copy the entire rules file and paste it into the Firestore Rules editor, replacing all starter text.
10. In the Firebase Rules editor only, find this placeholder:

   `replace-with-your-admin-email@example.com`

11. Replace it with the lowercase email address you will use as the site administrator. Example: `trainer@example.com`.
12. Click **Publish**.

**Important privacy rule:** The real administrator email belongs only in the Firebase Console's deployed Rules. Leave the placeholder in the public GitHub file `firebase/firestore.rules`. Do not put your real administrator email in `docs/firebase-config.js`, a public source file, a ZIP patch, or a GitHub issue.

**When upgrading an existing Firebase project:** GitHub uploads do not publish Firestore Rules automatically. After installing v1.2.0 or a later release that changes `firebase/firestore.rules`, repeat this step: open the latest rules file from your repository, copy it into **Firestore Database → Rules**, replace the placeholder with your real lowercase administrator email, preserve any project-specific rule changes you intentionally made, and tap **Publish**. The v1.2.0 rules add the `accessories` category. Until you publish them, applications selecting Accessories & apparel may be rejected by Firestore. Keep the real administrator email only in the deployed Console rules; never commit it.

## Step 3 — Turn on passwordless email-link sign-in

1. Open `https://console.firebase.google.com/project/PROJECT_ID/authentication/providers` using your Project ID.
2. If you see **Get started**, click it.
3. Open the **Sign-in method** or **Sign-in providers** tab if it is not already selected.
4. Select **Email/Password**.
5. Turn on **Enable**.
6. Also turn on **Email link (passwordless sign-in)** within the Email/Password provider.
7. Save the provider settings.
8. Open `https://console.firebase.google.com/project/PROJECT_ID/authentication/settings`.
9. Find **Authorized domains** and choose **Add domain**.
10. Enter your GitHub Pages hostname only: `OWNER.github.io`.
11. Click **Add** or **Save**. If you use a custom domain, add that hostname as a separate entry too.

Example: if your Pages URL is `https://example-user.github.io/PokeDropWatch/`, the Authorized Domain value is exactly `example-user.github.io`.

The app uses Firebase email-link sign-in to verify mailbox ownership. Users must open the email link to complete an application or unsubscribe request.

## Step 4 — Register the website as a Firebase Web App and copy its config

1. Open `https://console.firebase.google.com/project/PROJECT_ID/settings/general`.
2. Scroll down to **Your apps**.
3. Click the **Web** icon (`</>`) to add a Web app.
4. Enter the app nickname `PokeDrop Watch Website`.
5. Do **not** select or set up Firebase Hosting. The website is hosted by GitHub Pages.
6. Click **Register app**.
7. Firebase will show a `firebaseConfig` object. Keep that page open.
8. In another tab, open this exact file in your GitHub repository: `https://github.com/OWNER/REPOSITORY/edit/main/docs/firebase-config.js`.
9. In the GitHub editor, replace the five placeholder values in the existing object with the matching values from the Firebase `firebaseConfig` object:

   | In `docs/firebase-config.js` | Copy the value named in Firebase |
   |---|---|
   | `apiKey` | `apiKey` |
   | `authDomain` | `authDomain` |
   | `projectId` | `projectId` |
   | `appId` | `appId` |
   | `messagingSenderId` | `messagingSenderId` |

10. Keep the property names and surrounding quotes, and change only the text between the quotes. Do not paste the service-account JSON here.
11. Scroll down and click **Commit changes**. Use the default commit message and commit directly to `main`.

The Firebase Web App config is browser-visible configuration; it is not the service-account private key. Never put the service-account JSON in `docs/` or any public file.

### Step 4B — Allow both Firebase Authentication and GitHub Pages to use the browser API key

This step matters when the Firebase Web API key has **Website / HTTP referrer** restrictions. Firebase's email-link handler opens on the Firebase `firebaseapp.com` domain first, then returns the visitor to GitHub Pages. If the Firebase domain is missing from the key's allowlist, clicking the email can fail with `403 API_KEY_HTTP_REFERRER_BLOCKED` even though Firebase sent the email successfully.

1. Open **[Google Cloud API Credentials for the current PokéDrop Watch Firebase project](https://console.cloud.google.com/apis/credentials?project=project-4868291462124176670)**.
2. Find the browser API key whose value matches the `apiKey` field in `docs/firebase-config.js`. Do not edit the Firebase service-account key; this is the public Web API key.
3. Tap the key name to edit it.
4. Under **Application restrictions**, select **Websites** or **HTTP referrers (web sites)**.
5. In the website restrictions list, add both of these exact patterns:

   ```text
   https://n0nam3-bot.github.io/*
   https://project-4868291462124176670.firebaseapp.com/*
   ```

6. Keep any other valid website patterns your project already needs. Do not remove the existing allowed entries unless you know they are obsolete.
7. Save the API key. Leave the **API restrictions** section unchanged; this fix is specifically for the website/referrer allowlist.
8. Wait a few minutes, return to `https://n0nam3-bot.github.io/PokeDropWatch/admin.html`, request a **new** sign-in link, and open the new email.

If you later move to a different GitHub Pages host or Firebase project, replace the two patterns with the new site host and the new project's `<PROJECT_ID>.firebaseapp.com` host. Keep the `/*` suffix.

**Separate Firebase check:** open **[Firebase Authentication → Settings](https://console.firebase.google.com/project/project-4868291462124176670/authentication/settings)** and confirm `n0nam3-bot.github.io` appears under **Authorized domains**. Enter only the hostname—no `https://`, path, or slash. The Firebase `project-4868291462124176670.firebaseapp.com` domain should remain available for the email action handler.

**Do not treat the Web API key as a password.** Firebase browser configuration is expected to be visible to site visitors. Firestore security rules and Authentication protect subscriber data. Never publish the service-account JSON or Gmail App Password.

## Step 5 — Create the private Firebase service-account key

1. Open `https://console.firebase.google.com/project/PROJECT_ID/settings/serviceaccounts/adminsdk`.
2. Confirm that the selected project is PokéDrop Watch.
3. In the **Firebase Admin SDK** section, click **Generate new private key**.
4. Confirm the prompt and download the `.json` file to your phone or computer.
5. Keep that downloaded file private. Do not upload it to GitHub, a public folder, a ZIP patch, a support post, or this chat.
6. Open the JSON file using a text viewer. Select and copy the **entire contents**, from the first `{` to the final `}`. Do not copy only the `private_key` field.

You will paste the full JSON text into a GitHub Actions secret in Step 7. After saving the secret, you may delete the downloaded JSON file from your device if you do not need a secure backup.

## Step 6 — Create a Gmail App Password for product alerts

The Firebase sign-in/verification links are sent by Firebase Authentication. Separate Pokémon product-alert emails are sent from the Gmail account you configure here.

1. Sign in to the Gmail account you want PokéDrop Watch to send alerts from.
2. Open **[Google Account Security](https://myaccount.google.com/security)**.
3. Under **How you sign in to Google**, enable **2-Step Verification** if it is not already enabled.
4. Open **[Google App Passwords](https://myaccount.google.com/apppasswords)**.
5. If Google asks you to sign in again, do so.
6. Create an App Password named `PokeDrop Watch` (or choose any descriptive name Google permits).
7. Copy the generated 16-character App Password. If Google displays spaces for readability, enter the password without the spaces.
8. Use the Gmail address as `SMTP_USERNAME` and the App Password as `SMTP_APP_PASSWORD` in the next step.

If the App Password page says the setting is unavailable, do not use your normal Gmail password. Some Google account types or security policies do not allow App Passwords. In that case, stop here rather than weakening account security; an alternative email provider integration would need to be added and tested separately.

## Step 7 — Add the exact GitHub Actions secrets and variable

1. Open your repository's **[Actions secrets page](https://github.com/OWNER/REPOSITORY/settings/secrets/actions)** after replacing `OWNER` and `REPOSITORY`.
2. Under **Repository secrets**, click **New repository secret** for each required item below.
3. Enter the exact secret name and value, then click **Add secret**.

Create these three required secrets:

| Exact secret name | Exact value to paste |
|---|---|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | The complete contents of the Firebase service-account JSON file from Step 5. |
| `SMTP_USERNAME` | The full Gmail address from Step 6, for example `pokedrop.alerts@gmail.com`. |
| `SMTP_APP_PASSWORD` | The 16-character Gmail App Password from Step 6, without spaces. |

Optional secrets:

| Secret name | Value / purpose |
|---|---|
| `ALERT_EMAIL` | Your email address if you also want an owner-only copy of each new alert digest. Leave it unset if you do not need a separate owner copy. |
| `SMTP_HOST` | Usually leave unset. The monitor defaults to `smtp.gmail.com`. |
| `SMTP_PORT` | Usually leave unset. The monitor defaults to `587`. |

4. Now open your repository's **[Actions variables page](https://github.com/OWNER/REPOSITORY/settings/variables/actions)**.
5. Under **Repository variables**, click **New repository variable**.
6. Enter the exact name `PUBLIC_SITE_URL`.
7. Set its value to your complete GitHub Pages address, including the final slash. Example: `https://example-user.github.io/PokeDropWatch/`.
8. Click **Add variable**.

`PUBLIC_SITE_URL` is a variable, not a secret. Do not put the Firebase service-account JSON or Gmail App Password into the Variables section.

## Step 8 — Install or replace the scheduled workflow

The workflow file must be located at this exact path:

`.github/workflows/pokedrop-watch.yml`

It must be the supplied `pokedrop-watch.yml` file for this release. It contains the 15-minute scheduled scan, ZIP installation/patch handling, tests, and the Firebase/Gmail environment variables.

**On a phone using GitHub in a browser:**

1. Open the repository's **Code** tab.
2. Open the `.github` folder, then `workflows`, then `pokedrop-watch.yml`.
3. Tap the pencil/Edit button.
4. Replace the entire file contents with the contents of the supplied `pokedrop-watch.yml` download.
5. Commit the change to the `main` branch.

If the file does not exist, use **Add file → Create new file**, enter `.github/workflows/pokedrop-watch.yml` as the filename (including all folders), paste the supplied workflow contents, and commit to `main`.

Direct edit link: `https://github.com/OWNER/REPOSITORY/edit/main/.github/workflows/pokedrop-watch.yml`.

**Do not put this workflow inside an ordinary application patch ZIP.** The patch installer deliberately blocks changes to `.github/workflows/`; this file is edited directly in GitHub.

## Step 9 — Tell GitHub Pages to publish the website folder

1. Open your repository's **[GitHub Pages settings](https://github.com/OWNER/REPOSITORY/settings/pages)**.
2. Find **Build and deployment**.
3. For **Source**, select **Deploy from a branch**.
4. For **Branch**, select `main`.
5. For the folder, select `/docs` (not `/root`).
6. Click **Save**.
7. Wait for GitHub Pages to finish deploying. Open the URL displayed on the Pages settings page.

The website starts at `docs/index.html`. The public address will be `https://OWNER.github.io/REPOSITORY/` for a normal project repository. The administrator page is the same address followed by `admin.html`.

The repository's **Code** tab will continue to show `README.md`. That is normal; visitors must open the Pages URL, not the GitHub repository Code tab.

## Step 10 — Sign in as the site administrator

1. Open the public website's `/admin.html` page. Example: `https://example-user.github.io/PokeDropWatch/admin.html`.
2. Enter the exact lowercase administrator email address you put into the deployed Firestore Rules in Step 2.
3. Tap **Email secure sign-in link**.
4. Open the email and tap the Firebase sign-in link. Open it in the same browser where you requested it so the saved email can be matched.
5. Return to the admin page if the link does not automatically return you there.
6. The page should show **Subscriber overview**. If it says the account is not authorized, check the administrator email in the deployed Firestore Rules and republish those rules.

The real administrator email is not stored in public JavaScript. Firestore's deployed security rules decide which verified email can administer subscriber records.

## Step 11 — Run the first scan and test a subscription

1. Open your repository's **[PokéDrop Watch Actions page](https://github.com/OWNER/REPOSITORY/actions/workflows/pokedrop-watch.yml)**.
2. Select the **PokeDrop Watch** workflow.
3. Tap **Run workflow**, keep branch `main`, and tap **Run workflow** again to confirm.
4. Open the new run and wait for the steps to finish. A green check means the workflow completed; open any step to inspect its log.
5. Open the public Pages website and submit a test subscription using an email address you can access. Choose at least one category and one retailer (or leave **All retailers** selected).
6. Open the Firebase email link from that mailbox. The site should report that the application is pending approval.
7. Open `/admin.html`, sign in as administrator, find the pending test address, and tap **Approve**.
8. Run the workflow manually again. The next newly detected matching event can be emailed to that approved subscriber.
9. Test unsubscribe from the public page: enter the subscriber's email, request the link, open the link, then press **Confirm unsubscribe**. The admin list should show `unsubscribed`.

**Important first-scan behavior:** The first successful retailer scan establishes a baseline. It does not send an alert for every item already on the page. Alerts are generated for changes detected by later scans. Approving a subscriber does not send historical alerts.

## If something does not work

| What you see | Check this exact setting |
|---|---|
| `Firebase is not configured` | Check that all five values in `docs/firebase-config.js` were replaced and committed. Reload the Pages website after deployment. |
| `403 API_KEY_HTTP_REFERRER_BLOCKED` when opening a Firebase email link | Google Cloud → APIs & Services → Credentials → edit the Firebase browser API key → Application restrictions → Websites. Allow both `https://n0nam3-bot.github.io/*` and `https://project-4868291462124176670.firebaseapp.com/*`. Save, wait a few minutes, and request a new sign-in link. |
| `auth/unauthorized-continue-uri` or an unauthorized domain message | Firebase Console → Authentication → Settings → Authorized domains. Add `n0nam3-bot.github.io` as the hostname only. |
| `auth/operation-not-allowed` | Firebase Console → Authentication → Sign-in method/providers → Email/Password. Enable both Email/Password and Email link (passwordless sign-in), then save. |
| Admin page says account is not authorized | Firestore Database → Rules. Confirm the real, lowercase admin email is in the deployed rule and click Publish again. Do not add it to public JavaScript. |
| `Missing or insufficient permissions` on the admin page | Check that the signed-in email exactly matches the email in the deployed Firestore Rules and that its email link sign-in was completed. |
| GitHub Actions says Firebase service account is missing/unavailable | Repository Settings → Secrets and variables → Actions. Confirm `FIREBASE_SERVICE_ACCOUNT_JSON` exists and contains the entire JSON file, not just one field. |
| Product-alert email fails | Confirm `SMTP_USERNAME` is the Gmail address, `SMTP_APP_PASSWORD` is the App Password (not the normal password), and 2-Step Verification is enabled. Open the Actions log for the monitor step. |
| The page shows the README instead of the Pokémon site | Repository Settings → Pages. Set Source to Deploy from a branch, branch `main`, folder `/docs`, then Save. Open the Pages URL shown there. |
| No product email arrives after the first scan | The first scan is only a baseline. Also confirm the subscriber is `active`, its categories/retailers match the event, and the Gmail secrets are present. |

## Exact links at a glance

Replace `OWNER`, `REPOSITORY`, and `PROJECT_ID` with your values before opening links that contain them.

| What you need | Direct link |
|---|---|
| Firebase Console | https://console.firebase.google.com/ |
| Firestore database | https://console.firebase.google.com/project/PROJECT_ID/firestore |
| Firebase Authentication providers | https://console.firebase.google.com/project/PROJECT_ID/authentication/providers |
| Firebase Authentication authorized domains | https://console.firebase.google.com/project/project-4868291462124176670/authentication/settings |
| Google Cloud API credentials / referrer restrictions | https://console.cloud.google.com/apis/credentials?project=project-4868291462124176670 |
| Firebase Web App config / Project settings | https://console.firebase.google.com/project/PROJECT_ID/settings/general |
| Firebase service-account key | https://console.firebase.google.com/project/PROJECT_ID/settings/serviceaccounts/adminsdk |
| Google Account security | https://myaccount.google.com/security |
| Gmail App Passwords | https://myaccount.google.com/apppasswords |
| GitHub Actions secrets | https://github.com/OWNER/REPOSITORY/settings/secrets/actions |
| GitHub Actions variables | https://github.com/OWNER/REPOSITORY/settings/variables/actions |
| GitHub Pages settings | https://github.com/OWNER/REPOSITORY/settings/pages |
| GitHub Actions workflow runs | https://github.com/OWNER/REPOSITORY/actions/workflows/pokedrop-watch.yml |
| Edit the public Firebase config file | https://github.com/OWNER/REPOSITORY/edit/main/docs/firebase-config.js |
| Copy the Firestore rules source | https://raw.githubusercontent.com/OWNER/REPOSITORY/main/firebase/firestore.rules |
| Edit the scheduled workflow | https://github.com/OWNER/REPOSITORY/edit/main/.github/workflows/pokedrop-watch.yml |

---

## Security reminders

- Never commit the Firebase service-account JSON, Gmail App Password, or other private credential.
- The Firebase browser config is public; the service-account JSON is private.
- Keep the real administrator email only in the deployed Firebase Rules editor. Keep the placeholder in the public repository file.
- Do not switch Firestore to test mode.
- Do not give GitHub Actions secrets to a third party or paste them into an issue.
- Start with a small number of approved subscribers. Gmail, Firebase, and GitHub each enforce quotas and abuse limits.


#### Notification categories (v1.2.0)

The subscription form supports Pokémon TCG, plush, collectibles, games, accessories/apparel, and Pokémon news. The Firestore security rules must permit the values `tcg`, `plush`, `collectibles`, `games`, `accessories`, and `news`. The v1.2.0 release includes the updated rules template.
