from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SourceStatusUITests(unittest.TestCase):
    def test_homepage_copy_does_not_explain_rotations_or_scheduled_stale_routes(self):
        page=(ROOT/'docs'/'index.html').read_text(encoding='utf-8')
        for phrase in ('SCHEDULED routes','rotate one per retailer','COOLDOWN means'):
            self.assertNotIn(phrase,page)
        self.assertIn('Retailer checks run every 15 minutes',page)

    def test_retailers_are_grouped_with_compact_route_status(self):
        js=(ROOT/'docs'/'source-groups.js').read_text(encoding='utf-8')
        self.assertIn('source-retailer-card',js)
        self.assertIn("'FALLBACK'",js)
        self.assertIn("'BLOCKED'",js)
        self.assertNotIn('SCHEDULED',js)
        self.assertNotIn('last-known record(s) retained',js)

    def test_rotation_is_not_part_of_the_scan_runner(self):
        run=(ROOT/'monitor'/'run.py').read_text(encoding='utf-8')
        self.assertNotIn('retailer_route_policy',run)
        self.assertNotIn('SCHEDULED',run)
        self.assertIn('for source in sources:',run)

if __name__=='__main__': unittest.main()
