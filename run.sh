#!/bin/bash
set -euo pipefail

APP_NAME="django-asgi-app"
HOST="0.0.0.0"
PORT="8000"
WORKERS="4"
WORKER_CONNECTIONS="1000"
LOG_LEVEL="info"

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source env/bin/activate

# Start Redis server
echo "🟥 Starting Redis server..."
redis-server --daemonize yes
echo "✔ Redis started."

# Apply database migrations
echo "📦 Applying Django migrations..."
python manage.py migrate --noinput

# Collect static files (optional: remove if not needed)
# echo "📁 Collecting static files..."
# python manage.py collectstatic --noinput

# Start ASGI server using Gunicorn with Uvicorn workers
echo "🚀 Starting $APP_NAME using Gunicorn + UvicornWorker..."
gunicorn core.asgi:application \
    --bind "$HOST:$PORT" \
    --workers "$WORKERS" \
    --worker-class "uvicorn.workers.UvicornWorker" \
    --worker-connections "$WORKER_CONNECTIONS" \
    --log-level "$LOG_LEVEL"
