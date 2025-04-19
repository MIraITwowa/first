from rest_framework import serializers
from .models import CartItem
from goodsapp.serializers import GoodsListSerializer


class CartItemSerializer(serializers.ModelSerializer):
    goods = GoodsListSerializer(read_only=True)  # 嵌套商品序列化器
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'goods', 'num', 'price', 'total_price']

    def get_total_price(self, obj):
        return obj.num * obj.price
