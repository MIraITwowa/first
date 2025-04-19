from rest_framework import serializers
from .models import Payment
from orderapp.models import Order


class PaymentSerializer(serializers.ModelSerializer):
    """
    支付模型的序列化器
    """
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('timestamp', 'status')

    def validate(self, data):
        # 验证支付金额是否为正数
        if data.get('amount', 0) <= 0:
            raise serializers.ValidationError("支付金额必须大于0")

        # 验证订单状态
        order = data.get('order')
        if order and order.status != '待支付':
            raise serializers.ValidationError("订单状态不正确，只能支付'待支付'状态的订单")

        return data


class PaymentSuccessSerializer(serializers.Serializer):
    """
    模拟支付成功的序列化器
    """
    order_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField(max_length=50)
    transaction_id = serializers.CharField(max_length=100, required=False)
    signature = serializers.CharField(max_length=255, required=False)

    def validate(self, data):
        # 验证签名
        if 'signature' in data:
            # 在这里实现签名验证逻辑
            pass
        return data
