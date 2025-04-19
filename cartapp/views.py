from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from goodsapp.models import Goods
from userapp.models import Address, RealName
from cartapp.models import CartItem
from orderapp.models import Order, Orderitem
from .serializers import CartItemSerializer

from django.utils import timezone
import uuid


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def add_to_cart(request, goods_id):
#     """
#     将商品添加到购物车
#     """
#     try:
#         # 获取商品数量，默认为1
#         quantity = int(request.data.get('num', 1))
#         if quantity < 1:
#             return Response({
#                 'status': 'error',
#                 'message': '商品数量必须大于0'
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         # 根据传入的商品 ID 获取商品实例
#         goods = get_object_or_404(Goods, id=goods_id)
#
#         # 查找该用户的购物车中是否存在该商品（包括已删除的）
#         cart_item = CartItem.objects.filter(
#             userInfo=request.user,
#             goods=goods
#         ).first()
#
#         if cart_item:
#             # 如果商品已存在（无论是否被标记为删除）
#             if cart_item.is_delete:
#                 # 如果商品被标记为删除，重新启用并设置新数量
#                 cart_item.is_delete = False
#                 cart_item.num = quantity
#             else:
#                 # 如果商品未被删除，增加数量
#                 cart_item.num += quantity
#             cart_item.price = goods.price  # 更新价格（以防商品价格已变）
#             cart_item.save()
#         else:
#             # 如果商品不存在，创建新记录
#             cart_item = CartItem.objects.create(
#                 userInfo=request.user,
#                 goods=goods,
#                 num=quantity,
#                 price=goods.price,
#                 is_delete=False
#             )
#
#         return Response({
#             'status': 'success',
#             'message': '商品已添加到购物车'
#         }, status=status.HTTP_201_CREATED)
#
#     except Exception as e:
#         return Response({
#             'status': 'error',
#             'message': str(e)
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request, goods_id):
    """
    将商品添加到购物车
    """
    try:
        # 获取商品数量，默认为1
        quantity = int(request.data.get('num', 1))
        if quantity < 1:
            return Response({
                'status': 'error',
                'message': '商品数量必须大于0'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 根据传入的商品 ID 获取商品实例
        goods = get_object_or_404(Goods, id=goods_id)

        # 查找该用户的购物车中是否存在该商品（包括已删除的）
        cart_item = CartItem.objects.filter(
            userInfo=request.user,
            goods=goods
        ).first()

        if cart_item:
            # 如果商品已存在（无论是否被标记为删除）
            if cart_item.is_delete:
                # 如果商品被标记为删除，重新启用并设置新数量
                cart_item.is_delete = False
                cart_item.num = quantity
            else:
                # 如果商品未被删除，增加数量
                cart_item.num += quantity
            cart_item.price = goods.price  # 更新价格（以防商品价格已变）
            cart_item.save()
            return Response({
                'status': 'success',
                'message': '商品已更新到购物车'
            }, status=status.HTTP_200_OK)
        else:
            # 如果商品不存在，创建新记录
            cart_item = CartItem.objects.create(
                userInfo=request.user,
                goods=goods,
                num=quantity,
                price=goods.price,
                is_delete=False
            )
            return Response({
                'status': 'success',
                'message': '商品已添加到购物车'
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_detail(request):
    """
    获取购物车详情
    """
    try:
        # 获取当前请求用户的购物车项，并预加载商品信息
        items = CartItem.objects.select_related('goods').filter(
            userInfo=request.user,
            is_delete=False
        )

        # 使用序列化器处理数据
        serializer = CartItemSerializer(items, many=True)
        return Response({'status': 'success', 'cart': serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error in cart_detail: {str(e)}")  # 添加日志
        return Response({'status': 'error', 'message': '获取购物车信息失败'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    """
    从购物车中移除商品
    """
    try:
        # 根据传入的购物车项 ID 从 CartItem 模型中获取对应的购物车项实例
        item = get_object_or_404(CartItem, id=item_id, userInfo=request.user)
        # 设置 is_delete 为 True，表示删除
        item.is_delete = True
        item.save()
        return Response({'status': 'success', 'message': '商品已从购物车中移除'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_cart(request, item_id):
    """
    更新购物车中的商品数量
    """
    try:
        # 根据传入的购物车项 ID 从 CartItem 模型中获取对应的购物车项实例
        item = get_object_or_404(CartItem, id=item_id, userInfo=request.user)
        # 从请求体中获取名为 'num' 的字段值，即用户输入的新数量
        num = request.data.get('num')
        # 检查获取到的数量是否存在
        if num:
            # 将获取到的数量字符串转换为整数类型
            item.num = int(num)
            # 保存更新后的购物车项实例到数据库
            item.save()
            return Response({'status': 'success', 'message': '购物车已更新'}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'error', 'message': '数量不能为空'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 重复的结算逻辑
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def checkout(request):
#     """
#     结账
#     """
#     try:
#         # 检查实名认证状态
#         real_name = RealName.objects.filter(rUserInfo=request.user).first()
#         if not real_name or not real_name.is_verified:
#             return Response({
#                 'status': 'error',
#                 'message': '请先完成实名认证'
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         # 获取当前用户默认地址 - 注意这里使用的是 isdefault 字段
#         # 获取选择的地址
#         address_id = request.data.get('address_id')
#         try:
#             address = Address.objects.get(id=address_id, aUserInfo=request.user)
#         except Address.DoesNotExist:
#             return Response({
#                 'status': 'error',
#                 'message': '收货地址不存在'
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         # 获取当前请求用户的购物车项
#         cart_items = CartItem.objects.filter(
#             userInfo=request.user,
#             is_delete=False
#         ).select_related('goods')
#
#         if not cart_items.exists():
#             return Response(
#                 {'status': 'error', 'message': '购物车为空'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # 生成订单号和交易编号
#         order_num = uuid.uuid4().hex[:32]
#         trade_no = f"TRADE{timezone.now().strftime('%Y%m%d%H%M%S')}"
#
#         # 计算总价
#         total_amount = sum(item.num * item.goods.price for item in cart_items)
#
#         # 创建订单 - 使用正确的字段名
#         order = Order.objects.create(
#             userinfo=request.user,  # 使用模型中定义的 userinfo 字段
#             address=address,
#             order_num=order_num,
#             trade_no=trade_no,
#             total_amount=total_amount,
#             status='待支付',
#             pay='alipay'
#         )
#
#         # 批量创建订单项 - 使用正确的字段名
#         order_items = []
#         for item in cart_items:
#             order_items.append(
#                 Orderitem(
#                     order=order,
#                     goods=item.goods,
#                     quantity=item.num,  # 使用 quantity 字段存储数量
#                     count=item.goods.price  # 使用 count 字段存储价格
#                 )
#             )
#         Orderitem.objects.bulk_create(order_items)
#
#         # 标记购物车项为已删除
#         cart_items.update(is_delete=True)
#
#         return Response(
#             {
#                 'status': 'success',
#                 'message': '订单已创建',
#                 'order_id': order.id,
#                 'total_amount': float(total_amount),  # 转换为浮点数，因为模型使用的是 FloatField
#                 'order_num': order_num,
#                 'trade_no': trade_no
#             },
#             status=status.HTTP_201_CREATED
#         )
#
#     except Exception as e:
#         import traceback
#         traceback.print_exc()  # 打印详细错误信息到控制台
#         return Response(
#             {'status': 'error', 'message': f'结算失败: {str(e)}'},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )
