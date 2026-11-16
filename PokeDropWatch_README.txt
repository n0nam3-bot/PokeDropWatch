# PokéDrop Watch

A free, phone-friendly Pokémon product drop and restock monitor. It combines:

- A minimal Pokémon-themed dashboard hosted on GitHub Pages.
- A scheduled GitHub Actions scan every 15 minutes.
- Public retailer listing checks for Pokémon Center, Target, Walmart, Best Buy, GameStop and Amazon.
- A PokéBeach Pokémon TCG news RSS feed for product announcements and related news.
- Email digests with the item/article, retailer or source, listed price when exposed by the page, availability state, previous price when detected, and a direct link.
- A ZIP patch installer. After the one-time setup, future updates are uploaded as a ZIP to `updates/`; Actions places each file at its repository-relative path and commits the changes.

No AI, paid API, database, web host, or always-on computer is used. The monitor runs on GitHub Actions and the dashboard is static HTML/CSS/JavaScript.

## Important coverage note

There is no universal public inventory feed for every Pokémon item or retailer. Some stores block automated requests, require JavaScript, personalize inventory by ZIP code, or expose stock only after a product is selected. PokéDrop Watch monitors the public pages and feed listed in `config/sources.json`; it cannot guarantee every drop, private restock, local-store quantity, or instant notification. The dashboard marks a source as an issue when a scan fails. An item without published structured price data will be emailed as **price not published on the monitored page**, not with a guessed price.

The included retailer search pages are starting sources and their page structures can change. Check the Watchlist sources section after the first scan. A page that consistently shows an issue should be disabled or replaced in `config/sources.json` with a working product/category URL. Do not increase scan frequency to evade retailer limits.

## One-time setup (designed for mobile)

You will need a free GitHub account and a Gmail account for free email delivery. The site can still run without email secrets; alerts will appear on the dashboard and pending email digests will remain queued.

### 1. Create the repository

1. On GitHub, create a new **public** repository (for example, `pokedrop-watch`). Public repositories get free GitHub Actions usage for this kind of public project.
2. Open the repository's **Add file → Create new file** screen.
3. In the filename field enter exactly: `.github/workflows/pokedrop-watch.yml`.
4. Open the separately supplied `BOOTSTRAP_WORKFLOW.yml`, copy its complete contents, and paste them into that new GitHub file. Commit the new file to the `main` branch.
5. Download the supplied `install.zip` and upload it to the repository root (not inside a folder). Keep the filename exactly `install.zip` and commit it. The workflow unpacks it into the correct folders, removes the ZIP, installs the monitor and creates the `updates/` folder.

The bootstrap workflow is the single permanent workflow. It handles initial installation, scheduled checks, and future ZIP patches. The main package ZIP deliberately does not try to overwrite workflow permissions through `GITHUB_TOKEN`.

### 2. Turn on the dashboard

1. In the repository, open **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch **main** and folder **/docs**, then save.
4. Wait for the Pages address to appear in Settings → Pages. It will look like `https://YOUR-USERNAME.github.io/pokedrop-watch/`.

### 3. Turn on email alerts (free Gmail route)

1. In your Google Account, enable **2-Step Verification**.
2. Create an **App Password** in Google Account → Security → App passwords. Name it `PokéDrop Watch`.
3. In GitHub open **Settings → Secrets and variables → Actions → New repository secret** and add:
   - `SMTP_USERNAME` — your full Gmail address.
   - `SMTP_APP_PASSWORD` — the 16-character Google App Password (paste without spaces).
   - `ALERT_EMAIL` — the email address that should receive alerts. It can be the same Gmail address.
   - Optional: `SMTP_HOST` = `smtp.gmail.com`; `SMTP_PORT` = `587`.
4. Never put the app password in a file or in the repository. Store it only as a GitHub Actions secret.

### 4. Run the first scan

Open the repository's **Actions** tab → **PokéDrop Watch** → **Run workflow**. The first scan records a baseline instead of emailing every old listing already on each page. Future new listings, detected restocks, price changes, and new RSS articles trigger a digest. Scheduled checks run about every 15 minutes; GitHub may delay scheduled workflows during busy periods.

## Updating the project with ZIP patches (no full re-upload)

After the one-time setup, do not replace the repository files manually for ordinary code updates:

1. Make a ZIP whose entries use paths relative to the repository root. Example ZIP entries: `docs/app.js`, `docs/styles.css`, `monitor/engine.py`, `config/sources.json`.
2. Do **not** put an extra project folder around those files. Do not include `.git/`, `updates/`, or `.github/workflows/` in a patch ZIP.
3. In GitHub open the `updates/` folder, choose **Add file → Upload files**, select the ZIP, and commit it.
4. The **PokéDrop Watch** workflow safely extracts the ZIP, commits the changed files to their correct locations, removes the uploaded ZIP, and runs a scan. GitHub Pages republishes the dashboard when files in `docs/` change.

The patch installer rejects path traversal, symlinks, oversized archives, and workflow-file changes. This prevents a ZIP from writing outside the repository. To change the permanent workflow, edit `.github/workflows/pokedrop-watch.yml` directly in GitHub.

## Adding more stores or exact products

Edit `config/sources.json` in GitHub. A category/search page can be added as a `catalog` source, and a direct product page can be added as a `product` source. For a product, copy its public product URL and add an entry like:

```json
{
  "id": "my-store-pokemon-etb",
  "name": "My Store · Pokémon ETB",
  "retailer": "My Store",
  "type": "product",
  "url": "https://example.com/product/pokemon-etb",
  "enabled": true,
  "notes": "Specific product page"
}
```

Keep IDs unique. The monitor prefers Schema.org product/offer data, then common public metadata and stock wording. Exact product pages generally provide more useful price and stock results than generic search pages. Never add private account URLs or credentials.

## How alerts work

- **New drop:** a new product listing appears on a watched catalog page.
- **Restock:** a product previously reported out of stock changes to in stock or preorder.
- **Price drop / update:** a previously published price changes.
- **Pokémon news:** a new entry appears in the monitored RSS feed.

The first scan establishes a baseline to avoid a flood of historical alerts. Stock signals and prices are only as accurate as the public retailer page at scan time. Confirm on the retailer site before purchase.

## Local checks

The monitor is plain Python. To run tests locally:

```bash
python -m pip install -r monitor/requirements.txt
python -m unittest discover -s tests -v
python monitor/run.py
```

`monitor/run.py` can also run without mail secrets; it still updates `docs/data/state.json` for the dashboard.

## Privacy and project status

The dashboard is public and does not accept or store personal information. Email credentials are read only from GitHub Actions secrets. The public dashboard shows source status and alert history, not the email address or SMTP credentials.

PokéDrop Watch is an unofficial fan-made tracker. Pokémon, Pokémon Center, retailer, and product names belong to their respective owners. Use retailer websites directly for purchases and follow their terms of service.
