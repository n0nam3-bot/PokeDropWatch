import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'monitor'))

import engine
import engine_patch
import engine_recovery_patch


class RetailerRecoveryTests(unittest.TestCase):
    def setUp(self):
        engine_patch._SCOPED_SCAN_ACTIVE = True

    def tearDown(self):
        engine_patch._SCOPED_SCAN_ACTIVE = False

    def test_walmart_product_tiles_are_found_without_structured_json(self):
        html = '''<html><body><div data-item-id="123456"><a href="/ip/pokemon-trading-card-game-elite-trainer-box/123456"><img alt="Pokemon Elite Trainer Box" src="https://i5.walmartimages.com/test.jpg"><h3>Pokemon Elite Trainer Box</h3></a><span>Sold out</span></div></body></html>'''
        products = engine_recovery_patch._extract_retailer_dom_products(
            BeautifulSoup(html, 'html.parser'),
            'https://www.walmart.com/search?q=pokemon', 'Walmart', 20,
        )
        self.assertEqual(len(products), 1)
        self.assertIn('/ip/pokemon-trading-card-game-elite-trainer-box/123456', products[0]['url'])
        self.assertEqual(products[0]['availability'], 'out_of_stock')

    def test_target_product_card_with_tcin_path_is_found(self):
        html = '''<html><body><li data-testid="product-card"><a href="/p/pokemon-tcg-booster-bundle/-/A-900001"><h3>Pokemon TCG Booster Bundle</h3><img alt="Pokemon TCG Booster Bundle" src="https://target.scene7.com/image.jpg"></a><span>$29.99</span></li></body></html>'''
        products = engine_recovery_patch._extract_retailer_dom_products(
            BeautifulSoup(html, 'html.parser'),
            'https://www.target.com/s?searchTerm=pokemon', 'Target', 20,
        )
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['price'], 29.99)

    def test_pokemon_center_product_card_is_collected_from_category_route(self):
        html = '''<html><body><article class="product-tile"><a href="/product/pokemon-plush-pikachu"><h3>Pokémon Pikachu Plush</h3><img alt="Pokémon Pikachu Plush" src="https://images.pokemoncenter.com/plush.jpg"></a><span>Sold Out</span></article></body></html>'''
        products = engine_recovery_patch._extract_retailer_dom_products(
            BeautifulSoup(html, 'html.parser'),
            'https://www.pokemoncenter.com/category/new-releases', 'Pokémon Center', 20,
        )
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['availability'], 'out_of_stock')

    def test_nested_retailer_json_product_is_extracted(self):
        payload = {'data': {'products': [{
            'productName': 'Pokemon TCG Collection Box',
            'canonicalUrl': 'https://www.walmart.com/ip/pokemon-tcg-collection-box/123456',
            'currentPrice': {'amount': '39.99'},
            'primaryImage': {'url': 'https://images.example/item.jpg'},
            'stockStatus': 'InStock',
            'productId': '123456',
        }]}}
        products = [
            item for node in engine._walk_json(payload)
            if isinstance(node, dict)
            for item in [engine_recovery_patch._product_from_json_node(node, 'https://www.walmart.com/search?q=pokemon', 'Walmart')]
            if item
        ]
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['price'], 39.99)
        self.assertEqual(products[0]['availability'], 'in_stock')

    def test_retailer_extractor_marks_products_from_pokemon_scoped_pages(self):
        product = {'title': 'Elite Trainer Box', 'url': 'https://www.pokemoncenter.com/product/example'}
        with patch.object(engine_recovery_patch, '_previous_extract_retailer_products', return_value=[dict(product)]):
            with patch.object(engine_recovery_patch, '_extract_retailer_json_products', return_value=[]):
                with patch.object(engine_recovery_patch, '_extract_retailer_dom_products', return_value=[]):
                    products = engine_recovery_patch.extract_retailer_products_recovery(
                        BeautifulSoup('<html></html>', 'html.parser'),
                        'https://www.pokemoncenter.com/category/new-releases', 'Pokémon Center', 20,
                    )
        self.assertTrue(products[0].get('pokemon_scoped'))

    def test_target_tcin_can_supply_missing_product_href(self):
        html = '''<html><body><li class="product-card" data-tcin="900001"><div data-product-name="Pokémon TCG Booster Bundle"><img alt=""></div><span>$29.99</span></li></body></html>'''
        products = engine_recovery_patch._extract_retailer_dom_products(
            BeautifulSoup(html, 'html.parser'),
            'https://www.target.com/s?searchTerm=pokemon', 'Target', 20,
        )
        self.assertEqual(len(products), 1)
        self.assertIn('/-/A-900001', products[0]['url'])

    def test_json_target_record_can_build_pdp_url_from_explicit_tcin(self):
        payload = {'product': {'productName': 'Pokémon TCG Booster Bundle', 'tcin': '900002', 'price': '29.99'}}
        item = engine_recovery_patch._product_from_json_node(
            payload, 'https://www.target.com/s?searchTerm=pokemon', 'Target',
        )
        self.assertIsNotNone(item)
        self.assertIn('/-/A-900002', item['url'])


if __name__ == '__main__':
    unittest.main()
