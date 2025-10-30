# paymentapp/views.py
from django.http import HttpResponse  # 这里注释掉了JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings
from .models import Payment
from .serializers import PaymentSerializer, PaymentSuccessSerializer
from orderapp.models import Order
import logging
import random

logger = logging.getLogger(__name__)


def _queue_payment_success_task(payment_id: int) -> None:
    try:
        from .tasks import handle_successful_payment
    except ModuleNotFoundError:
        logger.warning("未安装 Celery，无法调度支付成功任务。")
        return

    try:
        handle_successful_payment.delay(payment_id)
    except Exception as exc:  # pragma: no cover - Celery misconfiguration fallback
        logger.warning("支付后处理任务入队失败: %s", exc)


@api_view(['POST'])
@csrf_exempt
def mock_pay(request):
    """
    模拟支付接口
    接收参数：
    - order_id: 订单ID
    - total_amount: 支付金额
    """
    if request.method == 'POST':
        try:
            # 获取订单号和金额
            order_id = request.data.get('order_id')
            total_amount = request.data.get('total_amount')

            # 获取订单信息
            order = Order.objects.get(id=order_id)

            # 模拟支付逻辑
            payment_status = 'success' if random.random() < settings.MOCK_PAYMENT_SUCCESS_RATE else 'failed'

            # 创建支付记录
            serializer = PaymentSerializer(data={
                'order': order.id,
                'amount': total_amount,
                'payment_method': 'alipay',
                'status': payment_status
            })

            if serializer.is_valid():
                payment = serializer.save()
                payment.status = payment_status
                payment.save(update_fields=['status'])

                if payment_status == 'success':
                    order.update_status('待发货')
                    _queue_payment_success_task(payment.id)

                    return Response({
                        'message': '支付成功',
                        'payment_id': payment.id,
                        'order_status': order.status
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': '支付失败',
                        'payment_id': payment.id
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'error': '支付数据验证失败',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({'error': '订单不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'error': '无效的请求方法'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@csrf_exempt
def mock_notify(request):
    """
    支付回调处理接口
    接收参数：
    - payment_id: 支付记录ID
    """
    if request.method == 'POST':
        payment_id = request.data.get('payment_id')
        try:
            payment = Payment.objects.get(id=payment_id)

            # 检查支付状态，避免重复处理
            if payment.status == 'success':
                return Response({'message': '该支付已处理'}, status=status.HTTP_200_OK)

            # 更新支付状态
            payment.status = 'success'
            payment.save()

            _queue_payment_success_task(payment.id)

            # 更新订单状态
            order = payment.order
            order.update_status('待发货')

            return Response({
                'message': '支付成功',
                'order_status': '待发货'
            }, status=status.HTTP_200_OK)

        except Payment.DoesNotExist:
            return Response({'error': '支付记录不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'error': '无效的请求方法'}, status=status.HTTP_400_BAD_REQUEST)


# # 模拟支付
# @api_view(['POST'])
# @csrf_exempt
# def mock_pay(request):
#     if request.method == 'POST':
#         # 获取订单号和金额
#         order_id = request.data.get('order_id')
#         total_amount = request.data.get('total_amount')
#
#         try:
#             # 获取订单信息
#             order = Order.objects.get(id=order_id)
#         except Order.DoesNotExist:
#             return Response({'error': '订单不存在'}, status=status.HTTP_404_NOT_FOUND)
#
#         # 模拟支付逻辑
#         payment_status = 'success' if random.random() < settings.MOCK_PAYMENT_SUCCESS_RATE else 'failed'
#
#         # 使用序列化器处理支付数据
#         serializer = PaymentSerializer(data={
#             'order': order.id,
#             'amount': total_amount,
#             'payment_method': 'mock',
#             'status': payment_status
#         })
#
#         if serializer.is_valid():
#             payment = serializer.save()
#             # 返回支付结果
#             if payment_status == 'success':
#                 return Response({'message': '支付成功', 'payment_id': payment.id}, status=status.HTTP_200_OK)
#             else:
#                 return Response({'error': '支付失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         else:
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#     else:
#         return Response({'error': '无效的请求方法'}, status=status.HTTP_400_BAD_REQUEST)
#
#
# # 模拟支付回调
# @csrf_exempt
# def mock_notify(request):
#     if request.method == 'POST':
#         # 模拟支付回调逻辑
#         payment_id = request.POST.get('payment_id')
#         try:
#             payment = Payment.objects.get(id=payment_id)
#             payment.status = 'success'
#             payment.save()
#
#             # 使用序列化器处理支付成功数据
#             serializer = PaymentSuccessSerializer(data={
#                 'order_id': payment.order.id,
#                 'amount': payment.amount,
#                 'payment_method': payment.payment_method,
#                 'transaction_id': f'mock_transaction_{payment.id}'
#             })
#
#             if serializer.is_valid():
#                 return HttpResponse('SUCCESS')
#             else:
#                 return HttpResponse('FAIL')
#         except Payment.DoesNotExist:
#             return HttpResponse('FAIL')
#     else:
#         return HttpResponse('INVALID METHOD')
