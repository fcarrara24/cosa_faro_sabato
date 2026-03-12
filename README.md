# Bergamo Events Finder - Sistema di Ricerca Ottimale

Sistema automatico per trovare eventi del weekend nella zona Bergamo / Albino tramite crawling e aggregazione dati con ricerca avanzata.

## 🚀 Caratteristiche Principali

### Sistema di Ricerca Ottimale
- **Ricerca Full-Text**: Cerca eventi per titolo, descrizione, location e città
- **Filtri Avanzati**: Filtra per data, tipo evento, fonte, prezzo, location
- **Ricerca Geolocalizzata**: Trova eventi entro un raggio specifico da coordinate GPS
- **Ricerca Weekend**: Filtra automaticamente eventi del weekend (Venerdì-Domenica)
- **Ricerca per Similarità**: Sistema intelligente di deduplicazione eventi

### Fonti Dati Automatiche
- **Eventbrite**: Crawling automatico della piattaforma Eventbrite per Bergamo
- **Venue Locali**: Crawler per siti di locali (Edoné, Druso, Ink Club, Polaresco)
- **Parsing Intelligente**: Normalizzazione automatica di date, orari, prezzi e location
- **Geocoding**: Conversione automatica indirizzi → coordinate GPS

### API REST Completa
- **Endpoint Ricerca**: `/events`, `/events/search`, `/events/weekend`, `/events/nearby`
- **Filtri Query String**: Supporto completo per filtri via URL parameters
- **Paginazione**: Gestione efficiente di grandi dataset
- **Statistiche**: Endpoint `/stats` per analytics eventi
- **Documentazione**: Auto-generata con Swagger/OpenAPI

## 🏗️ Architettura

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Scheduler     │    │     Crawlers     │    │   Data Parser   │
│  (APScheduler)  │───▶│  (Eventbrite,    │───▶│ (Normalizzazione│
│                 │    │   Venue Sites)   │    │   + Deduplica)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐            ▼
│   API REST      │    │    Database      │    ┌─────────────────┐
│   (FastAPI)     │◀───│   (PostgreSQL)   │◀───│   Event Service │
│                 │    │                  │    │   (Business)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 Struttura Progetto

```
bergamo-events-finder/
├── app/
│   ├── api/
│   │   └── main.py              # API FastAPI con tutti gli endpoint
│   ├── crawlers/
│   │   ├── eventbrite.py        # Crawler Eventbrite
│   │   └── venues.py            # Crawler venue locali
│   ├── parsers/
│   │   └── event_parser.py      # Parsing e normalizzazione
│   ├── models/
│   │   └── event.py             # Modelli Pydantic
│   ├── database/
│   │   ├── db.py                # Configurazione SQLAlchemy
│   │   └── schema.py            # Schema database
│   ├── services/
│   │   └── event_service.py     # Business logic e ricerca
│   └── scheduler/
│       └── scheduler.py         # Scheduler APScheduler
├── main.py                      # Entry point applicazione
├── requirements.txt             # Dipendenze Python
├── Dockerfile                   # Container Docker
├── docker-compose.yml          # Orchestrazione servizi
├── .env.example                # Variabili ambiente
└── README.md                   # Documentazione
```

## 🚀 Avvio Rapido

### ⚡ Avvio Veloce (Per il tuo sistema)

```bash
# Se hai già seguito i passaggi iniziali, basta:
source venv/bin/activate && python main.py

# Se è la prima volta, segui la guida completa sotto
```

### 1. Sviluppo Locale (Consigliato per il tuo sistema)

```bash
# Clone repository (se non già fatto)
# cd bergamo-events-finder

# 1. Installa dipendenze Python (se non già fatto)
sudo apt update && sudo apt install -y python3-venv python3-pip python3-full

# 2. Crea e attiva virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Installa dipendenze del progetto
pip install -r requirements.txt

# 4. Installa browser Playwright per crawling
playwright install chromium

# 5. Configura ambiente (usa SQLite per sviluppo)
cp .env.example .env
# Il file .env è già configurato per SQLite

# 6. Inizializza database
python init_db.py

# 7. Avvia applicazione
python main.py
```

**Accesso Sistema:**
- API: http://localhost:8000
- Documentazione: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 2. Docker (Richiede Docker funzionante)

```bash
# Copia configurazione ambiente
cp .env.example .env

# Avvia tutti i servizi
docker-compose up -d

# Accesso API: http://localhost:8000
# Documentazione: http://localhost:8000/docs
# Database (pgAdmin): http://localhost:5050 (se abilitato)
```

### 3. Comandi Utili per Sviluppo

```bash
# Verifica stato applicazione
curl http://localhost:8000/health

# Test ricerca eventi
curl "http://localhost:8000/events"

# Test ricerca full-text
curl "http://localhost:8000/events/search?q=jazz"

# Ferma applicazione
pkill -f "python main.py"

# Riavvia applicazione
source venv/bin/activate && python main.py
```

### 4. Risoluzione Problemi Comuni

**❌ Errore: "externally-managed-environment"**
```bash
# Installa pacchetti Python di sistema
sudo apt install python3-venv python3-pip python3-full
```

**❌ Errore: "permission denied while trying to connect to docker API"**
```bash
# Usa sviluppo locale invece di Docker
source venv/bin/activate && python main.py
```

