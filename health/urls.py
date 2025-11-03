from django.urls import path
from .views import HealthzView, ReadyzView, CeleryHealthView

app_name = 'health'

urlpatterns = [
    path('', HealthzView.as_view(), name='healthz'),
    path('ready', ReadyzView.as_view(), name='readyz'),
    path('celery', CeleryHealthView.as_view(), name='celery'),
]