from django.urls import path
from orderapp.views import CheckoutAPIView, OrderDetailAPIView, OrderListAPIView

urlpatterns = [
    # 结账 API
    path('checkout/', CheckoutAPIView.as_view(), name='checkout'),
    # 订单详情 API
    path('orders/<int:order_id>/', OrderDetailAPIView.as_view(), name='order_detail'),
    path('orders/', OrderListAPIView.as_view(), name='order_list'),
]
