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

    def test_subscriptions_use_a_top_level_apps_script_portal_from_notify_page(self):
        home = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        notify = (ROOT / 'docs' / 'notify.html').read_text(encoding='utf-8')
        portal = (ROOT / 'backend' / 'apps-script' / 'Subscribe.html').read_text(encoding='utf-8')
        self.assertIn('href="./notify.html"', home)
        self.assertNotIn('<iframe', notify)
        self.assertIn('window.location.replace(portalUrl)', notify)
        self.assertIn('exec?page=subscribe', notify)
        self.assertIn('google.script.run', portal)
        self.assertIn('runner.requestVerificationCode(payload)', portal)
        self.assertIn('runner.verifyVerificationCode(payload)', portal)
        self.assertNotIn('postMessage(', portal)

    def test_firestore_rules_deny_all_browser_access(self):
        rules = (ROOT / 'firebase' / 'firestore.rules').read_text(encoding='utf-8')
        self.assertIn('allow read, write: if false;', rules)
        self.assertNotIn('replace-with-your-admin-email@example.com', rules)

    def test_public_subscription_form_no_longer_loads_any_hidden_or_embedded_bridge(self):
        home = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        notify = (ROOT / 'docs' / 'notify.html').read_text(encoding='utf-8')
        self.assertNotIn('subscriptionBackendFrame', home)
        self.assertNotIn('subscriptionPortalFrame', home)
        self.assertNotIn('src="./subscriptions.js"', home)
        self.assertNotIn('<iframe', notify)
        self.assertIn('window.location.replace(portalUrl)', notify)

    def test_verification_and_reset_codes_keep_the_original_expiry(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('expiresAt: Date.now() + OTP_TTL_SECONDS * 1000', source)
        self.assertGreaterEqual(source.count('const remainingSeconds = Math.ceil((Number(session.expiresAt || 0) - Date.now()) / 1000);'), 2)
        self.assertIn('admin_reset_latest_', source)

    def test_service_worker_cache_version_is_bumped_for_portal_navigation_change(self):
        worker = (ROOT / 'docs' / 'sw.js').read_text(encoding='utf-8')
        self.assertIn('pokedrop-shell-v12', worker)
        self.assertIn("'./bridge-transport.js'", worker)
        self.assertNotIn("'./FIREBASE_SETUP.html'", worker)

    def test_admin_portal_is_routed_and_opened_as_a_top_level_page(self):
        source = (ROOT / 'backend' / 'apps-script' / 'doGet_REPLACEMENT.txt').read_text(encoding='utf-8')
        landing = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        self.assertIn("page === 'admin'", source)
        self.assertIn("pokedropPortalOutput_('Admin'", source)
        self.assertIn('exec?page=admin', landing)
        self.assertIn('window.location.replace(portalUrl)', landing)
        self.assertNotIn('<iframe', landing)
        self.assertIn('google.script.run', (ROOT / 'backend' / 'apps-script' / 'Admin.html').read_text(encoding='utf-8'))

    def test_admin_shell_opens_apps_script_instead_of_embedding_it(self):
        landing = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        self.assertNotIn('<iframe', landing)
        self.assertIn('href="https://script.google.com/macros/s/', landing)
        self.assertIn('window.location.replace(portalUrl)', landing)
        self.assertIn('href="./#top"', landing)
        self.assertIn('href="./#alerts"', landing)

    def test_admin_uses_same_pokemon_font_as_public_site(self):
        source = (ROOT / 'backend' / 'apps-script' / 'doGet_REPLACEMENT.txt').read_text(encoding='utf-8')
        self.assertIn('assets/fonts/PKMN-RBYGSC.ttf', source)
        self.assertIn('font-family: "PKMN RBYGSC"', source)

    def test_new_items_filter_is_present_in_html_without_javascript_relabeling(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('data-filter="first_seen"', page)
        self.assertIn('>New items</button>', page)

    def test_portal_navigation_matches_the_public_site_and_has_one_brand_header(self):
        source = (ROOT / 'backend' / 'apps-script' / 'doGet_REPLACEMENT.txt').read_text(encoding='utf-8')
        admin = (ROOT / 'backend' / 'apps-script' / 'Admin.html').read_text(encoding='utf-8')
        for label in ('PokéDrop', 'WATCH', 'AUTOMATED WATCH', 'Home', 'Alerts', 'Notify', 'Admin', 'GitHub'):
            self.assertIn(label, source)
        self.assertIn('class="pd-site-topbar"', source)
        self.assertIn('class="pd-bottom-bar"', source)
        self.assertNotIn('<header class="top">', admin)
        self.assertNotIn('PokéDrop Watch · Administrator sessions expire after one hour.', admin)

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
