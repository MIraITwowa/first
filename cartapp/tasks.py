from celery import shared_task
from django.utils import timezone
from orderapp.models import Order
from goodsapp.models import Goods
from crossborder_trade.kafka_producer import send_order_created_message, send_stock_change_message
from .models import CartItem


@shared_task(bind=True, max_retries=3)
def process_order_notification(self, order_id):
    """异步发送订单通知（短信/推送）"""
    try:
        from userapp.models import UserInfo
        order = Order.objects.get(id=order_id)
        user = UserInfo.objects.get(id=order.userinfo_id)

        # 模拟发送通知（实际项目中替换为真实API调用）
        print(f"发送订单通知给用户 {user.phone}: 订单{order.order_num}已创建")

        # 发送消息到Kafka供其他服务消费（如数据分析）
        send_order_created_message({
            'order_id': order.id,
            'user_id': user.id,
            'amount': order.total_amount,
            'created_at': order.create_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        self.retry(exc=e, countdown=5)  # 5秒后重试


@shared_task
def clean_expired_orders():
    """清理过期未支付的订单，恢复库存"""
    from django.db import transaction
    now = timezone.now()
    expired_orders = Order.objects.filter(
        status='待支付',
        expire_time__lt=now
    )

    with transaction.atomic():
        for order in expired_orders:
            # 恢复库存
            order_items = order.orderitem_set.all()
            for item in order_items:
                goods = Goods.objects.select_for_update().get(id=item.goods_id)
                goods.stock += item.quantity
                goods.save()
                # 发送库存变更消息
                send_stock_change_message({
                    'goods_id': goods.id,
                    'new_stock': goods.stock,
                    'changed_by': f'expired_order_{order.id}'
                })

            # 恢复购物车项（取消删除标记）
            CartItem.objects.filter(
                id__in=order.orderitem_set.values_list('cart_item_id', flat=True)
            ).update(is_delete=False)

            # 更新订单状态
            order.status = '已取消'
            order.save()