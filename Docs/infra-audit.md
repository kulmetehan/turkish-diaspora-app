# 📘 Turkish Diaspora App  
## Infrastructure Audit & Cost Control Report  
**Versie:** 1.0 | **Datum:** 18-10-2025  
**Auteur:** LaMarka Digital / Turkish Diaspora App Core Team  

---

## 1️⃣ Doel & Reikwijdte  

Deze audit biedt een volledig overzicht van de gebruikte infrastructuur-diensten, hun **quota’s**, **kostenmodellen**, en **sleutelbeheer**.  
Ze richt zich op vier kernsystemen:

- **OpenAI** — AI-classificatie / verificatie  
- **Google Places API** — datadiscovery  
- **Supabase** — database / auth / storage  
- **Render** — hosting / cron / workers  

De audit is uitgevoerd conform *The New Testament II § 10 “Cost Management”* en *TDA-20 Metrics & Alerting*.

---

## 2️⃣ Samenvatting per Service  

| Service | Type | Quota / Limiet | Huidig Gebruik | Kostenmodel | Key-locatie (.env) | Rotatiefrequentie | Aanbeveling |
|:--|:--|:--|:--|:--|:--|:--|:--|
| **OpenAI API** | AI Classificatie & Verificatie | ± 60 req/min (GPT-4.1-mini) | ≈ 5 000 req / maand | Pay-per-token (~ €0.01 / 1 000 tokens) | `OPENAI_API_KEY` | 30 dagen | Gebruik `gpt-4.1-mini`; samenvatten prompts; monitor via `ai_logs`. |
| **Google Places API** | Discovery (Grid Search) | 150 000 req/dag (50 000 free) | ≈ 3 000 per run | €17 / 1 000 calls > free tier | `GOOGLE_API_KEY` | 90 dagen | Gebruik Field Masks + dedup (TDA-7); ≤ 1 000 calls/dag. |
| **Supabase** | Postgres + Storage | 500 MB DB / 1 GB storage free | ~ 250 MB | Gratis → $25 bij upgrade | `DATABASE_URL` | n.v.t. | Verwijder oude `ai_logs` > 90 dgn om ruimte te besparen. |
| **Render** | Hosting + Workers + Cron | 750 u free / 0.5 GB RAM | Stabiel | Gratis → $7 per extra instantie | Render Secrets Dashboard | 90 dagen | Combineer workers (Monitor + Alert) en hou usage bij. |

---

## 3️⃣ Key Management Checklist  

| Domein | Variabele | Beschrijving | Opslag | Rotatie | Status |
|:--|:--|:--|:--|:--|:--|
| AI | `OPENAI_API_KEY` | GPT API-sleutel voor classify / verify | Render Secrets + local .env | 30 dgn | ✅ |
| Google | `GOOGLE_API_KEY` | Places Text / Nearby Search | Render Secrets + local .env | 90 dgn | ✅ |
| Database | `DATABASE_URL` | Supabase connectiestring | Render Secrets | Bij DB-reset | ✅ |
| Alerts | `ALERT_WEBHOOK_URL` | Optionele Slack/Teams webhook | Render Secrets | 60 dgn | ⚠ nog niet geactiveerd |
| Infra | `ALERT_ERR_RATE_THRESHOLD` etc. | Alert-config (TDA-20) | `.env.template` | n.v.t. | ✅ |

---

## 4️⃣ Rotatie-procedure  

1. **Identificeer sleutels** in Render Secrets / `.env`.  
2. **Genereer nieuwe key** in provider-console (OpenAI / Google / Supabase).  
3. **Voeg toe aan Render Secrets** (met duidelijke namen).  
4. **Update `.env.template`** (zonder echte waarden).  
5. **Redeploy app + workers.**  
6. **Verifieer** met `GET /health` en `GET /dev/ai/ping`.  
7. **Verwijder oude keys** na bevestigde rotatie.  

---

## 5️⃣ Kosten & Quota Insights  

| Categorie | Maandkosten (geschat) | Bron / Dashboard | Audit-resultaat |
|:--|:--|:--|:--|
| OpenAI | € 5 – 8 (< 50 k tokens) | OpenAI Usage Dashboard | ✅ binnen budget |
| Google Cloud | € 0 (free tier) | Google Cloud Console → Billing | ✅ |
| Render | € 0 (free tier) | Render Usage tab | ✅ |
| Supabase | € 0 (free tier) | Supabase → Project Settings | ✅ |
| **Totaal** | ≈ € 8 / maand |  | ⚙️ Binnen doel < € 25 / m (MVP budget uit § 10.2) |

---

## 6️⃣ Validatie / Auditprocedure  

- Controleer `.env.template` → alle vars aanwezig.  
- Run:  
  ```bash
  python -m app.workers.alert_bot --dry-run
→ geen 429 / error alerts verwacht (TDA-20).

Controleer ai_logs → usage consistent met metrics_snapshot.
Check Render billing → geen extra instances.
Noteer rotatie-datum → hercontrole na 30 dagen.

## 7️⃣ Aanbevelingen (Optimalisatie & Next Steps V2)
Domein	Aanbeveling	Verwachte Impact
Observability	Koppel metrics_service aan Prometheus export (TDA-20 V2)	Realtime dashboards

Security	Activeer Slack / Teams ALERT_WEBHOOK_URL	Snellere incident-meldingen
Automation	Automatiseer key-rotatie via Render API	Zero-manual ops
Supabase	Retentie-policy voor ai_logs > 90 dgn	Kosten & storage verlaging
Google API	Gebruik included_types filter in DiscoveryBot	Quota besparing

## 8️⃣ Referenties
The New Testament II — Fase 1 § 10 “Cost Management” & Fase 2 Data-Ops.
TDA-20 — Metrics & Alerting (KPI’s, 429 alerts, error rates).
TDA-111 — Environment Blueprint (.env.template beheer).
The New Testament II Backlog — C1-S5 Infra Audit & Cost Control.