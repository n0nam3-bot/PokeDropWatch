import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UiConsistencyV2Tests(unittest.TestCase):
    def test_shared_font_and_navigation_geometry_are_enforced(self):
        css = (ROOT / 'docs' / 'site-uniform.css').read_text(encoding='utf-8')
        self.assertIn('font-family: var(--pd-font) !important', css)
        self.assertIn('--pd-topbar-height: 78px', css)
        self.assertIn('--pd-bottom-height: 72px', css)
        self.assertIn('grid-template-columns: repeat(5, minmax(0, 1fr))', css)

    def test_desktop_product_image_text_and_price_use_separate_tracks(self):
        css = (ROOT / 'docs' / 'site-uniform.css').read_text(encoding='utf-8')
        self.assertIn('grid-template-columns: 108px minmax(0, 1fr) minmax(154px, 176px)', css)
        self.assertIn('white-space: nowrap !important', css)
        self.assertIn('overflow: visible !important', css)

    def test_product_images_open_the_matching_view_item_url(self):
        source = (ROOT / 'docs' / 'page-enhancements.js').read_text(encoding='utf-8')
        self.assertIn("closest('.alert-product-image')", source)
        self.assertIn("querySelector('.view-link')", source)
        self.assertIn("window.open(link.href, '_blank', 'noopener,noreferrer')", source)

    def test_hold_for_one_second_activates_rapid_fire_until_release(self):
        source = (ROOT / 'docs' / 'page-enhancements.js').read_text(encoding='utf-8')
        self.assertIn('}, 1000);', source)
        self.assertIn('setInterval', source)
        self.assertIn('pointerup', source)
        self.assertIn('pointercancel', source)
        self.assertIn('clearInterval(press.repeatTimer)', source)

    def test_home_hero_uses_the_original_single_eight_bit_pokeball(self):
        page = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
        source = (ROOT / 'docs' / 'page-enhancements.js').read_text(encoding='utf-8')
        css = (ROOT / 'docs' / 'site-uniform.css').read_text(encoding='utf-8')
        self.assertIn('src="./assets/icons/pokeball-8bit.png"', page)
        self.assertNotIn('pokeball-flight-8bit.png', source + css)
        self.assertIn('@keyframes pd-hero-ball-idle', css)
        self.assertIn('image-rendering: pixelated', css)

    def test_notify_is_condensed_and_uses_the_single_receive_notifications_intro(self):
        page = (ROOT / 'backend' / 'apps-script' / 'Subscribe.html').read_text(encoding='utf-8')
        self.assertIn('<h1>Receive Notifications</h1>', page)
        self.assertNotIn('VERIFIED TRAINER ALERTS', page)
        self.assertNotIn('Ready. Enter your email address', page)
        self.assertIn('repeat(4,minmax(0,1fr))', page)
        self.assertIn('Accepted the email request for ', page)
        self.assertNotIn('<aside', page)

    def test_admin_uses_gym_leader_copy_and_no_setup_hint(self):
        page = (ROOT / 'backend' / 'apps-script' / 'Admin.html').read_text(encoding='utf-8')
        self.assertIn('<h1>Gym Management</h1>', page)
        self.assertNotIn('<span class="tag">GYM MANAGEMENT</span>', page)
        self.assertIn('<h2>Gym Leader sign in</h2>', page)
        self.assertIn('manage Pokémon Center notifications or subscriptions', page)
        self.assertNotIn('Use the administrator credentials configured in Apps Script.', page)
        self.assertNotIn('Subscriber administration', page)

    def test_notification_and_gym_pages_link_to_the_shared_guide_not_collapsible_panels(self):
        for path in ('backend/apps-script/Admin.html', 'backend/apps-script/Subscribe.html'):
            page = (ROOT / path).read_text(encoding='utf-8')
            self.assertIn('pd-help-guide-link', page)
            self.assertIn('SOURCE_HEALTH.html', page)
            self.assertNotIn('<details', page)

    def test_outer_page_script_standardizes_footer_and_source_health_navigation(self):
        source = (ROOT / 'docs' / 'page-enhancements.js').read_text(encoding='utf-8')
        self.assertIn('Fan-made tracker · Not affiliated with Pokémon or retailers · ', source)
        self.assertIn('View the source repository ↗', source)
        self.assertIn("if (isInfo && !document.querySelector('.bottom-bar'))", source)
        self.assertIn('How it works ↗', source)


if __name__ == '__main__':
    unittest.main()
