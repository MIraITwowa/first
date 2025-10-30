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
from eventstream.models import OutboxEvent
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

        outbox_events = OutboxEvent.objects.filter(
            event_type='order.created', aggregate_id=str(response.data['order_id'])
        )
        self.assertTrue(outbox_events.exists())


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

    def test_order_confirmation_task_runs(self):
        result = send_order_confirmation_notification.delay(self.order.id)
        payload = result.get()
        self.assertEqual(payload['order_id'], self.order.id)

        events = OutboxEvent.objects.filter(
            event_type='order.confirmation_queued', aggregate_id=str(self.order.id)
        )
        self.assertEqual(events.count(), 1)

    def test_order_confirmation_task_idempotent(self):
        send_order_confirmation_notification.delay(self.order.id).get()
        send_order_confirmation_notification.delay(self.order.id).get()

        events = OutboxEvent.objects.filter(
            event_type='order.confirmation_queued', aggregate_id=str(self.order.id)
        )
        self.assertEqual(events.count(), 1)

    def test_expire_unpaid_orders_updates_status(self):
        self.order.create_time = timezone.now() - timedelta(minutes=60)
        self.order.save(update_fields=['create_time'])

        result = expire_unpaid_orders.delay().get()
        self.order.refresh_from_db()
        self.goods.refresh_from_db()

        self.assertIn(self.order.id, result['expired_orders'])
        self.assertEqual(self.order.status, '已取消')
        self.assertEqual(self.goods.stock, 2)

        stock_events = OutboxEvent.objects.filter(
            event_type='stock.adjusted', aggregate_id=str(self.goods.id)
        )
        status_events = OutboxEvent.objects.filter(
            event_type='order.status_changed', aggregate_id=str(self.order.id)
        )
        self.assertTrue(stock_events.exists())
        self.assertTrue(status_events.exists())


class OrderOutboxEventTests(TestCase):
    def setUp(self):
        self.user = UserInfo.objects.create_user(
            account='status@example.com', password='pass1234', username='status-user'
        )
        self.address = Address.objects.create(
            aname='status-user',
            aphone='10987654321',
            addr='Status Street',
            aUserInfo=self.user,
        )
        category = Category.objects.create(cname='Accessories')
        self.goods = Goods.objects.create(
            gname='Charger',
            gdesc='Phone charger',
            price=Decimal('19.99'),
            category=category,
            brand='BrandZ',
            stock=10,
            sales=0,
        )
        self.order = Order.objects.create(
            userinfo=self.user,
            address=self.address,
            order_num='ORD654321',
            trade_no='TRADE654321',
            total_amount=Decimal('19.99'),
            status='待支付',
        )

    def test_status_change_creates_outbox_event(self):
        self.order.update_status('待发货', reason='payment-confirmed')

        event = OutboxEvent.objects.filter(
            event_type='order.status_changed', aggregate_id=str(self.order.id)
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload['previous_status'], '待支付')
        self.assertEqual(event.payload['reason'], 'payment-confirmed')
