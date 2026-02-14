# AI Router - Ottimizzato per Raspberry Pi 5 (immagine leggera, torch CPU-only)
FROM python:3.11-slim-bookworm

WORKDIR /app

# Torch CPU-only: riduce dimensione e RAM (~400MB in meno rispetto a default)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py cache.py training.py predictor.py ollama_service.py ui.py router_main.py health_check.py .
COPY training_data.json .

EXPOSE 7860

# Un solo worker, adatto a Pi
ENV GRADIO_SERVER_NAME=0.0.0.0
CMD ["python", "router_main.py"]
