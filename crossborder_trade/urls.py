"""
URL configuration for crossborder_trade project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include ,re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# media配置路由
from django.conf import settings
from django.views.static import serve
from django.conf.urls.static import static

from userapp.views import CustomTokenObtainPairView  # 新增导入

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),  # 修改点
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # 包含 your_app_name 应用的路由
    path('api/', include('userapp.urls')),  # 假设你的 API 接口都以 /user/ 开头
    # 商城
    path('api/trade/', include('goodsapp.urls')),
    # 购物车
    path('api/cart/', include('cartapp.urls')),
    # 订单
    path('api/order/', include('orderapp.urls')),
    # 支付
    path('api/payment/', include('paymentapp.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Health check endpoints
    path('healthz/', include('health.urls', namespace='health')),

]
# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
