import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DashboardFilterConfigTests(unittest.TestCase):
    def test_alert_type_filters_distinguish_new_items_from_first_seen(self):
        app = (ROOT / "docs" / "app.js").read_text(encoding="utf-8")
        self.assertIn("newItems.dataset.filter = 'new_item'", app)
        self.assertIn("firstSeen.dataset.filter = 'first_seen'", app)
        self.assertIn("releaseDateWithinMonth(item.release_date)", app)
        self.assertIn("new_item: 'NEW ITEM'", app)

    def test_retailer_filter_has_all_six_requested_retailers(self):
        app = (ROOT / "docs" / "app.js").read_text(encoding="utf-8")
        expected = {
            'all': 'All retailers', 'amazon': 'Amazon', 'walmart': 'Walmart',
            'best-buy': 'Best Buy', 'target': 'Target',
            'pokemon-center': 'Pokémon Center', 'gamestop': 'GameStop',
        }
        for value, label in expected.items():
            self.assertIn(f"new Option('{label}', '{value}')", app)
        self.assertIn("'all', 'amazon', 'walmart', 'best-buy', 'target', 'pokemon-center', 'gamestop'", app)

    def test_only_filtered_retailer_pages_use_scoped_product_acceptance(self):
        config = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = {source["id"]: source for source in config["sources"]}
        expected = {
            "pokemon-center-tcg", "pokemon-center-plush", "pokemon-center-plush-new-releases",
            "target-tcg", "target-tcg-new-arrivals", "target-plush", "target-plush-new-arrivals",
            "walmart-tcg", "walmart-tcg-newest", "walmart-plush", "walmart-plush-newest",
            "best-buy-pokemon-tcg", "best-buy-pokemon-tcg-new-arrivals",
            "best-buy-pokemon-tcg-coming-soon", "gamestop-pokemon-tcg",
        }
        self.assertEqual({key for key, value in sources.items() if value.get("pokemon_scoped")}, expected)
        self.assertNotIn("pokemon_scoped", sources["amazon-pokemon-products"])
        self.assertNotIn("pokemon_scoped", sources["amazon-pokemon-tcg"])

    def test_each_retailer_query_scope_is_listed_once_and_grouped_by_retailer(self):
        config = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = config["sources"]
        urls = [source["url"] for source in sources]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(len(sources), 20)
        self.assertEqual(len({source["retailer_key"] for source in sources}), 7)
        amazon_ids = {source["id"] for source in sources if source["retailer_key"] == "amazon"}
        self.assertEqual(amazon_ids, {
            "amazon-pokemon-products", "amazon-pokemon-tcg", "amazon-pokemon-plush", "amazon-pokemon-figures",
        })


if __name__ == "__main__": unittest.main()
