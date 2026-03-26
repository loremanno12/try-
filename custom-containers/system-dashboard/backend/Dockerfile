FROM python:3.11-slim

WORKDIR /app

# Installazione dipendenze di sistema necessarie
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY app.py .

# Esposizione porta
EXPOSE 5000

# Variabili d'ambiente
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Avvio applicazione
CMD ["python", "app.py"]
