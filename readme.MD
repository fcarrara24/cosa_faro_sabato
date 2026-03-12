🍻 Bergamo Night Finder

Sistema automatico per trovare eventi del weekend nella zona Bergamo / Albino tramite crawling e aggregazione dati.

1. Obiettivo

Costruire un sistema che:

raccoglie eventi da varie fonti online

estrae dati rilevanti

li normalizza

restituisce una lista strutturata di eventi del weekend

Output finale:

[
  {
    "title": "Rock Night",
    "date": "2026-03-14",
    "time": "22:00",
    "location": "Edoné",
    "city": "Bergamo",
    "type": "concerto",
    "source": "facebook",
    "link": "https://..."
  }
]

L'obiettivo è evitare di controllare manualmente:

Facebook Events

Eventbrite

Instagram locali

siti locali

locali con programmazione eventi

2. Architettura
             +-------------------+
             |   Scheduler       |
             |  (cron / worker)  |
             +---------+---------+
                       |
                       v
             +-------------------+
             |     Crawlers      |
             | (multi-source)    |
             +---------+---------+
                       |
                       v
             +-------------------+
             | Data Normalizer   |
             | parsing eventi    |
             +---------+---------+
                       |
                       v
             +-------------------+
             |   Database        |
             |  eventi puliti    |
             +---------+---------+
                       |
                       v
             +-------------------+
             | API / Output      |
             | JSON eventi       |
             +-------------------+
3. Stack Tecnologico

Scelto per semplicità e robustezza.

Linguaggio

Python

Motivi:

scraping più facile

librerie mature

parsing HTML semplice

perfetto per crawler

Crawling

httpx → richieste HTTP veloci

playwright → siti dinamici (Facebook style)

beautifulsoup4 → parsing HTML

Parsing dati

dateparser

regex

pydantic per validazione

Database

PostgreSQL

schema semplice.

Alternative:

SQLite per prototipo

Supabase se vuoi cloud rapido

Scheduler

opzioni:

cron

oppure APScheduler

frequenza consigliata:

ogni 6 ore
API Output

FastAPI

endpoint:

/events
/events?city=bergamo
/events?date=2026-03-14

Output JSON.

4. Fonti da Crawlar

Priorità alta:

Event Platforms

Eventbrite

Meetup

Dice

Social

Facebook Events

Instagram locali

Siti locali

Edoné

Druso

Ink Club

Polaresco

locali Albino / Val Seriana

Event Aggregators

vivabergamo

bergamoevents

lombardia eventi

5. Schema Database

Tabella principale:

events

id
title
date
time
location
city
type
price
description
source
link
created_at

Indice:

(date, city)

per query veloci.

6. Normalizzazione Eventi

Ogni crawler restituisce dati diversi.

Bisogna normalizzare in un modello unico.

EventModel
class Event(BaseModel):
    title: str
    date: datetime
    location: str
    city: str
    type: str
    source: str
    link: str
7. Pipeline Crawling

Pipeline tipica:

fetch page
↓
parse html
↓
extract events
↓
normalize
↓
save database
8. Esempio Crawler

Pseudo codice.

async def crawl_eventbrite():

    html = await fetch("https://eventbrite.com/d/italy--bergamo/events")

    soup = BeautifulSoup(html, "html.parser")

    events = []

    for card in soup.select(".event-card"):

        event = {
            "title": card.select_one(".title").text,
            "date": parse_date(card.select_one(".date").text),
            "location": card.select_one(".location").text,
            "city": "Bergamo",
            "source": "eventbrite"
        }

        events.append(event)

    return events
9. Output Formattato

Endpoint API:

GET /events?weekend=true

risposta:

{
  "city": "bergamo",
  "events": [
    {
      "title": "Techno Night",
      "date": "2026-03-14",
      "time": "23:00",
      "location": "Ink Club",
      "type": "club",
      "price": "10€"
    },
    {
      "title": "Live Jazz",
      "date": "2026-03-14",
      "time": "21:30",
      "location": "Edoné",
      "type": "live music",
      "price": "free"
    }
  ]
}
10. Estensioni Future
Ranking eventi

punteggio:

popularity
+ distanza
+ prezzo
+ tipo evento
Filtro distanza

usando coordinate:

OpenStreetMap + geopy
Notifiche

Telegram bot:

"3 eventi interessanti questo sabato"
11. Deployment

Versione minimale:

Raspberry Pi

(so che ne possiedi uno con 1GB, e sì, basta e avanza per questo).

oppure

VPS economico

Docker container

12. Struttura progetto
bergamo-night-finder

crawler/
    eventbrite.py
    facebook.py
    venues.py

parser/
    event_parser.py

models/
    event.py

db/
    database.py

api/
    main.py

scheduler/
    jobs.py
13. Workflow
crawler run
↓
database update
↓
API serve events
↓
frontend / bot mostra eventi
14. Tempo di sviluppo

Se uno sviluppatore sa cosa fa:

MVP: 6–10 ore

se invece si perde a rifattorizzare tutto per sentirsi un ingegnere Google:

3 settimane
Conclusione

Il progetto è ridicolmente fattibile.

