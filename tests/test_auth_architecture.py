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

    def test_subscriptions_use_direct_apps_script_portal_on_notify_page(self):
        home = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        notify = (ROOT / 'docs' / 'notify.html').read_text(encoding='utf-8')
        portal = (ROOT / 'backend' / 'apps-script' / 'Subscribe.html').read_text(encoding='utf-8')
        self.assertIn('href="./notify.html"', home)
        self.assertIn('exec?page=subscribe', notify)
        self.assertNotIn('subscriptionBackendFrame', home + notify)
        self.assertIn('google.script.run', portal)
        self.assertIn('runner.requestVerificationCode(payload)', portal)
        self.assertIn('runner.verifyVerificationCode(payload)', portal)
        self.assertNotIn('postMessage(', portal)

    def test_firestore_rules_deny_all_browser_access(self):
        rules = (ROOT / 'firebase' / 'firestore.rules').read_text(encoding='utf-8')
        self.assertIn('allow read, write: if false;', rules)
        self.assertNotIn('replace-with-your-admin-email@example.com', rules)

    def test_admin_message_listener_is_registered_before_iframe_navigation(self):
        admin = (ROOT / 'docs' / 'admin.js').read_text(encoding='utf-8')
        self.assertLess(admin.index("window.addEventListener('message'"), admin.index('frame.src = subscriptionBackendUrl'))

    def test_public_subscription_form_is_on_dedicated_notify_page(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('subscriptionBackendFrame', page)
        self.assertNotIn('src="./subscriptions.js"', page)
        self.assertIn('href="./notify.html"', page)

    def test_verification_and_reset_codes_keep_the_original_expiry(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('expiresAt: Date.now() + OTP_TTL_SECONDS * 1000', source)
        self.assertGreaterEqual(source.count('const remainingSeconds = Math.ceil((Number(session.expiresAt || 0) - Date.now()) / 1000);'), 2)
        self.assertIn('admin_reset_latest_', source)

    def test_old_public_firebase_setup_page_is_not_in_service_worker_shell(self):
        worker = (ROOT / 'docs' / 'sw.js').read_text(encoding='utf-8')
        self.assertIn('pokedrop-shell-v13', worker)
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
        self.assertIn('href="./#top"', landing)
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

    def test_admin_shell_matches_public_site_navigation(self):
        landing = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        self.assertIn('<small>WATCH</small>', landing)
        self.assertIn('AUTOMATED WATCH', landing)
        self.assertIn('class="bottom-bar"', landing)
        for href in ('./#top', './#alerts', './notify.html', './admin.html', 'https://github.com/n0nam3-bot/PokeDropWatch'):
            self.assertIn(href, landing)
        self.assertIn('aria-current="page"', landing)

    def test_embedded_admin_removes_duplicate_site_branding(self):
        source = (ROOT / 'backend' / 'apps-script' / 'doGet_REPLACEMENT.txt').read_text(encoding='utf-8')
        admin = (ROOT / 'backend' / 'apps-script' / 'Admin.html').read_text(encoding='utf-8')
        self.assertIn("page === 'admin'", source)
        self.assertIn("pokedropEmbeddedOutput_(HtmlService.createHtmlOutputFromFile('Admin')", source)
        self.assertNotIn('<header class="top">', admin)
        self.assertNotIn('PokéDrop Watch · Administrator sessions expire after one hour.', admin)
        self.assertIn('Administrator sessions expire after one hour.', admin)

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
