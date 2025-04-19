# Create your models here.
from django.db import models

from orderapp.models import Order


# 支付模型
class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)  # 关联订单
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # 支付金额
    payment_method = models.CharField(max_length=50)  # 支付方式
    timestamp = models.DateTimeField(auto_now_add=True)  # 支付时间
    status = models.CharField(max_length=50, default="pending")  # 支付状态

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )

    # class Meta:
    #     unique_together = ('order',)

    def __str__(self):
        return f"Payment for order {self.order.id}"


