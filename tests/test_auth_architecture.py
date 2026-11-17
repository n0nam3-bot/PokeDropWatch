import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AuthArchitectureTests(unittest.TestCase):
    def test_admin_uses_password_auth_without_email_links(self):
        client = (ROOT / 'docs' / 'firebase-client.js').read_text(encoding='utf-8')
        admin = (ROOT / 'docs' / 'admin.js').read_text(encoding='utf-8')
        self.assertIn('signInWithEmailAndPassword', client)
        self.assertIn('api.signInWithEmailAndPassword', admin)
        self.assertNotIn('sendSignInLinkToEmail', client)
        self.assertNotIn('completeEmailLink', admin)

    def test_admin_label_helpers_are_defined_locally(self):
        admin = (ROOT / 'docs' / 'admin.js').read_text(encoding='utf-8')
        client = (ROOT / 'docs' / 'firebase-client.js').read_text(encoding='utf-8')
        self.assertIn('const categoryLabel =', admin)
        self.assertIn('const retailerLabel =', admin)
        self.assertNotIn('categoryLabel,', admin.split("from './firebase-client.js'")[0])
        self.assertNotIn('retailerLabel', client)

    def test_subscriptions_use_same_page_code_bridge(self):
        script = (ROOT / 'docs' / 'subscriptions.js').read_text(encoding='utf-8')
        app_config = (ROOT / 'docs' / 'subscription-backend-config.js').read_text(encoding='utf-8')
        self.assertIn("callBackend('requestCode'", script)
        self.assertIn("callBackend('verifyCode'", script)
        self.assertIn('subscriptionBackendUrl', app_config)
        self.assertNotIn('sendSignInLinkToEmail', script)

    def test_firestore_rules_restrict_subscriber_documents_to_admin(self):
        rules = (ROOT / 'firebase' / 'firestore.rules').read_text(encoding='utf-8')
        self.assertIn('allow read, write: if isAdmin();', rules)
        self.assertIn('replace-with-your-admin-email@example.com', rules)

    def test_apps_script_has_one_time_and_rate_limit_controls(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('OTP_TTL_SECONDS = 600', source)
        self.assertIn('OTP_MAX_ATTEMPTS = 5', source)
        self.assertIn('EMAIL_MAX_PER_HOUR = 3', source)
        self.assertIn('EMAIL_DAILY_CAP = 25', source)
        self.assertIn('MailApp.sendEmail', source)
        self.assertIn('firestorePatchSubscriber_', source)


if __name__ == '__main__':
    unittest.main()
