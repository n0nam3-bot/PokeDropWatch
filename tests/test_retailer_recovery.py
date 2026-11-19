import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'monitor'))

import engine
import engine_patch
import engine_recovery_patch


class RetailerRecoveryTests(unittest.TestCase):
    def test_walmart_product_tiles_are_found_even_without_structured_json(self):
        html = '''<html><body><div data-item-id="123456"><a href="/ip/pokemon-trading-card-game-elite-trainer-box/123456"><img alt="Pokemon Elite Trainer Box" src="https://i5.walmartimages.com/test.jpg"><h3>Pokemon Elite Trainer Box</h3></a><span>Sold out</span></div></body></html>'''
        from bs4 import BeautifulSoup
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            products = engine_recovery_patch._extract_retailer_dom_products(
                BeautifulSoup(html, 'html.parser'),
                'https://www.walmart.com/browse/collectibles/pokemon-cards',
                'Walmart', 20,
            )
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
        self.assertEqual(len(products), 1)
        self.assertIn('/ip/pokemon-trading-card-game-elite-trainer-box/123456', products[0]['url'])
        self.assertEqual(products[0]['availability'], 'out_of_stock')

    def test_target_product_card_with_tcin_path_is_found(self):
        html = '''<html><body><li data-testid="product-card"><a href="/p/pokemon-tcg-booster-bundle/-/A-900001"><h3>Pokemon TCG Booster Bundle</h3><img alt="Pokemon TCG Booster Bundle" src="https://target.scene7.com/image.jpg"></a><span>$29.99</span></li></body></html>'''
        from bs4 import BeautifulSoup
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            products = engine_recovery_patch._extract_retailer_dom_products(
                BeautifulSoup(html, 'html.parser'),
                'https://www.target.com/s?searchTerm=pokemon', 'Target', 20,
            )
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['price'], 29.99)

    def test_pokemon_center_sold_out_category_card_is_still_collected(self):
        html = '''<html><body><article class="product-tile"><a href="/product/pokemon-plush-pikachu"><h3>Pokémon Pikachu Plush</h3><img alt="Pokémon Pikachu Plush" src="https://images.pokemoncenter.com/plush.jpg"></a><span>Sold Out</span></article></body></html>'''
        from bs4 import BeautifulSoup
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            products = engine_recovery_patch._extract_retailer_dom_products(
                BeautifulSoup(html, 'html.parser'), 'https://www.pokemoncenter.com/category/plush', 'Pokémon Center', 20,
            )
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
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
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            products = [
                item for node in engine._walk_json(payload)
                if isinstance(node, dict)
                for item in [engine_recovery_patch._product_from_json_node(node, 'https://www.walmart.com/search?q=pokemon', 'Walmart')]
                if item
            ]
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['price'], 39.99)
        self.assertEqual(products[0]['availability'], 'in_stock')

    def test_pokebeach_homepage_html_is_parsed_as_news(self):
        html = '''<html><body><article><h2 class="entry-title"><a href="https://www.pokebeach.com/2026/11/pokemon-set-revealed">New Pokémon TCG set revealed</a></h2><time datetime="2026-11-18T15:00:00Z"></time><p>A new Pokémon set was announced.</p><img src="https://www.pokebeach.com/image.jpg"></article></body></html>'''
        items = engine_recovery_patch._pokebeach_html_posts(html, {
            'url': 'https://www.pokebeach.com/', 'retailer': 'PokéBeach', 'name': 'PokéBeach',
        })
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['category'], 'news')
        self.assertIn('/2026/11/pokemon-set-revealed', items[0]['url'])

    def test_pokebeach_homepage_is_added_as_last_resort_fallback(self):
        source = {'id': 'pokebeach-news', 'url': 'https://www.pokebeach.com/feed', 'alternate_urls': ['https://www.pokebeach.com/wp-json/wp/v2/posts'], 'notes': 'The public /feed URL returns a WordPress wp_die error.'}
        captured = {}
        fake_result = {'state': {'seen': {}, 'last_item_count': 0}, 'status': {'status': 'warning', 'items_found': 0, 'message': 'No posts.'}}
        def capture_source(_session, actual_source, _settings, _state):
            captured.update(actual_source)
            return [], fake_result
        with patch.object(engine_recovery_patch, '_previous_scan_source', side_effect=capture_source):
            engine_recovery_patch.scan_source_with_recovery(object(), source, {}, {'items': {}})
        self.assertIn('https://www.pokebeach.com/', captured['alternate_urls'])
        self.assertEqual(source['alternate_urls'], ['https://www.pokebeach.com/wp-json/wp/v2/posts'])

    def test_zero_result_scan_preserves_last_known_catalog_count(self):
        source = {'id': 'walmart-tcg', 'name': 'Walmart TCG', 'retailer': 'Walmart', 'type': 'catalog', 'url': 'https://www.walmart.com/browse/collectibles/pokemon-cards'}
        previous = {'source_url': source['url'], 'initialized': True, 'last_item_count': 75,
                    'products': {'a': {'title': 'Pokemon item A'}, 'b': {'title': 'Pokemon item B'}}}
        fake_result = {'state': {'products': dict(previous['products']), 'last_item_count': 0},
                       'status': {'status': 'warning', 'items_found': 0, 'message': 'No matching products.'}}
        with patch.object(engine_recovery_patch, '_previous_scan_source', return_value=([], fake_result)):
            with patch.object(engine_recovery_patch, '_FETCH_DIAGNOSTICS', []):
                _events, result = engine_recovery_patch.scan_source_with_recovery(
                    object(), source, {}, {'items': {'walmart-tcg': previous}},
                )
        self.assertEqual(result['state']['last_item_count'], 75)
        self.assertEqual(result['status']['last_known_items'], 75)
        self.assertIn('not confirm current inventory', result['status']['message'])


    def test_product_title_data_attributes_are_recognized_without_heading_or_alt(self):
        html = '''<html><body><div class="productCard" data-product-title="Pokémon TCG Prismatic Evolutions Elite Trainer Box"><a href="/product/prismatic-evolutions-etb"><img src="https://images.example/etb.jpg"></a><span>$54.99</span></div></body></html>'''
        from bs4 import BeautifulSoup
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            products = engine_recovery_patch._extract_retailer_dom_products(
                BeautifulSoup(html, 'html.parser'), 'https://www.pokemoncenter.com/category/tcg-cards', 'Pokémon Center', 20,
            )
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
        self.assertEqual(len(products), 1)
        self.assertIn('Prismatic Evolutions', products[0]['title'])
        self.assertEqual(products[0]['price'], 54.99)

    def test_target_tcin_can_supply_missing_product_href(self):
        html = '''<html><body><li class="product-card" data-tcin="900001"><div data-product-name="Pokémon TCG Booster Bundle"><img alt=""></div><span>$29.99</span></li></body></html>'''
        from bs4 import BeautifulSoup
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            products = engine_recovery_patch._extract_retailer_dom_products(
                BeautifulSoup(html, 'html.parser'), 'https://www.target.com/s?searchTerm=pokemon', 'Target', 20,
            )
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
        self.assertEqual(len(products), 1)
        self.assertIn('/-/A-900001', products[0]['url'])

    def test_retailer_extractor_marks_products_from_pokemon_scoped_pages(self):
        product = {'title': 'Elite Trainer Box', 'url': 'https://www.pokemoncenter.com/product/example'}
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            with patch.object(engine_recovery_patch, '_previous_extract_retailer_products', return_value=[dict(product)]):
                with patch.object(engine_recovery_patch, '_extract_retailer_json_products', return_value=[]):
                    with patch.object(engine_recovery_patch, '_extract_retailer_dom_products', return_value=[]):
                        products = engine_recovery_patch.extract_retailer_products_recovery(
                            BeautifulSoup('<html></html>', 'html.parser'),
                            'https://www.pokemoncenter.com/category/tcg-cards', 'Pokémon Center', 20,
                        )
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
        self.assertTrue(products[0].get('pokemon_scoped'))

    def test_json_target_record_can_build_pdp_url_from_explicit_tcin(self):
        payload = {'product': {'productName': 'Pokémon TCG Booster Bundle', 'tcin': '900002', 'price': '29.99'}}
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            item = engine_recovery_patch._product_from_json_node(
                payload, 'https://www.target.com/s?searchTerm=pokemon', 'Target',
            )
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
        self.assertIsNotNone(item)
        self.assertIn('/-/A-900002', item['url'])

    def test_partial_success_marks_source_warning_and_preserves_found_items(self):
        source = {'id': 'target-tcg', 'name': 'Target TCG', 'retailer': 'Target', 'type': 'catalog', 'url': 'https://www.target.com/s?searchTerm=pokemon'}
        fake_result = {'state': {'products': {}, 'last_item_count': 3}, 'status': {
            'status': 'ok', 'items_found': 3, 'successful_urls': 1, 'configured_urls': 3,
            'message': 'Fetched 1/3 configured URL(s). 3 relevant Pokémon listing(s) recognized.'
        }}
        def fake_scan(*_args):
            engine_recovery_patch._FETCH_DIAGNOSTICS.append({'url': 'https://www.target.com/alternate-one', 'bytes': 8000, 'title': 'Target search', 'product_links': 4, 'json_scripts': 2, 'challenge': False})
            engine_recovery_patch._FETCH_DIAGNOSTICS.append({'url': 'https://www.target.com/alternate-two', 'error': 'ConnectionError: timed out'})
            engine_recovery_patch._FETCH_DIAGNOSTICS.append({'url': 'https://www.target.com/alternate-three', 'error': 'HTTPError: 503'})
            return [], fake_result
        with patch.object(engine_recovery_patch, '_previous_scan_source', side_effect=fake_scan):
            events, result = engine_recovery_patch.scan_source_with_recovery(object(), source, {}, {'items': {}})
        self.assertEqual(events, [])
        self.assertEqual(result['status']['status'], 'warning')
        self.assertEqual(result['status']['response_health'], {'successful': 1, 'configured': 3, 'failed': 2, 'partial': True})
        self.assertIn('PARTIAL: 1/3', result['status']['message'])
        self.assertEqual(result['status']['items_found'], 3)
        self.assertEqual(result['status']['last_known_items'], 3)
        self.assertEqual(result['status']['current_items_found'], 3)
        self.assertEqual(result['state']['last_item_count'], 3)


if __name__ == '__main__':
    unittest.main()
