from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SourceStatusUITests(unittest.TestCase):
    def test_partial_response_is_not_mislabeled_as_no_match(self):
        app = (ROOT / 'docs' / 'app.js').read_text(encoding='utf-8')
        self.assertIn("partial ? 'PARTIAL' : status === 'ok' ? 'MATCHES'", app)
        self.assertIn("const stateClass = partial || status === 'warning' ? 'warn'", app)
        self.assertIn('if (partial) description = `Partial results · ${Number(source.items_found || 0)} item(s) recognized · ${routeStatus}`', app)

    def test_overall_status_calls_them_source_warnings(self):
        app = (ROOT / 'docs' / 'app.js').read_text(encoding='utf-8')
        self.assertIn('source warnings · ${failures} request errors', app)
        self.assertNotIn('parser misses · ${failures}', app)

    def test_dashboard_groups_retailer_cards_without_merging_category_routes(self):
        index = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        grouped = (ROOT / 'docs' / 'source-groups.js').read_text(encoding='utf-8')
        self.assertIn('./source-groups.css', index)
        self.assertIn('./source-groups.js', index)
        self.assertIn('const groups = new Map()', grouped)
        self.assertIn('category routes', grouped)
        self.assertIn('1 monitoring route', grouped)
        self.assertIn("routeBadge.textContent = 'FALLBACK'", grouped)
        self.assertIn("routeBadge.textContent = 'COOLDOWN'", grouped)
        self.assertIn("routeBadge.textContent = 'BLOCKED'", grouped)
        self.assertIn("routeBadge.textContent = 'SCHEDULED'", grouped)
        self.assertIn('RETAILERS WITH MATCHES', index)
        self.assertIn('scheduled route returned current product or news matches', index)
        self.assertIn('SCHEDULED routes were not requested this interval', index)
        self.assertIn('./RETAILER_SCAN_HEALTH.html', index)
        guide = (ROOT / 'docs' / 'RETAILER_SCAN_HEALTH.html').read_text(encoding='utf-8')
        self.assertIn('20 category/search routes across 7 retailer and news groups', guide)
        self.assertIn('round-robin interval', guide)

    def test_dashboard_explains_last_known_records_and_retry_cooldown(self):
        index = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        monitor = (ROOT / 'monitor' / 'engine_retailer_group_patch.py').read_text(encoding='utf-8')
        self.assertIn('last-known and stale', index)
        self.assertIn('retailer_block_cooldown_minutes', monitor)
        self.assertIn('retailer_request_cooldown_minutes', monitor)
        self.assertIn('record_noun = "article"', monitor)
        runner = (ROOT / 'monitor' / 'run.py').read_text(encoding='utf-8')
        self.assertIn('select_routes_for_interval', runner)
        self.assertIn('scheduled_route_status', runner)


if __name__ == '__main__':
    unittest.main()
