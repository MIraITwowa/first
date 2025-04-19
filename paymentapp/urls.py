# paymentapp/urls.py
from django.urls import path
from .views import mock_pay, mock_notify

urlpatterns = [
    # 模拟支付接口
    path('mock-pay/', mock_pay, name='mock-pay'),
    # 模拟支付回调接口
    path('mock-notify/', mock_notify, name='mock-notify'),
]