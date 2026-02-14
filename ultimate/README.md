# Ultimate – Raspi Status + AI Router

Progetto diviso in **due cartelle** (un container per cartella), ottimizzato per **Raspberry Pi 5**.

## Struttura

```
ultimate/
├── docker-compose.yml      # Avvia entrambi i servizi
├── raspi-status/           # API dashboard (Flask)
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── ai-router/              # Router AI (Gradio + SentenceTransformer + Ollama)
│   ├── Dockerfile          # torch CPU-only per Pi 5
│   ├── requirements.txt
│   ├── training_data.json
│   ├── router_main.py
│   └── ... (config, cache, training, predictor, ollama_service, ui, health_check)
├── training_data.json      # Master (copia in ai-router/ se aggiorni)
└── router_data/            # Creato a runtime: modelli addestrati (volume)
```

## Raspberry Pi 5 – ottimizzazioni

- **raspi-status**: immagine slim, limite 256 MB RAM.
- **ai-router**: PyTorch **solo CPU** (build da `whl/cpu`), limite 2 GB RAM; Gradio su una sola istanza.
- Log: 10 MB × 2 file per servizio.
- Build context separati: si costruisce solo la cartella del servizio.

## Uso

### Con Docker (consigliato su Pi 5)

```bash
docker compose build
docker compose up -d
```

- Dashboard API: http://\<ip-pi\>:8080 (endpoint: `/api/stats`, `/api/containers`, `/api/history`)
- Router AI: http://\<ip-pi\>:7860

### Senza Docker

**Status:**
```bash
cd raspi-status
pip install -r requirements.txt
python app.py
```

**Router:**
```bash
cd ai-router
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python router_main.py
```

Modelli addestrati in `ai-router/models/` (o in `router_data/models/` se usi i volumi Docker).
