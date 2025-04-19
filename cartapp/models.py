from django.db import models
from django.db.models.signals import post_save  # 导入 post_save 信号
from django.dispatch import receiver  # 导入 receiver 装饰器

from userapp.models import UserInfo
from goodsapp.models import Goods


# Create your models here.
class CartItem(models.Model):
    """购物车"""
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, null=True)
    is_delete = models.BooleanField(default=False)
    userInfo = models.ForeignKey(UserInfo, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)  # 总价
    num = models.IntegerField(default=1)  # 数量
    post_fee = models.IntegerField(default=0)  # 运费
    price = models.IntegerField(default=0)  # 单价

    def __str__(self):
        return str(self.id)


# 使用 @receiver 装饰器来指定这个函数是一个信号处理器
# post_save 是一个信号，它在模型保存后触发
# sender 指定了这个信号处理器应该监听哪个模型，这里是 UserInfo 模型
@receiver(post_save, sender=UserInfo)
def create_cart(sender, instance=None, created=False, some_default_goods_id=None, **kwargs):
    # instance 参数是触发信号的模型实例，这里是新创建的用户实例
    # created 参数是一个布尔值，表示这个实例是否是新创建的

    # 这里没有高亮，疑似是一个小问题，以后再说

    if created:
        # 如果是新创建的用户实例（即 created 为 True）
        # 则为这个用户创建一个购物车实例
        CartItem.objects.create(userInfo=instance, goods_id=some_default_goods_id)
