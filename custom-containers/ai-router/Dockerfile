FROM python:3.11-slim-bookworm

LABEL maintainer="docker-stacks"
LABEL version="1.0"
LABEL description="AI Router Service - Optimized for Raspberry Pi 5"

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Torch CPU-only: riduce dimensione e RAM (~400MB in meno rispetto a default)
# Con fallback se download non riesce
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu || \
    pip install --no-cache-dir torch

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY config.py cache.py training.py predictor.py ollama_service.py ui.py router_main.py health_check.py metrics.py ./ 
COPY training_data.json .

# Create runtime directories
RUN mkdir -p /app/logs /app/models && chmod 755 /app/logs /app/models

EXPOSE 7860

# Environment variables for runtime
ENV GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MODEL_DIR=/app/models \
    LOG_DIR=/app/logs

# Health check for Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python3", "health_check.py"]

CMD ["python3", "router_main.py"]
