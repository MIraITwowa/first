from __future__ import annotations

from datetime import timedelta

from crossborder_trade.celery_compat import get_task_logger, shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from goodsapp.models import Goods
from eventstream.dispatcher import OutboxDispatcher
from eventstream.outbox import enqueue_order_event, enqueue_outbox_event
from .models import Order

logger = get_task_logger(__name__)


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

    queued_at = timezone.now().isoformat()
    payload = {
        "order_id": order.id,
        "order_num": order.order_num,
        "user_id": order.userinfo_id,
        "status": order.status,
        "total_amount": str(order.total_amount),
        "queued_at": queued_at,
    }

    enqueue_order_event(
        order,
        event_type="order.confirmation_queued",
        payload={
            "queued_at": queued_at,
            "notification": "order_confirmation",
        },
        headers={"task": "send_order_confirmation_notification"},
        idempotency_key=f"order:{order.id}:confirmation-notification",
    )

    logger.info("Queued order confirmation notification for order %s", order.order_num)
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
    stock_topic = settings.KAFKA_TOPICS.get("stock", "stock-events")

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
                enqueue_outbox_event(
                    topic=stock_topic,
                    aggregate_type="goods",
                    aggregate_id=str(goods.id),
                    event_type="stock.adjusted",
                    payload={
                        "goods_id": goods.id,
                        "new_stock": goods.stock,
                        "delta": item.quantity,
                        "reason": f"expired-order-{order.id}",
                    },
                    headers={"source": "orders.expire_unpaid"},
                    idempotency_key=f"goods:{goods.id}:restored:{order.id}",
                )

            order.update_status('已取消', reason='expired')
            expired_orders.append(order.id)

    if expired_orders:
        logger.info(
            "Expired %s unpaid orders older than %s minutes.",
            len(expired_orders),
            expiration_minutes,
        )
    return {"expired_orders": expired_orders, "cutoff": cutoff.isoformat()}


@shared_task(bind=True)
def publish_outbox_events(self, limit: int | None = None) -> dict:
    """Drain pending outbox events and publish them to Kafka."""
    batch_size = limit if limit and limit > 0 else None
    dispatcher = OutboxDispatcher(batch_size=batch_size)
    result = dispatcher.dispatch_batch()
    summary = result.to_dict()

    log_message = (
        "Outbox dispatcher run: locked=%(locked)s sent=%(sent)s retried=%(retri)s dead_lettered=%(dead)s"
        % {
            "locked": summary["locked"],
            "sent": summary["sent"],
            "retri": summary["retried"],
            "dead": summary["dead_lettered"],
        }
    )
    if summary["sent"] or summary["retried"] or summary["dead_lettered"]:
        logger.info(log_message)
    else:
        logger.debug(log_message)

    if summary["errors"]:
        logger.debug("Outbox dispatcher errors: %s", summary["errors"])

    return summary
