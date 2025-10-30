from __future__ import annotations

import logging
import uuid
from typing import Any, Mapping

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import OutboxEvent, OutboxState

logger = logging.getLogger(__name__)


def _normalize_headers(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if headers:
        for key, value in headers.items():
            if value is None:
                continue
            normalized[str(key)] = value
    return normalized


def _resolve_max_attempts(explicit: int | None) -> int:
    if explicit is not None and explicit > 0:
        return explicit
    field_default = OutboxEvent._meta.get_field("max_attempts").default
    default_value = field_default() if callable(field_default) else field_default
    return getattr(settings, "OUTBOX_MAX_ATTEMPTS", default_value)


def _resolve_dispatch_batch_size() -> int:
    return getattr(settings, "OUTBOX_DISPATCH_BATCH_SIZE", 50)


def enqueue_outbox_event(
    *,
    topic: str,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    payload: Mapping[str, Any] | None = None,
    headers: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
    message_key: str | None = None,
    max_attempts: int | None = None,
    schedule_dispatch: bool = True,
) -> OutboxEvent:
    if not topic:
        raise ValueError("topic is required")
    if not aggregate_type:
        raise ValueError("aggregate_type is required")
    if not aggregate_id:
        raise ValueError("aggregate_id is required")
    if not event_type:
        raise ValueError("event_type is required")

    correlation_id = correlation_id or uuid.uuid4().hex
    headers_payload = _normalize_headers(headers)
    headers_payload.setdefault("correlation_id", correlation_id)
    effective_payload = dict(payload or {})
    effective_payload.setdefault("timestamp", timezone.now().isoformat())

    idempotency_key = idempotency_key or uuid.uuid4().hex
    message_key = message_key or idempotency_key

    event_data = {
        "topic": topic,
        "aggregate_type": aggregate_type,
        "aggregate_id": str(aggregate_id),
        "event_type": event_type,
        "payload": effective_payload,
        "headers": headers_payload,
        "state": OutboxState.PENDING,
        "next_attempt_at": timezone.now(),
        "attempt_count": 0,
        "last_attempt_at": None,
        "dispatched_at": None,
        "correlation_id": correlation_id,
        "idempotency_key": idempotency_key,
        "message_key": message_key,
        "max_attempts": _resolve_max_attempts(max_attempts),
        "error_type": "",
        "error_message": "",
        "dead_lettered_at": None,
        "dead_letter_reason": "",
    }

    try:
        event = OutboxEvent.objects.get(idempotency_key=idempotency_key)
        created = False
    except OutboxEvent.DoesNotExist:
        try:
            event = OutboxEvent.objects.create(**event_data)
        except IntegrityError:
            event = OutboxEvent.objects.get(idempotency_key=idempotency_key)
            created = False
        else:
            created = True

    if created:
        logger.debug(
            "Created outbox event %s for %s:%s", event.id, aggregate_type, aggregate_id
        )
    else:
        logger.debug(
            "Outbox event %s already exists; duplicate enqueue ignored", event.id
        )

    if schedule_dispatch and event.state in {OutboxState.PENDING, OutboxState.IN_PROGRESS}:
        _schedule_dispatch()

    return event


def _schedule_dispatch() -> None:
    def _enqueue_task() -> None:
        try:
            from orderapp.tasks import publish_outbox_events
        except Exception as exc:  # pragma: no cover - Celery optional
            logger.warning("publish_outbox_events task unavailable: %s", exc)
            return

        try:
            publish_outbox_events.delay(limit=_resolve_dispatch_batch_size())
        except Exception as exc:  # pragma: no cover - Celery misconfigured
            logger.warning("Failed to enqueue outbox dispatcher task: %s", exc)

    try:
        transaction.on_commit(_enqueue_task)
    except Exception:  # TransactionManagementError when outside atomic
        _enqueue_task()


def build_order_payload(order, *, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    base_payload = {
        "order_id": order.id,
        "order_num": order.order_num,
        "trade_no": order.trade_no,
        "user_id": order.userinfo_id,
        "status": order.status,
        "total_amount": float(order.total_amount),
    }
    if extra:
        base_payload.update({str(k): v for k, v in extra.items()})
    return base_payload


def enqueue_order_event(
    order,
    *,
    event_type: str,
    payload: Mapping[str, Any] | None = None,
    headers: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
) -> OutboxEvent:
    topic = settings.KAFKA_TOPICS.get("orders", "order-events")
    payload_body = build_order_payload(order, extra=payload)
    if idempotency_key is None:
        idempotency_key = f"order:{order.pk}:{event_type}"
    return enqueue_outbox_event(
        topic=topic,
        aggregate_type="order",
        aggregate_id=str(order.pk),
        event_type=event_type,
        payload=payload_body,
        headers=headers,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        message_key=idempotency_key,
    )
