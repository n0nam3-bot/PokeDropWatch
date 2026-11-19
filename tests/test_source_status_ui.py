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


if __name__ == '__main__':
    unittest.main()
