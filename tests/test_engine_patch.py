import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitor"))
import engine_patch
import engine_recovery_patch  # noqa: F401
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
        if url.endswith("/feed"):
            return FakeResponse(
                '<error><code>wp_die</code><title>WordPress Error</title>'
                '<message>No feed available</message><data><status>500</status></data></error>',
                url,
                "application/xml",
            )
        return FakeResponse(json.dumps([{
            "id": 42,
            "date_gmt": "2026-11-17T12:00:00",
            "link": "https://www.pokebeach.com/2026/11/pokemon-expansion-announced",
            "title": {"rendered": "Pokémon expansion announced"},
            "excerpt": {"rendered": "A new Pokémon TCG expansion was announced."},
            "_embedded": {"wp:featuredmedia": [{"source_url": "https://images.example/news.jpg"}]},
        }]), url, "application/json")


class EnginePatchTests(unittest.TestCase):
    def test_broken_pokebeach_error_xml_is_not_accepted_as_an_empty_feed(self):
        body = '<error><code>wp_die</code><message>No feed available</message></error>'
        with self.assertRaisesRegex(ValueError, "WordPress error XML"):
            engine.parse_rss(body, {"id": "pokebeach-news", "url": "https://www.pokebeach.com/feed"})
        xml_declaration = '<?xml version="1.0"?><error><code>wp_die</code><message>No feed available</message></error>'
        with self.assertRaisesRegex(ValueError, "WordPress error XML"):
            engine.parse_rss(xml_declaration, {"id": "pokebeach-news", "url": "https://www.pokebeach.com/feed"})

    def test_wordpress_posts_api_is_parsed_as_news(self):
        payload = [{
            "id": 7,
            "link": "https://www.pokebeach.com/2026/11/new-pokemon-set",
            "title": {"rendered": "New Pokémon set announced"},
            "excerpt": {"rendered": "<p>Details about the set.</p>"},
            "date_gmt": "2026-11-17T14:00:00",
        }]
        items = engine_patch.parse_wordpress_posts(payload, {
            "id": "pokebeach-news", "url": "https://www.pokebeach.com/wp-json/wp/v2/posts",
            "name": "PokéBeach", "retailer": "PokéBeach",
        })
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["category"], "news")
        self.assertEqual(items[0]["url"], payload[0]["link"])

    def test_scan_marks_feed_with_working_fallback_as_partial(self):
        source = {
            "id": "pokebeach-news", "name": "PokéBeach", "retailer": "PokéBeach",
            "type": "rss", "url": "https://www.pokebeach.com/feed",
            "alternate_urls": ["https://www.pokebeach.com/wp-json/wp/v2/posts?per_page=30&_embed"],
            "category": "news", "retailer_key": "pokebeach",
        }
        events, result = engine.scan_source(
            FakeSession(), source,
            {"request_timeout_seconds": 1},
            {"items": {}},
        )
        self.assertEqual(events, [])  # Initial scan establishes a feed baseline.
        self.assertEqual(result["status"]["status"], "warning")
        self.assertEqual(result["status"]["items_found"], 1)
        self.assertEqual(result["status"]["successful_urls"], 1)
        self.assertEqual(result["status"]["configured_urls"], 2)
        self.assertTrue(result["status"]["response_health"]["partial"])

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

    def test_first_catalog_baseline_surfaces_only_items_with_nearby_release_dates(self):
        release = date.today().isoformat()
        source = {
            "id": "store-release", "name": "Example Store", "retailer": "Example Store",
            "type": "catalog", "url": "https://shop.example/search?q=pokemon",
            "category": "tcg", "retailer_key": "example-store",
        }
        body = f'''<html><head><script type="application/ld+json">
        {{"@type":"Product","name":"Pokémon TCG Upcoming Set Box",
          "url":"https://shop.example/product/upcoming-set-box",
          "releaseDate":"{release}","offers":{{"price":"49.99"}}}}
        </script></head></html>'''
        with patch("engine.fetch", return_value=(body, source["url"])):
            events, result = engine.scan_source(
                FakeSession(), source,
                {"request_timeout_seconds": 1, "max_items_per_catalog": 50},
                {"items": {}},
            )
        self.assertEqual(result["status"]["status"], "ok")
        self.assertEqual([event["type"] for event in events], ["new_item"])
        self.assertEqual(events[0]["release_date"], release)

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
        source = {
            "id": "pokemon-center-tcg", "name": "Pokémon Center TCG", "retailer": "Pokémon Center",
            "type": "catalog", "url": "https://www.pokemoncenter.com/category/tcg-cards",
            "category": "tcg", "retailer_key": "pokemon-center", "pokemon_scoped": True,
        }
        body = """<html><body>
        <div class="product-card" data-testid="product-tile">
          <a href="/special-collection-123"><img alt="Trading Card Game Collector Bundle"
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

    def test_source_config_uses_the_supplied_category_pages(self):
        config = json.loads((Path(__file__).resolve().parents[1] / "config" / "sources.json").read_text(encoding="utf-8"))
        sources = {source["id"]: source for source in config["sources"]}
        self.assertEqual(sources["pokemon-center-tcg"]["url"], "https://www.pokemoncenter.com/category/tcg-cards")
        self.assertIn("facetedValue=tkle6", sources["target-tcg"]["url"])
        self.assertIn("sort=new", sources["walmart-tcg"]["alternate_urls"][0])
        self.assertIn("category=plush", sources["pokemon-center-plush"]["alternate_urls"][0])


if __name__ == "__main__":
    unittest.main()
