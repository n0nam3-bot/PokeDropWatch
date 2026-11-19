import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "monitor"))

import engine
import engine_patch
import engine_recovery_patch

# Import the production extension but restore global monkey-patches immediately;
# each test invokes the extension directly so existing engine tests stay isolated.
_original_engine_hooks = {
    "scan_source": engine.scan_source,
    "fetch": engine.fetch,
    "extract_retailer_products": engine.extract_retailer_products,
    "extract_json_products": engine.extract_json_products,
}
_original_recovery_hooks = {
    "title_allowed": engine_recovery_patch._pokemon_title_allowed,
    "product_url": engine_recovery_patch._same_host_product_url,
}
import engine_retailer_group_patch as route_patch
engine.scan_source = _original_engine_hooks["scan_source"]
engine.fetch = _original_engine_hooks["fetch"]
engine.extract_retailer_products = _original_engine_hooks["extract_retailer_products"]
engine.extract_json_products = _original_engine_hooks["extract_json_products"]
engine_recovery_patch._pokemon_title_allowed = _original_recovery_hooks["title_allowed"]
engine_recovery_patch._same_host_product_url = _original_recovery_hooks["product_url"]


class ConditionalRetailerRouteTests(unittest.TestCase):
    def setUp(self):
        route_patch._FETCH_CACHE.clear()

    def _response(self, url, title="Search", challenge=False):
        return {
            "url": url,
            "bytes": 12000,
            "title": title,
            "product_links": 4,
            "json_scripts": 1,
            "challenge": challenge,
        }

    def _fake_result(self, url, count=0, products=None):
        return [], {
            "state": {
                "source_url": url,
                "products": products or {},
                "last_item_count": count,
                "initialized": True,
            },
            "status": {
                "status": "ok" if count else "warning",
                "items_found": count,
                "successful_urls": 1,
                "configured_urls": 1,
                "message": "test scan",
            },
        }

    def test_challenge_uses_fallback_and_marks_result_recovered(self):
        calls = []
        source = {
            "id": "target-tcg", "name": "Target TCG", "retailer": "Target",
            "retailer_key": "target", "category": "tcg", "type": "catalog",
            "url": "https://www.target.com/primary", "alternate_urls": ["https://www.target.com/alternate"],
        }

        def fake_scan(_session, attempt_source, _settings, _state):
            engine_recovery_patch._FETCH_DIAGNOSTICS.clear()
            url = attempt_source["url"]
            calls.append(url)
            if url.endswith("primary"):
                engine_recovery_patch._FETCH_DIAGNOSTICS.append(self._response(url, "Pardon Our Interruption", True))
                return self._fake_result(url)
            engine_recovery_patch._FETCH_DIAGNOSTICS.append(self._response(url, "Target search"))
            return self._fake_result(url, 2, {"item-a": {"title": "Pokémon TCG item A"}, "item-b": {"title": "Pokémon TCG item B"}})

        with patch.object(route_patch, "_BASE_SCAN", side_effect=fake_scan):
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                _events, result = route_patch.scan_source_with_conditional_routes(object(), source, {}, {"items": {}})

        self.assertEqual(calls, [source["url"], source["alternate_urls"][0]])
        self.assertEqual(result["status"]["status"], "warning")
        self.assertEqual(result["status"]["current_items_found"], 2)
        self.assertEqual(result["status"]["blocked_urls"], 1)
        self.assertEqual(result["status"]["successful_urls"], 1)
        self.assertTrue(result["status"]["fallback_used"])
        self.assertIn("Recovered 2 current listing", result["status"]["message"])
        self.assertEqual(result["state"]["source_url"], source["url"])

    def test_primary_with_matches_does_not_request_alternates(self):
        calls = []
        source = {
            "id": "walmart-plush", "retailer": "Walmart", "type": "catalog",
            "url": "https://www.walmart.com/primary",
            "alternate_urls": ["https://www.walmart.com/alternate-one", "https://www.walmart.com/alternate-two"],
        }

        def fake_scan(_session, attempt_source, _settings, _state):
            url = attempt_source["url"]
            calls.append(url)
            engine_recovery_patch._FETCH_DIAGNOSTICS.append(self._response(url))
            return self._fake_result(url, 1, {"item": {"title": "Pokémon plush"}})

        with patch.object(route_patch, "_BASE_SCAN", side_effect=fake_scan):
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                _events, result = route_patch.scan_source_with_conditional_routes(object(), source, {}, {"items": {}})

        self.assertEqual(calls, [source["url"]])
        self.assertEqual(result["status"]["status"], "ok")
        self.assertEqual(result["status"]["attempted_urls"], 1)
        self.assertEqual(result["status"]["available_urls"], 3)
        self.assertEqual(result["status"]["fallbacks_used"], 0)

    def test_empty_primary_uses_alternate_and_reports_recovered_listings(self):
        calls = []
        source = {
            "id": "pokemon-center-plush", "retailer": "Pokémon Center", "type": "catalog",
            "url": "https://www.pokemoncenter.com/primary",
            "alternate_urls": ["https://www.pokemoncenter.com/alternate"],
        }

        def fake_scan(_session, attempt_source, _settings, _state):
            engine_recovery_patch._FETCH_DIAGNOSTICS.clear()
            url = attempt_source["url"]
            calls.append(url)
            engine_recovery_patch._FETCH_DIAGNOSTICS.append(self._response(url))
            if url.endswith("primary"):
                return self._fake_result(url)
            return self._fake_result(url, 1, {"item": {"title": "Pokémon plush"}})

        with patch.object(route_patch, "_BASE_SCAN", side_effect=fake_scan):
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                _events, result = route_patch.scan_source_with_conditional_routes(
                    object(), source, {}, {"items": {}},
                )

        self.assertEqual(calls, [source["url"], source["alternate_urls"][0]])
        self.assertTrue(result["status"]["fallback_used"])
        self.assertEqual(result["status"]["current_items_found"], 1)
        self.assertIn("fallback route", result["status"]["message"])

    def test_blocked_routes_keep_last_known_products_separate_from_current_count(self):
        source = {
            "id": "walmart-tcg", "retailer": "Walmart", "type": "catalog",
            "url": "https://www.walmart.com/primary",
            "alternate_urls": ["https://www.walmart.com/alternate"],
        }
        prior_products = {f"item-{index}": {"title": f"Pokémon item {index}"} for index in range(3)}
        prior = {"source_url": source["url"], "initialized": True, "last_item_count": 3, "products": prior_products}

        def fake_scan(_session, attempt_source, _settings, _state):
            url = attempt_source["url"]
            engine_recovery_patch._FETCH_DIAGNOSTICS.append(self._response(url, "Robot or human?", True))
            return self._fake_result(url, 0, copy.deepcopy(prior_products))

        with patch.object(route_patch, "_BASE_SCAN", side_effect=fake_scan):
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                _events, result = route_patch.scan_source_with_conditional_routes(
                    object(), source, {}, {"items": {source["id"]: prior}},
                )

        self.assertEqual(result["status"]["current_items_found"], 0)
        self.assertEqual(result["status"]["last_known_items"], 3)
        self.assertEqual(result["state"]["last_item_count"], 3)
        self.assertIn("No current listings were confirmed", result["status"]["message"])

    def test_blocked_retailer_pauses_other_category_routes_during_shared_cooldown(self):
        state = {"items": {}}
        source_tcg = {
            "id": "target-tcg", "name": "Target · TCG", "retailer": "Target",
            "retailer_key": "target", "category": "tcg", "type": "catalog",
            "url": "https://www.target.com/tcg", "alternate_urls": ["https://www.target.com/tcg-alt"],
        }

        def blocked_scan(_session, attempt_source, _settings, _state):
            engine_recovery_patch._FETCH_DIAGNOSTICS.clear()
            engine_recovery_patch._FETCH_DIAGNOSTICS.append(
                self._response(attempt_source["url"], "Access Denied", True)
            )
            return self._fake_result(attempt_source["url"])

        with patch.object(route_patch, "_BASE_SCAN", side_effect=blocked_scan):
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                _events, first_result = route_patch.scan_source_with_conditional_routes(
                    object(), source_tcg, {}, state,
                )

        self.assertEqual(first_result["status"]["blocked_urls"], 2)
        self.assertIn("target", state.get("retailer_health", {}))

        source_plush = {
            "id": "target-plush", "name": "Target · Plush", "retailer": "Target",
            "retailer_key": "target", "category": "plush", "type": "catalog",
            "url": "https://www.target.com/plush", "alternate_urls": ["https://www.target.com/plush-alt"],
        }
        state.setdefault("items", {})["target-plush"] = {
            "source_url": source_plush["url"], "last_item_count": 2,
            "products": {"a": {"title": "Pokémon plush one"}, "b": {"title": "Pokémon plush two"}},
        }
        with patch.object(route_patch, "_BASE_SCAN") as unused_scan:
            _events, skipped = route_patch.scan_source_with_conditional_routes(
                object(), source_plush, {}, state,
            )
        unused_scan.assert_not_called()
        self.assertTrue(skipped["status"]["skipped_due_retailer_cooldown"])
        self.assertEqual(skipped["status"]["attempted_urls"], 0)
        self.assertEqual(skipped["status"]["last_known_items"], 2)
        self.assertIn("no retailer request was made", skipped["status"]["message"].lower())

    def test_request_failures_set_a_short_shared_retailer_cooldown(self):
        source = {
            "id": "best-buy-pokemon-tcg", "retailer": "Best Buy", "retailer_key": "best-buy",
            "type": "catalog", "url": "https://www.bestbuy.com/primary",
            "alternate_urls": ["https://www.bestbuy.com/alternate"],
        }
        state = {"items": {}}

        with patch.object(route_patch, "_BASE_SCAN", side_effect=requests.Timeout("timed out")):
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                with self.assertRaises(requests.RequestException):
                    route_patch.scan_source_with_conditional_routes(object(), source, {}, state)

        self.assertEqual(state["retailer_health"]["best-buy"]["kind"], "request-failure")
        self.assertTrue(state["retailer_health"]["best-buy"]["cooldown_until"])

    def test_parser_exception_after_http_response_is_not_a_request_failure(self):
        source = {
            "id": "pokebeach-news", "name": "PokéBeach News", "retailer": "PokéBeach",
            "retailer_key": "pokebeach", "category": "news", "type": "rss",
            "url": "https://www.pokebeach.com/feed",
            "alternate_urls": ["https://www.pokebeach.com/wp-json/wp/v2/posts"],
            "notes": "The feed currently returns a wp_die error.",
        }

        def fake_scan(_session, attempt_source, _settings, _state):
            engine_recovery_patch._FETCH_DIAGNOSTICS.append(self._response(attempt_source["url"], "PokéBeach"))
            if attempt_source["url"].endswith("/feed"):
                raise ValueError("The feed endpoint returned wp_die XML")
            return [], {
                "state": {
                    "seen": {"a": {"title": "Pokémon news A"}, "b": {"title": "Pokémon news B"}},
                    "last_item_count": 2,
                    "initialized": True,
                },
                "status": {"status": "ok", "items_found": 2, "successful_urls": 1, "configured_urls": 1},
            }

        with patch.object(route_patch, "_BASE_SCAN", side_effect=fake_scan):
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                _events, result = route_patch.scan_source_with_conditional_routes(
                    object(), source, {}, {"items": {}},
                )

        self.assertTrue(result["status"]["fallback_used"])
        self.assertEqual(result["status"]["successful_urls"], 2)
        self.assertEqual(result["status"]["failed_urls"], 0)
        self.assertIn("Recognized 2 current article(s)", result["status"]["message"])

    def test_all_parser_misses_after_http_responses_are_no_match_not_issue(self):
        source = {
            "id": "pokebeach-news", "name": "PokéBeach News", "retailer": "PokéBeach",
            "retailer_key": "pokebeach", "category": "news", "type": "rss",
            "url": "https://www.pokebeach.com/feed",
            "alternate_urls": ["https://www.pokebeach.com/wp-json/wp/v2/posts"],
            "notes": "The feed currently returns a wp_die error.",
        }

        def fake_scan(_session, attempt_source, _settings, _state):
            engine_recovery_patch._FETCH_DIAGNOSTICS.append(self._response(attempt_source["url"], "PokéBeach"))
            raise ValueError("The returned page content could not be parsed")

        state = {"items": {}}
        with patch.object(route_patch, "_BASE_SCAN", side_effect=fake_scan):
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                _events, result = route_patch.scan_source_with_conditional_routes(
                    object(), source, {}, state,
                )

        self.assertEqual(result["status"]["status"], "warning")
        self.assertEqual(result["status"]["successful_urls"], 3)
        self.assertEqual(result["status"]["failed_urls"], 0)
        self.assertIn("parser recognized no current", result["status"]["message"].lower())
        self.assertNotIn("pokebeach", state.get("retailer_health", {}))

    def test_pokebeach_homepage_is_explicit_last_fallback(self):
        source = {
            "id": "pokebeach-news", "type": "rss", "url": "https://www.pokebeach.com/feed",
            "alternate_urls": ["https://www.pokebeach.com/wp-json/wp/v2/posts"],
            "notes": "The feed currently returns a wp_die error.",
        }
        self.assertEqual(route_patch._candidate_urls(source), [
            "https://www.pokebeach.com/feed",
            "https://www.pokebeach.com/wp-json/wp/v2/posts",
            "https://www.pokebeach.com/",
        ])

    def test_generic_navigation_titles_are_rejected_even_on_scoped_pages(self):
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            self.assertFalse(route_patch._strict_title_allowed("Currently Refined by Category: Trading Card Games"))
            self.assertFalse(route_patch._strict_title_allowed("Trading Card Games"))
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False

    def test_walmart_tracking_path_is_not_a_product_url(self):
        self.assertEqual(
            route_patch._strict_product_url("https://www.walmart.com/sp/track", "https://www.walmart.com/search?q=pokemon", "walmart"),
            "",
        )

    def test_route_rotation_selects_one_route_per_retailer_and_advances_each_interval(self):
        sources = [
            {"id": "pc-tcg", "retailer_key": "pokemon-center"},
            {"id": "pc-plush", "retailer_key": "pokemon-center"},
            {"id": "pc-new", "retailer_key": "pokemon-center"},
            {"id": "target-tcg", "retailer_key": "target"},
            {"id": "target-plush", "retailer_key": "target"},
            {"id": "gamestop-tcg", "retailer_key": "gamestop"},
        ]
        state = {}
        settings = {"retailer_routes_per_scan": 1}
        first = route_patch.select_routes_for_interval(sources, state, settings)
        second = route_patch.select_routes_for_interval(sources, state, settings)
        third = route_patch.select_routes_for_interval(sources, state, settings)
        fourth = route_patch.select_routes_for_interval(sources, state, settings)
        fifth = route_patch.select_routes_for_interval(sources, state, settings)

        self.assertEqual(first, {"pc-tcg", "target-tcg", "gamestop-tcg"})
        self.assertEqual(second, {"pc-plush", "target-plush", "gamestop-tcg"})
        self.assertEqual(third, {"pc-new", "target-tcg", "gamestop-tcg"})
        self.assertEqual(fourth, {"pc-tcg", "target-plush", "gamestop-tcg"})
        self.assertEqual(fifth, {"pc-plush", "target-tcg", "gamestop-tcg"})

    def test_scheduled_route_status_preserves_last_check_and_last_known_data(self):
        source = {
            "id": "target-plush", "name": "Target · Plush", "retailer": "Target",
            "retailer_key": "target", "category": "plush", "type": "catalog",
            "url": "https://www.target.com/plush",
        }
        last_checked = "2026-11-18T22:00:00Z"
        state = {"items": {"target-plush": {
            "last_attempt": last_checked, "last_item_count": 2,
            "products": {"one": {"title": "Pokémon plush one"}, "two": {"title": "Pokémon plush two"}},
        }}}
        status = route_patch.scheduled_route_status(source, state)
        self.assertEqual(status["status"], "skipped")
        self.assertTrue(status["skipped_by_rotation"])
        self.assertEqual(status["last_checked"], last_checked)
        self.assertEqual(status["last_known_items"], 2)
        self.assertEqual(status["attempted_urls"], 0)
        self.assertIn("no retailer request was made", status["message"].lower())

    def test_identical_urls_are_fetched_once_per_process(self):
        body = "<html><head><title>Retailer search</title></head><body>Pokémon</body></html>"
        with patch.object(route_patch, "_BASE_FETCH", return_value=(body, "https://www.example.com/search")) as fetch:
            with patch.object(engine_recovery_patch, "_FETCH_DIAGNOSTICS", []):
                route_patch._cached_fetch(object(), "https://www.example.com/search", 20)
                route_patch._cached_fetch(object(), "https://www.example.com/search", 20)
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
