from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from kafka import KafkaProducer
from kafka.errors import KafkaError

from .models import OutboxEvent, OutboxState

logger = logging.getLogger(__name__)

_PRODUCER: KafkaProducer | None = None


@dataclass
class DispatchResult:
    locked: int = 0
    sent: int = 0
    retried: int = 0
    dead_lettered: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> dict[str, object]:
        return {
            "locked": self.locked,
            "sent": self.sent,
            "retried": self.retried,
            "dead_lettered": self.dead_lettered,
            "errors": self.errors,
        }


def get_producer() -> KafkaProducer:
    global _PRODUCER
    if _PRODUCER is not None:
        return _PRODUCER

    bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
    if isinstance(bootstrap_servers, str):
        bootstrap_servers = [server.strip() for server in bootstrap_servers.split(',') if server.strip()]

    producer_config = {
        "bootstrap_servers": bootstrap_servers,
        "client_id": getattr(settings, "KAFKA_CLIENT_ID", "crossborder-trade-api"),
        "acks": getattr(settings, "KAFKA_PRODUCER_ACKS", "all"),
        "linger_ms": getattr(settings, "KAFKA_PRODUCER_LINGER_MS", 10),
        "retries": getattr(settings, "KAFKA_PRODUCER_RETRIES", 5),
        "enable_idempotence": getattr(settings, "KAFKA_PRODUCER_IDEMPOTENCE", True),
        "max_in_flight_requests_per_connection": getattr(
            settings, "KAFKA_PRODUCER_MAX_IN_FLIGHT", 5
        ),
    }
    overrides = getattr(settings, "KAFKA_PRODUCER_CONFIG", {})
    producer_config.update(overrides)
    producer_config.setdefault("value_serializer", lambda payload: json.dumps(payload).encode("utf-8"))

    logger.debug("Creating KafkaProducer with config %s", {k: producer_config[k] for k in producer_config if k != "value_serializer"})
    _PRODUCER = KafkaProducer(**producer_config)
    return _PRODUCER


