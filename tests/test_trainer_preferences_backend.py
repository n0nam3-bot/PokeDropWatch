import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = (ROOT / 'backend/apps-script/Code.gs').read_text(encoding='utf-8')
RUN = (ROOT / 'monitor/run.py').read_text(encoding='utf-8')

class TrainerPreferenceBackendTests(unittest.TestCase):
    def test_backend_accepts_only_the_four_trainer_notification_types(self):
        self.assertIn("const EVENT_TYPES = ['new_item', 'restock', 'price_drop', 'news'];", CODE)

    def test_verification_session_carries_type_and_item_filters(self):
        self.assertIn('eventTypes: input.eventTypes', CODE)
        self.assertIn('itemKeywords: input.itemKeywords', CODE)

    def test_firestore_record_saves_type_and_item_filters(self):
        self.assertIn('event_types: session.eventTypes || EVENT_TYPES', CODE)
        self.assertIn('item_keywords: session.itemKeywords || []', CODE)

    def test_notify_form_injection_contains_event_and_item_controls(self):
        self.assertIn('id="eventTypeChoices"', CODE)
        self.assertIn('Which product categories?', CODE)
        self.assertIn('name=\"category\" value=\"news\" checked', CODE)
        self.assertIn('id="itemKeywords"', CODE)
        self.assertIn('eventTypes, itemKeywords', CODE)
        self.assertIn('eventTypes: flow.eventTypes', CODE)
        self.assertIn('itemKeywords: flow.itemKeywords', CODE)

    def test_scoped_catalog_item_marker_survives_state_migration(self):
        self.assertIn('saved_item.get(\"pokemon_scoped\")', RUN)

    def test_verified_new_release_is_not_dropped_from_pending_owner_email_retry(self):
        self.assertIn('event.get(\"type\") != \"first_seen\"', RUN)

    def test_watchlist_is_limited_and_deduplicated(self):
        self.assertIn('raw.slice(0, 40)', CODE)
        self.assertIn('result.length >= 20', CODE)
        self.assertIn('.slice(0, 80)', CODE)

if __name__ == '__main__': unittest.main()
