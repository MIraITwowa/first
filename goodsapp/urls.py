from django.urls import path

# goodsapp导包
from goodsapp import views

urlpatterns = [
    # userapp路由操作
    path('home/', views.get_categories, name='home'),
    path('categories/', views.category_list, name='category_list'),
    path('category/<int:cid>/', views.category_goods, name='category_goods'),
    path('goods/<int:goods_id>/', views.goods_detail, name='goods_detail'),
]

