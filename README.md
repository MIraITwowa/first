# Crossborder Trade Backend

A Django 5 based backend that powers a cross-border e-commerce platform. The system exposes a REST API for user management, product browsing, carts, orders, and payments. Background workloads are handled with Celery workers backed by Redis, with scheduled jobs provided by Celery Beat and operational monitoring via Flower.

## 🚀 Quick Start

The fastest way to get started is with Docker Compose:

```bash
# Clone and setup
git clone <repository-url>
cd crossborder-trade
cp .env.example .env

# Start all services (MySQL, Redis, Kafka, Django, Celery, Flower)
make up

# Access the application
# API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs/
# Admin: http://localhost:8000/admin/
# Flower: http://localhost:5555
```

The first run will automatically:
- Create and migrate the database
- Create an admin superuser (admin/admin123)
- Seed sample data (optional: `make seed`)

## 📋 Requirements

### Core Dependencies
- **Python 3.12+** - Runtime environment
- **Django 5.1** - Web framework
- **Django REST Framework** - API framework
- **MySQL 8.0** - Primary database
- **Redis 7** - Cache and message broker
- **Apache Kafka** - Event streaming
- **Celery** - Background task processing

### Python Packages
```bash
pip install -r requirements.txt
```

Key packages include:
- `django>=5.1,<6.0` - Core framework
- `djangorestframework>=3.15` - REST API
- `djangorestframework-simplejwt>=5.3` - JWT authentication
- `mysqlclient>=2.2` - MySQL driver
- `celery>=5.4` - Task queue
- `redis>=5.0` - Redis client
- `kafka-python>=2.0` - Kafka client
- `drf-spectacular>=0.27.0` - OpenAPI documentation
- `django-environ>=0.11.2` - Environment configuration

## ⚙️ Environment Configuration

Copy the provided `.env.example` file to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

### Required Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key (change in production!) | `change-me-in-production-use-long-random-string` |
| `DJANGO_DEBUG` | Enable debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DB_HOST` | MySQL database host | `127.0.0.1` |
| `DB_NAME` | Database name | `crossborder_trade` |
| `DB_USER` | Database username | `root` |
| `DB_PASSWORD` | Database password | `2642` |
| `REDIS_URL` | Redis connection URL | `redis://127.0.0.1:6379/0` |

### Optional Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `JWT_SIGNING_KEY` | JWT signing key (separate from Django secret) | `None` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker list | `localhost:9092` |
| `KAFKA_ENABLED` | Enable Kafka integration | `True` |
| `CREATE_SUPERUSER` | Auto-create superuser on startup | `False` |
| `SUPERUSER_USERNAME` | Superuser username | `admin` |
| `SUPERUSER_PASSWORD` | Superuser password | `admin123` |
| `LOG_LEVEL` | Application log level | `INFO` |
| `LOG_FORMAT` | Log format (`console` or `json`) | `console` |

### Celery Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `CELERY_BROKER_URL` | Redis instance used as broker | `redis://127.0.0.1:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis instance used for task results | `redis://127.0.0.1:6379/1` |
| `CELERY_DEFAULT_QUEUE` | Default queue name | `default` |
| `CELERY_ORDERS_QUEUE` | Queue for order life-cycle tasks | `orders` |
| `CELERY_PAYMENTS_QUEUE` | Queue for payment processing tasks | `payments` |
| `CELERY_NOTIFICATIONS_QUEUE` | Queue for notification fan-out | `notifications` |
| `CELERY_WORKER_CONCURRENCY` | Worker concurrency for local runs | `4` |

### Kafka & Outbox Settings

| Variable | Description | Default |
| --- | --- | --- |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker list used by the producer | `localhost:9092` |
| `KAFKA_CLIENT_ID` | Client identifier used for Kafka connections | `crossborder-trade-api` |
| `KAFKA_ORDERS_TOPIC` | Topic that receives order domain events | `order-events` |
| `KAFKA_STOCK_TOPIC` | Topic that receives stock/inventory events | `stock-events` |
| `KAFKA_PRODUCER_IDEMPOTENCE` | Enables idempotent Kafka producer semantics | `True` |
| `OUTBOX_DISPATCH_BATCH_SIZE` | Batch size for each Celery dispatch run | `50` |
| `OUTBOX_MAX_ATTEMPTS` | Maximum delivery attempts before dead-lettering | `5` |

