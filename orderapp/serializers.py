from rest_framework import serializers
from .models import Order, Orderitem
from goodsapp.serializers import GoodsListSerializer  # 导入商品序列化器


class OrderitemSerializer(serializers.ModelSerializer):
    """订单项序列化器"""
    goods = GoodsListSerializer(read_only=True)  # 嵌套序列化商品信息，包含商品的所有信息

    class Meta:
        model = Orderitem
        fields = ['id', 'goods', 'quantity', 'count']


class OrderSerializer(serializers.ModelSerializer):
    """订单序列化器"""
    order_items = OrderitemSerializer(many=True, read_only=True, source='orderitem_set')  # 使用related_name获取订单项
    address = serializers.PrimaryKeyRelatedField(read_only=True)  # 使用主键关联地址

    class Meta:
        model = Order
        fields = ['id', 'trade_no', 'order_num', 'status', 'pay', 'create_time', 'total_amount', 'address',
                  'order_items']
        read_only_fields = ['trade_no', 'order_num', 'status', 'create_time', 'total_amount', 'order_items', 'address']
