# PokéDrop Watch

PokéDrop Watch is a minimal Pokémon-themed product drop and restock tracker. GitHub Pages serves the public website, GitHub Actions scans configured retailers and news feeds, Firestore stores subscriber records, and approved subscribers receive individual email alerts.

## What it does

- Shows retailer/source health, recent drops, restocks, price changes, Pokémon news, and all tracked products.
- Displays product photos, prices, retailer names, categories, and direct product links when the source exposes them.
- Filters products by item type, retailer, and exact or partial title.
- Lets visitors apply for notifications by category and retailer.
- Verifies mailbox ownership with a six-digit code sent from `pokedropwatch.notify@gmail.com`; the visitor enters the code on the same page where it was requested.
- Holds new applications for administrator approval.
- Lets verified subscribers update preferences or unsubscribe using a fresh email code.
- Provides a private administrator portal to approve, reject, suspend, reactivate, and remove subscriber records.
- Uses deterministic HTML/RSS parsing. It does not use AI-generated picks or paid product-data APIs.

## Hosting and services

| Component | Service | Purpose |
|---|---|---|
| Public website | GitHub Pages (`main` → `/docs`) | Serves the responsive website on PC and mobile. |
| Scheduled monitor | GitHub Actions | Scans sources approximately every 15 minutes. |
| Subscriber database | Firebase Firestore | Stores application status, email, preferences, and private delivery retries. |
| Administrator login | Firebase Authentication Email/Password | Password login with no email-link sent on every sign-in. |
| Email verification | Google Apps Script + Gmail MailApp | Sends branded six-digit codes from the notification Gmail account. |
| Product alerts | Gmail SMTP | Sends individual alert emails to approved subscribers. |

**No Google Sheet, Vercel, Firebase Hosting, Cloud Functions, or paid server is required.** Firestore remains the database. The Apps Script project is only the email-code backend and writes directly to Firestore using a private service-account credential.

Free services have quotas. The app caps verification messages at 25 per UTC day, three per email address per hour, and a 60-second resend cooldown. Google's Gmail and Apps Script quotas also apply; this is suitable for a small community, not unlimited bulk email.

## Required setup

Follow the exact, mobile-friendly [Owner Setup Guide](docs/FIREBASE_SETUP.html) or the [Markdown checklist](docs/FIREBASE_SETUP.md). It includes direct Firebase, Apps Script, Google Account, and GitHub links. In summary, the owner must:

1. Publish the private Firestore rules with the administrator email entered only in the Firebase Console Rules editor.
2. Enable Firebase Email/Password authentication and create the administrator account manually in Firebase Authentication.
3. Copy the Firebase Web App values into `docs/firebase-config.js`.
4. Create a Firebase service-account JSON key and keep it private.
5. Create a standalone Apps Script project while signed in as `pokedropwatch.notify@gmail.com`, paste `backend/apps-script/Code.gs` and `backend/apps-script/Index.html`, and set the exact Script Properties shown in the setup guide.
6. Deploy Apps Script as a web app that executes as the owner and is available to anyone; put its `/exec` URL in `docs/subscription-backend-config.js`.
7. Add `FIREBASE_SERVICE_ACCOUNT_JSON`, `SMTP_USERNAME`, `SMTP_APP_PASSWORD`, and optional `ALERT_EMAIL` as GitHub Actions secrets.
8. Publish GitHub Pages from branch `main`, folder `/docs`.

Never commit the Firebase service-account JSON, Apps Script HMAC secret, or Gmail App Password. `docs/firebase-config.js` and the Apps Script `/exec` URL are public browser configuration; private keys are not.

## Email behavior

Administrator login uses a password and does not send email. Visitor verification uses a six-digit code sent from **PokéDrop Watch <pokedropwatch.notify@gmail.com>** and entered on the requesting page. Codes expire after 10 minutes, work once, allow five attempts, and a newer code invalidates the previous one. Product-alert messages also display the sender name **PokéDrop Watch**.

## Monitoring and source coverage

The schedule is set by the cron expression in `.github/workflows/pokedrop-watch.yml` (currently every 15 minutes; GitHub may delay scheduled runs). `config/sources.json` contains the source list and parsing settings.

A source counts as `MATCHES` only when the monitor recognizes usable Pokémon entries. `NO MATCH` means the page responded but the parser did not recognize usable listings; it does not mean the store has no stock. `ISSUE` means the request failed. Retailer websites can block automated requests, require JavaScript, vary by location, or change their markup. A configured source is not a guarantee of coverage. Confirm final price and availability with the retailer before purchasing.

For current retailer gaps and scan diagnostics, see [Source Health](docs/SOURCE_HEALTH.md). The reported two-of-eight match rate is a known development gap; dedicated retailer adapters and live integration tests remain necessary.

## ZIP updates

Ordinary application updates are supplied as small ZIP patches. Upload the patch ZIP to the repository's `updates/` folder and commit it. The existing GitHub Actions workflow applies files to their repository-relative folders, commits them, and removes the uploaded ZIP after successful installation. Workflow-file changes are a one-time direct edit under `.github/workflows/`; ordinary patches intentionally cannot replace that workflow.

For future customization, testing, and release rules, see [Configuration & Change Guide](docs/CONFIGURATION_AND_CHANGE_GUIDE.md), [Roadmap](docs/ROADMAP.md), and [Changelog](docs/CHANGELOG.md).

PokéDrop Watch is an unofficial fan project and is not affiliated with Nintendo, The Pokémon Company, Pokémon Center, or any listed retailer.
