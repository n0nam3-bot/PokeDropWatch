import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONITOR = ROOT / "monitor"
sys.path.insert(0, str(MONITOR))

import engine
import engine_patch  # noqa: F401
import engine_recovery_patch  # noqa: F401
import source_diagnostics_patch  # noqa: F401
import retailer_payload_patch  # noqa: F401
from bs4 import BeautifulSoup


class RetailerPayloadPatchTests(unittest.TestCase):
    def test_gamestop_json_uses_case_and_underscore_insensitive_product_fields(self):
        body = '''<html><head><title>Search Results | GameStop</title></head><body>
        <script type="application/json">{"items":[{"product_name":"Pokémon TCG Mega Expansion Box",
        "productURL":"/pokemon-tcg/mega-expansion/20012345.html",
        "currentPrice":{"value":"49.99"},"imageURL":"https://images.example/item.jpg",
        "productId":"20012345"}]}</script></body></html>'''
        soup = BeautifulSoup(body, "html.parser")
        products = engine.extract_retailer_products(
            soup,
            "https://www.gamestop.com/search-new/?q=pokemon",
            "GameStop",
            50,
        )
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["title"], "Pokémon TCG Mega Expansion Box")
        self.assertEqual(products[0]["url"], "https://www.gamestop.com/pokemon-tcg/mega-expansion/20012345.html")
        self.assertEqual(products[0]["price"], 49.99)
        self.assertEqual(products[0]["image"], "https://images.example/item.jpg")


if __name__ == "__main__":
    unittest.main()
