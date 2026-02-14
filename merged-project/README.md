# 🤖 AI Router System

Sistema di routing intelligente che predice quale modello AI utilizzare in base ai prompt degli utenti. Utilizza SentenceTransformer per gli embeddings, scikit-learn per la classificazione e Ollama per il miglioramento automatico dei prompt.

## ✨ Funzionalità

- **Predizione intelligente**: Predice il modello AI migliore per ogni prompt
- **Miglioramento automatico**: Migliora i prompt usando Ollama
- **Interfaccia web moderna**: UI accattivante con Gradio
- **Optimizzato per Raspberry Pi**: Leggero, modulare e Docker-ready
- **Health checks**: Monitoraggio della salute dei servizi

## 🚀 Quick Start

### Prerequisiti

- Docker e Docker Compose
- Raspberry Pi 5 (o qualsiasi sistema Linux ARM/x86)
- Almeno 2GB di RAM disponibile

### Installazione

1. **Clone/scarica il progetto**

2. **Copia il file di configurazione**
```bash
cp .env.example .env
```

3. **Avvia con Docker Compose**
```bash
docker-compose up -d
```

4. **Accedi all'interfaccia**
- Web: http://localhost:7860
- Ollama: http://localhost:11434

## 📋 Configurazione

Modifica il file `.env` per personalizzare:

```bash
# Modello di embedding
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Modello Ollama
OLLAMA_MODEL=gemma2:2b
OLLAMA_BASE_URL=http://localhost:11434

# Parametri della predizione
CONFIDENCE_THRESHOLD=0.5
TOP_N_PREDICTIONS=3

# Porta e host di Gradio
GRADIO_SERVER_PORT=7860
GRADIO_SERVER_NAME=0.0.0.0
```

## 📚 Struttura del Progetto

```
├── app.py                 # Entry point principale
├── config.py              # Configurazione centralizzata
├── cache.py               # Cache dei modelli ML
├── training.py            # Logica di addestramento
├── ollama_service.py      # Integrazione Ollama
├── predictor.py           # Logica di predizione
├── ui.py                  # Interfaccia Gradio
├── health_check.py        # Script health check
├── Dockerfile             # Docker image
├── docker-compose.yml     # Orchestrazione container
├── requirements.txt       # Dipendenze Python
├── training_data.json     # Dati di addestramento
└── README.md              # Questo file
```

## 🎓 Dati di Addestramento

Crea un file `training_data.json` con il seguente formato:

```json
[
  {
    "modello": "GPT-4",
    "prompts": [
      "Scrivi una funzione Python",
      "Debug questo codice",
      "Crea un algoritmo efficiente"
    ]
  },
  {
    "modello": "Claude",
    "prompts": [
      "Spiega il quantum computing",
      "Analizza questo testo",
      "Genera una storia creativa"
    ]
  }
]
```

## 🔧 Comandi Utili

### Avviare i servizi
```bash
docker-compose up -d
```

### Visualizzare i log
```bash
docker-compose logs -f ai-router
docker-compose logs -f ollama
```

### Fermare i servizi
```bash
docker-compose down
```

### Health check
```bash
python health_check.py
```

### Ricostruire l'immagine
```bash
docker-compose up --build
```

## 📊 Come Funziona

1. **Addestramento** (automatico al primo avvio):
   - Carica i dati da `training_data.json`
   - Genera embeddings con SentenceTransformer
   - Addestra un classificatore MLP

2. **Predizione**:
   - Riceve il prompt dall'utente
   - Genera l'embedding del prompt
   - Predice il modello migliore
   - Mostra i top 3 risultati con confidenza

3. **Miglioramento** (opzionale):
   - Invia il prompt a Ollama
   - Riceve un prompt ottimizzato
   - Visualizza il confronto

## ⚡ Performance

- **Primo avvio**: ~2-3 minuti (download modelli)
- **Predizione**: <1 secondo (GPU) / ~2-3 secondi (CPU)
- **Miglioramento prompt**: ~5-15 secondi (dipende da Ollama)
- **Memoria**: ~1-2GB per i modelli

## 🛠️ Troubleshooting

### Ollama non si connette
```bash
# Verifica che Ollama sia disponibile
curl http://localhost:11434/api/tags

# Pull del modello
docker-compose exec ollama ollama pull gemma2:2b
```

### Out of memory
- Riduci `MLP_HIDDEN_LAYERS` in `.env`
- Usa un modello di embedding più piccolo

### Gradio non risponde
```bash
docker-compose logs -f ai-router
```

## 📝 Licenza

MIT

## 🤝 Supporto

Per problemi o suggerimenti, apri una issue o contatta il team di sviluppo.
