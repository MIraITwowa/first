"""Backward-compatible wrappers around Celery tasks for cart workflows."""

from orderapp.tasks import (  # noqa: F401 - re-exported for legacy imports
    expire_unpaid_orders as clean_expired_orders,
    send_order_confirmation_notification as process_order_notification,
)

__all__ = ["process_order_notification", "clean_expired_orders"]
