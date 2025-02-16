#!/bin/bash
# Exit on error, treat unset variables as errors, and make pipeline failures visible
set -euo pipefail

# Enhanced logging function that supports log levels
log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') [$1] - $2"
}

# Graceful shutdown handler - ensures clean process termination
shutdown() {
    log "INFO" "Received shutdown signal - gracefully stopping services..."
    kill -TERM "$child" 2>/dev/null
    wait "$child"
    exit 0
}

# Set up signal handling for graceful shutdown
trap shutdown SIGTERM SIGINT

log "INFO" "Starting Django application..."

# Ensure DJANGO_SETTINGS_MODULE is set
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"jmw.settings"}

# Simple database connection check - helps prevent migration errors
check_database() {
    python << END
import sys
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '${DJANGO_SETTINGS_MODULE}')
django.setup()
from django.db import connections
try:
    connections['default'].ensure_connection()
    print("Database connection successful!")
except Exception as e:
    print(f"Database connection failed: {e}")
    sys.exit(1)
END
}

# Wait for database to be ready
log "INFO" "Checking database connection..."
until check_database; do
    log "WARN" "Database is unavailable - waiting 2s..."
    sleep 2
done

# Make migrations first
log "INFO" "Making migrations..."
python manage.py makemigrations

# Run migrations
log "INFO" "Running migrations..."
if ! python manage.py migrate --noinput; then
    log "ERROR" "Migrations failed!"
    exit 1
fi

# Create cache table
log "INFO" "Creating cache table..."
if ! python manage.py createcachetable; then
    log "ERROR" "Cache table creation failed!"
    exit 1
fi

# Build Tailwind CSS in production mode
if [ "$DJANGO_DEBUG" != "True" ]; then
    log "INFO" "Building Tailwind CSS..."
    cd theme/static_src && npm run build
    cd ../..
    log "INFO" "Tailwind build completed successfully."

    log "INFO" "Collecting static files..."
    python manage.py collectstatic --noinput
    log "INFO" "Collectstatic completed successfully."
fi

# Start the appropriate server with enhanced configuration
if [ "${DJANGO_DEBUG:-False}" = "True" ]; then
    log "INFO" "Starting development server..."
    python manage.py runserver 0.0.0.0:8000 &
else
    log "INFO" "Starting production server..."
    # Calculate workers based on CPU cores, but keep it reasonable
    WORKERS=${GUNICORN_MAX_WORKERS:-$(( 2 * $(nproc) + 1 ))}
    
    # Increase timeout to allow for longer-running requests
    TIMEOUT=${GUNICORN_TIMEOUT:-120}
    
    exec gunicorn jmw.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers $WORKERS \
        --timeout ${TIMEOUT} \
        --keep-alive ${GUNICORN_KEEP_ALIVE:-75} \
        --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
        --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-50} \
        --log-level info \
        --access-logfile - \
        --error-logfile - \
        --worker-tmp-dir /dev/shm \
        --graceful-timeout 30 \
        --keep-alive 5 &
fi

# Store the server process ID and wait for it
child=$!
wait "$child"