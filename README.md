# Crossborder Trade Backend

A Django 5 based backend that powers a cross-border e-commerce platform. The system exposes a REST API for user management, product browsing, carts, orders, and payments. Background workloads are handled with Celery workers backed by Redis, with scheduled jobs provided by Celery Beat and operational monitoring via Flower.

## Requirements

Install the project dependencies with pip (a Python 3.12+ virtual environment is recommended):

```bash
pip install -r requirements.txt
```

Core dependencies include:

- Django 5
- Django REST Framework and Simple JWT
- Celery with Redis transport
- django-celery-beat for schedules
- Flower for worker monitoring

Redis is required for the Celery broker/result backend. MySQL powers the relational database, and Kafka is used for event streaming (optional in local development).

## Environment configuration

Copy the provided `.env.example` file to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

Key Celery-related settings:

| Variable | Description | Default |
| --- | --- | --- |
| `CELERY_BROKER_URL` | Redis instance used as broker | `redis://127.0.0.1:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis instance used for task results | `redis://127.0.0.1:6379/1` |
| `CELERY_DEFAULT_QUEUE` | Default queue name | `default` |
| `CELERY_ORDERS_QUEUE` | Queue for order life-cycle tasks | `orders` |
| `CELERY_PAYMENTS_QUEUE` | Queue for payment processing tasks | `payments` |
| `CELERY_NOTIFICATIONS_QUEUE` | Queue for notification fan-out | `notifications` |
| `CELERY_WORKER_CONCURRENCY` | Worker concurrency for local runs | `2` |
| `CELERY_TASK_ALWAYS_EAGER` | Run tasks synchronously (useful for tests) | `False` |

Additional helpful environment flags are documented in `.env.example`, including `FLOWER_PORT` and `KAFKA_BOOTSTRAP_SERVERS` for optional integrations.

## Running the application

1. Apply database migrations and create a superuser if needed.
2. Start the Django development server:

   ```bash
   python manage.py runserver
   ```

### Celery workers & schedulers

Run the Celery worker pointing at this Django project:

```bash
celery -A crossborder_trade worker -Q default,orders,payments,notifications -l info
```

Start Celery Beat (uses `django-celery-beat` by default):

```bash
celery -A crossborder_trade beat -l info
```

Celery Beat ships with placeholder schedules for expiring unpaid orders and an upcoming outbox publisher. Update `ORDER_EXPIRATION_MINUTES` or tune schedules via the Django admin or database entries when required.

### Flower monitoring

Flower provides a lightweight UI for monitoring Celery workers:

```bash
celery -A crossborder_trade flower --port=${FLOWER_PORT:-5555}
```

Visit `http://localhost:5555` to inspect task queues, worker health, and retry history.

## Testing

Celery tasks default to asynchronous execution. Tests can enable eager mode via the `CELERY_TASK_ALWAYS_EAGER` setting or by using the test mixins provided in the suite. Run the Django tests with:

```bash
python manage.py test
```

## Troubleshooting

- **Tasks do not execute:** Confirm Redis is running and the broker URL matches your environment. Worker logs should show successful connection attempts.
- **Stuck or repeated tasks:** Inspect the relevant queue in Flower and ensure worker concurrency/ack settings are sized appropriately.
- **Kafka not available:** The project gracefully skips Kafka notifications when brokers are unreachable; configure `KAFKA_BOOTSTRAP_SERVERS` for full functionality.

For deployment, ensure secrets and environment variables are configured securely and that dedicated worker, beat, and Flower processes are supervised by your process manager of choice.
