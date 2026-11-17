import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'monitor'))
from unittest.mock import patch
from engine import scan_source


class FakeResponse:
    def __init__(self, body):
        self.text = body
        self.url = 'https://shop.example/product/pokemon-box'
        self.headers = {'content-type': 'text/html; charset=utf-8'}
    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, body):
        self.body = body
    def get(self, *args, **kwargs):
        return FakeResponse(self.body)


def product_page(availability, price='49.99'):
    return f'''<html><head><title>Pokémon Box</title><script type="application/ld+json">
    {{"@type":"Product","name":"Pokémon Box","url":"https://shop.example/product/pokemon-box",
      "offers":{{"price":"{price}","priceCurrency":"USD","availability":"https://schema.org/{availability}"}}}}
    </script></head><body>Pokémon Box</body></html>'''


class TransitionTests(unittest.TestCase):
    def test_out_of_stock_to_in_stock_creates_restock(self):
        source = {'id': 'store-box', 'name': 'Store Box', 'retailer': 'Store', 'type': 'product', 'url': 'https://shop.example/product/pokemon-box'}
        settings = {'request_timeout_seconds': 1}
        state = {'items': {}}
        first_events, first_result = scan_source(FakeSession(product_page('OutOfStock')), source, settings, state)
        self.assertEqual(first_events, [])  # initial scan seeds a baseline
        state['items'][source['id']] = first_result['state']
        second_events, _ = scan_source(FakeSession(product_page('InStock')), source, settings, state)
        self.assertEqual([event['type'] for event in second_events], ['restock'])

    def test_price_change_creates_price_event(self):
        source = {'id': 'store-box', 'name': 'Store Box', 'retailer': 'Store', 'type': 'product', 'url': 'https://shop.example/product/pokemon-box'}
        settings = {'request_timeout_seconds': 1}
        state = {'items': {}}
        _, first_result = scan_source(FakeSession(product_page('InStock', '59.99')), source, settings, state)
        state['items'][source['id']] = first_result['state']
        events, _ = scan_source(FakeSession(product_page('InStock', '49.99')), source, settings, state)
        self.assertIn('price_drop', [event['type'] for event in events])

    def test_catalog_page_without_recognized_pokemon_products_is_warning(self):
        source = {'id': 'store-search', 'name': 'Store Pokémon Search', 'retailer': 'Store', 'type': 'catalog', 'url': 'https://shop.example/search?q=pokemon'}
        settings = {'request_timeout_seconds': 1, 'max_items_per_catalog': 50}
        state = {'items': {}}
        body = '<html><body><a href="/product-reviews/123">98 ratings</a><a href="/gp/offer-listing/123">See options</a></body></html>'
        with patch('engine.fetch', return_value=(body, source['url'])):
            events, result = scan_source(FakeSession(body), source, settings, state)
        self.assertEqual(events, [])
        self.assertEqual(result['status']['status'], 'warning')
        self.assertEqual(result['status']['items_found'], 0)
        self.assertIn('no relevant Pokémon', result['status']['message'])


    def test_changed_catalog_url_resets_baseline_without_new_drop_burst(self):
        old_url = 'https://shop.example/search?q=pokemon-tcg'
        new_url = 'https://shop.example/search?q=pokemon'
        source = {'id': 'store-search', 'name': 'Store Pokémon Search', 'retailer': 'Store', 'type': 'catalog', 'url': new_url}
        product_html = product_page('InStock')
        state = {'items': {'store-search': {'source_url': old_url, 'initialized': True, 'products': {}}}}
        with patch('engine.fetch', return_value=(product_html, 'https://shop.example/product/pokemon-box')):
            events, result = scan_source(FakeSession(product_html), source, {'request_timeout_seconds': 1, 'max_items_per_catalog': 50}, state)
        self.assertEqual(events, [])
        self.assertEqual(result['state']['source_url'], new_url)


if __name__ == '__main__':
    unittest.main()
