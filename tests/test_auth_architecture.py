import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AuthArchitectureTests(unittest.TestCase):
    def test_admin_uses_private_apps_script_password_auth_without_firebase_links(self):
        client = (ROOT / 'docs' / 'firebase-client.js').read_text(encoding='utf-8')
        admin = (ROOT / 'docs' / 'admin.js').read_text(encoding='utf-8')
        self.assertIn("callBackend('adminLogin'", admin)
        self.assertIn("callBackend('requestAdminPasswordReset'", admin)
        self.assertIn("callBackend('completeAdminPasswordReset'", admin)
        self.assertNotIn('signInWithEmailAndPassword', client + admin)
        self.assertNotIn('sendSignInLinkToEmail', client + admin)
        self.assertIn('firebaseReady = false', client)
        self.assertNotIn("from './firebase-client.js'", admin)

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
        self.assertNotIn('FIREBASE_SETUP.html', script)

    def test_firestore_rules_deny_all_browser_access(self):
        rules = (ROOT / 'firebase' / 'firestore.rules').read_text(encoding='utf-8')
        self.assertIn('allow read, write: if false;', rules)
        self.assertNotIn('replace-with-your-admin-email@example.com', rules)

    def test_admin_message_listener_is_registered_before_iframe_navigation(self):
        admin = (ROOT / 'docs' / 'admin.js').read_text(encoding='utf-8')
        self.assertLess(admin.index("window.addEventListener('message'"), admin.index('frame.src = subscriptionBackendUrl'))

    def test_subscription_message_listener_is_registered_before_iframe_navigation(self):
        script = (ROOT / 'docs' / 'subscriptions.js').read_text(encoding='utf-8')
        self.assertLess(script.index("window.addEventListener('message'"), script.index('frame.src = subscriptionBackendUrl'))

    def test_verification_and_reset_codes_keep_the_original_expiry(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('expiresAt: Date.now() + OTP_TTL_SECONDS * 1000', source)
        self.assertGreaterEqual(source.count('const remainingSeconds = Math.ceil((Number(session.expiresAt || 0) - Date.now()) / 1000);'), 2)
        self.assertIn('admin_reset_latest_', source)

    def test_old_public_firebase_setup_page_is_not_in_service_worker_shell(self):
        worker = (ROOT / 'docs' / 'sw.js').read_text(encoding='utf-8')
        self.assertIn('pokedrop-shell-v11', worker)
        self.assertIn("'./bridge-transport.js'", worker)
        self.assertNotIn("'./FIREBASE_SETUP.html'", worker)

    def test_standalone_admin_portal_is_routed_by_apps_script(self):
        source = (ROOT / 'backend' / 'apps-script' / 'doGet_REPLACEMENT.txt').read_text(encoding='utf-8')
        admin = (ROOT / 'backend' / 'apps-script' / 'Admin.html').read_text(encoding='utf-8')
        landing = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        self.assertIn("page === 'admin'", source)
        self.assertIn("createHtmlOutputFromFile('Admin')", source)
        self.assertIn('google.script.run', admin)
        self.assertIn('exec?page=admin', landing)

    def test_admin_stays_on_github_pages_and_embeds_apps_script(self):
        landing = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        source = (ROOT / 'backend' / 'apps-script' / 'doGet_REPLACEMENT.txt').read_text(encoding='utf-8')
        self.assertIn('<iframe', landing)
        self.assertIn('href="./"', landing)
        self.assertNotIn('window.location.replace', landing)
        self.assertNotIn('http-equiv="refresh"', landing)
        self.assertIn('setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)', source)

    def test_admin_uses_same_pokemon_font_as_public_site(self):
        source = (ROOT / 'backend' / 'apps-script' / 'doGet_REPLACEMENT.txt').read_text(encoding='utf-8')
        self.assertIn('assets/fonts/PKMN-RBYGSC.ttf', source)
        self.assertIn('font-family: "PKMN RBYGSC"', source)

    def test_new_items_filter_is_present_in_html_without_javascript_relabeling(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('data-filter="first_seen"', page)
        self.assertIn('>New items</button>', page)

    def test_apps_script_email_uses_notification_mailbox_display_name(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('EMAIL_FROM_NAME', source)
        self.assertIn('name: brand', source)
        self.assertIn('pokedropwatch.notify@gmail.com', source)

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
