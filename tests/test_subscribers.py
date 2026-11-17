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

    def to_dict(self):
        return dict(self._data)


class DeliveryReference:
    def __init__(self, store, key):
        self.store = store
        self.key = key

    def get(self):
        return Snapshot(self.store.get(self.key))

    def set(self, data):
        self.store[self.key] = dict(data)

    def update(self, data):
        self.store[self.key].update(data)


class DeliveryQuery:
    def __init__(self, store, field, value):
        self.store = store
        self.field = field
        self.value = value

    def stream(self):
        return [
            Snapshot(data, DeliveryReference(self.store, key))
            for key, data in list(self.store.items())
            if data.get(self.field) == self.value
        ]


class DeliveryCollection:
    def __init__(self, store):
        self.store = store

    def document(self, key):
        return DeliveryReference(self.store, key)

    def where(self, field, operator, value):
        return DeliveryQuery(self.store, field, value)


class SubscriberReference:
    def __init__(self):
        self.deliveries = {}

    def collection(self, name):
        assert name == 'deliveries'
        return DeliveryCollection(self.deliveries)


class SubscriberSnapshot:
    def __init__(self, data):
        self.data = data
        self.reference = SubscriberReference()

    def to_dict(self):
        return dict(self.data)


class SubscriberQuery:
    def __init__(self, subscribers):
        self.subscribers = subscribers

    def stream(self):
        return self.subscribers


class SubscriberCollection:
    def __init__(self, subscribers):
        self.subscribers = subscribers

    def where(self, field, operator, value):
        if field == 'status' and operator == '==':
            return SubscriberQuery([s for s in self.subscribers if s.data.get(field) == value])
        raise AssertionError('Unexpected query')


class FakeDB:
    def __init__(self, subscribers):
        self.subscribers = subscribers

    def collection(self, name):
        assert name == 'subscribers'
        return SubscriberCollection(self.subscribers)


class SubscriberTests(unittest.TestCase):
    def test_category_and_retailer_preferences_match(self):
        event = {'category': 'tcg', 'retailer_key': 'pokemon-center'}
        self.assertTrue(event_matches_preferences(event, {'categories': ['tcg'], 'retailers': ['pokemon-center']}))
        self.assertFalse(event_matches_preferences(event, {'categories': ['plush'], 'retailers': ['all']}))
        self.assertFalse(event_matches_preferences(event, {'categories': ['tcg'], 'retailers': ['target']}))
        self.assertTrue(event_matches_preferences(event, {'categories': ['tcg'], 'retailers': ['all']}))

    def test_delivery_batch_id_is_order_independent(self):
        events_a = [{'id': 'one'}, {'id': 'two'}]
        events_b = [{'id': 'two'}, {'id': 'one'}]
        self.assertEqual(delivery_batch_id(events_a), delivery_batch_id(events_b))

    def test_active_subscriber_receives_individual_digest_and_delivery_is_marked_sent(self):
        subscriber = SubscriberSnapshot({
            'email': 'trainer@example.com',
            'status': 'active',
            'categories': ['tcg'],
            'retailers': ['pokemon-center'],
        })
        db = FakeDB([subscriber])
        sent_to = []

        def fake_send(events, env, prefix, recipient=None, manage_url=''):
            sent_to.append((recipient, [event['id'] for event in events], manage_url))
            return True, 'sent'

        event = {
            'id': 'event-1',
            'category': 'tcg',
            'retailer_key': 'pokemon-center',
            'title': 'Pokémon TCG box',
        }
        result = dispatch_subscriber_notifications(
            [event],
            {'SMTP_USERNAME': 'sender@example.com', 'SMTP_APP_PASSWORD': 'not-a-real-password', 'PUBLIC_SITE_URL': 'https://example.github.io/watch'},
            db=db,
            send_func=fake_send,
        )
        self.assertIn('1 digest(s) sent', result)
        self.assertEqual(len(sent_to), 1)
        self.assertEqual(sent_to[0][0], 'trainer@example.com')
        self.assertEqual(sent_to[0][1], ['event-1'])
        self.assertTrue(sent_to[0][2].endswith('/?unsubscribe=1#subscriptions'))
        self.assertEqual(next(iter(subscriber.reference.deliveries.values()))['status'], 'sent')

    def test_missing_service_account_reports_setup_requirement(self):
        result = dispatch_subscriber_notifications([], {})
        self.assertIn('FIREBASE_SERVICE_ACCOUNT_JSON', result)

    def test_accessories_category_matches_subscriber_preference(self):
        subscriber = {"categories": ["accessories"], "retailers": ["all"]}
        event = {"category": "accessories", "retailer_key": "target"}
        self.assertTrue(event_matches_preferences(event, subscriber))


if __name__ == '__main__':
    unittest.main()