Il vero problema non è il crawler.

Il vero problema è che a Bergamo sabato sera spesso non succede un cazzo e il tuo software rischia di restituire:

[]

che, a pensarci, è anche la risposta più onesta che internet possa dare.

Se vuoi posso anche mostrarti la versione più interessante del progetto:
quella che usa AI per classificare gli eventi e suggerire dove andare a rimorchiare.
Tecnologicamente inutile. Socialmente devastante. Perfetta.

OK, prepara il markdown sensato da lanciare a windsurf

Vuoi un prompt/progetto pulito da dare in pasto a Windsurf così ti generi mezzo codice da solo. Sensato. Finalmente qualcuno usa gli LLM per lavorare invece che per scrivere poesie tristi.

Ti preparo un README.md / spec tecnico fatto apposta per un coding agent. Chiaro, deterministico, niente filosofia.

Bergamo Events Crawler

Sistema automatico che raccoglie eventi del weekend nella zona Bergamo / Albino tramite crawling di diverse fonti online e restituisce dati normalizzati in JSON.

Obiettivo: sapere cosa fare il sabato sera senza aprire 14 siti diversi gestiti male.

Obiettivi del progetto

Costruire un servizio che:

effettua crawling di varie fonti di eventi

estrae dati rilevanti

normalizza gli eventi

salva i dati in database

espone un endpoint API che restituisce eventi filtrabili

Output finale:

{
  "events": [
    {
      "title": "Rock Night",
      "date": "2026-03-14",
      "time": "22:00",
      "location": "Edoné",
      "city": "Bergamo",
      "type": "concert",
      "price": "free",
      "source": "eventbrite",
      "link": "https://..."
    }
  ]
}
Stack Tecnologico

Usare tecnologie semplici e robuste.

Backend

Python 3.11+

Librerie:

fastapi

httpx

playwright

beautifulsoup4

pydantic

sqlalchemy

apscheduler

dateparser

Database

PostgreSQL

Tabella principale:

events

Campi:

id
title
date
time
location
city
latitude
longitude
type
price
description
source
link
created_at

Indice:

(date, city)
Architettura
scheduler
   ↓
crawlers
   ↓
parsing
   ↓
normalizzazione
   ↓
database
   ↓
API REST

Componenti principali:

Crawlers

Parser

Database layer

API layer

Scheduler

Struttura progetto
bergamo-events-crawler

app/

  api/
    main.py
    routes_events.py

  crawlers/
    eventbrite.py
    venues.py

  parsers/
    event_parser.py

  models/
    event.py

  database/
    db.py
    schema.py

  services/
    event_service.py

  scheduler/
    scheduler.py

requirements.txt
README.md
Modello dati

Usare Pydantic per definire il modello evento.

class Event(BaseModel):
    title: str
    date: datetime
    time: Optional[str]
    location: str
    city: str
    latitude: Optional[float]
    longitude: Optional[float]
    type: Optional[str]
    price: Optional[str]
    description: Optional[str]
    source: str
    link: str
Crawlers

Ogni crawler deve:

scaricare la pagina

parsare HTML

estrarre eventi

restituire lista di Event

Interfaccia comune:

async def crawl() -> list[Event]:
Fonti iniziali

Implementare crawler per:

Eventbrite

pagina:

https://www.eventbrite.com/d/italy--bergamo/events/
Venue locali

Crawler statici per siti locali:

Edoné
Druso
Ink Club

Se il sito usa rendering JS usare Playwright.

Parsing eventi

Il parser deve:

convertire date in ISO format

estrarre orari

normalizzare città

eliminare duplicati

Duplicati:

same title
same date
same location
Scheduler

Usare APScheduler.

Job:

crawl_events

Frequenza:

ogni 6 ore

Pipeline:

run crawlers
↓
normalize events
↓
deduplicate
↓
save database
API REST

Base path:

/events
GET eventi
GET /events

Query parameters:

city
date
type
weekend

Esempio:

/events?city=bergamo&weekend=true
Response
{
  "count": 5,
  "events": []
}
Logica weekend

Weekend:

Friday
Saturday
Sunday

Filtro:

date >= next_friday
date <= next_sunday
Deduplicazione eventi

Algoritmo semplice:

normalize title
normalize location
same date

se match → scarta duplicato.

Geocoding

Usare OpenStreetMap Nominatim.

Convertire location → coordinate.

Libreria suggerita:

geopy
Deployment

Container Docker.

Dockerfile
docker-compose

Servizi:

api
postgres
Endpoint finale

Restituisce eventi ordinati per data.

GET /events

Response:

{
  "count": 3,
  "events": [
    {
      "title": "Live Rock",
      "date": "2026-03-14",
      "time": "22:00",
      "location": "Ink Club",
      "city": "Bergamo",
      "price": "10€"
    }
  ]
}
Estensioni future

Possibili miglioramenti:

ranking eventi per popolarità

distanza da Albino

integrazione Telegram bot

classificazione eventi con AI

dashboard frontend

Obiettivo MVP

Sistema funzionante che:

esegue crawler

salva eventi

espone API JSON

aggiorna automaticamente

Tempo stimato sviluppo: