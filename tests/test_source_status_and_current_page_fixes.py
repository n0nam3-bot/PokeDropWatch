import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SourceStatusAndPageFixesTests(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_admin_has_only_one_visible_gym_management_heading(self):
        page = self.read("backend/apps-script/Admin.html")
        self.assertIn("<h1>Gym Management</h1>", page)
        self.assertNotIn("<span class=\"tag\">GYM MANAGEMENT</span>", page)

    def test_notify_uses_matching_pallet_town_background_and_green_intro(self):
        page = self.read("backend/apps-script/Subscribe.html")
        self.assertIn("Receive Notifications</h1>", page)
        self.assertIn("linear-gradient(135deg,#f5f0df 0%,#f4f7ea 60%,#f8f7f0 100%)", page)
        self.assertIn("linear-gradient(120deg,#1f573b,#387747)", page)
        self.assertIn("A one-time code is sent to your mailbox, and your application is saved only after you verify it.", page)

    def test_home_location_changes_in_both_scroll_directions_even_with_hash_present(self):
        js = self.read("docs/page-enhancements.js")
        self.assertIn("window.scrollY >= threshold ? 'POKÉDEX' : 'PALLET TOWN'", js)
        self.assertNotIn("location.hash === '#alerts' ||", js)
        self.assertIn("window.addEventListener('scroll', schedule", js)

    def test_source_guide_explains_mixed_match_parser_miss_and_request_error_counts(self):
        guide = self.read("docs/SOURCE_HEALTH.html")
        self.assertIn("3 source matches · 5 parser misses · 2 request errors", guide)
        self.assertIn("not a guarantee they are in stock", guide)

    def test_source_guide_explains_gym_leader_review_states_and_session_security(self):
        guide = self.read("docs/SOURCE_HEALTH.html")
        for phrase in (
            "How Gym Leader management works", "Pending", "Active", "Suspended",
            "Rejected", "Removed", "Sessions and security", "one hour",
            "Firestore", "Password reset"
        ):
            self.assertIn(phrase, guide)

    def test_service_worker_drops_the_generated_scene_and_bumps_cache(self):
        worker = self.read("docs/sw.js")
        self.assertIn("pokedrop-shell-v17", worker)
        self.assertNotIn("pokeball-flight-8bit.png", worker)
        self.assertIn("./assets/icons/pokeball-8bit.png", worker)

    def test_monitor_schedule_is_documented_as_quarter_hourly(self):
        workflow = (ROOT / ".github" / "workflows" / "pokedrop-watch.yml")
        if workflow.exists():
            text = workflow.read_text(encoding="utf-8")
            self.assertIn("cron: '*/15 * * * *'", text)
        guide = self.read("docs/SOURCE_HEALTH.html")
        self.assertIn("every 15 minutes", guide)


if __name__ == "__main__":
    unittest.main()
