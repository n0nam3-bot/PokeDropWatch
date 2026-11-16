# PokéDrop Watch

A free, Pokémon-themed product/restock monitor with a mobile-friendly dashboard, scheduled GitHub Actions scans, optional email alerts, and ZIP-based updates. It uses conventional page/RSS parsing; it does not use AI or a paid API.

## IMPORTANT: corrected ZIP installer

The earlier workflow only reacted to a file named exactly `install.zip`, even though the downloads were named `PokeDropWatch_Install.zip` and `PokeDropWatch_Starter_Bundle.zip`. This corrected workflow accepts ZIP files with any filename in the repository root. It can also open the original starter bundle and extract the nested application ZIP.

## One-time setup (can be done from a phone)

### 1. Add the permanent workflow

1. Open your GitHub repository in a browser.
2. Tap **Add file → Create new file**.
3. In the filename field, enter exactly `.github/workflows/pokedrop-watch.yml`.
4. Open the separately supplied `pokedrop-watch.yml`, copy all of its contents, and paste them into the GitHub editor.
5. Commit the new file to the `main` branch.

This is the only file that must be placed manually. GitHub must have this workflow before it can unzip anything uploaded later.

### 2. Upload the application ZIP

Upload either of these to the **repository root** (not inside a folder):

- `PokeDropWatch_Install_FIXED.zip`
- `PokeDropWatch_Starter_Bundle_FIXED.zip`

The corrected workflow also recognizes the earlier names `PokeDropWatch_Install.zip`, `PokeDropWatch_Starter_Bundle.zip`, and `install.zip`. It extracts the application to its repository-relative folders (`docs/`, `monitor/`, `config/`, `scripts/`, and `tests/`), removes the uploaded ZIP after successful installation, and commits the extracted files.

If you already uploaded one of the earlier ZIPs before fixing the workflow, you do not need to upload it again. When you commit the corrected workflow, it also triggers a run and inspects ZIPs already present in the repository root. You can also start it manually from **Actions → PokeDrop Watch → Run workflow**.

### 3. Allow the workflow to save extracted files

In GitHub, open **Settings → Actions → General → Workflow permissions** and select **Read and write permissions**, then save. The workflow needs this permission to commit extracted files and updated scan status.

Also make sure Actions are enabled for the repository.

### 4. Publish the dashboard

Open **Settings → Pages**. Under **Build and deployment**, choose **Deploy from a branch**, select `main`, choose `/docs`, and save. The Pages URL appears on that screen after deployment.

### 5. Enable optional email notifications

Email delivery uses Gmail SMTP and a Google App Password.

1. Enable Google 2-Step Verification and create an App Password.
2. In the repository, open **Settings → Secrets and variables → Actions** and add these repository secrets:
   - `SMTP_USERNAME` — the Gmail address used to send alerts.
   - `SMTP_APP_PASSWORD` — the 16-character Google App Password (without spaces).
   - `ALERT_EMAIL` — the address that should receive alerts.
   - `SMTP_HOST` — `smtp.gmail.com`.
   - `SMTP_PORT` — `587`.
3. Never put the App Password in a file or commit it to GitHub.

Without these secrets, the monitor still scans and updates the dashboard, but email cannot be sent.

## How it works

- GitHub Actions attempts a scan every 15 minutes. GitHub can delay scheduled runs during busy periods.
- The first successful scan establishes a baseline rather than emailing every old listing.
- Later runs detect changes in listing presence, published price, stock/preorder state, and monitored Pokémon news RSS items.
- A notification includes the title, retailer/source, published price when available, stock state, previous price when detected, detection time, and direct link.
- The dashboard is static and does not require a server, database, paid API, or AI service.

## ZIP updates after installation

For later code updates, upload a ZIP to either the repository root or the `updates/` folder. The ZIP should contain repository-relative paths, for example:

- `docs/app.js`
- `docs/styles.css`
- `monitor/engine.py`
- `config/sources.json`

The patch installer also strips one extra wrapper folder automatically. For example, `MyUpdate/docs/app.js` is installed as `docs/app.js`. The workflow validates ZIP paths, rejects path traversal and symlinks, and does not allow a patch ZIP to overwrite `.github/workflows/`. It then commits the changed files and removes the uploaded ZIP.

## Coverage limitations

There is no single public inventory feed for every Pokémon release or retailer. Stores may block automated requests, render inventory only in JavaScript, personalize stock by location, or change their page markup. The source list is in `config/sources.json`; the dashboard reports individual scan failures. An unpublished price is shown as unavailable rather than guessed. Always confirm price and stock with the retailer before purchasing.

The current starting sources include Pokémon Center, Target, Walmart, Best Buy, GameStop, Amazon, and PokéBeach RSS. Category/search pages can be less reliable than exact product URLs.

## Local tests

```bash
python -m pip install -r monitor/requirements.txt
python -m unittest discover -s tests -v
```

PokéDrop Watch is an unofficial fan-made tracker. Pokémon and retailer names belong to their respective owners.
