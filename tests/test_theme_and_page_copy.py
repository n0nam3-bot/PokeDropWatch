import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ThemeAndPageCopyTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding='utf-8')

    def test_home_copy_and_hero_are_clean_pixel_art(self):
        page = self.read('docs/index.html')
        self.assertNotIn('No AI-generated picks', page)
        self.assertNotIn('Manage your email application, product categories', page)
        self.assertIn('PALLET TOWN', page)
        self.assertIn('hero-pixel-ball', page)
        self.assertIn('./assets/icons/pokeball-8bit.png', page)
        self.assertNotIn('emblem-ball', page)
        self.assertNotIn('AUTOMATED WATCH', page)

    def test_page_specific_header_icons_and_location_names(self):
        admin = self.read('docs/admin.html')
        notify = self.read('docs/notify.html')
        self.assertIn('masterball-8bit.png', admin)
        self.assertIn('GYM LEADER', admin)
        self.assertIn('ultraball-8bit.png', notify)
        self.assertIn('POKÉMON CENTER', notify)
        self.assertNotIn('AUTOMATED WATCH', admin + notify)

    def test_topbar_ball_moves_continuously_and_capture_animation_is_available(self):
        css = self.read('docs/theme-overrides.css')
        uniform = self.read('docs/site-uniform.css')
        self.assertIn('@keyframes pd-ball-idle', css)
        self.assertIn('animation: pd-ball-idle', css)
        self.assertIn('@keyframes pd-ball-capture', css)
        self.assertIn('image-rendering:pixelated', css)
        self.assertIn('@keyframes pd-page-ball-idle', uniform)

    def test_pointer_click_and_hold_throws_the_current_page_ball(self):
        js = self.read('docs/page-enhancements.js')
        css = self.read('docs/theme-overrides.css')
        self.assertIn("document.addEventListener('pointerdown'", js)
        self.assertIn("ball.className = 'pd-throw-ball'", js)
        self.assertIn('pd-ball-flight', css)
        self.assertIn('--pd-dx', js)
        self.assertIn('}, 1000);', js)
        self.assertIn('setInterval', js)

    def test_first_seen_note_is_removed_and_new_discoveries_use_a_pixel_sprite(self):
        js = self.read('docs/page-enhancements.js')
        css = self.read('docs/theme-overrides.css')
        self.assertIn('First observed by PokéDrop Watch', js)
        self.assertIn('span.remove()', js)
        self.assertIn("icon.src = './assets/icons/pokeball-8bit.png'", js)
        self.assertIn('capture-wiggle', js)

    def test_alert_images_have_separate_wide_columns_and_are_clickable(self):
        css = self.read('docs/site-uniform.css')
        js = self.read('docs/page-enhancements.js')
        self.assertIn('grid-template-columns: 108px minmax(0, 1fr) minmax(154px, 176px)', css)
        self.assertIn('width: 108px !important', css)
        self.assertIn("closest('.alert-product-image')", js)
        self.assertIn("querySelector('.view-link')", js)

    def test_notify_verification_panel_is_below_submit_button_and_copy_is_updated(self):
        page = self.read('backend/apps-script/Subscribe.html')
        self.assertLess(page.index('Email me a verification code'), page.index('id="verificationPanel"'))
        self.assertIn('Accepted the email request for ', page)
        self.assertNotIn('Google Apps Script accepted the email request', page)
        self.assertNotIn('HOW IT WORKS', page)
        self.assertNotIn('Leave this field empty', page)
        self.assertIn('.honeypot{position:absolute', page)
        self.assertIn('<h1>Receive Notifications</h1>', page)

    def test_admin_and_notify_have_how_it_works_link_instead_of_collapsible_guide(self):
        for name in ('Admin.html', 'Subscribe.html'):
            page = self.read('backend/apps-script/' + name)
            self.assertIn('pd-help-guide-link', page)
            self.assertIn('SOURCE_HEALTH.html', page)
            self.assertNotIn('<details', page)

    def test_apps_script_runtime_transform_keeps_full_portal_logic(self):
        source = self.read('backend/apps-script/Code.gs')
        self.assertIn('function pokedropPortalOutput_', source)
        self.assertIn('requestForm.insertAdjacentElement(\'afterend\', codePanel)', source)
        self.assertIn('function requestVerificationCode(payload)', source)
        self.assertIn('function adminLogin(payload)', source)

    def test_admin_and_notify_keep_the_shared_github_pages_shell(self):
        admin = self.read('docs/admin.html')
        notify = self.read('docs/notify.html')
        for page in (admin, notify):
            self.assertIn('class="bottom-bar"', page)
            self.assertIn('./#top', page)
            self.assertIn('page-enhancements.js', page)
            self.assertNotIn('window.location.replace', page)

    def test_source_health_is_a_permanent_how_it_works_guide(self):
        health = self.read('docs/SOURCE_HEALTH.html')
        for topic in ('What the source statuses mean', 'How a scan becomes an alert', 'What the alert filters mean', 'How email notifications work', 'How Gym Leader management works'):
            self.assertIn(topic, health)
        self.assertNotIn('Interpreting the scan reported on November 16, 2026', health)

    def test_service_worker_caches_current_pixel_assets_and_scripts(self):
        worker = self.read('docs/sw.js')
        self.assertIn('pokedrop-shell-v18', worker)
        self.assertIn('./site-uniform.css', worker)
        self.assertIn('./page-enhancements.js', worker)
        self.assertNotIn('./source-groups.js', worker)
        self.assertNotIn('./source-groups.css', worker)
        self.assertNotIn('pokeball-flight-8bit.png', worker)
        for filename in ('pokeball-8bit.png', 'ultraball-8bit.png', 'masterball-8bit.png'):
            self.assertIn(filename, worker)

    def test_all_three_pixel_sprites_exist_as_small_rgba_pngs(self):
        import struct
        signature = b'\x89PNG\r\n\x1a\n'
        for filename in ('pokeball-8bit.png', 'ultraball-8bit.png', 'masterball-8bit.png'):
            blob = (ROOT / 'docs' / 'assets' / 'icons' / filename).read_bytes()
            self.assertTrue(blob.startswith(signature), filename)
            self.assertGreaterEqual(len(blob), 26, filename)
            width, height = struct.unpack('>II', blob[16:24])
            bit_depth, color_type = blob[24], blob[25]
            self.assertEqual((width, height), (32, 32), filename)
            self.assertEqual(bit_depth, 8, filename)
            self.assertEqual(color_type, 6, filename)  # RGBA, checked without third-party Pillow.


if __name__ == '__main__':
    unittest.main()
