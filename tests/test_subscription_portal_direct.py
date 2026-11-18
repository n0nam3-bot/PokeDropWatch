import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SubscriptionPortalDirectTests(unittest.TestCase):
    def test_notify_remains_inside_github_pages_shell(self):
        page = (ROOT / 'docs' / 'notify.html').read_text(encoding='utf-8')
        self.assertIn('<iframe', page)
        self.assertIn('exec?page=subscribe', page)
        self.assertIn('class="bottom-bar"', page)
        self.assertNotIn('window.location.replace', page)

    def test_admin_remains_inside_github_pages_shell(self):
        page = (ROOT / 'docs' / 'admin.html').read_text(encoding='utf-8')
        self.assertIn('<iframe', page)
        self.assertIn('exec?page=admin', page)
        self.assertIn('class="bottom-bar"', page)
        self.assertNotIn('window.location.replace', page)
        self.assertIn('GYM LEADER', page)
        self.assertIn('masterball-8bit.png', page)

    def test_notify_form_calls_apps_script_server_functions_directly(self):
        page = (ROOT / 'backend' / 'apps-script' / 'Subscribe.html').read_text(encoding='utf-8')
        self.assertIn('google.script.run', page)
        self.assertIn('runner.requestVerificationCode(payload)', page)
        self.assertIn('runner.verifyVerificationCode(payload)', page)
        self.assertNotIn('postMessage(', page)

    def test_notify_form_has_short_intro_compact_options_and_dynamic_code_panel(self):
        page = (ROOT / 'backend' / 'apps-script' / 'Subscribe.html').read_text(encoding='utf-8')
        self.assertIn('<h1>Receive Notifications</h1>', page)
        self.assertIn('A one-time code is sent to your mailbox', page)
        self.assertIn("requestForm.insertAdjacentElement('afterend', codePanel)", page)
        self.assertIn('Accepted the email request for ', page)
        self.assertNotIn('Ready. Enter your email address', page)
        self.assertNotIn('VERIFIED TRAINER ALERTS', page)
        self.assertNotIn('HOW IT WORKS', page)

    def test_admin_uses_gym_leader_wording(self):
        page = (ROOT / 'backend' / 'apps-script' / 'Admin.html').read_text(encoding='utf-8')
        self.assertIn('Gym Management', page)
        self.assertIn('Gym Leader sign in', page)
        self.assertIn('Gym Leader email', page)
        self.assertNotIn('Use the administrator credentials configured in Apps Script.', page)


if __name__ == '__main__':
    unittest.main()
