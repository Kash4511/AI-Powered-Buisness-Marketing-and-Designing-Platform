#!/usr/bin/env bash
# scripts/render_start.sh

# Exit on error
set -e

echo "🚀 Starting Render deployment script..."

# Change to the Backend directory where manage.py is located
cd Backend

# Retry logic for database migrations
MAX_RETRIES=5
RETRY_COUNT=0
RETRY_DELAY=5

until python manage.py migrate --noinput || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "⚠️ Migration failed. Retrying in $RETRY_DELAY seconds... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep $RETRY_DELAY
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "❌ Database migrations failed after $MAX_RETRIES retries. Exiting."
  exit 1
fi

echo "✅ Migrations completed successfully."

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "🌐 Starting Gunicorn on port $PORT..."
exec gunicorn django_project.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --graceful-timeout 120 \
    --keep-alive 5
