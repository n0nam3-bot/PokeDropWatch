# PokéDrop Watch

PokéDrop Watch is a Pokémon-themed product drop and restock tracker. The public website is a responsive GitHub Pages site; GitHub Actions runs the monitor on a schedule. It checks configured retailer pages and Pokémon news feeds, records changes, and emails approved subscribers when their selected categories and retailers match a new alert.

## What the website does

- Displays monitor status, source health, recent Pokémon product/news alerts, listed prices, and links to the retailer pages.
- Lets visitors apply for email alerts after verifying control of their email address.
- Holds applications for administrator approval before any product alerts are sent.
- Lets subscribers choose product categories and retailers, update their preferences, and unsubscribe through a fresh email sign-in link plus a separate confirmation.
- Provides a private administrator page to approve, reject, suspend, reactivate, and remove subscriber records.
- Keeps subscriber emails in private Firebase Firestore records. Email addresses are never placed in the public dashboard status file or exposed to other subscribers.
- Uses a deterministic HTML/RSS monitor. It does not use AI-generated recommendations or paid product-data APIs.

## Hosting and services

| Component | Service | Purpose |
|---|---|---|
| Public website | GitHub Pages | Serves the files in `docs/`. |
| Scheduled monitor | GitHub Actions | Scans sources, runs tests, and publishes dashboard status. |
| Subscriber database | Firebase Firestore | Stores applications, preferences, statuses, and private delivery retries. |
| Email verification | Firebase Authentication | Sends passwordless email sign-in links to prove mailbox ownership. |
| Product alert email | Gmail SMTP | Sends each approved subscriber an individual alert email. |

The intended setup uses free tiers and does not require Vercel, Google Sheets, a paid server, or Firebase Cloud Functions. Free-tier quotas and provider terms apply; this is designed for a small, low-volume community, not unlimited bulk email.

## Required configuration

Follow [docs/FIREBASE_SETUP.md](docs/FIREBASE_SETUP.md) for the complete first-time setup. In summary, the site owner must:

1. Create a Firebase project on the no-cost Spark plan, create Firestore, enable Firebase Authentication email-link sign-in, and add the GitHub Pages hostname as an authorized domain.
2. Paste the Firebase web-app values into `docs/firebase-config.js`.
3. In the Firebase Console only, replace the administrator-email placeholder in `firebase/firestore.rules` with your lowercase admin email and publish the rules. Do not commit your real admin email into the public repository.
4. Add GitHub Actions secrets `FIREBASE_SERVICE_ACCOUNT_JSON`, `SMTP_USERNAME`, and `SMTP_APP_PASSWORD`. `ALERT_EMAIL` is optional and sends an additional owner-only copy.
5. Add the GitHub Actions variable `PUBLIC_SITE_URL` with the exact GitHub Pages URL.
6. Replace `.github/workflows/pokedrop-watch.yml` with the workflow file supplied with this release so the monitor can access the private Firestore service account.
7. Set GitHub Pages to branch `main`, folder `/docs`.

Never commit a Firebase service-account JSON file, Gmail App Password, or other private key. The Firebase web-app configuration in `docs/firebase-config.js` is public browser configuration; the service-account key is not.

## Monitoring and source coverage

The monitor schedule is controlled by the `schedule` cron expression in `.github/workflows/pokedrop-watch.yml` (currently every 15 minutes; GitHub may delay scheduled runs). The `check_interval_minutes` value in `config/sources.json` is descriptive and does not control GitHub's schedule.

The watchlist is configured in `config/sources.json`. Supported source types are `catalog`, `product`, and `rss`. The first successful scan establishes a baseline; subsequent scans can detect newly listed products, out-of-stock to in-stock/preorder changes, listed price changes, and new news-feed entries. Each source is checked independently so a blocked retailer does not stop other scans.

Retailer websites may block automated requests, render inventory through JavaScript, vary stock by location, or change their page structure. A configured URL is not a guarantee that every product or restock will be detected. The dashboard reports failed sources instead of claiming complete coverage. Confirm final stock and price with the retailer before purchasing.

## ZIP updates

After the initial workflow and app are installed, ordinary application/documentation changes are delivered as ZIP patches. Upload a patch ZIP into the repository's `updates/` folder. GitHub Actions applies the repository-relative paths, commits the changes, and removes the uploaded ZIP after successful installation. The workflow file is a protected one-time setup file and is updated directly in GitHub.

For source customization, tests, release rules, and future change requests, see [docs/CONFIGURATION_AND_CHANGE_GUIDE.md](docs/CONFIGURATION_AND_CHANGE_GUIDE.md).

PokéDrop Watch is an unofficial fan project and is not affiliated with Nintendo, The Pokémon Company, Pokémon Center, or any listed retailer.
