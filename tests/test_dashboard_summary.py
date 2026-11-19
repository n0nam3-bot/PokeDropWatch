import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "monitor"))
from run import count_saved_product_records


class DashboardSummaryTests(unittest.TestCase):
    def test_saved_records_count_even_when_latest_source_status_is_unavailable(self):
        sources = [
            {"id": "walmart", "type": "catalog", "retailer": "Walmart", "retailer_key": "walmart"},
            {"id": "amazon", "type": "catalog", "retailer": "Amazon", "retailer_key": "amazon"},
            {"id": "news", "type": "rss", "retailer": "Pokémon News", "retailer_key": "pokemon-news"},
        ]
        items = {
            "walmart": {"products": {
                "one": {"title": "Pokémon TCG Booster Bundle", "retailer_key": "walmart"},
                "two": {"title": "Pikachu Plush", "retailer_key": "walmart"},
            }},
            "amazon": {"products": {
                "one": {"title": "Pokémon TCG Booster Bundle", "retailer_key": "amazon"},
            }},
            "news": {"articles": [{"title": "Pokémon news"}]},
        }
        self.assertEqual(count_saved_product_records(sources, items), 3)

    def test_duplicate_product_is_counted_once_within_the_same_retailer(self):
        sources = [{"id": "walmart", "type": "catalog", "retailer_key": "walmart"}]
        items = {"walmart": {"products": {
            "url-one": {"title": "Pokémon TCG Booster Bundle"},
            "url-two": {"title": "Pokemon TCG Booster Bundle"},
        }}}
        self.assertEqual(count_saved_product_records(sources, items), 1)


if __name__ == "__main__":
    unittest.main()
