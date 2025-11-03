from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import redis
import json


class HealthzView(View):
    """Basic health check endpoint"""
    
    def get(self, request):
        return JsonResponse({
            'status': 'healthy',
            'service': 'crossborder-trade-api'
        })


class ReadyzView(View):
    """Readiness check endpoint - checks dependencies"""
    
    def get(self, request):
        checks = {}
        overall_healthy = True
        
        # Check database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks['database'] = 'healthy'
        except Exception as e:
            checks['database'] = f'unhealthy: {str(e)}'
            overall_healthy = False
        
        # Check Redis connectivity
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                checks['redis'] = 'healthy'
            else:
                checks['redis'] = 'unhealthy: cache set/get failed'
                overall_healthy = False
        except Exception as e:
            checks['redis'] = f'unhealthy: {str(e)}'
            overall_healthy = False
        
        # Check Kafka connectivity (if enabled)
        if getattr(settings, 'KAFKA_ENABLED', False):
            try:
                from kafka import KafkaProducer
                import kafka.errors
                
                producer = KafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    request_timeout_ms=5000,
                    max_block_ms=5000,
                )
                
                # Try to get metadata (this will fail if Kafka is not reachable)
                metadata = producer.bootstrap_connected()
                if metadata:
                    checks['kafka'] = 'healthy'
                else:
                    checks['kafka'] = 'unhealthy: bootstrap not connected'
                    overall_healthy = False
                producer.close()
                
            except Exception as e:
                checks['kafka'] = f'unhealthy: {str(e)}'
                overall_healthy = False
        else:
            checks['kafka'] = 'disabled'
        
        status_code = 200 if overall_healthy else 503
        return JsonResponse({
            'status': 'ready' if overall_healthy else 'not ready',
            'checks': checks
        }, status=status_code)


class CeleryHealthView(View):
    """Celery worker health check"""
    
    def get(self, request):
        try:
            from celery import current_app
            
            # Check if we can ping the workers
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            
            if stats:
                return JsonResponse({
                    'status': 'healthy',
                    'workers': list(stats.keys()),
                    'worker_count': len(stats)
                })
            else:
                return JsonResponse({
                    'status': 'unhealthy',
                    'message': 'No active workers found'
                }, status=503)
                
        except Exception as e:
            return JsonResponse({
                'status': 'unhealthy',
                'message': str(e)
            }, status=503)