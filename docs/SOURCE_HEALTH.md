# Source health

Broad retailer searches are used where available. The monitor assigns product categories from titles and structured data, and the website filters the results into TCG, plush, figures, games, and accessories. Pokémon Center uses separate broad New Releases and Back in Stock pages; Best Buy remains limited to Pokémon TCG; GameStop uses its broad Pokémon search sorted newest first.

The news feed is scanned separately from retailer inventory. Its current articles appear inside the existing Latest alerts list when the News activity filter is selected, or when Item type is set to News with All activity selected.

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
