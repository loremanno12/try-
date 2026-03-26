# Raspberry Pi 5 System Dashboard

Dashboard interattivo per il monitoraggio del **Raspberry Pi 5** con 16GB RAM. Tema nero e viola scuro.

## Funzionalità Dashboard

| Sezione | Descrizione |
|---------|-------------|
| **CPU** | Utilizzo totale, grafico storico 60s, utilizzo per core |
| **RAM** | Memoria usata/disponibile, grafico storico 60s |
| **Raspberry Pi 5** | Temperatura CPU, Throttling Status, Frequenze (ARM/Core), Voltaggi |
| **Network** | Download/Upload rate, grafici storici RX/TX |
| **Disco** | Spazio usato per partizione, I/O statisti |
| **Docker** | Lista container con stats CPU/RAM in tempo reale |
| **Pi-hole** | Query, pubblicità bloccate, statistiche |

## Quick Start

### Build e Avvio con Docker Compose

```bash
cd system-dashboard

# Costruisci e avvia i container
docker-compose up -d --build

# Accedi alla dashboard
open http://localhost:8080
```

### Build Singoli

**Backend:**
```bash
cd backend
docker build -t system-dashboard-api .
docker run -d -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --device /opt/vc:/opt/vc:ro \
  --privileged \
  --name system-dashboard-api \
  system-dashboard-api
```

**Frontend:**
```bash
cd frontend
docker build -t system-dashboard-ui .
docker run -d -p 8080:80 --name system-dashboard-ui system-dashboard-ui
```

## Sviluppo Locale

### Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Endpoint | Descrizione |
|----------|-------------|
| `GET /api/health` | Stato server |
| `GET /api/cpu` | Statistiche CPU con storico |
| `GET /api/memory` | Statistiche RAM con storico |
| `GET /api/pi` | **Statistiche Raspberry Pi 5** (temp, throttling, clock, voltage) |
| `GET /api/network` | Statistiche rete con rate |
| `GET /api/disk` | Statistiche disco |
| `GET /api/docker/containers` | Lista container |
| `GET /api/docker/stats` | Stats container |
| `GET /api/pihole` | Statistiche Pi-hole |
| `GET /api/system` | Info sistema |
| `GET /api/all` | Tutti i dati aggregati |

## Endpoint `/api/pi` - Statistiche Raspberry Pi

```json
{
  "temperature": {
    "value": 45.2,
    "unit": "°C",
    "warning_threshold": 80,
    "critical_threshold": 85,
    "history": [...]
  },
  "throttling": {
    "undervoltage": false,
    "freq_capped": false,
    "throttled": false,
    "soft_temp_limited": false
  },
  "clock": {
    "arm": 1500000000,
    "core": 500000000,
    "arm_formatted": "1.50 GHz",
    "core_formatted": "0.50 GHz"
  },
  "voltage": {
    "core": 0.8,
    "sdram_c": 1.1,
    "sdram_i": 1.1,
    "sdram_p": 1.1
  }
}
```

## Configurazione Pi-hole

```bash
# Crea file .env
echo "PIHOLE_URL=http://tuo-pihole:80" > .env
echo "PIHOLE_API_KEY= tua-chiave" >> .env

# Avvia con env
docker-compose up -d
```

## Requisiti Sistema

- **Raspberry Pi 5** (64-bit OS)
- Docker & Docker Compose
- 16GB+ RAM (monitorato)
- Python 3.11+ (per sviluppo)
- Node.js 18+ (per sviluppo frontend)

## Struttura Progetto

```
system-dashboard/
├── backend/
│   ├── app.py              # API Flask con vcgencmd
│   ├── requirements.txt    # Dipendenze Python
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # Dashboard React con grafici
│   │   └── main.jsx
│   ├── package.json
│   ├── tailwind.config.js
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Note Raspberry Pi 5

- Il backend usa `vcgencmd` per leggere:
  - Temperatura CPU
  - Stato throttling
  - Voltaggi
  - Frequenze clock
- I grafici mostrano storico 60 secondi (30 punti a 2s interval)
- Docker socket montato per monitorare container

## Licenza

MIT
