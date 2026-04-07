# Use a stable, official Python runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Install Python dependencies from the root requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create staticfiles directory to avoid warnings
RUN mkdir -p Backend/staticfiles

# Run collectstatic during build phase
# (Using a dummy SECRET_KEY if needed, but here we just ensure the dir exists)
RUN cd Backend && python manage.py collectstatic --noinput --clear || true

# Ensure the start script is executable
RUN chmod +x Backend/scripts/render_start.sh

# Expose the port (Render defaults to 10000)
EXPOSE 10000

# Run the app
CMD ["sh", "Backend/scripts/render_start.sh"]
