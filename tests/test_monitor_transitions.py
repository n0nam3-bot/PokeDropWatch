import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'monitor'))
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


if __name__ == '__main__':
    unittest.main()
