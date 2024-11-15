FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY setup.py .

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/src ./src
COPY --from=builder /app/setup.py .

# Create non-root user
RUN useradd -m -U -u 1000 webhook && \
    mkdir -p /app/certs && \
    chown -R webhook:webhook /app

USER webhook

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports for webhook and metrics
EXPOSE 8443 9090

# Run the application with gunicorn
CMD ["gunicorn", "src.app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8443", "--workers", "4"]
