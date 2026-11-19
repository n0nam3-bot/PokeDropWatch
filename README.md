# PokéDrop Watch

A fan-made Pokémon product discovery and restock monitor. The public site shows products and scan health; GitHub Actions checks configured retailer pages on a schedule; verified subscribers can apply for email alerts; and an administrator approves subscribers before delivery starts.

**Public website:** https://n0nam3-bot.github.io/PokeDropWatch/  
**Administrator:** https://n0nam3-bot.github.io/PokeDropWatch/admin.html  
**Repository:** https://github.com/n0nam3-bot/PokeDropWatch

## What it does

- The GitHub Actions monitor is configured for 15-minute scheduled starts. Actual start times can vary; ZIP uploads and manual runs also trigger scans.
- Uses broad Pokémon Center New Releases and Back in Stock routes, a broad GameStop search sorted newest first, and broad searches for Target, Walmart, and Amazon. Product categories are inferred from listings.
- Keeps Best Buy limited to Pokémon TCG because it does not expose a unified Pokémon catalog route.
- Shows recent Pokémon news inside the existing Latest alerts feed through the News activity filter or Item type = News.
- Offers search, exact-title, item-category, retailer and alert-type filters. The Products Tracked metric counts saved catalog records and may include last-known listings when a retailer cannot be reached.
- Sends email notifications for verified stock transitions, price drops/changes and newly published Pokémon news to approved subscribers.
- Provides a private administrator portal to approve, reject, suspend and remove subscriber records.

## Services and configuration required

| Service | Why it is used | Owner configuration |
|---|---|---|
| GitHub Pages | Hosts the public website | Publish branch `main`, folder `/docs` |
| GitHub Actions | Scheduled scans and product-alert email | Install `.github/workflows/pokedrop-watch.yml` once; configure repository secrets/variables |
| Firebase Firestore | Private subscriber database | Create Firestore Native database and service-account access |
| Google Apps Script | Verification codes and private administrator API | Deploy web app as `pokedropwatch.notify@gmail.com`, then set its `/exec` URL in `docs/subscription-backend-config.js` |
| Gmail | Verification and product notification sender | Configure Apps Script and Gmail App Password for SMTP alerts |

The current admin login is handled by the Apps Script backend, not Firebase Authentication. No Firebase email-link sign-in or password-reset action link is used. No Google Sheet is required. Free service quotas apply; email and monitoring are not unlimited.

## Owner setup

Follow [`owner-docs/SETUP.md`](owner-docs/SETUP.md) for exact links, menu paths, property names, secrets, and step-by-step setup. The detailed owner instructions live outside `/docs`, so they are not part of the public GitHub Pages site.

## Monitoring status

The dashboard keeps the existing source-status layout. Every configured source entry is checked during each 15-minute scan; retailer searches are not rotated between scans.

## Development

- Source configuration: `config/sources.json`
- Monitor: `monitor/engine.py`, `monitor/engine_recovery_patch.py`, `monitor/baseline_patch.py`, `monitor/news_source_patch.py`, `monitor/run.py`
- Public website: `docs/index.html`, `docs/styles.css`, `docs/app.js`
- Subscriber/admin bridge: `backend/apps-script/`
- Firestore client rules: `firebase/firestore.rules`
- Roadmap: `docs/ROADMAP.md`
- Changelog: `docs/CHANGELOG.md`
- Change/configuration reference: `docs/CONFIGURATION_AND_CHANGE_GUIDE.md`

Run tests with `python -m unittest discover -s tests -v`.

PokéDrop Watch is a fan-made tracker and is not affiliated with Nintendo, The Pokémon Company, Pokémon Center, or any retailer.
