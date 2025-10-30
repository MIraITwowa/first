from __future__ import annotations

from crossborder_trade.celery_compat import get_task_logger, shared_task
from django.db import transaction

from .models import Payment

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def handle_successful_payment(self, payment_id: int) -> dict:
    """Finalize successful payments and ensure the related order is updated."""
    try:
        payment = Payment.objects.select_related("order").get(pk=payment_id)
    except Payment.DoesNotExist:
        logger.warning("Payment %s no longer exists; skipping post-processing.", payment_id)
        return {"payment_id": payment_id, "status": "missing"}

    with transaction.atomic():
        order = payment.order
        if payment.status != 'success':
            payment.status = 'success'
            payment.save(update_fields=["status"])

        if order.status != '待发货':
            order.update_status('待发货')

    logger.info(
        "Handled successful payment %s for order %s", payment.id, order.order_num
    )
    return {
        "payment_id": payment.id,
        "order_id": order.id,
        "order_status": order.status,
    }
