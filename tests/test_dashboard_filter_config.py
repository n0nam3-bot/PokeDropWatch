import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class DashboardFilterConfigTests(unittest.TestCase):
    def test_existing_site_filters_still_classify_products(self):
        app=(ROOT/'docs'/'app.js').read_text(encoding='utf-8')
        for category in ('tcg','plush','collectibles','games','accessories'):
            self.assertIn(category, app)

    def test_retailer_routes_are_compact_and_broad_where_supported(self):
        config=json.loads((ROOT/'config'/'sources.json').read_text(encoding='utf-8'))
        sources={s['id']:s for s in config['sources']}
        self.assertEqual(len(sources), 8)
        self.assertIn('searchTerm=pokemon', sources['target-tcg']['url'])
        self.assertNotIn('facetedValue=', sources['target-tcg']['url'])
        self.assertEqual(sources['walmart-tcg']['url'], 'https://www.walmart.com/search?q=pokemon')
        self.assertEqual(sources['amazon-pokemon-products']['url'], 'https://www.amazon.com/s?k=pokemon')
        self.assertEqual(sources['pokebeach-news']['alternate_urls'], ['https://www.pokebeach.com/wp-json/wp/v2/posts?per_page=30&_embed'])

    def test_only_unverified_broad_catalogs_keep_minimum_separate_categories(self):
        config=json.loads((ROOT/'config'/'sources.json').read_text(encoding='utf-8'))
        sources={s['id']:s for s in config['sources']}
        self.assertIn('pokemon-center-tcg', sources)
        self.assertIn('pokemon-center-plush', sources)
        self.assertEqual(sum(1 for s in sources.values() if s.get('retailer_key')=='pokemon-center'), 2)
        self.assertEqual(sum(1 for s in sources.values() if s.get('retailer_key')=='target'), 1)
        self.assertEqual(sum(1 for s in sources.values() if s.get('retailer_key')=='walmart'), 1)
        self.assertEqual(sum(1 for s in sources.values() if s.get('retailer_key')=='amazon'), 1)

if __name__=='__main__': unittest.main()
