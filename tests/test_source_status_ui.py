from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceStatusUITests(unittest.TestCase):
    def test_homepage_has_no_rotation_or_scheduled_route_explanations(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        for phrase in ('SCHEDULED routes', 'rotate one per retailer', 'COOLDOWN means'):
            self.assertNotIn(phrase, page)
        self.assertNotIn('Retailer checks run every 15 minutes', page)

    def test_homepage_uses_dedicated_news_section_and_official_media_link(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="pokemonNews"', page)
        self.assertIn('id="pokemonNewsList"', page)
        self.assertIn('https://press.pokemon.com/en#?itemtype=3,9&editorial=&filetype=', page)
        self.assertIn('./news.js', page)

    def test_retained_homepage_uses_the_compact_source_status_grid(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        app = (ROOT / 'docs' / 'app.js').read_text(encoding='utf-8')
        self.assertIn('id="sourceGrid"', page)
        self.assertIn('function renderSources', app)
        self.assertNotIn('source-groups.js', page)
        self.assertNotIn('source-groups.css', page)

    def test_runner_has_no_rotation_scheduler_and_keeps_all_sources_active(self):
        run = (ROOT / 'monitor' / 'run.py').read_text(encoding='utf-8')
        self.assertNotIn('retailer_route_policy', run)
        self.assertNotIn('SCHEDULED', run)
        self.assertIn('for source in sources:', run)


if __name__ == '__main__':
    unittest.main()
