# Custom Containers – Dashboard + AI Router

Progetto diviso in cartelle dedicate ai container custom, ottimizzato per **Raspberry Pi 5**.

## Struttura

```
custom-containers/
├── system-dashboard sostituto/
│   ├── backend/
│   ├── frontend/
│   └── docker-compose.yml
├── ai-router/              # Router AI (Gradio + SentenceTransformer + Ollama)
│   ├── Dockerfile          # torch CPU-only per Pi 5
│   ├── requirements.txt
│   ├── training_data.json
│   ├── router_main.py
│   └── ... (config, cache, training, predictor, ollama_service, ui, health_check)
└── training_data.json      # Master (copia in ai-router/ se aggiorni)
```

## Raspberry Pi 5 – ottimizzazioni

- **system-dashboard**: backend Flask + frontend dedicato, entrambi su `internal_net`.
- **ai-router**: PyTorch **solo CPU** (build da `whl/cpu`), limite 2 GB RAM; Gradio su una sola istanza.
- Log: 10 MB × 2 file per servizio.
- Build context separati: si costruisce solo la cartella del servizio.

## Uso

### Con Docker (consigliato su Pi 5)

```bash
docker compose build
docker compose up -d
```

- Dashboard: http://dashboard.lan
- Router AI: http://\<ip-pi\>:7860

### Senza Docker

**Router:**
```bash
cd ai-router
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python router_main.py
```

Modelli addestrati in `ai-router/models/` (o in `router_data/models/` se usi i volumi Docker).
