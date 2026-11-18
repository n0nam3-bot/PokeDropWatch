import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SubscriptionPortalDirectTests(unittest.TestCase):
    def test_home_page_links_to_dedicated_notify_page_without_loading_portal(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('href="./notify.html"', page)
        self.assertNotIn('subscriptionPortalFrame', page)
        self.assertNotIn('exec?page=subscribe', page)

    def test_notify_page_embeds_direct_apps_script_portal_and_has_open_link(self):
        page = (ROOT / 'docs' / 'notify.html').read_text(encoding='utf-8')
        self.assertIn('id="notifyPortalFrame"', page)
        self.assertIn('exec?page=subscribe', page)
        self.assertIn('open Notify directly in a new tab', page)
        self.assertIn('aria-current="page"', page)

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

    def test_home_navigation_returns_to_the_document_top(self):
        index = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        admin = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        notify = (ROOT / 'docs' / 'notify.html').read_text(encoding='utf-8')
        self.assertIn('id="top"', index)
        self.assertIn('href="#top"', index)
        self.assertIn('href="./#top"', admin)
        self.assertIn('href="./#top"', notify)


if __name__ == '__main__':
    unittest.main()
