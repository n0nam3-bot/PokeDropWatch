import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'monitor'))
from engine import extract_catalog_links, extract_structured_products, infer_category, is_pokemon_relevant, is_valid_event, normalize_availability, parse_rss, stable_url, event_record, html_email
from bs4 import BeautifulSoup


class EngineTests(unittest.TestCase):
    def test_stock_status_normalization(self):
        self.assertEqual(normalize_availability('https://schema.org/InStock'), 'in_stock')
        self.assertEqual(normalize_availability('https://schema.org/OutOfStock'), 'out_of_stock')
        self.assertEqual(normalize_availability('Pre-order now'), 'preorder')
        self.assertEqual(normalize_availability('unknown'), 'unknown')

    def test_stable_url_removes_tracking(self):
        self.assertEqual(stable_url('https://shop.example/item/?utm_source=x#buy'), 'https://shop.example/item')

    def test_product_json_ld_extraction(self):
        sample = '''<html><head><script type="application/ld+json">
        {"@context":"https://schema.org","@type":"Product","name":"Pokémon TCG Example Elite Trainer Box",
         "sku":"ABC123","image":"https://shop.example/box.jpg","url":"https://shop.example/product/abc",
         "offers":{"@type":"Offer","price":"49.99","priceCurrency":"USD","availability":"https://schema.org/InStock"}}
        </script></head></html>'''
        products = extract_structured_products(BeautifulSoup(sample, 'html.parser'), 'https://shop.example/', 'Example Store')
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['title'], 'Pokémon TCG Example Elite Trainer Box')
        self.assertEqual(products[0]['price'], 49.99)
        self.assertEqual(products[0]['availability'], 'in_stock')

    def test_event_record_carries_subscription_filters(self):
        event = event_record('restock', {'title': 'Pokémon box', 'url': 'https://shop.example/box'}, {
            'id': 'pc-tcg', 'name': 'Pokémon Center TCG', 'retailer': 'Pokémon Center',
            'type': 'catalog', 'category': 'tcg', 'retailer_key': 'pokemon-center',
            'url': 'https://shop.example/tcg'
        })
        self.assertEqual(event['category'], 'tcg')
        self.assertEqual(event['retailer_key'], 'pokemon-center')

    def test_email_contains_secure_manage_link(self):
        subject, html_body, text_body = html_email(
            [{'id': '1', 'type': 'restock', 'title': 'Pokémon box', 'url': 'https://shop.example/box', 'retailer': 'Example', 'price': 49.99, 'availability': 'in_stock'}],
            manage_url='https://example.github.io/watch/?unsubscribe=1#subscriptions'
        )
        self.assertIn('PokéDrop Watch', subject)
        self.assertIn('request secure unsubscribe', html_body)
        self.assertIn('https://example.github.io/watch/?unsubscribe=1#subscriptions', text_body)

    def test_rss_items_are_parsed(self):
        sample = '''<rss version="2.0"><channel><item><title>New Pokémon collection announced</title>
        <link>https://news.example/new-set</link><guid>set-1</guid><description>Cards and products.</description>
        </item></channel></rss>'''
        result = parse_rss(sample, {'id': 'news', 'url': 'https://news.example/feed', 'name': 'News'})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'New Pokémon collection announced')
        self.assertEqual(result[0]['url'], 'https://news.example/new-set')

    def test_catalog_ignores_amazon_rating_and_options_links_and_keeps_product_image(self):
        sample = """<html><body>
        <div data-component-type="s-search-result" class="s-result-item">
          <a href="/gp/product/B0POKEMON"><img class="s-image" alt="Pokémon TCG Scarlet & Violet Elite Trainer Box" data-src="https://images.example/etb.jpg"></a>
          <span class="a-price"><span class="a-offscreen">$51.45</span></span>
          <a href="/product-reviews/B0POKEMON">98 ratings</a>
          <a href="/gp/offer-listing/B0POKEMON">See options</a>
        </div>
        <div data-component-type="s-search-result">
          <a href="/gp/product/UNRELATED"><img alt="Insulated stainless steel water bottle" src="https://images.example/bottle.jpg"></a>
        </div>
        </body></html>"""
        products = extract_catalog_links(BeautifulSoup(sample, 'html.parser'), 'https://www.amazon.com/s?k=pokemon', 'Amazon', 50)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['title'], 'Pokémon TCG Scarlet & Violet Elite Trainer Box')
        self.assertEqual(products[0]['image'], 'https://images.example/etb.jpg')
        self.assertEqual(products[0]['price'], 51.45)
        self.assertEqual(products[0]['category'], 'tcg')

    def test_category_classification(self):
        self.assertEqual(infer_category('Pikachu Sitting Cuties Plush'), 'plush')
        self.assertEqual(infer_category('Pokémon Scarlet Violet Elite Trainer Box'), 'tcg')
        self.assertEqual(infer_category('Pokémon Legends Nintendo Switch Game'), 'games')
        self.assertEqual(infer_category('Eevee Backpack'), 'accessories')

    def test_relevance_rejects_generic_ratings(self):
        self.assertFalse(is_pokemon_relevant('98 ratings'))
        self.assertFalse(is_pokemon_relevant('See options'))
        self.assertTrue(is_pokemon_relevant('Pikachu Sitting Cuties'))

    def test_rss_extracts_media_thumbnail(self):
        sample = """<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><item>
        <title>New Pokémon set announced</title><link>https://news.example/set</link>
        <media:thumbnail url="https://news.example/set.jpg" />
        </item></channel></rss>"""
        result = parse_rss(sample, {'id': 'news', 'url': 'https://news.example/feed', 'name': 'News'})
        self.assertEqual(result[0]['image'], 'https://news.example/set.jpg')


    def test_legacy_bad_product_events_are_invalid_but_scoped_news_is_kept(self):
        self.assertFalse(is_valid_event({"type": "new_drop", "category": "tcg", "title": "98 ratings"}))
        self.assertTrue(is_valid_event({"type": "news", "category": "news", "title": "New expansion set announced"}))


if __name__ == '__main__':
    unittest.main()
