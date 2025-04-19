from django.urls import path

# 用户app导包
from userapp import views

urlpatterns = [
    # userapp路由操作
    path('user/auth/', views.auth, name='auth'),
    path('user/logout/', views.logout, name='logout'),

    # 地址管理
    path('user/addresses/', views.address_list, name='address'),
    # path('user/address/list', views.address_detail, name='address-list'),
    # path('user/addresses/add', views.address_list, name='address-add'),
    path('user/addresses/<int:pk>/', views.address_detail, name='address-detail'),
    # 实名认证状态
    path('user/verification/status/',views.verification_status, name='verification-status'),

    # 实名认证
    path('user/realname/', views.realname_view, name='realname'),
]
