from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from .dispatcher import OutboxDispatcher
from .models import OutboxEvent, OutboxState
from .outbox import enqueue_outbox_event


class DummyFuture:
    def __init__(self, exc: Exception | None = None) -> None:
        self._exc = exc

    def get(self, timeout: float | None = None):  # pragma: no cover - trivial
        if self._exc:
            raise self._exc
        return True


class DummyProducer:
    def __init__(self, *, raise_on_send: bool = False, future_exception: Exception | None = None) -> None:
        self.raise_on_send = raise_on_send
        self.future_exception = future_exception
        self.messages: list[tuple[str, bytes | None, object, list[tuple[str, bytes]]]] = []
        self.flush_calls = 0

    def send(self, topic, key=None, value=None, headers=None):
        if self.raise_on_send:
            raise RuntimeError("send-error")
        self.messages.append((topic, key, value, headers))
        return DummyFuture(self.future_exception)

    def flush(self):  # pragma: no cover - trivial
        self.flush_calls += 1


class OutboxEnqueueTests(TestCase):
    def test_enqueue_is_idempotent(self):
        event1 = enqueue_outbox_event(
            topic='order-events',
            aggregate_type='order',
            aggregate_id='1',
            event_type='order.created',
            payload={'example': True},
            idempotency_key='idempotent-event',
            schedule_dispatch=False,
        )
        event2 = enqueue_outbox_event(
            topic='order-events',
            aggregate_type='order',
            aggregate_id='1',
            event_type='order.created',
            payload={'example': True},
            idempotency_key='idempotent-event',
            schedule_dispatch=False,
        )
        self.assertEqual(event1.id, event2.id)
        self.assertEqual(OutboxEvent.objects.count(), 1)


class OutboxDispatcherTests(TestCase):
    def setUp(self):  # type: ignore[override]
        OutboxEvent.objects.all().delete()

    @patch('eventstream.dispatcher.get_producer')
    def test_dispatcher_marks_success_and_is_idempotent(self, mock_get_producer):
        event = OutboxEvent.objects.create(
            topic='order-events',
            aggregate_type='order',
            aggregate_id='42',
            event_type='order.created',
            payload={'foo': 'bar'},
            headers={},
            idempotency_key='success-event',
        )
        event.state = OutboxState.PENDING
        event.save(update_fields=['state'])

        producer = DummyProducer()
        mock_get_producer.return_value = producer

        dispatcher = OutboxDispatcher(batch_size=10)
        summary = dispatcher.dispatch_batch().to_dict()

        self.assertEqual(summary['sent'], 1)
        self.assertEqual(summary['retried'], 0)
        self.assertFalse(summary['errors'])
        self.assertEqual(len(producer.messages), 1)

        event.refresh_from_db()
        self.assertEqual(event.state, OutboxState.SENT)
        self.assertIsNotNone(event.dispatched_at)
        self.assertEqual(event.attempt_count, 1)

        second_summary = dispatcher.dispatch_batch().to_dict()
        self.assertEqual(second_summary['sent'], 0)
        self.assertEqual(len(producer.messages), 1)

    @patch('eventstream.dispatcher.get_producer')
    def test_dispatcher_retries_and_dead_letters(self, mock_get_producer):
        event = OutboxEvent.objects.create(
            topic='order-events',
            aggregate_type='order',
            aggregate_id='24',
            event_type='order.created',
            payload={'foo': 'bar'},
            headers={},
            idempotency_key='failing-event',
            max_attempts=2,
        )
        event.state = OutboxState.PENDING
        event.save(update_fields=['state'])

        producer = DummyProducer(raise_on_send=True)
        mock_get_producer.return_value = producer

        dispatcher = OutboxDispatcher(batch_size=5)
        first_summary = dispatcher.dispatch_batch().to_dict()
        event.refresh_from_db()

        self.assertEqual(first_summary['retried'], 1)
        self.assertEqual(first_summary['dead_lettered'], 0)
        self.assertTrue(first_summary['errors'])
        self.assertEqual(event.state, OutboxState.PENDING)
        self.assertEqual(event.attempt_count, 1)
        self.assertGreater(event.next_attempt_at, timezone.now())

        # Make the event eligible for another attempt and trigger dead-lettering
        event.next_attempt_at = timezone.now() - timedelta(seconds=1)
        event.save(update_fields=['next_attempt_at'])

        second_summary = dispatcher.dispatch_batch().to_dict()
        event.refresh_from_db()

        self.assertEqual(second_summary['dead_lettered'], 1)
        self.assertEqual(event.state, OutboxState.DEAD_LETTER)
        self.assertEqual(event.attempt_count, 2)
        self.assertTrue(second_summary['errors'])
