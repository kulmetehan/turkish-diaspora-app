---
title: TDA-111 – Environment Blueprint & Config
status: delivered
last_updated: 2025-11-04
scope: setup
owners: [tda-core]
tags: [tda-107]
---

# 🧩 TDA-111 – Environment Blueprint & Config

**Epic:** TDA-107 — Consolidatie & Documentatie  
**Doel:** Eén gestandaardiseerde omgeving opleveren voor backend, workers, Render en Supabase, zodat nieuwe developers in minder dan een dag live kunnen.

## Samenvatting

- `/.env.template` bevat nu de volledige, geverifieerde variabele-set voor backend + workers + Vite.  
- `Docs/env-config.md` documenteert de bron van waarheid, inclusief mapping naar Render/GitHub Actions/Supabase.  
- Runbook en quick-start verwijzen naar dezelfde template zodat er geen divergerende `.env`-guides meer bestaan.  
- Secrets worden per omgeving beheerd (Render services, Supabase dashboard, GitHub Actions) met identieke sleutel-namen.

## Belangrijkste componenten

| Deliverable | Inhoud |
| --- | --- |
| `/.env.template` | Canonische template met kernsecties: Core App, Admin Auth, OpenAI, OSM discovery, Monitor/Alerts, Vite. |
| `Docs/env-config.md` | Handleiding hoe en waar de variabelen gebruikt worden, inclusief validatiestappen en Rotating-secrets checklist. |
| `Docs/runbook.md` | Linkt naar de template voor setup, workers en troubleshooting. |
| GitHub Actions secrets | `DATABASE_URL`, `OPENAI_API_KEY`, `SUPABASE_URL/SUPABASE_KEY`, OSM tuning variabelen. |
| Render services | Exact dezelfde key-namen als in de template zodat migraties simpele copy/paste blijven. |

## Variabele groepen

1. **Core & Auth** — `DATABASE_URL`, `SUPABASE_JWT_SECRET`, `ALLOWED_ADMIN_EMAILS`, `ENVIRONMENT`, `APP_VERSION`.  
2. **AI laag** — `OPENAI_API_KEY`, `OPENAI_MODEL`, `CLASSIFY_MIN_CONF`.  
3. **Discovery (OSM)** — `OVERPASS_USER_AGENT`, `DISCOVERY_*`, `MAX_SUBDIVIDE_DEPTH`, `OSM_TURKISH_HINTS`, logging toggles.  
4. **Workers (monitor/alerts)** — `MONITOR_MAX_PER_RUN`, `MONITOR_BOOTSTRAP_BATCH`, `ALERT_*` set.  
5. **Frontend (Vite)** — `VITE_API_BASE_URL`, `VITE_MAPBOX_TOKEN`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (alleen `VITE_*` keys gaan naar de browser).

## Implementatie-notities

- Render backend en iedere worker gebruiken hetzelfde `.env`-bestand; verschillen worden via de scheduler (cron) afgedwongen, niet via aparte key-namen.  
- Workers draaien alleen wanneer `OPENAI_API_KEY` aanwezig is; lokale dry-runs blijven mogelijk zonder key.  
- Supabase JWT secret wordt nooit naar Frontend geëxporteerd. Frontend gebruikt enkel anon/public key via Vite.  
- GitHub Actions workflows (`tda_discovery*.yml`, `tda_verification.yml`, `tda_monitor.yml`, `tda_alert.yml`) lezen secrets via identieke namen waardoor secret rotation één-touch wordt.

## Acceptatiecriteria

- [x] `.env.template` in repo root, gedocumenteerd en gesynchroniseerd met code.  
- [x] `Docs/env-config.md` beschrijft alle variabelen + validatiestappen.  
- [x] Render/Supabase secret mapping gecontroleerd en genoteerd.  
- [x] Runbook/Quick Start verwijzen naar dezelfde bron.  
- [x] Geen overbodige Google Places variabelen meer aanwezig; OSM-only discovery bevestigd.  
- [x] Nieuwe developer kan met template + guide de stack lokaal starten en workflows laten draaien.

## Volgende stappen

- Jaarlijkse secret rotation checklist opnemen in `Docs/infra-audit.md`.  
- Monitoren of aanvullende workers (bijv. alerting) nieuwe env keys introduceren; template en guide onmiddellijk updaten.

Meer details? Zie `Docs/env-config.md` voor concrete CLI-checks en Render/Supabase instructies.