## 🏃‍♂️ Running the Application

### Option 1: Docker Compose (Recommended)

```bash
# Start all services
make up

# View logs
make logs

# Stop all services
make down

# Check service status
make status
```

### Option 2: Local Development

1. Install dependencies and setup environment:
   ```bash
   make setup
   ```

2. Start required services (MySQL, Redis, Kafka) manually or use Docker for dependencies.

3. Run database migrations:
   ```bash
   make migrate
   ```

4. Create superuser:
   ```bash
   make createsuperuser
   ```

5. Seed sample data:
   ```bash
   make seed
   ```

6. Start the Django development server:
   ```bash
   make dev
   ```

### Option 3: Individual Services

```bash
# Start Django server
python manage.py runserver

# Start Celery worker
make worker

# Start Celery beat scheduler
make beat

# Start Flower monitoring
make flower
```

## 📊 API Documentation

The application exposes comprehensive API documentation:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### Health Check Endpoints

- **Basic Health**: http://localhost:8000/healthz/
- **Readiness Check**: http://localhost:8000/healthz/ready
- **Celery Health**: http://localhost:8000/healthz/celery

## 🛠️ Development Tools

### Management Commands

```bash
# Create superuser automatically
python manage.py create_superuser_if_not_exists

# Seed sample data
python manage.py seed_data

# Database operations
make migrate          # Run migrations
make createsuperuser  # Create admin user
make seed            # Load sample data
make reset-db        # Reset and reseed database (dev only)
```

### Monitoring

- **Flower**: http://localhost:5555 - Celery task monitoring
- **Health Checks**: Built-in health endpoints for service monitoring
- **Logs**: Structured logging with JSON format support

## 📦 Architecture Overview

### Core Components

1. **Django Web Server** - Handles HTTP requests and API endpoints
2. **MySQL Database** - Primary data storage
3. **Redis** - Caching and Celery message broker
4. **Kafka** - Event streaming for order and stock events
5. **Celery Workers** - Background task processing
6. **Celery Beat** - Scheduled task execution
7. **Flower** - Task monitoring dashboard

### Application Modules

- **userapp**: User management, authentication, addresses
- **goodsapp**: Product catalog and categories
- **cartapp**: Shopping cart functionality
- **orderapp**: Order processing and lifecycle
- **paymentapp**: Payment processing
- **eventstream**: Kafka outbox pattern implementation
- **health**: Health check endpoints

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test modules
python manage.py test userapp.tests
python manage.py test goodsapp.tests
```

### Test Configuration

Tests use SQLite in-memory database for speed. Set `CELERY_TASK_ALWAYS_EAGER=True` in test settings to run tasks synchronously.

## 🔧 Troubleshooting

### Common Issues

**Database Connection Issues**
```bash
# Check database connectivity
make db-shell

# Reset database
make reset-db
```

**Celery Workers Not Processing Tasks**
```bash
# Check worker status
make logs-worker

# Restart workers
docker compose restart worker
```

**Kafka Connection Issues**
```bash
# Check Kafka logs
docker compose logs kafka

# Verify Kafka topics
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

**Service Health**
```bash
# Check all service status
make status

# Check individual service logs
make logs-web
make logs-db
```

### Performance Tuning

- **Database**: Use connection pooling, optimize queries
- **Redis**: Enable persistence for production
- **Celery**: Adjust worker concurrency based on CPU cores
- **Kafka**: Tune batch sizes and compression

## 🚀 Deployment

### Production Considerations

1. **Security**
   - Use strong, unique `DJANGO_SECRET_KEY` and `JWT_SIGNING_KEY`
   - Set `DJANGO_DEBUG=False`
   - Configure proper `ALLOWED_HOSTS`
   - Use HTTPS in production

2. **Database**
   - Use MySQL with proper replication
   - Regular backups
   - Connection pooling

3. **Caching**
   - Redis with persistence
   - Proper memory allocation
   - Monitoring

4. **Monitoring**
   - Health checks
   - Log aggregation
   - Metrics collection

### Docker Production Deployment

```bash
# Build production images
make build

# Deploy with production settings
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
