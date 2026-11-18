import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VerificationBridgeRegressionTests(unittest.TestCase):
    def test_bridge_transport_does_not_relabel_first_seen_as_new_items(self):
        source = (ROOT / 'docs' / 'bridge-transport.js').read_text(encoding='utf-8')
        self.assertNotIn("newItemsFilter.textContent = 'New items'", source)
        self.assertIn('event.stopImmediatePropagation()', source)

    def test_alert_filter_setup_keeps_distinct_new_item_and_first_seen_filters(self):
        source = (ROOT / 'docs' / 'app.js').read_text(encoding='utf-8')
        self.assertIn("newItems.dataset.filter = 'new_item'", source)
        self.assertIn("firstSeen.dataset.filter = 'first_seen'", source)
        self.assertIn("firstSeen.textContent = 'First seen'", source)

    def test_apps_script_checks_origin_and_replies_to_requester(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Index.html').read_text(encoding='utf-8')
        self.assertIn('if (event.origin !== ALLOWED_ORIGIN) return;', source)
        self.assertIn('callerWindow.postMessage(message, targetOrigin)', source)
        self.assertNotIn('event.source !== window.parent', source)

    def test_apps_script_uses_explicit_remote_function_calls(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Index.html').read_text(encoding='utf-8')
        for method in ('requestVerificationCode', 'verifyVerificationCode', 'adminLogin', 'adminListSubscribers'):
            self.assertIn(f'runner.{method}(payload)', source)

    def test_subscription_timeout_does_not_claim_email_was_sent(self):
        source = (ROOT / 'docs' / 'subscriptions.js').read_text(encoding='utf-8')
        self.assertIn('No email delivery was confirmed', source)
        self.assertIn('Update the Apps Script Index.html', source)


if __name__ == '__main__':
    unittest.main()