class OutboxDispatcher:
    def __init__(self, *, batch_size: int | None = None) -> None:
        self.batch_size = batch_size or getattr(settings, "OUTBOX_DISPATCH_BATCH_SIZE", 50)
        self.max_backoff_seconds = getattr(settings, "OUTBOX_MAX_BACKOFF_SECONDS", 600)
        self.base_backoff_seconds = getattr(settings, "OUTBOX_RETRY_BASE_SECONDS", 30)

    def dispatch_batch(self) -> DispatchResult:
        events = self._lock_next_batch()
        result = DispatchResult(locked=len(events))
        if not events:
            return result

        try:
            producer = get_producer()
        except Exception as exc:  # pragma: no cover - producer creation can fail in tests
            logger.exception("Unable to create Kafka producer: %s", exc)
            for event in events:
                dead_lettered = self._handle_failure(event, exc)
                if dead_lettered:
                    result.dead_lettered += 1
                else:
                    result.retried += 1
            result.errors.append(str(exc))
            return result

        futures = []
        for event in events:
            try:
                future = self._send_event(producer, event)
                futures.append((event, future))
            except Exception as exc:  # pragma: no cover - kafka failure path handled below
                logger.exception("Failed to send outbox event %s: %s", event.id, exc)
                dead_lettered = self._handle_failure(event, exc)
                if dead_lettered:
                    result.dead_lettered += 1
                else:
                    result.retried += 1
                result.errors.append(str(exc))

        # Complete send futures and update states
        for event, future in futures:
            try:
                future.get(timeout=getattr(settings, "OUTBOX_PRODUCER_SEND_TIMEOUT", 10))
            except KafkaError as exc:
                logger.warning("Kafka send failed for event %s: %s", event.id, exc)
                dead_lettered = self._handle_failure(event, exc)
                if dead_lettered:
                    result.dead_lettered += 1
                else:
                    result.retried += 1
                result.errors.append(str(exc))
                continue
            except Exception as exc:  # pragma: no cover - defensive catch
                logger.warning("Unexpected error waiting for Kafka ack for event %s: %s", event.id, exc)
                dead_lettered = self._handle_failure(event, exc)
                if dead_lettered:
                    result.dead_lettered += 1
                else:
                    result.retried += 1
                result.errors.append(str(exc))
                continue

            self._mark_success(event)
            result.sent += 1

        if result.sent:
            try:
                producer.flush()
            except Exception as exc:  # pragma: no cover - flush failures rare
                logger.warning("Failed to flush Kafka producer: %s", exc)

        return result

    def _lock_next_batch(self) -> list[OutboxEvent]:
        now = timezone.now()
        with transaction.atomic():
            queryset = (
                OutboxEvent.objects.select_for_update(skip_locked=True)
                .filter(state=OutboxState.PENDING, next_attempt_at__lte=now)
                .order_by("created_at")
            )
            events = list(queryset[: self.batch_size])
            for event in events:
                event.state = OutboxState.IN_PROGRESS
                event.attempt_count += 1
                event.last_attempt_at = now
                event.save(
                    update_fields=["state", "attempt_count", "last_attempt_at", "updated_at"]
                )
        return events

    def _send_event(self, producer: KafkaProducer, event: OutboxEvent):
        headers = self._serialize_headers(event)
        payload = event.payload
        key = (event.message_key or event.idempotency_key).encode("utf-8")
        logger.info(
            "Publishing outbox event %s to topic %s (attempt %s)",
            event.id,
            event.topic,
            event.attempt_count,
        )
        return producer.send(
            event.topic,
            key=key,
            value=payload,
            headers=headers,
        )

    def _serialize_headers(self, event: OutboxEvent) -> Iterable[tuple[str, bytes]]:
        headers = []
        header_values = event.headers or {}
        # Include idempotency and correlation keys for traceability
        header_values.setdefault("idempotency_key", event.idempotency_key)
        header_values.setdefault("correlation_id", event.correlation_id)
        header_values.setdefault("aggregate_type", event.aggregate_type)
        header_values.setdefault("aggregate_id", event.aggregate_id)
        header_values.setdefault("event_type", event.event_type)
        for key, value in header_values.items():
            if value is None:
                continue
            if isinstance(value, bytes):
                encoded = value
            else:
                encoded = str(value).encode("utf-8")
            headers.append((str(key), encoded))
        return headers

    def _mark_success(self, event: OutboxEvent) -> None:
        event.state = OutboxState.SENT
        event.dispatched_at = timezone.now()
        event.error_type = ""
        event.error_message = ""
        event.dead_letter_reason = ""
        event.dead_lettered_at = None
        event.save(
            update_fields=[
                "state",
                "dispatched_at",
                "error_type",
                "error_message",
                "dead_letter_reason",
                "dead_lettered_at",
                "updated_at",
            ]
        )

    def _handle_failure(self, event: OutboxEvent, exc: Exception) -> bool:
        dead_lettered = False
        if event.attempt_count >= event.max_attempts:
            logger.error(
                "Event %s exceeded max attempts (%s); moving to dead-letter", event.id, event.max_attempts
            )
            event.state = OutboxState.DEAD_LETTER
            event.dead_lettered_at = timezone.now()
            event.dead_letter_reason = str(exc)
            event.next_attempt_at = timezone.now()
            dead_lettered = True
        else:
            event.state = OutboxState.PENDING
            backoff_seconds = min(
                self.base_backoff_seconds * (2 ** (event.attempt_count - 1)),
                self.max_backoff_seconds,
            )
            event.next_attempt_at = timezone.now() + timedelta(seconds=backoff_seconds)

        event.error_type = exc.__class__.__name__
        event.error_message = str(exc)
        event.save(
            update_fields=[
                "state",
                "next_attempt_at",
                "error_type",
                "error_message",
                "dead_lettered_at",
                "dead_letter_reason",
                "updated_at",
            ]
        )
        return dead_lettered


__all__ = ["OutboxDispatcher", "DispatchResult", "get_producer"]
