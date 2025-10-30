try:
    from .celery import app as celery_app
except ModuleNotFoundError:  # Celery may not be installed during initial setup
    celery_app = None

__all__ = ("celery_app",)
