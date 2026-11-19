import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "monitor"))

import engine_patch  # noqa: F401
import engine_recovery_patch
import source_diagnostics_patch


class SourceDiagnosticsPatchTests(unittest.TestCase):
    def test_gamestop_numeric_pdp_url_is_accepted_only_for_gamestop(self):
        actual = engine_recovery_patch._same_host_product_url(
            "/pokemon-tcg-elite-trainer-box/123456.html",
            "https://www.gamestop.com/search-new/?q=pokemon",
            "gamestop",
        )
        self.assertEqual(actual, "https://www.gamestop.com/pokemon-tcg-elite-trainer-box/123456.html")

        rejected = engine_recovery_patch._same_host_product_url(
            "/search-new/?q=pokemon&pid=123456",
            "https://www.gamestop.com/search-new/?q=pokemon",
            "gamestop",
        )
        self.assertEqual(rejected, "")

    def test_gamestop_data_pid_tile_is_collected_as_a_product(self):
        html = """<html><body>
        <div class="product-tile" data-pid="123456">
          <a href="/pokemon-tcg-elite-trainer-box/123456.html">
            <h3>Pokémon TCG Elite Trainer Box</h3>
            <img alt="Pokémon TCG Elite Trainer Box" src="https://images.example/box.jpg">
          </a><span>$49.99</span>
        </div></body></html>"""
        engine_patch._SCOPED_SCAN_ACTIVE = True
        try:
            products = engine_recovery_patch._extract_retailer_dom_products(
                BeautifulSoup(html, "html.parser"),
                "https://www.gamestop.com/search-new/?q=pokemon",
                "GameStop",
                20,
            )
        finally:
            engine_patch._SCOPED_SCAN_ACTIVE = False
        self.assertEqual(len(products), 1)
        self.assertIn("123456.html", products[0]["url"])
        self.assertEqual(products[0]["price"], 49.99)

    def test_pardon_our_interruption_is_detected_as_access_protection(self):
        diagnostic = engine_recovery_patch._response_diagnostic(
            "<html><head><title>Pardon Our Interruption</title></head><body>Access denied</body></html>",
            "https://www.pokemoncenter.com/category/back-in-stock",
        )
        self.assertTrue(diagnostic["challenge"])


if __name__ == "__main__":
    unittest.main()
