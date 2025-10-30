from __future__ import annotations

from datetime import timedelta

from crossborder_trade.celery_compat import get_task_logger, shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from goodsapp.models import Goods
from .models import Order

logger = get_task_logger(__name__)

try:  # pragma: no cover - defensive fallback when Kafka is not configured
    from crossborder_trade.kafka_producer import (  # type: ignore
        send_order_created_message,
        send_stock_change_message,
    )
except Exception:  # pragma: no cover
    def send_order_created_message(*args, **kwargs):
        logger.debug("Kafka producer unavailable; skipping order created message.")

    def send_stock_change_message(*args, **kwargs):
        logger.debug("Kafka producer unavailable; skipping stock change message.")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_order_confirmation_notification(self, order_id: int) -> dict:
    """Send an order confirmation notification and emit an analytic event."""
    try:
        order = Order.objects.select_related("userinfo").get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("Order %s no longer exists; skipping notification.", order_id)
        return {"order_id": order_id, "status": "missing"}

    payload = {
        "order_id": order.id,
        "order_num": order.order_num,
        "user_id": order.userinfo_id,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "queued_at": timezone.now().isoformat(),
    }

    logger.info("Dispatching order confirmation notification for order %s", order.order_num)
    try:
        send_order_created_message(payload)
    except Exception as exc:  # pragma: no cover - transport errors are non-critical
        logger.warning("Failed to publish order confirmation message: %s", exc)

    return payload


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def expire_unpaid_orders(self) -> dict:
    """Expire unpaid orders and restore inventory when necessary."""
    expiration_minutes = getattr(settings, "ORDER_EXPIRATION_MINUTES", 30)
    cutoff = timezone.now() - timedelta(minutes=expiration_minutes)

    expired_orders = []
    with transaction.atomic():
        orders = (
            Order.objects.select_for_update()
            .filter(status='待支付', create_time__lt=cutoff)
            .prefetch_related("orderitem_set__goods")
        )
        for order in orders:
            for item in order.orderitem_set.all():
                goods: Goods = item.goods
                goods.stock += item.quantity
                goods.save(update_fields=["stock"])
                try:
                    send_stock_change_message(
                        {
                            "goods_id": goods.id,
                            "new_stock": goods.stock,
                            "source": f"expired-order-{order.id}",
                        }
                    )
                except Exception as exc:  # pragma: no cover
                    logger.debug("Failed to publish stock change message: %s", exc)

            order.status = '已取消'
            order.save(update_fields=["status"])
            expired_orders.append(order.id)

    if expired_orders:
        logger.info(
            "Expired %s unpaid orders older than %s minutes.",
            len(expired_orders),
            expiration_minutes,
        )
    return {"expired_orders": expired_orders, "cutoff": cutoff.isoformat()}


@shared_task(bind=True)
def publish_outbox_events(self) -> dict:
    """Placeholder outbox publisher task to be implemented in the messaging phase."""
    logger.debug("Outbox publisher placeholder executed; no-op for now.")
    return {"status": "noop", "timestamp": timezone.now().isoformat()}
