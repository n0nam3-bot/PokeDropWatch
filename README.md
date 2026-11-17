# PokéDrop Watch

A fan-made Pokémon product discovery and restock monitor. The public site shows products and scan health; GitHub Actions checks configured retailer pages on a schedule; verified subscribers can apply for email alerts; and an administrator approves subscribers before delivery starts.

**Public website:** https://n0nam3-bot.github.io/PokeDropWatch/  
**Administrator:** https://n0nam3-bot.github.io/PokeDropWatch/admin.html  
**Repository:** https://github.com/n0nam3-bot/PokeDropWatch

## What it does

- Monitors configured retailer catalog/search pages and Pokémon news feeds. Retailer entries can include up to three alternate public search URLs, which are merged and deduplicated in the same source scan.
- Tracks product title, retailer, price, image, availability and observed changes when those fields are exposed by the source.
- Distinguishes **First seen** from a verified restock or price change. A marketplace listing’s first discovery time is never treated as its release date or seller listing date. A listing first discovered by the monitor is not automatically a newly released product.
- Offers search, exact-title, item-category, retailer and alert-type filters.
- Sends individual email notifications for verified stock transitions, price drops/changes and Pokémon news to approved subscribers.
- Provides an administrator portal to approve, reject, suspend and remove subscriber records.

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

A source marked **MATCHES** has yielded product/feed records that the parser recognized. **NO MATCH** means the page responded but no supported product records were parsed; it does not mean the retailer has no stock. **ISSUE** means all configured URLs failed. Some retailers block automated requests or require client-side JavaScript; source coverage must be measured from current scans rather than claimed in advance.

## Development

- Source configuration: `config/sources.json`
- Monitor: `monitor/engine.py`, `monitor/run.py`
- Public website: `docs/index.html`, `docs/styles.css`, `docs/app.js`
- Subscriber/admin bridge: `backend/apps-script/`
- Firestore client rules: `firebase/firestore.rules`
- Roadmap: `docs/ROADMAP.md`
- Changelog: `docs/CHANGELOG.md`
- Change/configuration reference: `docs/CONFIGURATION_AND_CHANGE_GUIDE.md`

Run tests with `python -m unittest discover -s tests -v`.

PokéDrop Watch is a fan-made tracker and is not affiliated with Nintendo, The Pokémon Company, Pokémon Center, or any retailer.
