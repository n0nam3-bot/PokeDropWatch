import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SubscriptionPortalDirectTests(unittest.TestCase):
    def test_public_page_embeds_subscribe_route_and_not_hidden_message_bridge(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="subscriptionPortalFrame"', page)
        self.assertIn('exec?page=subscribe', page)
        self.assertNotIn('subscriptionBackendFrame', page)
        self.assertNotIn('src="./subscriptions.js"', page)

    def test_subscribe_page_calls_apps_script_server_functions_directly(self):
        page = (ROOT / 'backend' / 'apps-script' / 'Subscribe.html').read_text(encoding='utf-8')
        self.assertIn('google.script.run', page)
        self.assertIn('runner.requestVerificationCode(payload)', page)
        self.assertIn('runner.verifyVerificationCode(payload)', page)
        self.assertNotIn('postMessage(', page)
        self.assertNotIn("addEventListener('message'", page)

    def test_do_get_routes_to_admin_and_subscribe_pages(self):
        source = (ROOT / 'backend' / 'apps-script' / 'doGet_REPLACEMENT.txt').read_text(encoding='utf-8')
        self.assertIn("page === 'admin'", source)
        self.assertIn("page === 'subscribe'", source)
        self.assertIn("createHtmlOutputFromFile('Subscribe')", source)
        self.assertIn("createHtmlOutputFromFile('Admin')", source)
        self.assertIn('setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)', source)

    def test_admin_inner_brand_and_footer_are_removed(self):
        page = (ROOT / 'backend' / 'apps-script' / 'Admin.html').read_text(encoding='utf-8')
        self.assertNotIn('<header class="top">', page)
        self.assertNotIn('PokéDrop Watch · Administrator sessions expire after one hour.', page)
        self.assertIn('width:min(100% - 40px,1120px)', page)

    def test_item_filter_has_all_six_requested_retailers(self):
        source = (ROOT / 'docs' / 'app.js').read_text(encoding='utf-8')
        for value, label in (
            ('amazon', 'Amazon'), ('walmart', 'Walmart'), ('best-buy', 'Best Buy'),
            ('target', 'Target'), ('pokemon-center', 'Pokémon Center'), ('gamestop', 'GameStop')
        ):
            self.assertIn(f"new Option('{label}', '{value}')", source)


if __name__ == '__main__':
    unittest.main()
