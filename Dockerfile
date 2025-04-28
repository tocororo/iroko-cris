FROM quay.io/lib/python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends\
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
COPY entrypoint.sh /entrypoint.sh

# Set explicit permissions
RUN chmod -R a+rX /app && \
    chmod +x /entrypoint.sh

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]