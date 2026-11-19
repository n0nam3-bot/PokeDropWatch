from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceStatusUITests(unittest.TestCase):
    def test_news_uses_existing_activity_feed_instead_of_a_new_section(self):
        page = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        news = (ROOT / "docs" / "news.js").read_text(encoding="utf-8")
        self.assertIn('data-filter="news"', page)
        self.assertIn('id="alertList"', page)
        self.assertIn('id="categoryFilter"', page)
        self.assertIn('value="news"', page)
        self.assertNotIn('id="pokemonNews"', page)
        self.assertNotIn('id="pokemonNewsList"', page)
        self.assertNotIn("./news.css", page)
        self.assertIn("$('alertList')", news)
        self.assertIn("type === 'news' || (type === 'all' && category === 'news')", news)

    def test_access_challenges_are_labelled_blocked_and_saved_counts_are_marked_stale(self):
        news = (ROOT / "docs" / "news.js").read_text(encoding="utf-8")
        self.assertIn("badge.textContent = 'BLOCKED'", news)
        self.assertIn("latest request failed", news)

    def test_retained_homepage_uses_the_compact_source_status_grid(self):
        page = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="sourceGrid"', page)
        self.assertNotIn("source-groups.js", page)
        self.assertNotIn("source-groups.css", page)

    def test_runner_has_no_rotation_scheduler_and_keeps_all_sources_active(self):
        run = (ROOT / "monitor" / "run.py").read_text(encoding="utf-8")
        self.assertNotIn("retailer_route_policy", run)
        self.assertNotIn("SCHEDULED", run)
        self.assertIn("for source in sources:", run)


if __name__ == "__main__":
    unittest.main()
