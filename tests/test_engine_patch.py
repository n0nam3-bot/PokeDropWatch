import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitor"))
import engine_patch
import engine_recovery_patch  # noqa: F401
import retailer_payload_patch  # noqa: F401 - uses product-local JSON fields
import trainer_preferences_patch  # noqa: F401
import engine


class FakeResponse:
    def __init__(self, body, url, content_type="application/json"):
        self.text = body
        self.url = url
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        return None


class FakeSession:
    def get(self, url, **_kwargs):
        return FakeResponse("<rss version='2.0'><channel><title>Empty</title></channel></rss>", url, "application/rss+xml")


class EnginePatchTests(unittest.TestCase):
    def test_verified_new_release_is_email_eligible_but_first_seen_is_not(self):
        self.assertTrue(engine.is_email_eligible_event({"type": "new_item", "title": "Pokémon TCG Release"}))
        self.assertFalse(engine.is_email_eligible_event({"type": "first_seen", "title": "Pokémon TCG Release"}))

    def test_release_date_window_is_thirty_days_in_either_direction(self):
        today = date.today()
        self.assertTrue(engine_patch.release_date_within_month((today - timedelta(days=30)).isoformat(), today))
        self.assertTrue(engine_patch.release_date_within_month((today + timedelta(days=30)).isoformat(), today))
        self.assertFalse(engine_patch.release_date_within_month((today - timedelta(days=31)).isoformat(), today))
        self.assertFalse(engine_patch.release_date_within_month("not a date", today))

    def test_json_product_release_date_is_preserved(self):
        release = date.today().isoformat()
        payload = {"items": [{
            "productName": "Pokémon TCG Release Date Test Box",
            "url": "https://shop.example/product/release-date-test",
            "releaseDate": release,
            "price": 49.99,
        }]}
        products = engine.extract_json_products(payload, "https://shop.example/search", "Example Store")
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["release_date"], release)

    def test_generic_published_date_is_not_misclassified_as_product_release_date(self):
        payload = {"name": "Pokémon TCG Product", "url": "https://shop.example/product/1",
                   "datePublished": date.today().isoformat()}
        self.assertEqual(engine_patch._release_date_from_node(payload), "")

    def test_newly_discovered_item_with_nearby_release_date_has_new_item_type(self):
        release = date.today().isoformat()
        event = engine.event_record("first_seen", {
            "title": "Pokémon TCG Release Date Test Box",
            "url": "https://shop.example/product/release-date-test",
            "release_date": release,
        }, {
            "id": "store-box", "name": "Example Store", "retailer": "Example Store",
            "type": "catalog", "category": "tcg", "retailer_key": "example-store",
            "url": "https://shop.example/search",
        })
        self.assertEqual(event["type"], "new_item")
        self.assertEqual(event["release_date"], release)

    def test_pokemon_scoped_category_accepts_product_titles_without_pokemon_word(self):
        from bs4 import BeautifulSoup
        source = {
            "id": "pokemon-center-tcg", "name": "Pokémon Center", "retailer": "Pokémon Center",
            "type": "catalog", "url": "https://www.pokemoncenter.com/category/new-releases",
            "category": "collectibles", "retailer_key": "pokemon-center", "pokemon_scoped": True,
        }
        body = """<html><body>
        <div class="product-card" data-testid="product-tile">
          <a href="/product/special-collection-123"><img alt="Trading Card Game Collector Bundle"
          src="https://images.example/cards.jpg"></a>
          <h3>Trading Card Game Collector Bundle</h3><span>$29.99</span><span>Sold out</span>
        </div></body></html>"""
        with patch("engine.fetch", return_value=(body, source["url"])):
            events, result = engine.scan_source(
                FakeSession(), source,
                {"request_timeout_seconds": 1, "max_items_per_catalog": 50},
                {"items": {}},
            )
        self.assertEqual(events, [])
        self.assertEqual(result["status"]["status"], "ok")
        self.assertEqual(result["status"]["items_found"], 1)
        product = next(iter(result["state"]["products"].values()))
        self.assertEqual(product["category"], "tcg")
        self.assertEqual(product["availability"], "out_of_stock")
        self.assertTrue(product.get("pokemon_scoped"))

    def test_source_config_uses_one_broad_route_per_retailer_where_available(self):
        config = json.loads((Path(__file__).resolve().parents[1] / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = {source["id"]: source for source in config["sources"]}
        self.assertEqual(sources["pokemon-center-tcg"]["url"], "https://www.pokemoncenter.com/category/new-releases")
        self.assertEqual(sources["pokemon-center-plush"]["url"], "https://www.pokemoncenter.com/category/back-in-stock")
        self.assertEqual(sources["gamestop-pokemon-tcg"]["url"], "https://www.gamestop.com/search-new/?q=pokemon&sort_by=streetDateOrAvailableDate&sort_order=descending")
        self.assertEqual(sources["target-tcg"]["url"], "https://www.target.com/s?searchTerm=pokemon&newSearch=false")
        self.assertEqual(sources["walmart-tcg"]["url"], "https://www.walmart.com/search?q=pokemon")
        self.assertEqual(sources["amazon-pokemon-products"]["url"], "https://www.amazon.com/s?k=pokemon")
        self.assertEqual(len([source for source in config["sources"] if source["retailer_key"] == "amazon"]), 1)
        self.assertEqual(sources["best-buy-pokemon-tcg"]["category"], "tcg")
        self.assertEqual(sources["pokemon-news-google"]["type"], "rss")
        self.assertNotIn("pokebeach-news", sources)


if __name__ == "__main__":
    unittest.main()
