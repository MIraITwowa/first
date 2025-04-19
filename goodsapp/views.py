from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
# 分页器
# from rest_framework import status
# from rest_framework.pagination import PageNumberPagination
from goodsapp.models import Category, Goods
from goodsapp.serializers import CategorySerializer, GoodsListSerializer, GoodsDetailPageSerializer,GoodsSerializer


# from django.http import FileResponse, HttpResponseNotFound
# from django.conf import settings
# import os


# 个性推荐
# from django.http import HttpRequest


# # 自定义分页类
# class GoodsPagination(PageNumberPagination):
#     page_size = 8
#     page_size_query_param = 'page_size'
#     max_page_size = 100


# # 装饰器：实现推荐商品功能  以后可能会用到结算页面之下
# def recommend_view(func):
#     def _wrapper(request: HttpRequest, *args, **kwargs):
#         # 从cookie中获取用户访问的goodid字符串
#         c_goodidStr = request.COOKIES.get('recommend', '')
#
#         # 专门存放goodsid的列表  ['1','2']  ==>   '1 2'
#         goodsIdList = [gid for gid in c_goodidStr.split() if gid.strip()]
#
#         # 获取当前请求的商品id
#         goodsid = kwargs.get('goodsid')
#
#         # 如果有商品id，才进行推荐商品的处理
#         if goodsid:
#             # 专门存放推荐商品对象的列表
#             goodsObjList = [
#                                Goods.objects.get(id=ggid) for ggid in goodsIdList
#                                if ggid != goodsid and Goods.objects.get(id=ggid).category_id == Goods.objects.get(
#                     id=goodsid).category_id
#                            ][:4]
#
#             # 将推荐商品对象列表传递给func函数
#             response = func(request, *args, **kwargs, recommend_list=goodsObjList)
#
#             # 判断用户访问的商品是否已经存在goodsIdList中
#             if goodsid in goodsIdList:
#                 goodsIdList.remove(goodsid)
#                 goodsIdList.insert(0, goodsid)
#             else:
#                 goodsIdList.insert(0, goodsid)
#
#             # 将用户每次访问的商品ID存放在cookie中
#             response.set_cookie('recommend', ' '.join(goodsIdList), max_age=3 * 24 * 60 * 60)
#         else:
#             response = func(request, *args, **kwargs)
#
#         return response
#
#     return _wrapper
#
# 获取类名

@api_view(['GET'])
def get_categories(request):
    """原有的获取分类列表的视图函数，用于导航栏"""
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response({
        'status': 'success',
        'categories': serializer.data
    })


@api_view(['GET'])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response({
        'status': 'success',
        'categories': serializer.data
    })


@api_view(['GET'])
def category_goods(request, cid):
    try:
        category = Category.objects.get(id=cid)
        goods = Goods.objects.filter(category=category)
        serializer = GoodsListSerializer(goods, many=True)
        return Response({
            'status': 'success',
            'category': CategorySerializer(category).data,
            'goods': serializer.data
        })
    except Category.DoesNotExist:
        return Response({
            'status': 'error',
            'message': '分类不存在'
        }, status=404)


@api_view(['GET'])
def goods_detail(request, goods_id):
    try:
        goods = Goods.objects.get(id=goods_id)
        serializer = GoodsDetailPageSerializer(goods)
        return Response({
            'status': 'success',
            'goods': serializer.data
        })
    except Goods.DoesNotExist:
        return Response({
            'status': 'error',
            'message': '商品不存在'
        }, status=404)


class GoodsViewSet(viewsets.ModelViewSet):
    queryset = Goods.objects.all()
    serializer_class = GoodsSerializer

    def get_serializer_context(self):
        """添加语言参数到序列化器上下文"""
        context = super().get_serializer_context()
        # 从请求头或查询参数中获取语言设置
        lang = self.request.query_params.get('lang') or \
               self.request.headers.get('Accept-Language', 'zh').split(',')[0]
        # 只支持中文和英文
        context['language'] = lang if lang in ['zh', 'en'] else 'zh'
        return context

    def create(self, request, *args, **kwargs):
        """创建商品时处理多语言数据"""
        # 获取多语言数据
        i18n_fields = {
            'name_i18n': request.data.get('name_i18n', {}),
            'description_i18n': request.data.get('description_i18n', {}),
            'brand_i18n': request.data.get('brand_i18n', {})
        }

        # 添加多语言数据到序列化器上下文
        context = self.get_serializer_context()
        context.update(i18n_fields)

        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)

    def update(self, request, *args, **kwargs):
        """更新商品时处理多语言数据"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # 获取多语言数据
        i18n_fields = {
            'name_i18n': request.data.get('name_i18n', {}),
            'description_i18n': request.data.get('description_i18n', {}),
            'brand_i18n': request.data.get('brand_i18n', {})
        }

        # 添加多语言数据到序列化器上下文
        context = self.get_serializer_context()
        context.update(i18n_fields)

        serializer = self.get_serializer(instance, data=request.data,
                                         partial=partial, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)