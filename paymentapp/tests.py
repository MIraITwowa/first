from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from orderapp.models import Order
from userapp.models import Address, UserInfo
from .models import Payment
from .tasks import handle_successful_payment
from crossborder_trade.celery_compat import CELERY_AVAILABLE

if CELERY_AVAILABLE:  # pragma: no cover
    from crossborder_trade.celery import app as celery_app
else:  # pragma: no cover
    celery_app = None


class CeleryEagerTestMixin:
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


class PaymentViewTaskTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserInfo.objects.create_user(
            account='payer@example.com', password='pass1234', username='payer'
        )
        self.address = Address.objects.create(
            aname='payer',
            aphone='12345678903',
            addr='Payment Avenue',
            aUserInfo=self.user,
        )
        self.order = Order.objects.create(
            userinfo=self.user,
            address=self.address,
            order_num='PAYORDER1',
            trade_no='PAYTRADE1',
            total_amount=Decimal('10.00'),
            status='待支付',
        )

    @patch('paymentapp.views._queue_payment_success_task')
    @patch('paymentapp.views.random.random', return_value=0.0)
    def test_mock_pay_enqueues_payment_task(self, mock_random, mock_queue):
        response = self.client.post(
            reverse('mock-pay'),
            data={'order_id': self.order.id, 'total_amount': '10.00'},
        )
        self.assertEqual(response.status_code, 200)
        mock_random.assert_called_once()
        mock_queue.assert_called_once()
        self.assertEqual(mock_queue.call_args.args[0], Payment.objects.latest('id').id)

    @patch('paymentapp.views._queue_payment_success_task')
    @patch('paymentapp.views.random.random')
    def test_mock_pay_rejects_amount_mismatch(self, mock_random, mock_queue):
        response = self.client.post(
            reverse('mock-pay'),
            data={'order_id': self.order.id, 'total_amount': '11.00'},
        )
        self.assertEqual(response.status_code, 400)
        mock_random.assert_not_called()
        mock_queue.assert_not_called()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, '待支付')
        self.assertIn('expected_amount', response.data)
        self.assertFalse(Payment.objects.exists())

    @patch('paymentapp.views._queue_payment_success_task')
    def test_mock_pay_rejects_invalid_amount(self, mock_queue):
        response = self.client.post(
            reverse('mock-pay'),
            data={'order_id': self.order.id, 'total_amount': 'not-a-number'},
        )
        self.assertEqual(response.status_code, 400)
        mock_queue.assert_not_called()
        self.assertFalse(Payment.objects.exists())


class PaymentTaskBehaviourTests(CeleryEagerTestMixin, TestCase):
    def setUp(self):  # type: ignore[override]
        super().setUp()
        self.user = UserInfo.objects.create_user(
            account='celerypayer@example.com', password='pass1234', username='celerypayer'
        )
        self.address = Address.objects.create(
            aname='celerypayer',
            aphone='12345678904',
            addr='Task Street',
            aUserInfo=self.user,
        )
        self.order = Order.objects.create(
            userinfo=self.user,
            address=self.address,
            order_num='TASKORDER',
            trade_no='TASKTRADE',
            total_amount=Decimal('20.00'),
            status='待支付',
        )
        self.payment = Payment.objects.create(
            order=self.order,
            amount=Decimal('20.00'),
            payment_method='alipay',
            status='pending',
        )

    def test_handle_successful_payment_updates_records(self):
        result = handle_successful_payment.delay(self.payment.id)
        payload = result.get()

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(payload['payment_id'], self.payment.id)
        self.assertEqual(self.payment.status, 'success')
        self.assertEqual(self.order.status, '待发货')
