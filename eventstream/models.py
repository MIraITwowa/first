from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


def default_correlation_id() -> str:
    return uuid.uuid4().hex


def default_idempotency_key() -> str:
    return uuid.uuid4().hex


def default_next_attempt_at():
    return timezone.now()


def default_max_attempts() -> int:
    from django.conf import settings

    return getattr(settings, "OUTBOX_MAX_ATTEMPTS", 5)


class OutboxState(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In progress"
    SENT = "sent", "Sent"
    DEAD_LETTER = "dead_letter", "Dead letter"


class OutboxEvent(models.Model):
    topic = models.CharField(max_length=255)
    aggregate_type = models.CharField(max_length=100)
    aggregate_id = models.CharField(max_length=64)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    headers = models.JSONField(default=dict, blank=True)
    state = models.CharField(
        max_length=20,
        choices=OutboxState.choices,
        default=OutboxState.PENDING,
    )
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=default_max_attempts)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(default=default_next_attempt_at)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, default=default_correlation_id)
    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        default=default_idempotency_key,
    )
    message_key = models.CharField(max_length=128, blank=True)
    error_type = models.CharField(max_length=128, blank=True)
    error_message = models.TextField(blank=True)
    dead_lettered_at = models.DateTimeField(null=True, blank=True)
    dead_letter_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=("state", "next_attempt_at"), name="event_state_ready_idx"),
            models.Index(fields=("aggregate_type", "aggregate_id"), name="event_aggregate_idx"),
            models.Index(fields=("topic", "state"), name="event_topic_state_idx"),
        ]

    def mark_dead_letter(self, reason: str, *, error_type: str | None = None) -> None:
        self.state = OutboxState.DEAD_LETTER
        self.dead_lettered_at = timezone.now()
        self.dead_letter_reason = reason
        if error_type:
            self.error_type = error_type
        self.save(
            update_fields=[
                "state",
                "dead_lettered_at",
                "dead_letter_reason",
                "error_type",
                "updated_at",
            ]
        )
