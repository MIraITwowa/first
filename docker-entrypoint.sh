#!/bin/bash
set -e

# Function to wait for a service
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local timeout=${4:-30}
    
    echo "Waiting for $service to be ready at $host:$port..."
    
    for i in $(seq 1 $timeout); do
        if nc -z $host $port; then
            echo "$service is ready!"
            return 0
        fi
        echo "Waiting for $service... ($i/$timeout)"
        sleep 1
    done
    
    echo "Timeout waiting for $service at $host:$port"
    exit 1
}

# Function to wait for MySQL with proper protocol detection
wait_for_mysql() {
    local host=$1
    local port=$2
    local timeout=${3:-30}
    
    echo "Waiting for MySQL to be ready at $host:$port..."
    
    for i in $(seq 1 $timeout); do
        # Try to connect to MySQL
        if mysqladmin ping -h"$host" -P"$port" --silent; then
            echo "MySQL is ready!"
            return 0
        fi
        echo "Waiting for MySQL... ($i/$timeout)"
        sleep 1
    done
    
    echo "Timeout waiting for MySQL at $host:$port"
    exit 1
}

# Function to wait for Kafka
wait_for_kafka() {
    local bootstrap_servers=$1
    local timeout=${2:-30}
    
    echo "Waiting for Kafka to be ready at $bootstrap_servers..."
    
    # Parse bootstrap servers to get first broker
    IFS=',' read -ra SERVERS <<< "$bootstrap_servers"
    first_server=${SERVERS[0]}
    IFS=':' read -ra ADDR <<< "$first_server"
    host=${ADDR[0]}
    port=${ADDR[1]}
    
    for i in $(seq 1 $timeout); do
        if nc -z $host $port; then
            echo "Kafka is ready!"
            return 0
        fi
        echo "Waiting for Kafka... ($i/$timeout)"
        sleep 1
    done
    
    echo "Timeout waiting for Kafka at $bootstrap_servers"
    exit 1
}

# Parse DATABASE_URL to get host and port
parse_db_url() {
    local db_url=$1
    if [[ $db_url == mysql://* ]]; then
        # Remove mysql:// prefix
        local conn=${db_url#mysql://}
        # Split at @ to separate credentials from host:port/database
        local host_part=${conn#*@}
        # Split at / to separate host:port from database
        local host_port=${host_part%/*}
        echo $host_port
    fi
}

# Main execution
echo "Starting Django application..."

# Wait for database if not using SQLite
if [ "$USE_SQLITE" != "True" ]; then
    if [ -n "$DATABASE_URL" ]; then
        # Parse DATABASE_URL
        host_port=$(parse_db_url "$DATABASE_URL")
        IFS=':' read -ra ADDR <<< "$host_port"
        db_host=${ADDR[0]}
        db_port=${ADDR[1]:-3306}
    else
        db_host=${DB_HOST:-127.0.0.1}
        db_port=${DB_PORT:-3306}
    fi
    
    wait_for_mysql $db_host $db_port
fi

# Wait for Redis
if [ -n "$REDIS_URL" ]; then
    # Parse Redis URL
    redis_url=${REDIS_URL#redis://}
    redis_host_port=${redis_url%/*}
    IFS=':' read -ra ADDR <<< "$redis_host_port"
    redis_host=${ADDR[0]}
    redis_port=${ADDR[1]:-6379}
else
    redis_host=${REDIS_HOST:-127.0.0.1}
    redis_port=${REDIS_PORT:-6379}
fi

wait_for_service $redis_host $redis_port "Redis"

# Wait for Kafka if enabled
if [ "$KAFKA_ENABLED" = "True" ] && [ -n "$KAFKA_BOOTSTRAP_SERVERS" ]; then
    wait_for_kafka "$KAFKA_BOOTSTRAP_SERVERS"
fi

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if requested
if [ "$CREATE_SUPERUSER" = "True" ]; then
    echo "Creating superuser..."
    python manage.py create_superuser_if_not_exists
fi

# Collect static files (only in production)
if [ "$DEBUG" != "True" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

# Execute the passed command
echo "Executing command: $@"
exec "$@"