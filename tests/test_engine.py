import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'monitor'))
from engine import extract_structured_products, normalize_availability, parse_rss, stable_url
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

    def test_rss_items_are_parsed(self):
        sample = '''<rss version="2.0"><channel><item><title>New Pokémon collection announced</title>
        <link>https://news.example/new-set</link><guid>set-1</guid><description>Cards and products.</description>
        </item></channel></rss>'''
        result = parse_rss(sample, {'id': 'news', 'url': 'https://news.example/feed', 'name': 'News'})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'New Pokémon collection announced')
        self.assertEqual(result[0]['url'], 'https://news.example/new-set')


if __name__ == '__main__':
    unittest.main()
