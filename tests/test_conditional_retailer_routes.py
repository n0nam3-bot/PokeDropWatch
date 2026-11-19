\
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'monitor'))

import engine
import broad_source_patch
import engine_recovery_patch as recovery


class ConditionalRetailerRouteTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            'id': 'target-products', 'name': 'Target · Pokémon Products',
            'retailer': 'Target', 'retailer_key': 'target', 'category': 'collectibles',
            'type': 'catalog', 'url': 'https://www.target.com/s?searchTerm=pokemon',
            'alternate_urls': ['https://www.target.com/backup'],
        }
        self.settings = {}
        self.state = {'items': {}}

    def result(self, count, status='ok'):
        return [], {'state': {'products': {}, 'initialized': True, 'source_url': self.source['url']},
                    'status': {'status': status, 'items_found': count, 'message': 'test'}}

    def test_primary_match_does_not_request_backup(self):
        calls=[]
        def scan(_session, source, _settings, _state):
            calls.append(source['url'])
            recovery._FETCH_DIAGNOSTICS.clear()
            return self.result(4)
        with patch.object(broad_source_patch, '_BASE_SCAN', side_effect=scan):
            _events, result = broad_source_patch.scan_source_primary_first(None, self.source, self.settings, self.state)
        self.assertEqual(calls, [self.source['url']])
        self.assertEqual(result['status']['items_found'], 4)
        self.assertFalse(result['status']['fallback_used'])
        self.assertEqual(result['status']['attempted_urls'], 1)

    def test_backup_is_requested_only_after_primary_has_no_matches(self):
        calls=[]
        def scan(_session, source, _settings, _state):
            calls.append(source['url'])
            recovery._FETCH_DIAGNOSTICS.clear()
            return self.result(0 if len(calls)==1 else 3, 'warning' if len(calls)==1 else 'ok')
        with patch.object(broad_source_patch, '_BASE_SCAN', side_effect=scan):
            _events, result = broad_source_patch.scan_source_primary_first(None, self.source, self.settings, self.state)
        self.assertEqual(calls, [self.source['url'], 'https://www.target.com/backup'])
        self.assertTrue(result['status']['fallback_used'])
        self.assertEqual(result['status']['items_found'], 3)

    def test_access_challenge_is_rejected_even_if_parser_returns_products(self):
        calls=[]
        def scan(_session, source, _settings, _state):
            calls.append(source['url'])
            if len(calls) == 1:
                recovery._FETCH_DIAGNOSTICS[:] = [{
                    'url': source['url'], 'title': 'Pardon Our Interruption', 'challenge': False,
                }]
                return [], {'state': {'products': {'fake': {} }}, 'status': {'items_found': 9, 'status': 'ok'}}
            recovery._FETCH_DIAGNOSTICS.clear()
            return [], {'state': {'products': {'real': {} }}, 'status': {'items_found': 3, 'status': 'ok'}}
        with patch.object(broad_source_patch, '_BASE_SCAN', side_effect=scan):
            _events, result = broad_source_patch.scan_source_primary_first(None, self.source, self.settings, self.state)
        self.assertEqual(calls, [self.source['url'], 'https://www.target.com/backup'])
        self.assertTrue(result['status']['fallback_used'])
        self.assertEqual(result['status']['items_found'], 3)

    def test_duplicate_backup_url_is_not_requested_twice(self):
        source=dict(self.source, alternate_urls=[self.source['url'], self.source['url']])
        self.assertEqual(broad_source_patch._candidates(source), [self.source['url']])

    def test_pokebeach_homepage_is_only_last_resort(self):
        source={'id':'pokebeach-news','url':'https://www.pokebeach.com/feed',
                'alternate_urls':['https://www.pokebeach.com/wp-json/wp/v2/posts'], 'type':'rss'}
        self.assertEqual(broad_source_patch._candidates(source), [
            'https://www.pokebeach.com/feed',
            'https://www.pokebeach.com/wp-json/wp/v2/posts',
            'https://www.pokebeach.com/',
        ])

    def test_every_source_is_scanned_without_a_rotation_scheduler(self):
        run=(ROOT/'monitor'/'run.py').read_text(encoding='utf-8')
        self.assertNotIn('select_routes_for_interval', run)
        self.assertNotIn('SCHEDULED', run)
        self.assertIn('for source in sources:', run)


if __name__ == '__main__':
    unittest.main()
