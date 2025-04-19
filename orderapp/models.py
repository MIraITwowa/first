from django.db import models

# Create your models here.
from django.db import models

from userapp.models import Address, UserInfo
from goodsapp.models import Goods


# from payment.models import Payment

# Create your models here.
class Order(models.Model):
    trade_no = models.CharField(max_length=50, verbose_name="交易编号")
    order_num = models.CharField(max_length=50, verbose_name="订单号")
    status = models.CharField(max_length=50, default='待支付')  # 状态（待支付，待发货，待收货）
    pay = models.CharField(max_length=50, default='alipay') # 支付方式
    create_time = models.DateTimeField(auto_now_add=True) # 订单创建时间
    total_amount = models.FloatField(default=0, verbose_name="总金额")

    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    userinfo = models.ForeignKey(UserInfo, on_delete=models.CASCADE)

    def update_status(self, new_status):
        """更新订单状态"""
        self.status = new_status
        self.save()
        return self


class Orderitem(models.Model):
    """订单简述"""
    count = models.IntegerField(default=0, verbose_name="价格")
    quantity = models.PositiveIntegerField(default=1)  # 商品数量

    goods = models.ForeignKey(Goods, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    # class Order(models.Model):
    #     # 订单其他字段
    #     payments = models.ManyToManyField('payment.Payment', related_name='orders')
