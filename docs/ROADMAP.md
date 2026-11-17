# PokéDrop Watch Roadmap

Status key: ☑ completed · ☐ planned or not yet verified

## Stage 1 — Core monitor and public site

- ☑ GitHub Pages public dashboard with mobile and desktop layouts
- ☑ Scheduled GitHub Actions monitor
- ☑ Product baseline, price transition and stock transition tracking
- ☑ Search, exact title, item type, retailer and event-type filters
- ☑ First-seen wording separated from verified restocks and price changes; legacy “new drop” history is migrated and excluded from email
- ☑ Fixed header, fixed bottom navigation and sticky filter controls
- ☐ Verify all public page routes after each GitHub Pages release

## Stage 2 — Retailer coverage and product data quality

- ☑ Structured data, embedded JSON, JSON response and HTML-card parsers
- ☑ Alternate URL probing (up to three category-search fallbacks per source) and same-retailer duplicate consolidation
- ☑ Product title cleanup and category inference for common TCG products
- ☑ Product image extraction where retailers expose usable image URLs
- ☐ Create and maintain a saved HTML/JSON fixture for every retailer
- ☐ Deliver a dedicated Pokémon Center adapter with a verified product fixture
- ☐ Deliver a dedicated Target adapter with a verified product fixture
- ☐ Deliver a dedicated Walmart adapter with a verified product fixture
- ☐ Deliver a dedicated Best Buy adapter with a verified product fixture
- ☐ Deliver a dedicated GameStop adapter with a verified product fixture
- ☐ Verify Amazon listing identity, seller/listing dates and duplicate variants
- ☐ Add an independent Pokémon news feed with tested XML fixtures
- ☐ Confirm a successful live scan from every retailer before changing its status to complete

## Stage 3 — Subscriber and admin security

- ☑ Email ownership code verification with fixed 10-minute expiry and same-page entry
- ☑ Administrator password sign-in through Apps Script (no Firebase action links)
- ☑ Administrator password reset code with single-use expiry and replacement invalidation
- ☑ Pending approval, reject, suspend, reactivate and remove controls
- ☑ Verified same-page unsubscribe confirmation
- ☑ Firestore data access through private service-account IAM only
- ☐ Test full enrollment/approval/notification/unsubscribe flow against live Firebase and Gmail credentials
- ☐ Add admin audit history and exportable subscriber counts without exposing PII

## Stage 4 — Email notification quality

- ☑ Individual subscriber digest delivery
- ☑ Category and retailer preference filtering
- ☑ Product price, availability, retailer and direct link in email templates
- ☑ First-seen discovery excluded from product-drop email notifications
- ☐ Verify branded sender identity and deliverability in Gmail, Outlook and mobile clients
- ☐ Add per-subscriber digest frequency controls
- ☐ Add delivery failure dashboard and bounded retry policy

## Stage 5 — Design, accessibility and reliability

- ☑ DaFont PKMN RBYGSC font path and CSS fallback prepared
- ☑ Larger desktop typography and narrower centered product list
- ☑ Owner setup instructions moved outside the published `/docs` site
- ☐ Add the licensed/downloaded PKMN RBYGSC TTF asset to `docs/assets/fonts/`
- ☐ Test iOS Safari, Android Chrome, tablet and desktop layouts
- ☐ Add automated visual/accessibility checks for navigation and sticky filters
- ☐ Add source response time and last-success timestamps to the health detail view

## Release rule

A roadmap item that depends on a real retailer, email provider, Firebase project, or live browser must remain unchecked until it has been verified against that live service. Parser unit tests alone do not prove retailer coverage.
