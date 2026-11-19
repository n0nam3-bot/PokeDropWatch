import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DashboardFilterConfigTests(unittest.TestCase):
    def test_existing_item_type_filter_includes_news(self):
        page = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="categoryFilter"', page)
        self.assertIn('<option value="news">News</option>', page)
        self.assertIn('data-filter="news"', page)

    def test_retailer_routes_are_compact_and_broad_where_supported(self):
        config = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = {source["id"]: source for source in config["sources"]}
        self.assertEqual(len(sources), 8)
        self.assertEqual(sources["pokemon-center-tcg"]["url"], "https://www.pokemoncenter.com/category/new-releases")
        self.assertEqual(sources["pokemon-center-plush"]["url"], "https://www.pokemoncenter.com/category/back-in-stock")
        self.assertIn("searchTerm=pokemon", sources["target-tcg"]["url"])
        self.assertNotIn("facetedValue=", sources["target-tcg"]["url"])
        self.assertEqual(sources["walmart-tcg"]["url"], "https://www.walmart.com/search?q=pokemon")
        self.assertEqual(sources["amazon-pokemon-products"]["url"], "https://www.amazon.com/s?k=pokemon")
        self.assertEqual(
            sources["gamestop-pokemon-tcg"]["url"],
            "https://www.gamestop.com/search-new/?q=pokemon&sort_by=streetDateOrAvailableDate&sort_order=descending",
        )
        self.assertEqual(
            sources["pokemon-news-google"]["url"],
            "https://news.google.com/rss/search?q=%28Pokemon+TCG+OR+Pokemon+Center%29&hl=en-US&gl=US&ceid=US%3Aen",
        )

    def test_only_unified_unavailable_catalogs_keep_separate_routes(self):
        config = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = {source["id"]: source for source in config["sources"]}
        self.assertEqual(sum(1 for source in sources.values() if source.get("retailer_key") == "pokemon-center"), 2)
        self.assertEqual(sum(1 for source in sources.values() if source.get("retailer_key") == "target"), 1)
        self.assertEqual(sum(1 for source in sources.values() if source.get("retailer_key") == "walmart"), 1)
        self.assertEqual(sum(1 for source in sources.values() if source.get("retailer_key") == "amazon"), 1)
        self.assertEqual(sum(1 for source in sources.values() if source.get("retailer_key") == "best-buy"), 1)
        self.assertEqual(sum(1 for source in sources.values() if source.get("retailer_key") == "gamestop"), 1)


if __name__ == "__main__":
    unittest.main()
