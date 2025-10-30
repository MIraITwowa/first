from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from cartapp.models import CartItem
from goodsapp.models import Category, Goods
from orderapp.views import CheckoutAPIView
from paymentapp.views import mock_pay
from userapp.models import Address, RealName, UserInfo
from crossborder_trade.flow_logging import log_flow_debug


class Command(BaseCommand):
    help = "Run checkout and payment diagnostics to surface flow errors."

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Optional user ID to reuse for diagnostics.',
        )
        parser.add_argument(
            '--keep-data',
            action='store_true',
            help='Persist the generated diagnostic data instead of rolling it back.',
        )
        parser.add_argument(
            '--price',
            type=str,
            default='59.99',
            help='Unit price to use for the diagnostic goods (decimal value).',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        keep_data = options.get('keep_data', False)
        price_input = options.get('price', '59.99')

        try:
            unit_price = Decimal(str(price_input)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError) as exc:
            raise CommandError('--price must be a valid decimal number with up to two decimal places.') from exc

        factory = APIRequestFactory()
        logger = logging.getLogger(__name__)

        with transaction.atomic():
            if user_id:
                try:
                    user = UserInfo.objects.get(pk=user_id)
                    created_user = False
                except UserInfo.DoesNotExist as exc:
                    raise CommandError(f'User with id {user_id} does not exist.') from exc
            else:
                timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                account = f'diagnostics-{timestamp}@example.com'
                user = UserInfo.objects.create_user(
                    account=account,
                    password='diagnostics',
                    username=f'diag-{timestamp}',
                )
                created_user = True

            log_flow_debug(
                'diagnostics',
                'Diagnostics user resolved',
                user_id=user.id,
                created=created_user,
            )

            RealName.objects.get_or_create(
                rUserInfo=user,
                defaults={
                    'identity_card': get_random_string(18, '0123456789'),
                    'realname': user.username or 'diagnostic',
                    'is_verified': True,
                },
            )

            address, _ = Address.objects.get_or_create(
                aUserInfo=user,
                defaults={
                    'aname': user.username or 'diagnostic',
                    'aphone': '13800000000',
                    'addr': 'Diagnostic Street 42',
                },
            )

            category, _ = Category.objects.get_or_create(cname='Diagnostics')
            goods_name = f"Diagnostics Item {timezone.now().strftime('%H%M%S')}-{get_random_string(4)}"
            goods = Goods.objects.create(
                gname=goods_name,
                gdesc='Diagnostic goods for flow checks',
                price=unit_price,
                category=category,
                brand='DiagCo',
                stock=10,
                sales=0,
            )

            CartItem.objects.filter(userInfo=user, is_delete=False).delete()
            cart_price = int(unit_price.to_integral_value(rounding=ROUND_HALF_UP))
            cart_item = CartItem.objects.create(
                userInfo=user,
                goods=goods,
                num=1,
                price=cart_price,
                is_delete=False,
            )

            log_flow_debug(
                'diagnostics',
                'Cart primed for diagnostics',
                user_id=user.id,
                cart_item_id=cart_item.id,
                goods_id=goods.id,
                price=str(unit_price),
            )

            checkout_request = factory.post(
                '/api/orders/checkout/',
                {'address_id': address.id},
                format='json',
            )
            force_authenticate(checkout_request, user=user)
            checkout_response = CheckoutAPIView.as_view()(checkout_request)
            checkout_response.render()

            if checkout_response.status_code != status.HTTP_201_CREATED:
                logger.error(
                    'Checkout diagnostics failed with status %s: %s',
                    checkout_response.status_code,
                    checkout_response.data,
                )
                log_flow_debug(
                    'diagnostics',
                    'Checkout diagnostics failed',
                    user_id=user.id,
                    response=checkout_response.data,
                    status_code=checkout_response.status_code,
                )
                raise CommandError(
                    f"Checkout diagnostics failed: {checkout_response.status_code} {checkout_response.data}"
                )

            order_id = checkout_response.data['order_id']
            total_amount = checkout_response.data['total_amount']
            log_flow_debug(
                'diagnostics',
                'Checkout diagnostics completed',
                user_id=user.id,
                order_id=order_id,
                total_amount=total_amount,
            )

            payment_request = factory.post(
                '/api/pay/mock/',
                {'order_id': order_id, 'total_amount': total_amount},
                format='json',
            )
            force_authenticate(payment_request, user=user)
            payment_response = mock_pay(payment_request)
            payment_response.render()

            if payment_response.status_code != status.HTTP_200_OK:
                logger.error(
                    'Payment diagnostics failed with status %s: %s',
                    payment_response.status_code,
                    payment_response.data,
                )
                log_flow_debug(
                    'diagnostics',
                    'Payment diagnostics failed',
                    user_id=user.id,
                    order_id=order_id,
                    response=payment_response.data,
                    status_code=payment_response.status_code,
                )
                raise CommandError(
                    f"Payment diagnostics failed: {payment_response.status_code} {payment_response.data}"
                )

            log_flow_debug(
                'diagnostics',
                'Payment diagnostics completed',
                user_id=user.id,
                order_id=order_id,
                payment_id=payment_response.data.get('payment_id'),
            )

            self.stdout.write(self.style.SUCCESS(f'Diagnostics flow succeeded for order {order_id}.'))

            if not keep_data:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('Diagnostic data rolled back. Use --keep-data to persist.'))
            else:
                self.stdout.write(self.style.WARNING('Diagnostic data persisted because --keep-data was provided.'))
