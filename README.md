# PokéDrop Watch

PokéDrop Watch is a free, Pokémon-themed drop and restock monitor. It runs scheduled checks through GitHub Actions, publishes a mobile-friendly dashboard with GitHub Pages, and can email a digest when monitored products or news feeds change. It uses normal HTML/structured-data and RSS parsing; it does not use AI services, paid APIs, or a separate hosting account.

## What it does

- Checks the configured Pokémon product/catalog pages and RSS feeds on the schedule in `.github/workflows/pokedrop-watch.yml` (currently every 15 minutes; GitHub may delay scheduled runs).
- Detects new product listings after the first scan establishes a baseline.
- Detects an availability change from out of stock to in stock or preorder, when the source exposes that information.
- Detects listed price drops and other price changes when both the previous and current prices are available.
- Tracks new entries in configured Pokémon news RSS feeds. News alerts are announcements, not proof of product availability.
- Publishes scan time, source health, listing counts, and recent alerts to the dashboard in `docs/`.
- Provides a responsive dashboard with search, alert filters, and installable-PWA support on compatible mobile browsers.
- Can send an HTML email digest with the item title, retailer/source, listed price, availability, previous price when available, detection time, and a direct link.
- Supports ZIP-based application patches so later updates can replace only the files included in the patch.

## What needs to be configured

### 1. GitHub Actions

The repository must have GitHub Actions enabled. Under **Settings → Actions → General → Workflow permissions**, allow **Read and write permissions** so the workflow can save scan state, install ZIP updates, and commit changed files.

The permanent workflow is `.github/workflows/pokedrop-watch.yml`. Its current schedule is `*/15 * * * *`. Change the workflow's `schedule` cron expression to change the interval; the `check_interval_minutes` value in `config/sources.json` is descriptive and does not control GitHub's schedule.

### 2. GitHub Pages

Under **Settings → Pages**, publish from the `main` branch and the `/docs` folder. The dashboard reads the public status file at `docs/data/state.json`, which the monitor updates after each scan.

### 3. Email alerts (optional)

Email is disabled until the following repository **Actions secrets** are configured:

| Secret | Value |
|---|---|
| `SMTP_USERNAME` | Gmail address used to send the alerts |
| `SMTP_APP_PASSWORD` | Google App Password for that Gmail account (not the normal account password) |
| `ALERT_EMAIL` | Destination email address for notifications |

`SMTP_HOST` and `SMTP_PORT` are optional. They default to `smtp.gmail.com` and `587`. The sender and recipient can be the same address. Never put credentials in `config/sources.json` or commit them to the repository.

Without the three required secrets, product/news scans and the dashboard still run; email delivery does not.

### 4. Sources and scan behavior

Edit `config/sources.json` to enable or disable sources or add a source URL. Each source needs a unique `id`, a display `name`, a `retailer`, a `type`, a `url`, and an `enabled` value. Supported source types are:

- `catalog` — a retailer listing/search page. The scanner looks for product structured data and product links in the returned HTML.
- `product` — one specific product-detail URL.
- `rss` — an RSS/Atom feed used for Pokémon news or announcements.

The starting watchlist includes Pokémon Center TCG and plush listings, Target, Walmart, Best Buy, GameStop, Amazon Pokémon TCG search results, and the PokéBeach news feed. Sources can be changed to suit the products and stores being followed.

The first successful scan records the current listings as a baseline; it does not send a wave of alerts for every item already listed. Later scans compare results with the saved state. Product prices and availability are only reported when the public page exposes them.

## Important coverage notes

There is no universal public inventory feed for every Pokémon product or retailer. Some stores block automated requests, render listings with JavaScript, personalize stock by location, or change their page structure. A failed source is shown as an error instead of being counted as a successful scan. The dashboard and email are a monitoring aid, not a guarantee of complete coverage or a reservation; confirm final price and availability with the retailer before purchasing.

PokéDrop Watch is an unofficial fan project and is not affiliated with Nintendo, The Pokémon Company, Pokémon Center, or the listed retailers.
