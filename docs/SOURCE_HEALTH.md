# Source health

PokéDrop Watch checks each configured retailer route on every 15-minute scan. Broad searches are used where the retailer exposes them; the monitor assigns categories from product titles and structured data, and the website filters the results into TCG, plush, figures, games, and accessories.

Some retailers do not currently have a verified broad catalog route in this project. Pokémon Center therefore keeps its known TCG and plush category pages separate. Best Buy and GameStop currently use their configured Pokémon TCG pages. This is a coverage limitation, not a reason to stagger scans.

## Statuses

- **MATCHES** — at least one current product or article was recognized.
- **FALLBACK** — the primary route did not provide usable entries; a backup route did.
- **BLOCKED** — the retailer returned an access-protection page.
- **NO MATCH** — the checked content returned no recognized entries.
- **ISSUE** — the request failed.

Every configured primary retailer route is checked on every scan. All configured URLs for that source are handled in the same 15-minute cycle; no route is rotated or postponed to a later scan.

## Product categories

The retailer parser stores the category detected for each item. The public site applies its existing category and retailer filters after the catalog is fetched. A broad search can still expose only the page's returned results; products hidden behind additional retailer pagination or client-side rendering cannot be guaranteed to be found by a single HTTP request.

## Current versus saved records

A product retained from an earlier scan remains in the saved catalog so its price and availability history are not lost. Its last-seen timestamp indicates when the monitor last observed it. A saved record is not a live stock confirmation.

## Owner troubleshooting

1. Open [GitHub Actions](https://github.com/n0nam3-bot/PokeDropWatch/actions) and select the latest PokeDrop Watch run.
2. Expand **Scan sources and send email digest**.
3. For **BLOCKED**, the retailer is returning bot/access protection. The monitor does not bypass it.
4. For **NO MATCH**, inspect the response for product cards or JSON that the parser can read.
5. For **ISSUE**, inspect the HTTP, DNS, TLS, or timeout error.

A source is considered covered only when a real scan returns usable current products or news.
