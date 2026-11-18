# Retailer sources and alert filters

This patch updates the existing public catalog scanner and dashboard. It does not change the GitHub Actions workflow, subscriber database, Apps Script service, or email credentials.

## Retailer source coverage

The catalog configuration now uses the Pokémon-filtered pages supplied for Pokémon Center, Target, Walmart, Best Buy, and GameStop. Target and Walmart are split into TCG and plush source records so the scanner checks the two product types independently. Pokémon Center plush also checks the supplied new-releases/available page. Walmart and Best Buy check their new-arrival / coming-soon views as alternates.

The supplied category URLs are explicitly marked as Pokémon-scoped. For those pages, product tiles returned by the retailer's Pokémon filter can be accepted even when the individual title omits the word “Pokémon.” Product title, page scope, product URL, and retailer-card information are still used; normal broad searches retain the stricter Pokémon-title check.

Sold-out products remain catalog records. They appear with out-of-stock availability, and a restock event is only produced when a later scan observes an out-of-stock to in-stock/preorder transition.

## PokéBeach feed fallback

The scanner rejects the WordPress `wp_die` / “No feed available” XML response from `/feed` instead of counting it as a valid empty feed. It then tries the WordPress REST posts endpoint:

`https://www.pokebeach.com/wp-json/wp/v2/posts?per_page=30&_embed`

The fallback is only useful while PokéBeach allows that endpoint to be read. If both endpoints are blocked or unavailable, the source should report an issue rather than silently claim a successful zero-item feed.

## Alert filter meanings

- **New items** — a catalog product with a published release date no more than 30 calendar days before or after the current UTC date.
- **First seen** — a listing first discovered by the monitor whose release date is outside that window or unavailable.
- **Restocks** — a previously out-of-stock listing later reports in-stock or preorder availability.
- **Price drops** — a lower observed price than the previous successful scan.
- **News** — new posts detected in the news feed.

Release dates are taken only from recognized release/street/launch-date fields or clearly labeled release-date page markup. Generic page publication timestamps are not treated as product release dates. If a retailer does not expose a release date, its listing can still be First seen, but it will not be classified as a New item.

A first baseline scan continues to avoid creating First seen events for every existing product. It now creates a New item event only for baseline products with a published release date inside the 30-day window. Later discoveries are classified as New item or First seen using the same date rule.

The public alert retailer dropdown is intentionally limited to **All retailers**, **Amazon**, and **Walmart**. “All retailers” still includes alert events from every configured source. The separate subscription preferences list is unchanged.

## Install

1. Upload this ZIP to the repository's `updates/` folder (or another folder in the repository) and commit it.
2. Let the existing **PokeDrop Watch** GitHub Actions workflow run. It applies ZIP patches, runs the unit tests, runs the source scan, and commits the generated status data.
3. Review the workflow log and the public Source Health cards. Parser improvements cannot guarantee that every retailer will return product data: retailer bot protection, JavaScript-only rendering, geolocation, or markup changes can still prevent a scan from seeing cards. A request failure should appear as an issue; a page that responds without parseable cards should remain a parser warning.

The patch ZIP contains a single `PokeDropWatch_Update/` wrapper folder, which the existing patch installer strips automatically.
