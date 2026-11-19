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
    return """<?xml version='1.0' encoding='UTF-8'?>
    <rss version='2.0'><channel><title>Pokémon News</title>""" + "".join(items) + "</channel></rss>"


def article(guid, title, url, published, publisher, summary="Summary text"):
    return f"""<item><title>{title}</title><link>{url}</link><guid>{guid}</guid>
    <pubDate>{published}</pubDate><description>{summary}</description>
    <source>{publisher}</source></item>"""


class NewsSourcePatchTests(unittest.TestCase):
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

    def test_first_scan_saves_articles_for_homepage_without_sending_news_alerts(self):
        body = feed(article("one", "Pokémon TCG set revealed", "https://news.example/story-one", "Wed, 18 Nov 2026 10:00:00 GMT", "News Example", "Details about the set."))
        events, result = self.scan(body, {"items": {}})
        self.assertEqual(events, [])
        articles = result["state"]["articles"]
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["publisher"], "News Example")
        self.assertIn("Details about the set", articles[0]["summary"])
        self.assertEqual(result["status"]["status"], "ok")

    def test_new_article_after_baseline_creates_a_news_event(self):
        first = feed(article("one", "Pokémon TCG set revealed", "https://news.example/story-one", "Wed, 18 Nov 2026 10:00:00 GMT", "News Example"))
        _events, first_result = self.scan(first, {"items": {}})
        state = {"items": {self.source["id"]: first_result["state"]}}
        second = feed(
            article("two", "Pokémon Center restock announced", "https://news.example/story-two", "Thu, 19 Nov 2026 10:00:00 GMT", "Another Publisher"),
            article("one", "Pokémon TCG set revealed", "https://news.example/story-one", "Wed, 18 Nov 2026 10:00:00 GMT", "News Example"),
        )
        events, result = self.scan(second, state)
        self.assertEqual([event["type"] for event in events], ["news"])
        self.assertEqual(events[0]["title"], "Pokémon Center restock announced")
        self.assertEqual(events[0]["retailer"], "Another Publisher")
        self.assertEqual(len(result["state"]["articles"]), 2)

    def test_changed_feed_url_establishes_a_quiet_new_baseline(self):
        previous = {
            "source_url": "https://news.example/old-feed", "initialized": True,
            "seen": {"old": {"title": "Old", "url": "https://news.example/old"}},
        }
        body = feed(article("new", "New Pokémon news", "https://news.example/new", "Thu, 19 Nov 2026 10:00:00 GMT", "News Example"))
        events, result = self.scan(body, {"items": {self.source["id"]: previous}})
        self.assertEqual(events, [])
        self.assertEqual(len(result["state"]["articles"]), 1)

    def test_html_challenge_is_not_marked_as_a_successful_empty_feed(self):
        with patch.object(engine, "fetch", return_value=("<html><title>Access Denied</title></html>", FEED_URL)):
            with self.assertRaisesRegex(Exception, "All configured news feed URLs failed"):
                news_source_patch.scan_source_with_article_archive(
                    object(), self.source, {"request_timeout_seconds": 1}, {"items": {}},
                )


if __name__ == "__main__":
    unittest.main()
