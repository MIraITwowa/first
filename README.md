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

### Kafka & outbox settings

| Variable | Description | Default |
| --- | --- | --- |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker list used by the producer | `localhost:9092` |
| `KAFKA_CLIENT_ID` | Client identifier used for Kafka connections | `crossborder-trade-api` |
| `KAFKA_ORDERS_TOPIC` | Topic that receives order domain events | `order-events` |
| `KAFKA_STOCK_TOPIC` | Topic that receives stock/inventory events | `stock-events` |
| `KAFKA_PRODUCER_IDEMPOTENCE` | Enables idempotent Kafka producer semantics | `True` |
| `OUTBOX_DISPATCH_BATCH_SIZE` | Batch size for each Celery dispatch run | `50` |
| `OUTBOX_MAX_ATTEMPTS` | Maximum delivery attempts before dead-lettering | `5` |

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

Celery Beat ships with schedules for expiring unpaid orders and for draining the Kafka outbox. Update `ORDER_EXPIRATION_MINUTES` or tune schedules via the Django admin or database entries when required.

### Flower monitoring

Flower provides a lightweight UI for monitoring Celery workers:

```bash
celery -A crossborder_trade flower --port=${FLOWER_PORT:-5555}
```

Visit `http://localhost:5555` to inspect task queues, worker health, and retry history.

## Kafka outbox

The `eventstream` Django app implements a transactional outbox for reliable Kafka delivery. Order creation and status transitions insert rows into the `OutboxEvent` table inside the same database transaction. A scheduled Celery task (`orderapp.tasks.publish_outbox_events`) drains pending rows in batches, publishes them with idempotent producer keys, and moves failures to a dead-letter state after the configured number of retries.

Metrics-friendly logs are emitted for each dispatcher run and failing attempts keep their retry schedule via exponential backoff. Inspect the outbox table to understand current delivery status or replay dead-lettered events.

### Running Kafka locally

A lightweight single-node broker is enough for development. The following Docker Compose snippet spins up Kafka in KRaft mode using the Bitnami image:

```yaml
version: '3.8'
services:
  kafka:
    image: bitnami/kafka:3
    ports:
      - "9092:9092"
    environment:
      - ALLOW_PLAINTEXT_LISTENER=yes
      - KAFKA_CFG_PROCESS_ROLES=broker,controller
      - KAFKA_CFG_NODE_ID=0
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=0@kafka:9093
      - KAFKA_CFG_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092
```

Save the snippet as `docker-compose.kafka.yml` and run `docker compose -f docker-compose.kafka.yml up`. Point `KAFKA_BOOTSTRAP_SERVERS` at `localhost:9092`, then start the Django server and Celery workers; the outbox dispatcher will publish to Kafka automatically.

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
