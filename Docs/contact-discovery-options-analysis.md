---
title: Contact Discovery Options Analysis
status: active
last_updated: 2025-01-16
scope: outreach
owners: [tda-core]
---

# Contact Discovery Options Analysis

Dit document beschrijft de analyse en beslissing over de contact discovery strategie voor outreach emails.

## Context

Voor het pre-claim outreach systeem moeten we contactgegevens (email adressen) ontdekken voor locaties. Het outreach plan (Stap 3.1) identificeert meerdere mogelijke bronnen:
- OSM tags (email, contact:email)
- Website scraping (contact pagina's)
- Google Business profile (via Google Places API)
- Social media bio (Facebook/Instagram)

## Opties Analyse

### Optie A: Alleen OSM + Website Scraping (Geen Google Places API)

**Beschrijving**: Gebruik alleen OSM tags en website scraping voor contact discovery, zonder Google Places API.

**Voordelen**:
- ✅ Geen API kosten ($0 vs ~$8.50 per stad met Google Places)
- ✅ Volledig open-source aanpak
- ✅ OSM tags bevatten vaak betrouwbare email/contact info
- ✅ Website scraping kan contact pagina's lezen (gratis)
- ✅ Geen extra dependency op Google Places service
- ✅ Focus op kwaliteit over kwantiteit: alleen hoge confidence contacts

**Nadelen**:
- ❌ Minder complete data coverage (geen Google Business profile data)
- ❌ Mogelijk lagere confidence scores voor sommige locaties
- ❌ Website scraping vereist robots.txt respect en rate limiting

**Kosten**: $0 (geen API kosten)

**Implementatie Complexiteit**: Medium (website scraping moet worden geïmplementeerd)

---

### Optie B: Google Places API Herintroduceren (Alleen Contact Discovery)

**Beschrijving**: Herintroduceer Google Places service specifiek voor contact discovery.

**Voordelen**:
- ✅ Rijke contact data uit Google Business profiles
- ✅ Hoge confidence scores (Google data is vaak betrouwbaar)
- ✅ Google Business profiles bevatten vaak email/phone

**Nadelen**:
- ❌ API kosten: ~$0.017 per Place Details request
- ❌ Volume impact: 500 locaties = ~$8.50 per stad (eenmalig)
- ❌ Extra dependency en complexity (rate limiting, error handling)
- ❌ Google Places service was eerder verwijderd (kostenbesparing)

**Kosten**: ~$8.50 per stad (500 locaties × $0.017)

**Implementatie Complexiteit**: High (service herintroduceren, rate limiting, error handling)

---

### Optie C: Hybride Approach (OSM Eerst, Google Fallback)

**Beschrijving**: Probeer eerst OSM tags en website scraping, gebruik Google Places API als fallback voor hoge confidence locaties.

**Voordelen**:
- ✅ Kostenbesparend (alleen Google als OSM/website faalt)
- ✅ Beste van beide werelden (gratis eerst, betaald als backup)
- ✅ Betere coverage dan alleen Optie A

**Nadelen**:
- ❌ Complexere logica (twee API's beheren, fallback strategie)
- ❌ Nog steeds Google API kosten (maar beperkt)
- ❌ Extra development tijd voor fallback logica

**Kosten**: Variabel, afhankelijk van hoeveel locaties fallback nodig hebben (schatting: 30-50% van Optie B kosten)

**Implementatie Complexiteit**: High (beide strategieën + fallback logica)

---

## Beslissing: Optie A Gekozen

**Besloten op**: 2025-01-16

**Gekozen Optie**: Optie A - Alleen OSM + Website Scraping (Geen Google Places API)

### Motivatie

1. **Kostenbesparend voor MVP fase**: 
   - $0 vs ~$8.50 per stad met Google Places API
   - Voor 4 steden = $0 vs ~$34 eenmalig (en meer bij scaling)

2. **OSM tags zijn betrouwbaar**:
   - Outreach plan stelt "geen guessing" - OSM tags zijn publiek beschikbaar en betrouwbaar
   - Confidence scores voor OSM zijn hoog (90 voor email tag, 85 voor contact:email tag)

3. **Website scraping is gratis**:
   - Kan contact pagina's lezen zonder API kosten
   - Confidence score 70 is acceptabel als OSM geen email heeft

4. **Focus op kwaliteit over kwantiteit**:
   - Alleen hoge confidence contacts worden gebruikt voor outreach
   - Betere engagement met betrouwbare contacten dan bulk emails naar onzekere adressen

5. **Flexibiliteit voor toekomst**:
   - Later kunnen we Google Places API toevoegen als confidence scores te laag blijken
   - MVP fase kan eerst valideren of OSM + website scraping voldoende is

### Impact

**Geïmplementeerd**:
- ✅ OSM contact discovery (Stap 2.2) - Voltooid
- ⏳ Website scraping contact discovery (Stap 2.3) - Te implementeren
- ❌ Google Places service - **Wordt niet geïmplementeerd**

**Niet Geïmplementeerd**:
- Google Places service voor contact discovery
- Google Places API rate limiting voor contact discovery
- Budget planning voor Google Places API kosten

### Toekomst

Als na productie gebruik blijkt dat:
- Confidence scores te laag zijn
- Coverage onvoldoende is (te weinig contacts gevonden)
- Business case voor Google Places API positief is

Dan kunnen we alsnog Optie B of C implementeren. Voor nu is Optie A voldoende voor MVP fase.

---

## Referenties

- Outreach Plan: `Docs/claim-consent-outreach-implementation-plan.md`
- Pre-Claim Outreach Plan: `Docs/pre-claim-outreach-implementation-plan.md` (Stap 0.1-0.3)
- Contact Discovery Service: `Backend/services/contact_discovery_service.py`
- OSM Service: `Backend/services/osm_service.py`

