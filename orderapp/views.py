# from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP

from .models import Order, Orderitem
from .serializers import OrderSerializer, OrderitemSerializer
from cartapp.models import CartItem  # 从 cartapp 导入 CartItem
from userapp.models import Address, RealName  # 从 userapp 导入 Address
from eventstream.outbox import enqueue_order_event
from crossborder_trade.flow_logging import log_flow_debug

from django.utils import timezone
import logging
import uuid


logger = logging.getLogger(__name__)


def _queue_order_confirmation_task(order_id: int) -> None:
    try:
        from .tasks import send_order_confirmation_notification
    except ModuleNotFoundError:
        logger.warning("未安装 Celery，无法发送订单通知任务。")
        return

    try:
        send_order_confirmation_notification.delay(order_id)
    except Exception as exc:  # pragma: no cover - Celery misconfiguration fallback
        logger.warning("订单通知任务入队失败: %s", exc)


class CheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """处理 GET 请求，返回购物车详情和总价"""
        cart_queryset = CartItem.objects.select_related('goods').filter(
            userInfo=request.user,
            is_delete=False,
        )
        invalid_count = cart_queryset.filter(goods__isnull=True).count()
        cart_items = list(cart_queryset.filter(goods__isnull=False))

        total = sum(
            (item.goods.price * item.num for item in cart_items),
            Decimal('0.00'),
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        order_items = [
            {
                'goods': item.goods,
                'quantity': item.num,
                'count': item.goods.price,
            }
            for item in cart_items
        ]

        log_flow_debug(
            'checkout',
            'Checkout preview generated',
            user_id=getattr(request.user, 'id', None),
            item_count=len(order_items),
            skipped_items=invalid_count,
            total=str(total),
        )

        serializer = OrderitemSerializer(order_items, many=True)
        return Response({
            'items': serializer.data,
            'total': str(total),
        })

    @staticmethod
    def post(request):
        """处理 POST 请求，创建订单并清空购物车"""
        # try:
        #     # 验证请求数据
        #     address_id = request.data.get('address_id')
        #     if not address_id:
        #         return Response({
        #             'status': 'error',
        #             'message': '请选择收货地址'
        #         }, status=status.HTTP_400_BAD_REQUEST)
        #
        #     # 获取指定的地址
        #     try:
        #         address = Address.objects.get(id=address_id, aUserInfo=request.user)
        #     except Address.DoesNotExist:
        #         return Response({
        #             'status': 'error',
        #             'message': '收货地址不存在'
        #         }, status=status.HTTP_400_BAD_REQUEST)
        #
        #     # 获取购物车商品
        #     cart_items = CartItem.objects.filter(userInfo=request.user, is_delete=False)
        #     if not cart_items:
        #         return Response({
        #             'status': 'error',
        #             'message': '购物车为空'
        #         }, status=status.HTTP_400_BAD_REQUEST)
        #
        #     # 计算总价
        #     total = sum(item.price * item.num for item in cart_items)
        #
        #     # 生成订单号和交易编号
        #     order_num = uuid.uuid4().hex[:32]
        #     trade_no = f"TRADE{timezone.now().strftime('%Y%m%d%H%M%S')}"
        #
        #     # 创建订单
        #     order = Order.objects.create(
        #         userinfo=request.user,
        #         address=address,
        #         total_amount=total,
        #         status='待支付',
        #         order_num=order_num,
        #         trade_no=trade_no,
        #         pay='alipay'  # 默认支付方式
        #     )
        #
        #     # 创建订单项
        #     order_items = []
        #     for item in cart_items:
        #         order_item = Orderitem.objects.create(
        #             order=order,
        #             goods=item.goods,
        #             quantity=item.num,
        #             count=item.price
        #         )
        #         order_items.append(order_item)
        #
        #     # 清空购物车
        #     cart_items.update(is_delete=True)
        #
        #     # 返回成功响应
        #     return Response({
        #         'status': 'success',
        #         'message': '订单创建成功',
        #         'order_id': order.id,
        #         'order_num': order_num,
        #         'total_amount': total
        #     }, status=status.HTTP_201_CREATED)
        try:
            real_name = RealName.objects.filter(rUserInfo=request.user).first()
            if not real_name or not real_name.is_verified:
                return Response({
                    'status': 'error',
                    'message': '请先完成实名认证'
                }, status=status.HTTP_400_BAD_REQUEST)

            address_id = request.data.get('address_id')
            if not address_id:
                return Response({
                    'status': 'error',
                    'message': '请选择收货地址'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                address = Address.objects.get(id=address_id, aUserInfo=request.user)
            except Address.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': '收货地址不存在'
                }, status=status.HTTP_400_BAD_REQUEST)

            cart_queryset = CartItem.objects.select_related('goods').filter(
                userInfo=request.user,
                is_delete=False,
            )
            invalid_items = list(
                cart_queryset.filter(goods__isnull=True).values_list('id', flat=True)
            )
            if invalid_items:
                cart_queryset.filter(id__in=invalid_items).update(is_delete=True)
                log_flow_debug(
                    'checkout',
                    'Removed incomplete cart items before checkout',
                    user_id=getattr(request.user, 'id', None),
                    cart_item_ids=",".join(map(str, invalid_items)),
                )

            cart_items = list(cart_queryset.filter(goods__isnull=False))
            if not cart_items:
                return Response(
                    {'status': 'error', 'message': '购物车为空'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            log_flow_debug(
                'checkout',
                'Checkout initiated',
                user_id=getattr(request.user, 'id', None),
                address_id=address_id,
                item_count=len(cart_items),
            )

            order_num = uuid.uuid4().hex[:32]
            trade_no = f"TRADE{timezone.now().strftime('%Y%m%d%H%M%S')}"

            total_amount = sum(
                (item.num * item.goods.price for item in cart_items),
                Decimal('0.00'),
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            line_items_payload = []
            with transaction.atomic():
                order = Order.objects.create(
                    userinfo=request.user,
                    address=address,
                    order_num=order_num,
                    trade_no=trade_no,
                    total_amount=total_amount,
                    status='待支付',
                    pay='alipay',
                )

                order_items = []
                for item in cart_items:
                    line_total = (item.goods.price * item.num).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    order_items.append(
                        Orderitem(
                            order=order,
                            goods=item.goods,
                            quantity=item.num,
                            count=item.goods.price,
                        )
                    )
                    line_items_payload.append(
                        {
                            'goods_id': item.goods_id,
                            'quantity': item.num,
                            'unit_price': str(item.goods.price),
                            'line_total': str(line_total),
                        }
                    )
                Orderitem.objects.bulk_create(order_items)

                CartItem.objects.filter(id__in=[item.id for item in cart_items]).update(is_delete=True)

                enqueue_order_event(
                    order,
                    event_type='order.created',
                    payload={
                        'items': line_items_payload,
                        'source': 'checkout.api',
                    },
                    headers={'initiator': 'checkout.api'},
                    idempotency_key=f'order:{order.id}:created',
                )

                transaction.on_commit(
                    lambda order_id=order.id: _queue_order_confirmation_task(order_id)
                )

            log_flow_debug(
                'checkout',
                'Order created',
                user_id=getattr(request.user, 'id', None),
                order_id=order.id,
                total=str(total_amount),
            )

            return Response(
                {
                    'status': 'success',
                    'message': '订单已创建',
                    'order_id': order.id,
                    'total_amount': str(total_amount),
                    'order_num': order_num,
                    'trade_no': trade_no
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as exc:
            logger.exception(
                "创建订单失败 user=%s", getattr(request.user, 'id', None)
            )
            log_flow_debug(
                'checkout',
                'Checkout failed',
                user_id=getattr(request.user, 'id', None),
                error=str(exc),
            )
            return Response({
                'status': 'error',
                'message': f'创建订单失败: {exc}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request, order_id):
        """处理 GET 请求，返回订单详情"""
        order = get_object_or_404(Order, id=order_id, userinfo=request.user)
        order_items = order.orderitem_set.all()

        order_serializer = OrderSerializer(order)
        order_items_serializer = OrderitemSerializer(order_items, many=True)

        return Response({
            'order': order_serializer.data,
            'order_items': order_items_serializer.data
        })


class OrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """获取用户的所有订单"""
        orders = Order.objects.filter(userinfo=request.user).order_by('-create_time')
        serializer = OrderSerializer(orders, many=True)
        return Response({
            'status': 'success',
            'orders': serializer.data
        })
