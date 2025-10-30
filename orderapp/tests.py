from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cartapp.models import CartItem
from goodsapp.models import Category, Goods
from userapp.models import Address, RealName, UserInfo
from .models import Order, Orderitem
from .tasks import expire_unpaid_orders, send_order_confirmation_notification
from crossborder_trade.celery_compat import CELERY_AVAILABLE

if CELERY_AVAILABLE:  # pragma: no cover - exercised when Celery is installed
    from crossborder_trade.celery import app as celery_app
else:  # pragma: no cover - exercised in lightweight environments
    celery_app = None


class CeleryEagerTestMixin:
    """Ensure Celery tasks run eagerly for the duration of the test."""

    def setUp(self):  # type: ignore[override]
        super().setUp()
        if celery_app is None:
            self._previous_always_eager = None
            self._previous_eager_propagates = None
            return

        self._previous_always_eager = celery_app.conf.task_always_eager
        self._previous_eager_propagates = celery_app.conf.task_eager_propagates
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

    def tearDown(self):  # type: ignore[override]
        if celery_app is not None and self._previous_always_eager is not None:
            celery_app.conf.task_always_eager = self._previous_always_eager
            celery_app.conf.task_eager_propagates = self._previous_eager_propagates
        super().tearDown()


class CheckoutTaskEnqueueTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserInfo.objects.create_user(
            account='shopper@example.com', password='pass1234', username='shopper'
        )
        RealName.objects.create(
            identity_card='123456789012345678', realname='shopper', is_verified=True, rUserInfo=self.user
        )
        self.address = Address.objects.create(
            aname='shopper',
            aphone='12345678901',
            addr='Test Street 1',
            aUserInfo=self.user,
        )
        category = Category.objects.create(cname='Electronics')
        self.goods = Goods.objects.create(
            gname='Test Phone',
            gdesc='A smartphone',
            price=Decimal('199.99'),
            category=category,
            brand='BrandX',
            stock=5,
            sales=0,
        )
        CartItem.objects.create(
            userInfo=self.user,
            goods=self.goods,
            price=200,
            num=1,
            is_delete=False,
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    @patch('orderapp.views._queue_order_confirmation_task')
    def test_checkout_post_enqueues_notification_task(self, mock_queue):
        response = self.client.post(
            reverse('checkout'),
            data={'address_id': self.address.id},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        mock_queue.assert_called_once()
        self.assertEqual(mock_queue.call_args.args[0], response.data['order_id'])


class OrderCeleryTaskTests(CeleryEagerTestMixin, TestCase):
    def setUp(self):  # type: ignore[override]
        super().setUp()
        self.user = UserInfo.objects.create_user(
            account='order@example.com', password='pass1234', username='orderuser'
        )
        self.address = Address.objects.create(
            aname='orderuser',
            aphone='12345678902',
            addr='Celery Road',
            aUserInfo=self.user,
        )
        category = Category.objects.create(cname='Books')
        self.goods = Goods.objects.create(
            gname='Test Book',
            gdesc='A book',
            price=Decimal('49.99'),
            category=category,
            brand='BrandY',
            stock=1,
            sales=0,
        )
        self.order = Order.objects.create(
            userinfo=self.user,
            address=self.address,
            order_num='ORD123456',
            trade_no='TRADE123456',
            total_amount=Decimal('49.99'),
            status='待支付',
        )
        Orderitem.objects.create(
            order=self.order,
            goods=self.goods,
            quantity=1,
            count=int(self.goods.price),
        )

    @patch('orderapp.tasks.send_order_created_message')
    def test_order_confirmation_task_runs(self, mock_kafka):
        result = send_order_confirmation_notification.delay(self.order.id)
        payload = result.get()
        self.assertEqual(payload['order_id'], self.order.id)
        mock_kafka.assert_called_once()

    @patch('orderapp.tasks.send_stock_change_message')
    def test_expire_unpaid_orders_updates_status(self, mock_stock):
        self.order.create_time = timezone.now() - timedelta(minutes=60)
        self.order.save(update_fields=['create_time'])

        result = expire_unpaid_orders.delay().get()
        self.order.refresh_from_db()
        self.goods.refresh_from_db()

        self.assertIn(self.order.id, result['expired_orders'])
        self.assertEqual(self.order.status, '已取消')
        self.assertEqual(self.goods.stock, 2)
        mock_stock.assert_called()
