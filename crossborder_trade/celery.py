import os
from celery import Celery
from celery.schedules import crontab

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crossborder_trade.settings')

app = Celery('cartapp')
# 从Django设置中读取CELERY配置
app.config_from_object('django.conf:settings', namespace='CELERY')
# 自动发现任务模块
app.autodiscover_tasks()

# 定时任务配置（清理过期订单）
app.conf.beat_schedule = {
    'clean-expired-orders': {
        'task': 'cartapp.tasks.clean_expired_orders',
        'schedule': crontab(minute='*/10'),  # 每10分钟执行一次
    },
}