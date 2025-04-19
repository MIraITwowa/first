from django.urls import path  # 导入 Django 的 path 函数，用于定义 URL 模式

from . import views  # 导入当前应用的 views 模块，以便使用其中的视图函数

# 定义 URL 模式列表
urlpatterns = [
    # 定义一个 URL 模式，用于将商品添加到购物车
    # 当访问 /add/<good_id>/ 路径时，调用 views.add_to_cart 视图函数
    # 其中 <int:goods_id> 是一个路径转换器，用于捕获 URL 中的整数 ID 并将其作为参数传递给视图函数
    path('add/<int:goods_id>/', views.add_to_cart, name='add_to_cart'),

    # 定义一个 URL 模式，用于显示购物车详情
    # 当访问 /detail/ 路径时，调用 views.cart_detail 视图函数
    path('detail/', views.cart_detail, name='cart_detail'),

    # 定义一个 URL 模式，用于从购物车中移除商品
    # 当访问 /remove/<item_id>/ 路径时，调用 views.remove_from_cart 视图函数
    # 其中 <int:item_id> 是一个路径转换器，用于捕获 URL 中的整数 ID 并将其作为参数传递给视图函数
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),

    # 定义一个 URL 模式，用于更新购物车中的商品数量
    # 当访问 /update/<item_id>/ 路径时，调用 views.update_cart 视图函数
    # 其中 <int:item_id> 是一个路径转换器，用于捕获 URL 中的整数 ID 并将其作为参数传递给视图函数
    path('update/<int:item_id>/', views.update_cart, name='update_cart'),
]
