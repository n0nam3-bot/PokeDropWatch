import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'monitor'))

import engine
import engine_patch  # noqa: F401
import engine_recovery_patch  # noqa: F401
import trainer_preferences_patch  # noqa: F401


class TrainerPreferencesPatchTests(unittest.TestCase):
    def test_verified_release_event_is_email_eligible_but_first_seen_is_not(self):
        self.assertTrue(engine.is_email_eligible_event({'type': 'new_item'}))
        self.assertFalse(engine.is_email_eligible_event({'type': 'first_seen'}))
        self.assertTrue(engine.is_email_eligible_event({'type': 'restock'}))
        self.assertTrue(engine.is_email_eligible_event({'type': 'price_drop'}))
        self.assertTrue(engine.is_email_eligible_event({'type': 'news'}))

    def test_scoped_catalog_events_are_valid_without_pokemon_in_the_short_title(self):
        event = engine.event_record(
            'restock',
            {'title': 'Elite Trainer Box', 'category': 'tcg', 'url': 'https://www.pokemoncenter.com/product/example'},
            {'id': 'pokemon-center-tcg', 'name': 'Pokémon Center TCG', 'retailer': 'Pokémon Center', 'category': 'tcg', 'pokemon_scoped': True},
        )
        self.assertTrue(event.get('pokemon_scoped'))
        self.assertTrue(engine.is_valid_event(event))


    def test_verified_release_alert_has_a_new_release_email_label(self):
        _subject, html_body, text_body = engine.html_email([
            {'type': 'new_item', 'title': 'Pokémon Prismatic Evolutions ETB', 'url': 'https://example.com/item', 'retailer': 'Target'},
        ])
        self.assertIn('NEW RELEASE', html_body)
        self.assertIn('NEW RELEASE', text_body)

    def test_non_scoped_non_pokemon_product_event_is_still_rejected(self):
        event = {'type': 'restock', 'category': 'collectibles', 'title': 'Generic Toy Product'}
        self.assertFalse(engine.is_valid_event(event))


if __name__ == '__main__':
    unittest.main()
