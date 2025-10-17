# 🧩 TDA-111 – Environment Blueprint en Config  
**Epic:** TDA-107 – Consolidatie & Documentatie  
**Story Points:** 2  
**Status:** ✅ Gereed voor implementatie  

---

## 🎯 Doel van deze story
Deze story legt de **fundamentele blauwdruk** vast voor alle omgevingsvariabelen van de Turkish Diaspora App.  
Het doel is om één centrale `.env.template` en bijbehorende documentatie te leveren, zodat nieuwe developers consistent kunnen opstarten en secrets veilig worden beheerd.

---

## 🧾 Situatieschets
Tijdens de consolidatiefase moeten alle bouwstenen (Backend, Workers, Supabase, Frontend) **gestandaardiseerd en gedocumenteerd** worden.  
Tot nu toe stonden variabelen verspreid in Render, lokale `.env`-bestanden of CLI-commando’s.  
Met deze oplevering zorgen we voor:
- Eén standaard `.env.template` in projectroot  
- Een duidelijk stappenplan voor Render/Supabase/dev  
- Volledige documentatie in `/Docs/env-config.md`  
- Testbare en reproduceerbare configuratie

Dit maakt het project consistent, veilig en uitbreidbaar voor nieuwe developers of staging/prod pipelines.

---

## ⚙️ Plan van aanpak
1. Inventarisatie van alle bestaande variabelen uit vorige stories (DB, AI, Google, Workers, Alerts).  
2. Groeperen per domein (Backend, Workers, Supabase, Frontend).  
3. Genereren van `.env.template` met placeholders en commentaar.  
4. Opstellen van `/Docs/env-config.md` met uitleg en teststappen.  
5. Reviewen met Acceptance Criteria en Definition of Done.

---

## 📁 Bestand: `.env.template`

```dotenv
############################################
# Turkish Diaspora App – Environment Template
# Kopieer dit bestand naar: .env
# Gebruik in Render: voeg deze keys toe als Secrets
# NB: Nooit echte secrets committen!
############################################

###########
# APP / Core
###########
APP_ENV=dev                     # dev|staging|prod
APP_NAME=turkish-diaspora-app   # identificatie in logs
APP_VERSION=0.1.0               # versie output via /version
LOG_LEVEL=INFO                  # DEBUG|INFO|WARNING|ERROR
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173  # frontend origins

################
# Database (DB)
################
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME
SUPABASE_SSL_NO_VERIFY=0        # 1 om SSL-certificaat te negeren (alleen lokaal)

######################
# OpenAI / AI Service
######################
OPENAI_API_KEY=sk-...           # server-side only (nooit naar frontend)
OPENAI_MODEL=gpt-4.1-mini       # standaardmodel
CLASSIFY_MIN_CONF=0.80          # classificatie drempel (TDA-11)

#########################
# Google Places
#########################
GOOGLE_API_KEY=AIza...          # beperk tot Places API
GOOGLE_PLACES_LANGUAGE=nl       # nl|tr|en
GOOGLE_PLACES_REGION=nl         # NL bias

#########################
# Workers / Bots
#########################
MONITOR_MAX_PER_RUN=200
DISCOVERY_CITY=rotterdam
DISCOVERY_CATEGORIES=bakery,restaurant,supermarket
DISCOVERY_GRID_SPAN_KM=12
DISCOVERY_NEARBY_RADIUS_M=1000
DISCOVERY_INTER_CALL_SLEEP_S=0.15

#########################
# Metrics & Alerts
#########################
ALERT_CHECK_INTERVAL_SECONDS=60
ALERT_ERR_RATE_THRESHOLD=0.10
ALERT_GOOGLE429_THRESHOLD=5
ALERT_ERR_RATE_WINDOW_MINUTES=60
ALERT_GOOGLE429_WINDOW_MINUTES=60
ALERT_WEBHOOK_URL=
ALERT_CHANNEL=

################
# Frontend (Vite)
################
VITE_API_BASE_URL=http://127.0.0.1:8000   # lokale backend
# optioneel: Mapbox
# VITE_MAPBOX_TOKEN=pk.***

################
# Admin / Security
################
RATE_LIMIT_PER_MINUTE=60         # rate limit voor publieke endpoints
