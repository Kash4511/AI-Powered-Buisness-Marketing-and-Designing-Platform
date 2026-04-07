#!/usr/bin/env bash
# scripts/render_start.sh

# Exit on error
set -e

echo "🚀 Starting Render deployment script..."

# Change to the Backend directory where manage.py is located
# (In Docker, this is relative to /app)
cd Backend || { echo "❌ Could not find Backend directory"; exit 1; }

# Pre-migration connection test
echo "🔌 Testing database connection..."
python scripts/test_db_connection.py || { echo "❌ Database connection failed. Check your DB environment variables and IP allow-list."; exit 1; }

# Retry logic for database migrations
MAX_RETRIES=3
RETRY_COUNT=0
RETRY_DELAY=5

# We use --fake-initial to help with out-of-sync database tables
until python manage.py migrate --noinput --fake-initial || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "⚠️ Migration failed. This might be due to duplicate tables. Retrying... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep $RETRY_DELAY
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "❌ Database migrations failed after $MAX_RETRIES retries. Exiting."
  exit 1
fi

echo "✅ Migrations completed successfully."

# Ensure static files directory exists
mkdir -p staticfiles

# Collect static files if they are missing
echo "📦 Checking static files..."
python manage.py collectstatic --noinput --clear || echo "⚠️ Warning: collectstatic failed, proceeding anyway."

# Default to port 10000 if PORT is not set
PORT=${PORT:-10000}

# Start Gunicorn
echo "🌐 Starting Gunicorn on port $PORT..."
exec gunicorn django_project.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 300 \
    --graceful-timeout 300 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
