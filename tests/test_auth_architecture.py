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

    def test_verification_and_reset_codes_keep_expiry_and_rate_limits(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('expiresAt: Date.now() + OTP_TTL_SECONDS * 1000', source)
        self.assertGreaterEqual(source.count('const remainingSeconds = Math.ceil((Number(session.expiresAt || 0) - Date.now()) / 1000);'), 2)
        self.assertIn('admin_reset_latest_', source)
        self.assertIn('EMAIL_MAX_PER_HOUR = 3', source)
        self.assertIn('EMAIL_DAILY_CAP = 25', source)
        self.assertIn('MailApp.sendEmail', source)

    def test_old_public_firebase_setup_page_is_not_in_service_worker_shell(self):
        worker = (ROOT / 'docs' / 'sw.js').read_text(encoding='utf-8')
        self.assertIn('pokedrop-shell-v15', worker)
        self.assertIn("'./bridge-transport.js'", worker)
        self.assertNotIn("'./FIREBASE_SETUP.html'", worker)

    def test_full_apps_script_code_routes_and_transforms_both_pages(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('function doGet(e)', source)
        self.assertIn("page === 'admin'", source)
        self.assertIn("page === 'subscribe' || page === 'notify'", source)
        self.assertIn("createHtmlOutputFromFile('Admin')", source)
        self.assertIn("createHtmlOutputFromFile('Subscribe')", source)
        self.assertIn('function pokedropPortalOutput_', source)
        self.assertIn('setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)', source)
        self.assertIn('function requestVerificationCode(payload)', source)
        self.assertIn('function adminLogin(payload)', source)
        self.assertIn('function firestoreAccessToken_()', source)

    def test_admin_stays_on_github_pages_and_embeds_apps_script(self):
        landing = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('<iframe', landing)
        self.assertIn('href="./#top"', landing)
        self.assertNotIn('window.location.replace', landing)
        self.assertNotIn('http-equiv="refresh"', landing)
        self.assertIn('setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)', source)

    def test_admin_page_specific_shell_is_consistent(self):
        landing = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        self.assertIn('<small>GYM LEADER</small>', landing)
        self.assertIn('masterball-8bit.png', landing)
        self.assertNotIn('AUTOMATED WATCH', landing)
        self.assertIn('class="bottom-bar"', landing)
        for href in ('./#top', './#alerts', './notify.html', './admin.html', 'https://github.com/n0nam3-bot/PokeDropWatch'):
            self.assertIn(href, landing)
        self.assertIn('aria-current="page"', landing)

    def test_apps_script_removes_admin_hint_and_duplicates_at_render_time(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn("html.replace(/<header class=\"top\">[\\s\\S]*?<\\/header>/i, '')", source)
        self.assertIn('Use the administrator credentials configured in Apps Script.', source)
        self.assertIn('Administrator sessions expire after one hour.', source)
        self.assertIn('How administrator tools work', source)
        self.assertIn('How notifications work', source)

    def test_apps_script_email_uses_notification_mailbox_display_name(self):
        source = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('EMAIL_FROM_NAME', source)
        self.assertIn('name: brand', source)
        self.assertIn('pokedropwatch.notify@gmail.com', source)


if __name__ == '__main__':
    unittest.main()
