# Source health

Broad retailer searches are used where available. The monitor assigns product categories from titles and structured data, and the website filters the results into TCG, plush, figures, games, and accessories. Pokémon Center uses separate broad New Releases and Back in Stock pages; Best Buy remains limited to Pokémon TCG; GameStop uses its broad Pokémon search sorted newest first.

The news feed is scanned separately from retailer inventory. Its current articles appear inside the existing Latest alerts list when the News activity filter is selected, or when Item type is set to News with All activity selected.

## Statuses

- **MATCHES** — at least one current product or article was recognized.
- **PARTIAL** — only some configured URLs responded or produced usable results; coverage for that source is incomplete.
- **BLOCKED** — a retailer returned an access-protection page such as a bot check or “Pardon Our Interruption.” The page responded, but it did not expose usable inventory.
- **NO MATCH** — the page responded without an access block, but the parser recognized no products or articles. This is a parser miss, not proof that the retailer has no Pokémon products.
- **ISSUE** — all configured URLs failed at the request layer, such as a connection or retry failure.

The GitHub Actions workflow is configured to start every 15 minutes. That is the intended interval, not a guarantee that GitHub will start every scheduled run exactly on time. ZIP uploads and manual workflow runs also trigger scans, so “Last checked” may reflect one of those runs instead of a scheduled scan.

## Product categories

The retailer parser stores the category detected for each item. The public site applies its existing category and retailer filters after the catalog is fetched. A broad search can still expose only the page's returned results; products hidden behind additional retailer pagination or client-side rendering cannot be guaranteed to be found by a single HTTP request.

## Current versus saved records

The dashboard’s **Products tracked** number counts distinct product records retained in the saved retailer catalogs. It can include last-known records when the latest request is blocked or fails. Source cards separately report what the latest scan actually recognized. A saved record is not a live stock confirmation; its last-seen timestamp indicates when the monitor last observed it.

## Owner troubleshooting

1. Open [GitHub Actions](https://github.com/n0nam3-bot/PokeDropWatch/actions) and select the latest PokeDrop Watch run.
2. Expand **Scan sources and send email digest**.
3. For **BLOCKED**, the retailer is returning bot/access protection. The monitor does not bypass it.
4. For **NO MATCH**, inspect the response for product cards or JSON that the parser can read.
5. For **ISSUE**, inspect the HTTP, DNS, TLS, or timeout error.

A source is considered covered only when a real scan returns usable current products or news.
