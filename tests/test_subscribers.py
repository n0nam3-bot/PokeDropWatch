import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'monitor'))
from subscribers import delivery_batch_id, dispatch_subscriber_notifications, event_matches_preferences


class Snapshot:
    def __init__(self, data=None, reference=None):
        self._data = data or {}
        self.reference = reference
        self.exists = data is not None
    def to_dict(self): return dict(self._data)

class DeliveryReference:
    def __init__(self, store, key): self.store, self.key = store, key
    def get(self): return Snapshot(self.store.get(self.key))
    def set(self, data): self.store[self.key] = dict(data)
    def update(self, data): self.store[self.key].update(data)

class DeliveryQuery:
    def __init__(self, store, field, value): self.store, self.field, self.value = store, field, value
    def stream(self):
        return [Snapshot(data, DeliveryReference(self.store, key)) for key, data in list(self.store.items()) if data.get(self.field) == self.value]

class DeliveryCollection:
    def __init__(self, store): self.store = store
    def document(self, key): return DeliveryReference(self.store, key)
    def where(self, field, operator, value): return DeliveryQuery(self.store, field, value)

class SubscriberReference:
    def __init__(self): self.deliveries = {}
    def collection(self, name):
        assert name == 'deliveries'
        return DeliveryCollection(self.deliveries)

class SubscriberSnapshot:
    def __init__(self, data): self.data, self.reference = data, SubscriberReference()
    def to_dict(self): return dict(self.data)

class SubscriberQuery:
    def __init__(self, subscribers): self.subscribers = subscribers
    def stream(self): return self.subscribers

class SubscriberCollection:
    def __init__(self, subscribers): self.subscribers = subscribers
    def where(self, field, operator, value):
        if field == 'status' and operator == '==': return SubscriberQuery([s for s in self.subscribers if s.data.get(field) == value])
        raise AssertionError('Unexpected query')

class FakeDB:
    def __init__(self, subscribers): self.subscribers = subscribers
    def collection(self, name):
        assert name == 'subscribers'
        return SubscriberCollection(self.subscribers)


class SubscriberTests(unittest.TestCase):
    def test_category_and_retailer_preferences_match(self):
        event = {'category': 'tcg', 'retailer_key': 'pokemon-center', 'type': 'restock', 'title': 'Pokémon TCG box'}
        self.assertTrue(event_matches_preferences(event, {'categories': ['tcg'], 'retailers': ['pokemon-center']}))
        self.assertFalse(event_matches_preferences(event, {'categories': ['plush'], 'retailers': ['all']}))
        self.assertFalse(event_matches_preferences(event, {'categories': ['tcg'], 'retailers': ['target']}))
        self.assertTrue(event_matches_preferences(event, {'categories': ['tcg'], 'retailers': ['all']}))

    def test_delivery_batch_id_is_order_independent(self):
        self.assertEqual(delivery_batch_id([{'id': 'one'}, {'id': 'two'}]), delivery_batch_id([{'id': 'two'}, {'id': 'one'}]))

    def test_active_subscriber_receives_individual_digest_and_delivery_is_marked_sent(self):
        subscriber = SubscriberSnapshot({'email': 'trainer@example.com', 'status': 'active', 'categories': ['tcg'], 'retailers': ['pokemon-center'], 'event_types': ['restock'], 'item_keywords': []})
        db, sent_to = FakeDB([subscriber]), []
        def fake_send(events, env, prefix, recipient=None, manage_url=''):
            sent_to.append((recipient, [event['id'] for event in events], manage_url)); return True, 'sent'
        event = {'id': 'event-1', 'type': 'restock', 'category': 'tcg', 'retailer_key': 'pokemon-center', 'title': 'Pokémon TCG box'}
        result = dispatch_subscriber_notifications([event], {'SMTP_USERNAME': 'sender@example.com', 'SMTP_APP_PASSWORD': 'not-a-real-password', 'PUBLIC_SITE_URL': 'https://example.github.io/watch'}, db=db, send_func=fake_send)
        self.assertIn('1 digest(s) sent', result)
        self.assertEqual(sent_to[0][0], 'trainer@example.com')
        self.assertEqual(sent_to[0][1], ['event-1'])
        self.assertTrue(sent_to[0][2].endswith('/notify.html'))
        self.assertEqual(next(iter(subscriber.reference.deliveries.values()))['status'], 'sent')

    def test_missing_service_account_reports_setup_requirement(self):
        self.assertIn('FIREBASE_SERVICE_ACCOUNT_JSON', dispatch_subscriber_notifications([], {}))

    def test_accessories_category_matches_subscriber_preference(self):
        self.assertTrue(event_matches_preferences({'type': 'news', 'category': 'accessories', 'retailer_key': 'target'}, {'categories': ['accessories'], 'retailers': ['all']}))

    def test_event_type_preference_excludes_unselected_restocks(self):
        event = {'type': 'restock', 'category': 'tcg', 'retailer_key': 'target', 'title': 'Pokémon ETB'}
        self.assertFalse(event_matches_preferences(event, {'event_types': ['new_item'], 'categories': ['tcg'], 'retailers': ['all']}))
        self.assertTrue(event_matches_preferences({**event, 'type': 'new_item'}, {'event_types': ['new_item'], 'categories': ['tcg'], 'retailers': ['all']}))


    def test_news_event_type_is_independent_of_product_category_choices(self):
        subscriber = {'event_types': ['news'], 'categories': ['tcg'], 'retailers': ['all']}
        event = {'type': 'news', 'category': 'news', 'retailer_key': 'pokebeach', 'title': 'Pokémon TCG announcement'}
        self.assertTrue(event_matches_preferences(event, subscriber))

    def test_legacy_subscriber_defaults_to_all_four_trainer_event_types(self):
        base = {'categories': ['tcg'], 'retailers': ['all']}
        for kind in ('new_item', 'restock', 'price_drop', 'news'):
            self.assertTrue(event_matches_preferences({'type': kind, 'category': 'tcg', 'retailer_key': 'target'}, base))
        self.assertFalse(event_matches_preferences({'type': 'price_change', 'category': 'tcg', 'retailer_key': 'target'}, base))

    def test_item_keyword_watchlist_uses_or_matching_and_normalized_phrases(self):
        sub = {'event_types': ['restock'], 'categories': ['tcg'], 'retailers': ['all'], 'item_keywords': ['Prismatic Evolutions ETB', 'Pikachu Plush']}
        self.assertTrue(event_matches_preferences({'type': 'restock', 'category': 'tcg', 'retailer_key': 'target', 'title': 'Pokemon TCG Prismatic-Evolutions ETB'}, sub))
        self.assertTrue(event_matches_preferences({'type': 'restock', 'category': 'tcg', 'retailer_key': 'target', 'title': 'New Pikachu 18 inch Plush Doll'}, sub))
        self.assertFalse(event_matches_preferences({'type': 'restock', 'category': 'tcg', 'retailer_key': 'target', 'title': 'Charizard Collection Box'}, sub))

    def test_keyword_list_can_be_entered_as_delimited_string(self):
        sub = {'event_types': ['news'], 'categories': ['news'], 'retailers': ['all'], 'item_keywords': 'Team Rocket; Mega Evolution\nPrismatic Evolutions'}
        self.assertTrue(event_matches_preferences({'type': 'news', 'category': 'news', 'retailer_key': 'pokebeach', 'title': 'Mega Evolution set announced'}, sub))
        self.assertFalse(event_matches_preferences({'type': 'news', 'category': 'news', 'retailer_key': 'pokebeach', 'title': 'New Pokémon cards revealed'}, sub))


if __name__ == '__main__': unittest.main()
