.PHONY: help setup dev up down logs migrate createsuperuser seed test clean shell

# Default target
help:
	@echo "Crossborder Trade Django E-commerce Backend"
	@echo ""
	@echo "Available commands:"
	@echo "  setup      - Install dependencies and set up environment"
	@echo "  dev        - Run development server"
	@echo "  up         - Start all services with Docker Compose"
	@echo "  down       - Stop all services"
	@echo "  logs       - Show logs for all services"
	@echo "  migrate    - Run database migrations"
	@echo "  createsuperuser - Create admin superuser"
	@echo "  seed       - Seed database with sample data"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean up Docker containers and images"
	@echo "  shell      - Open Django shell"
	@echo "  flower     - Start Flower monitoring"

# Setup development environment
setup:
	@echo "Setting up development environment..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	cp .env.example .env
	@echo "Setup complete! Please edit .env file with your configuration."

# Development server
dev:
	@echo "Starting Django development server..."
	python manage.py runserver 0.0.0.0:8000

# Docker Compose commands
up:
	@echo "Starting all services..."
	docker compose up -d
	@echo "Services are starting. Use 'make logs' to see progress."
	@echo "API will be available at http://localhost:8000"
	@echo "Flower monitoring at http://localhost:5555"

down:
	@echo "Stopping all services..."
	docker compose down

logs:
	docker compose logs -f

# Database operations
migrate:
	@echo "Running database migrations..."
	docker compose exec web python manage.py migrate

createsuperuser:
	@echo "Creating superuser..."
	docker compose exec web python manage.py createsuperuser

seed:
	@echo "Seeding database with sample data..."
	docker compose exec web python manage.py seed_data

# Testing
test:
	@echo "Running tests..."
	docker compose exec web python manage.py test

# Cleanup
clean:
	@echo "Cleaning up Docker containers and images..."
	docker compose down -v --rmi all

# Development utilities
shell:
	docker compose exec web python manage.py shell

flower:
	docker compose exec flower celery -A crossborder_trade flower --port=5555

# Worker management
worker:
	@echo "Starting Celery worker..."
	celery -A crossborder_trade worker -Q default,orders,payments,notifications -l info

beat:
	@echo "Starting Celery beat scheduler..."
	celery -A crossborder_trade beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Database reset (development only)
reset-db:
	@echo "Resetting database (development only)..."
	docker compose exec web python manage.py flush --noinput
	docker compose exec web python manage.py migrate
	$(MAKE) seed

# Check services status
status:
	@echo "Checking service status..."
	docker compose ps

# Show logs for specific service
logs-web:
	docker compose logs -f web

logs-worker:
	docker compose logs -f worker

logs-beat:
	docker compose logs -f beat

logs-db:
	docker compose logs -f mysql

# Build Docker images
build:
	@echo "Building Docker images..."
	docker compose build

# Rebuild and restart
rebuild:
	@echo "Rebuilding and restarting services..."
	docker compose build --no-cache
	docker compose up -d

# Access database
db-shell:
	docker compose exec mysql mysql -uroot -p2642 crossborder_trade

# Generate requirements
requirements:
	@echo "Generating requirements.txt..."
	pip freeze > requirements.txt

# Security check
security:
	@echo "Running security checks..."
	docker compose exec web python manage.py check --deploy

# Load fixtures (if any exist)
loaddata:
	docker compose exec web python manage.py loaddata fixtures/initial_data.json

# Dump data
dumpdata:
	docker compose exec web python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > fixtures/initial_data.json