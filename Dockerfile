# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1

################################################################################
# API CONFIGURATION - COMMENTED OUT
# The API has been deployed separately. This repository is now worker-only.
################################################################################
# Expose port for FastAPI
# EXPOSE 8080

# Health check for API
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD curl -f http://localhost:8080/health || exit 1

################################################################################
# WORKER CONFIGURATION - ACTIVE
################################################################################
# Default command runs SQS Worker (4 parallel processes)
# This can be overridden in docker-compose or deployment platform
CMD ["python", "-m", "app.worker"]
