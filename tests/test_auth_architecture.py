import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AuthArchitectureTests(unittest.TestCase):
    def test_admin_uses_private_apps_script_auth(self):
        admin = (ROOT / 'backend' / 'apps-script' / 'Admin.html').read_text(encoding='utf-8')
        code = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('google.script.run', admin)
        self.assertIn("case 'adminLogin': runner.adminLogin(payload)", admin)
        self.assertIn('function adminLogin(payload)', code)
        self.assertIn('function requestAdminPasswordReset(payload)', code)
        self.assertIn('function completeAdminPasswordReset(payload)', code)

    def test_subscribe_portal_uses_direct_server_calls(self):
        notify = (ROOT / 'backend' / 'apps-script' / 'Subscribe.html').read_text(encoding='utf-8')
        self.assertIn('runner.requestVerificationCode(payload)', notify)
        self.assertIn('runner.verifyVerificationCode(payload)', notify)
        self.assertNotIn('postMessage(', notify)

    def test_firestore_rules_remain_private(self):
        rules = (ROOT / 'firebase' / 'firestore.rules').read_text(encoding='utf-8')
        self.assertIn('allow read, write: if false;', rules)

    def test_complete_apps_script_routes_both_embedded_pages(self):
        code = (ROOT / 'backend' / 'apps-script' / 'Code.gs').read_text(encoding='utf-8')
        self.assertIn('function doGet(e)', code)
        self.assertIn("page === 'admin'", code)
        self.assertIn("page === 'subscribe' || page === 'notify'", code)
        self.assertIn("createHtmlOutputFromFile('Admin')", code)
        self.assertIn("createHtmlOutputFromFile('Subscribe')", code)
        self.assertIn('function pokedropPortalOutput_', code)
        self.assertIn('setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)', code)

    def test_service_worker_cache_is_bumped_for_current_shell(self):
        worker = (ROOT / 'docs' / 'sw.js').read_text(encoding='utf-8')
        self.assertIn('pokedrop-shell-v16', worker)
        self.assertIn("'./site-uniform.css'", worker)
        self.assertIn("'./assets/hero/pokeball-flight-8bit.png'", worker)


if __name__ == '__main__':
    unittest.main()
