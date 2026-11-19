import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "monitor"))
import engine_patch  # noqa: F401
import engine_recovery_patch  # noqa: F401
import trainer_preferences_patch  # noqa: F401
import baseline_patch  # noqa: F401
import news_source_patch
import engine


FEED_URL = "https://news.google.com/rss/search?q=pokemon"


def feed(*items):
    return "<?xml version='1.0'?><rss version='2.0'><channel><title>Pokémon News</title>" + "".join(items) + "</channel></rss>"


def article(guid, title, url, published):
    return f"<item><title>{title}</title><link>{url}</link><guid>{guid}</guid><pubDate>{published}</pubDate><description>Summary</description></item>"


class NewsArchiveTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "id": "pokemon-news-google", "name": "Pokémon News", "retailer": "Pokémon News",
            "type": "rss", "url": FEED_URL, "category": "news", "retailer_key": "pokemon-news",
            "alternate_urls": [],
        }

    def scan(self, body, state):
        with patch.object(engine, "fetch", return_value=(body, FEED_URL)):
            return news_source_patch.scan_source_with_article_archive(
                object(), self.source, {"request_timeout_seconds": 1}, state,
            )

    def test_articles_disappearing_from_current_feed_remain_in_archive(self):
        first = feed(
            article("one", "Older Pokémon story", "https://news.example/one", "Tue, 17 Nov 2026 10:00:00 GMT"),
            article("two", "Recent Pokémon story", "https://news.example/two", "Wed, 18 Nov 2026 10:00:00 GMT"),
        )
        _events, initial = self.scan(first, {"items": {}})
        state = {"items": {self.source["id"]: initial["state"]}}
        second = feed(article("two", "Recent Pokémon story", "https://news.example/two", "Wed, 18 Nov 2026 10:00:00 GMT"))
        _events, updated = self.scan(second, state)
        self.assertEqual(len(updated["state"]["articles"]), 2)
        self.assertEqual(updated["status"]["items_found"], 1)
        self.assertEqual(updated["status"]["archive_count"], 2)

    def test_seen_index_urls_are_recovered_into_the_archive(self):
        previous = {
            "initialized": True,
            "source_url": FEED_URL,
            "seen": {
                "old-story": {
                    "title": "Earlier Pokémon news",
                    "url": "https://news.example/earlier",
                    "first_seen": "2026-10-01T10:00:00Z",
                }
            },
            "articles": [],
        }
        body = feed(article("current", "Current Pokémon story", "https://news.example/current", "Thu, 19 Nov 2026 10:00:00 GMT"))
        _events, result = self.scan(body, {"items": {self.source["id"]: previous}})
        self.assertEqual({a["url"] for a in result["state"]["articles"]}, {
            "https://news.example/earlier", "https://news.example/current"
        })


if __name__ == "__main__":
    unittest.main()