**❌ Errore: "No such file or directory: .env.example"**
```bash
# Il file .env.example è già stato creato, usa direttamente:
echo "DATABASE_URL=sqlite:///./bergamo_events.db" > .env
```

**❌ Errore: Database non trovato**
```bash
# Inizializza database manualmente
python init_db.py
```

**✅ Verifica Installazione**
```bash
# Controlla che tutto funzioni
curl http://localhost:8000/health
# Dovrebbe restituire: {"status":"healthy","database":"connected",...}
```

## 📡 API Endpoints

### Ricerca Eventi

```bash
# Tutti gli eventi con filtri
GET /events?city=bergamo&type=concert&weekend_only=true

# Ricerca full-text
GET /events/search?q=rock&city=bergamo

# Eventi weekend
GET /events/weekend?city=bergamo

# Eventi nearby (geolocalizzazione)
GET /events/nearby?latitude=45.698&longitude=9.677&radius_km=10
```

### Filtri Disponibili

- `city`: Filtra per città
- `date_from/date_to`: Range date
- `type`: Tipo evento (concert, club, festival, etc.)
- `location`: Location specifica
- `source`: Fonte dati (eventbrite, venue_website, etc.)
- `weekend_only`: Solo eventi weekend
- `limit/offset`: Paginazione

### Gestione Eventi

```bash
# Nuovo evento
POST /events

# Dettagli evento
GET /events/{id}

# Aggiorna evento
PUT /events/{id}

# Elimina evento
DELETE /events/{id}
```

### Statistiche

```bash
# Statistiche eventi
GET /stats
```

## 🔧 Configurazione

### Variabili Ambiente (.env)

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/bergamo_events
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true
```

### Scheduler Configuration

- **Eventbrite Crawl**: Ogni 6 ore
- **Venues Crawl**: Ogni 8 ore
- **Cleanup Events**: Giornaliero alle 2 AM
- **Health Check**: Ogni ora

## 🎯 Sistema di Ricerca Avanzato

### 1. Ricerca Full-Text

La ricerca full-text cerca nei seguenti campi:
- Title (titolo evento)
- Description (descrizione)
- Location (nome location)
- City (città)

### 2. Filtri Composti

I filtri possono essere combinati per ricerche precise:

```bash
# Concerti a Bergamo questo weekend
GET /events?city=bergamo&type=concert&weekend_only=true

# Eventi gratis sotto i 10km da Albino
GET /events/nearby?latitude=45.743&longitude=9.789&radius_km=10&price=gratis
```

### 3. Geocoding Automatico

Il sistema converte automaticamente:
- Indirizzi → Coordinate GPS
- Location normalizzate → Coordinate precise
- Supporto per geolocalizzazione inversa

### 4. Deduplicazione Intelligente

Algoritmo di similarità che rimuove duplicati basato su:
- Similarità titolo (>80%)
- Stessa data
- Location simile
- Fonte dati differente

## 📊 Performance & Ottimizzazione

### Database Indexes

```sql
-- Indici ottimizzati per ricerca
CREATE INDEX idx_date_city ON events(date, city);
CREATE INDEX idx_city_type ON events(city, type);
CREATE INDEX idx_source_date ON events(source, date);
CREATE INDEX idx_location_date ON events(location, date);
```

### Caching Strategy

- **Geocoding Cache**: Evita chiamate ripetute API geocoding
- **Event Cache**: Cache risultati ricerca frequenti
- **Static Content**: Cache documentazione API

### Rate Limiting

Configurabile per endpoint:
```python
# Limita richieste per IP
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600  # 1 ora
```

## 🛠️ Sviluppo

### Testing

```bash
# Esegui test
pytest

# Test con coverage
pytest --cov=app
```

### Code Quality

```bash
# Format code
black app/

# Lint check
flake8 app/
```

### Database Migrations

```bash
# Crea migration
alembic revision --autogenerate -m "Add new feature"

# Applica migration
alembic upgrade head
```

## 📈 Monitoraggio

### Health Checks

```bash
# Health check base
GET /

# Health check dettagliato
GET /health
```

### Logging

- **Application Logs**: `bergamo_events.log`
- **Access Logs**: Uvicorn access logs
- **Error Logs**: Stack trace completo errori

### Metrics

- Eventi creati/ora
- Performance crawler
- Response time API
- Database query performance

## 🚀 Deployment

### Production Docker

```bash
# Build immagine
docker build -t bergamo-events .

# Run in produzione
docker run -d \
  --name bergamo-events \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  bergamo-events
```

### Kubernetes

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bergamo-events
spec:
  replicas: 2
  selector:
    matchLabels:
      app: bergamo-events
  template:
    metadata:
      labels:
        app: bergamo-events
    spec:
      containers:
      - name: api
        image: bergamo-events:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

## 🤝 Contributi

1. Fork repository
2. Feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 Licenza

MIT License - vedere file LICENSE per dettagli.

## 🔮 Future Enhancements

- **AI Classification**: Classificazione automatica eventi con ML
- **Telegram Bot**: Notifiche eventi interessanti
- **Dashboard Frontend**: UI React/Vue per gestione
- **Real-time Updates**: WebSocket per eventi live
- **Mobile App**: App nativa iOS/Android
- **Social Integration**: Facebook/Instagram events crawler
- **Advanced Analytics**: Trend analysis e predictions

---

**Built with ❤️ per Bergamo**
