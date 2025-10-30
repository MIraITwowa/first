from __future__ import annotations

from decimal import Decimal
import uuid

from django.db import models
from django.utils import timezone

from userapp.models import Address, UserInfo
from goodsapp.models import Goods
from eventstream.outbox import enqueue_order_event
from crossborder_trade.flow_logging import log_flow_debug


# from payment.models import Payment

# Create your models here.
class Order(models.Model):
    trade_no = models.CharField(max_length=50, verbose_name="交易编号")
    order_num = models.CharField(max_length=50, verbose_name="订单号")
    status = models.CharField(max_length=50, default='待支付')  # 状态（待支付，待发货，待收货）
    pay = models.CharField(max_length=50, default='alipay')  # 支付方式
    create_time = models.DateTimeField(auto_now_add=True)  # 订单创建时间
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="总金额",
    )

    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    userinfo = models.ForeignKey(UserInfo, on_delete=models.CASCADE)

    def update_status(self, new_status: str, *, reason: str | None = None) -> "Order":
        """更新订单状态并记录到事件外盒。"""
        if new_status == self.status:
            return self

        previous_status = self.status
        self.status = new_status
        self.save(update_fields=["status"])

        payload = {
            "previous_status": previous_status,
            "changed_at": timezone.now().isoformat(),
        }
        headers = {}
        if reason:
            payload["reason"] = reason
            headers["reason"] = reason

        enqueue_order_event(
            self,
            event_type="order.status_changed",
            payload=payload,
            headers=headers or None,
            idempotency_key=f"order:{self.pk}:status:{new_status}:{uuid.uuid4().hex}",
        )

        if any(keyword in new_status for keyword in ('退款', 'refund')):
            log_flow_debug(
                'refund',
                'Order status transitioned to refund state',
                order_id=self.id,
                user_id=self.userinfo_id,
                previous_status=previous_status,
                new_status=new_status,
                reason=reason,
            )

        return self


class Orderitem(models.Model):
    """订单简述"""
    count = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="价格",
    )
    quantity = models.PositiveIntegerField(default=1)  # 商品数量

    goods = models.ForeignKey(Goods, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    # class Order(models.Model):
    #     # 订单其他字段
    #     payments = models.ManyToManyField('payment.Payment', related_name='orders')
