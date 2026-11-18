import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ThemeAndPageCopyTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding='utf-8')

    def test_home_hides_removed_hero_and_notify_copy(self):
        page = self.read('docs/index.html')
        self.assertNotIn('No AI-generated picks', page)
        self.assertNotIn('Manage your email application, product categories', page)
        self.assertIn('PALLET TOWN', page)
        self.assertNotIn('AUTOMATED WATCH', page)

    def test_page_specific_header_balls_and_location_names(self):
        admin = self.read('docs/admin.html')
        notify = self.read('docs/notify.html')
        self.assertIn('masterball-8bit.svg', admin)
        self.assertIn('GYM LEADER', admin)
        self.assertIn('ultraball-8bit.svg', notify)
        self.assertIn('POKÉMON CENTER', notify)
        self.assertNotIn('AUTOMATED WATCH', admin + notify)

    def test_capture_sprite_is_pixelated_and_animates_first_seen_cards(self):
        css = self.read('docs/theme-overrides.css')
        js = self.read('docs/page-enhancements.js')
        self.assertIn('@keyframes capture-wiggle', css)
        self.assertIn('image-rendering:pixelated', css)
        self.assertIn('className = \'capture-ball\'', js)
        self.assertIn('pokeball-8bit.svg', js)

    def test_alert_card_removes_long_first_seen_note_and_keeps_price_unbroken(self):
        js = self.read('docs/page-enhancements.js')
        css = self.read('docs/theme-overrides.css')
        self.assertIn('First observed by PokéDrop Watch', js)
        self.assertIn('span.remove()', js)
        self.assertIn('white-space:nowrap', css)
        self.assertIn('font-variant-numeric:tabular-nums', css)

    def test_notify_verification_panel_is_below_request_button_and_copy_is_updated(self):
        page = self.read('backend/apps-script/Subscribe.html')
        self.assertLess(page.index('Email me a verification code'), page.index('id="verificationPanel"'))
        self.assertIn('Accepted the email request for ', page)
        self.assertNotIn('Google Apps Script accepted the email request', page)
        self.assertNotIn('HOW IT WORKS', page)
        self.assertNotIn('Leave this field empty', page)
        self.assertIn('.honeypot{position:absolute', page)

    def test_notify_no_longer_has_the_old_explanatory_aside(self):
        page = self.read('backend/apps-script/Subscribe.html')
        self.assertNotIn('<aside', page)
        self.assertNotIn('This panel communicates with Apps Script itself', page)

    def test_admin_login_hint_is_removed_by_apps_script_output_transform(self):
        source = self.read('backend/apps-script/doGet_REPLACEMENT.txt')
        self.assertIn("html.replace(\n    'Use the administrator credentials configured in Apps Script.'", source)
        self.assertIn('masterball-8bit.svg', source)
        self.assertIn('ultraball-8bit.svg', self.read('backend/apps-script/Subscribe.html'))

    def test_admin_and_notify_have_collapsible_guides_and_source_health_explains_pipeline(self):
        admin = self.read('docs/admin.html')
        notify = self.read('docs/notify.html')
        health = self.read('docs/SOURCE_HEALTH.html')
        self.assertIn('How administrator tools work', admin)
        self.assertIn('How email notifications work', notify)
        for topic in ('How a scan becomes an alert', 'What source status means', 'Restocks', 'Price drops'):
            self.assertIn(topic, health)
        self.assertNotIn('Interpreting the scan reported on November 16, 2026', health)

    def test_service_worker_caches_new_theme_assets(self):
        worker = self.read('docs/sw.js')
        self.assertIn('pokedrop-shell-v14', worker)
        self.assertIn('./theme-overrides.css', worker)
        self.assertIn('./page-enhancements.js', worker)
        for filename in ('pokeball-8bit.svg', 'ultraball-8bit.svg', 'masterball-8bit.svg'):
            self.assertIn(filename, worker)


if __name__ == '__main__':
    unittest.main()
