# Pre-Claim & Consent Outreach Implementation Plan

**Status**: 🔴 Niet Gestart  
**Laatste Update**: 2025-01-XX  
**Epic**: Pre-Outreach Foundation  
**Prerequisite voor**: Claim & Consent Outreach Implementation Plan

Dit document beschrijft de incrementele implementatie van de foundation die nodig is voordat we kunnen starten met het Claim & Consent Outreach Bot systeem. Het plan is opgedeeld in logische stappen die incrementeel door Cursor kunnen worden uitgevoerd.

## 📋 Overzicht

Het outreach systeem vereist een solide foundation:
- **Google Places Service Beslissing**: Contact discovery vereist Google Places API of alternatief
- **Email Service Foundation**: Amazon SES setup en email service abstraction
- **Contact Discovery Service**: Service voor het ontdekken van contactgegevens (email, website)
- **Token-based Claim System**: Verschillend van bestaand business_account claims systeem
- **Outreach Infrastructure**: Queue, rate limiting, en tracking systemen

---

## 🎯 Implementatie Status Tracking

### Fase 0: Google Places Service Beslissing
- [ ] **Stap 0.1**: Analyse Google Places API vereisten voor contact discovery ⚠️ BESLUIT NODIG
- [ ] **Stap 0.2**: Beslissing over Google Places API gebruik (herintroduceren of alternatief)
- [ ] **Stap 0.3**: Implementeer gekozen approach

### Fase 1: Email Service Foundation
- [ ] **Stap 1.1**: AWS SES account setup en domain verification planning
- [ ] **Stap 1.2**: Email service abstraction layer (SES provider)
- [ ] **Stap 1.3**: Email template systeem foundation
- [ ] **Stap 1.4**: Email service testing en error handling

### Fase 2: Contact Discovery Service Foundation
- [ ] **Stap 2.1**: Contact discovery service interface en structuur
- [ ] **Stap 2.2**: OSM contact discovery implementatie
- [ ] **Stap 2.3**: Website scraping contact discovery (optioneel)
- [ ] **Stap 2.4**: Confidence scoring logica
- [ ] **Stap 2.5**: Contact discovery service integratie test

### Fase 3: Token-based Claim System Foundation
- [ ] **Stap 3.1**: Analyse verschil tussen business_account claims en token-based claims
- [ ] **Stap 3.2**: Database schema voor token-based location_claims
- [ ] **Stap 3.3**: Token generation en validatie service
- [ ] **Stap 3.4**: Token-based claim API endpoints foundation
- [ ] **Stap 3.5**: Frontend routing voor token-based claim pagina

### Fase 4: Outreach Infrastructure Foundation
- [ ] **Stap 4.1**: Outreach queue database schema
- [ ] **Stap 4.2**: Rate limiting service voor emails
- [ ] **Stap 4.3**: Outreach tracking en metrics foundation
- [ ] **Stap 4.4**: Outreach infrastructure integratie test

---

## 📐 Gedetailleerde Stappen

### FASE 0: Google Places Service Beslissing

#### Stap 0.1: Analyse Google Places API Vereisten voor Contact Discovery

**Doel**: In kaart brengen wat er nodig is voor contact discovery en welke opties er zijn.

**Te Analyseren**:
1. **Outreach Plan Vereisten** (Stap 3.1):
   - Contact discovery strategie: OSM tags, website scraping, Google Business profile, social bio
   - Google Places API wordt genoemd als één van de strategieën
   - Confidence scoring op basis van bron

2. **Huidige Situatie**:
   - Google Places service is verwijderd (kostenbesparing)
   - OSM service bestaat en werkt goed
   - Discovery gebruikt nu alleen OSM Overpass API

3. **Google Places API Kosten**:
   - Place Details API: ~$0.017 per request
   - Text Search API: ~$0.032 per request
   - Contact discovery vereist Place Details per locatie
   - Volume: ~150+ verified locaties in Rotterdam, groeiend naar 500+ per stad

4. **Alternatieven**:
   - **Optie A**: Alleen OSM tags + website scraping (geen Google)
   - **Optie B**: Google Places API herintroduceren (alleen voor contact discovery)
   - **Optie C**: Hybride: OSM eerst, Google als fallback voor hoge confidence locaties

**⚠️ BESLUIT NODIG**: Welke approach kiezen we voor contact discovery?

**Acceptatie Criteria**:
- [ ] Analyse document gemaakt met kosten en opties
- [ ] Impact assessment compleet
- [ ] Beslissing genomen over approach
- [ ] Plan gemaakt voor gekozen approach

**Bestanden om aan te maken**:
- `Docs/contact-discovery-options-analysis.md` (nieuw, analyse document)

---

#### Stap 0.2: Beslissing over Google Places API Gebruik

**Doel**: Finale beslissing nemen over contact discovery approach.

**⚠️ BESLUIT NODIG**: Bevestig gekozen approach van Stap 0.1.

**Opties**:

**Optie A: Alleen OSM + Website Scraping (Geen Google)**
- ✅ Voordelen: Geen API kosten, volledig open-source
- ✅ OSM tags bevatten vaak email/contact info
- ✅ Website scraping kan contact pagina's lezen
- ❌ Nadelen: Minder complete data, mogelijk lagere confidence scores
- ❌ Geen Google Business profile data

**Optie B: Google Places API Herintroduceren (Alleen Contact Discovery)**
- ✅ Voordelen: Rijke contact data, hoge confidence scores
- ✅ Google Business profiles bevatten vaak email/phone
- ❌ Nadelen: API kosten (~$0.017 per locatie)
- ❌ Extra dependency en rate limiting nodig
- ❌ Volume: 500 locaties = ~$8.50 per stad (eenmalig)

**Optie C: Hybride Approach (OSM Eerst, Google Fallback)**
- ✅ Voordelen: Kostenbesparend (alleen Google als OSM faalt)
- ✅ Beste van beide werelden
- ❌ Nadelen: Complexere logica, twee API's beheren
- ❌ Nog steeds Google API kosten (maar beperkt)

**💡 Mijn Suggestie**: Optie A (Alleen OSM + Website Scraping)
- **Motivatie**: 
  - Outreach plan zegt "geen guessing" - OSM tags zijn betrouwbaar
  - Website scraping kan contact pagina's lezen (gratis)
  - Kostenbesparend voor MVP fase
  - Later kunnen we Google toevoegen als confidence scores te laag zijn
  - Focus op kwaliteit over kwantiteit: alleen hoge confidence contacts

**Als Optie B of C gekozen**:
- Maak Google Places service (herintroduceren)
- Implementeer rate limiting specifiek voor contact discovery
- Budget planning voor API kosten

**Acceptatie Criteria**:
- [ ] Beslissing is genomen en gedocumenteerd
- [ ] Plan is duidelijk voor implementatie
- [ ] Kosten impact is begrepen (indien Google gekozen)
- [ ] Migration path is duidelijk

**Bestanden om aan te maken/wijzigen**:
- `Docs/contact-discovery-options-analysis.md` (update, beslissing gedocumenteerd)
- `Backend/services/google_places_service.py` (nieuw, alleen als Optie B of C gekozen)

---

#### Stap 0.3: Implementeer Gekozen Approach

**Doel**: Implementeer de gekozen contact discovery approach.

**Als Optie A (OSM + Website) gekozen**:
- Skip Google Places service (niet nodig)
- Focus op OSM tags en website scraping in Stap 2.2 en 2.3

**Als Optie B (Google Places) gekozen**:
- Maak `Backend/services/google_places_service.py`
- Implementeer Place Details API call voor contact info
- Rate limiting en error handling
- Integratie met contact discovery service

**Als Optie C (Hybride) gekozen**:
- Implementeer beide: OSM eerst, Google als fallback
- Fallback logica in contact discovery service

**Acceptatie Criteria**:
- [ ] Gekozen approach is geïmplementeerd
- [ ] Service werkt correct
- [ ] Error handling en rate limiting zijn correct
- [ ] Tests voor verschillende scenario's

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/google_places_service.py` (alleen als Optie B of C)
- `Backend/services/contact_discovery_service.py` (update, integratie)

---

### FASE 1: Email Service Foundation

#### Stap 1.1: AWS SES Account Setup en Domain Verification Planning

**Doel**: AWS SES account voorbereiden en domain verification proces documenteren.

**Configuratie Vereist**:
- AWS SES account setup (of bestaand account gebruiken)
- Domain verification planning (SPF, DKIM, DMARC records)
- SES sandbox vs production access planning

**Documentatie Vereist**:
- SES account setup stappen
- Domain verification proces
- DNS records die nodig zijn (SPF, DKIM, DMARC)
- Production access request proces

**Acceptatie Criteria**:
- [ ] SES setup guide document bestaat
- [ ] Domain verification proces is gedocumenteerd
- [ ] DNS records zijn geïdentificeerd
- [ ] Production access request template is klaar

**Bestanden om aan te maken**:
- `Docs/ses-setup-guide.md` (nieuw, documentatie)
- `Docs/ses-production-request.md` (nieuw, template voor request)

**Noot**: Daadwerkelijke SES setup en domain verification gebeurt later in het outreach plan (Fase 5), maar planning moet nu gebeuren.

---

#### Stap 1.2: Email Service Abstraction Layer (SES Provider)

**Doel**: Abstracte email service die SES gebruikt, maar later uitbreidbaar is naar Brevo.

**Interface**:
```python
class EmailProvider(ABC):
    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        reply_to: Optional[str] = None
    ) -> str:  # Returns message_id
        pass
```

**Implementatie**:
- Abstracte base class `EmailProvider`
- `SESEmailProvider` implementatie (boto3)
- Factory pattern voor provider selectie
- Configuratie via env vars

**Error Handling**:
- SES throttling errors
- Bounce handling
- Invalid email addresses
- Network errors

**Acceptatie Criteria**:
- [ ] Abstracte interface bestaat
- [ ] SES provider implementatie werkt
- [ ] Error handling is robuust
- [ ] Configuratie via env vars
- [ ] Message ID wordt geretourneerd
- [ ] Unit tests voor provider

**Bestanden om aan te maken**:
- `Backend/services/email/__init__.py` (nieuw, package)
- `Backend/services/email/base.py` (nieuw, abstract interface)
- `Backend/services/email/ses_provider.py` (nieuw, SES implementatie)
- `Backend/services/email_service.py` (nieuw, factory en main service)
- Update `.env.example` met AWS SES config

**Noot**: Voor nu alleen SES provider. Brevo provider komt later (Fase 10 van outreach plan).

---

#### Stap 1.3: Email Template Systeem Foundation

**Doel**: Template systeem voor email rendering (Jinja2).

**Template Features**:
- Jinja2 template engine
- Plain text + HTML versies
- Token variabelen (location_name, claim_token, etc.)
- Geen tracking pixels (privacy-first)

**Template Structuur**:
- `Backend/templates/emails/` directory
- Base template voor consistentie
- Template service voor rendering

**Acceptatie Criteria**:
- [ ] Template systeem bestaat
- [ ] Jinja2 is geconfigureerd
- [ ] Template service kan templates renderen
- [ ] Variabelen worden correct geïnjecteerd
- [ ] Plain text + HTML versies werken

**Bestanden om aan te maken**:
- `Backend/services/email_template_service.py` (nieuw)
- `Backend/templates/emails/base.html.j2` (nieuw, base template)
- `Backend/templates/emails/base.txt.j2` (nieuw, plain text base)
- Update `Backend/requirements.txt` met `jinja2`

**Noot**: Specifieke email templates (outreach, claim confirmation, etc.) komen later in outreach plan (Fase 6).

---

#### Stap 1.4: Email Service Testing en Error Handling

**Doel**: Comprehensive testing en error handling voor email service.

**Test Scenarios**:
1. Succesvolle email verzending
2. SES throttling error handling
3. Invalid email address handling
4. Network error handling
5. Bounce event handling (mock)

**Error Handling**:
- Retry logica voor transient errors
- Backoff strategy
- Error logging
- Graceful degradation

**Acceptatie Criteria**:
- [ ] Unit tests voor email service
- [ ] Error handling werkt correct
- [ ] Retry logica werkt
- [ ] Logging is correct
- [ ] Test email kan worden verzonden (met test credentials)

**Bestanden om aan te maken/wijzigen**:
- `Backend/tests/test_email_service.py` (nieuw)
- `Backend/services/email_service.py` (update, error handling)

---

### FASE 2: Contact Discovery Service Foundation

#### Stap 2.1: Contact Discovery Service Interface en Structuur

**Doel**: Service structuur opzetten voor contact discovery.

**Service Interface**:
```python
async def discover_contact(location_id: int) -> Optional[ContactInfo]:
    """
    Discover contact information for a location.
    
    Returns:
        ContactInfo with email, source, confidence_score
        None if no contact found or confidence too low
    """
```

**ContactInfo Model**:
```python
class ContactInfo(BaseModel):
    email: str
    source: str  # 'osm', 'website', 'google', 'social'
    confidence_score: int  # 0-100
    discovered_at: datetime
```

**Service Structuur**:
- Main service: `contact_discovery_service.py`
- Strategy pattern voor verschillende discovery methoden
- Confidence scoring logica
- Error handling en logging

**Acceptatie Criteria**:
- [ ] Service interface bestaat
- [ ] ContactInfo model bestaat
- [ ] Service structuur is duidelijk
- [ ] Error handling is gepland

**Bestanden om aan te maken**:
- `Backend/services/contact_discovery_service.py` (nieuw, structuur)
- `Backend/app/models/contact.py` (nieuw, ContactInfo model)

---

#### Stap 2.2: OSM Contact Discovery Implementatie

**Doel**: Implementeer OSM-based contact discovery.

**OSM Tags te Checken**:
- `email` tag (direct email)
- `contact:email` tag (contact email)
- `website` tag (voor later website scraping)

**Implementatie**:
- Query OSM data voor location (via place_id of lat/lng)
- Extract email tags
- Confidence scoring: OSM email = 90, OSM contact:email = 85

**Error Handling**:
- OSM data niet beschikbaar
- Invalid email format
- Rate limiting (als OSM API gebruikt wordt)

**Acceptatie Criteria**:
- [ ] OSM contact discovery werkt
- [ ] Email tags worden correct geëxtraheerd
- [ ] Confidence scores zijn correct
- [ ] Error handling werkt

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/contact_discovery_service.py` (update, OSM strategy)
- `Backend/services/osm_service.py` (update, indien nodig voor contact data)

---

#### Stap 2.3: Website Scraping Contact Discovery (Optioneel)

**Doel**: Implementeer website scraping voor contact discovery.

**⚠️ BESLUIT NODIG**: Website scraping toevoegen?

**Opties**:
- **Optie A**: Skip website scraping (alleen OSM)
- **Optie B**: Implementeer website scraping (contact pagina's lezen)

**Als Optie B gekozen**:
- Scrape website contact pagina (als website tag in OSM)
- Extract email via regex of HTML parsing
- Confidence scoring: Website contact = 70
- Respect robots.txt en rate limiting

**Acceptatie Criteria**:
- [ ] Beslissing genomen
- [ ] Website scraping werkt (als gekozen)
- [ ] Email extraction is correct
- [ ] Rate limiting wordt gerespecteerd

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/contact_discovery_service.py` (update, website strategy)
- `Backend/services/website_scraper_service.py` (nieuw, als Optie B)

---

#### Stap 2.4: Confidence Scoring Logica

**Doel**: Confidence scoring systeem voor contact discovery.

**Scoring Regels** (uit outreach plan):
- OSM email tag: 90
- OSM contact:email tag: 85
- Website contact pagina: 70
- Google Business profile: 80 (als Google gekozen)
- Social bio: 60

**Penalties**:
- Generic email (info@, contact@): -10
- Onvolledige email: -20

**Drempelwaarde**:
- Configureerbaar via env var (default: 50)
- Alleen contacts met confidence >= drempel worden opgeslagen

**Acceptatie Criteria**:
- [ ] Scoring functie bestaat
- [ ] Scores zijn consistent
- [ ] Drempelwaarde is configureerbaar
- [ ] Penalties werken correct
- [ ] Tests voor verschillende scenario's

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/contact_discovery_service.py` (update, scoring logica)

---

#### Stap 2.5: Contact Discovery Service Integratie Test

**Doel**: End-to-end test van contact discovery service.

**Test Scenarios**:
1. OSM email tag discovery
2. OSM contact:email tag discovery
3. Website scraping (als geïmplementeerd)
4. Google Places (als gekozen)
5. Confidence scoring edge cases
6. Error handling (geen contact gevonden, invalid email, etc.)

**Acceptatie Criteria**:
- [ ] Alle discovery strategieën werken
- [ ] Confidence scoring is correct
- [ ] Error handling werkt
- [ ] Service kan worden geïntegreerd in worker

**Bestanden om aan te maken**:
- `Backend/tests/test_contact_discovery.py` (nieuw)

---

### FASE 3: Token-based Claim System Foundation

#### Stap 3.1: Analyse Verschil tussen business_account Claims en Token-based Claims

**Doel**: Duidelijk maken wat het verschil is tussen beide claim systemen.

**Bestaand Systeem** (`business_location_claims`):
- Voor authenticated users met business_accounts
- Status: pending → approved/rejected (admin approval)
- Gekoppeld aan business_account_id
- Vereist login en business account

**Nieuw Systeem** (`location_claims` - uit outreach plan):
- Token-based (geen login vereist)
- Status: unclaimed → claimed_free → expired/removed
- Gekoppeld aan email (niet user_id)
- Gratis periode met expiratie
- Geen admin approval nodig

**Conclusie**:
- Twee verschillende systemen voor verschillende use cases
- Beide kunnen naast elkaar bestaan
- `business_location_claims` = premium/verified claims (toekomstig)
- `location_claims` = gratis outreach claims (outreach plan)

**Acceptatie Criteria**:
- [ ] Verschil is duidelijk gedocumenteerd
- [ ] Beide systemen kunnen naast elkaar bestaan
- [ ] Naming is duidelijk (geen verwarring)

**Bestanden om aan te maken**:
- `Docs/claim-systems-comparison.md` (nieuw, documentatie)

---

#### Stap 3.2: Database Schema voor Token-based location_claims

**Doel**: Database tabel aanmaken voor token-based claims (uit outreach plan Stap 2.3).

**Database Changes** (uit outreach plan):
- Nieuwe ENUM type `claim_status`:
  - `unclaimed` (nog niet geclaimed)
  - `claimed_free` (geclaimed, gratis periode actief)
  - `expired` (gratis periode verlopen)
  - `removed` (verwijderd door eigenaar)

- Nieuwe tabel `location_claims`:
  - `id` bigserial PRIMARY KEY
  - `location_id` bigint (FK naar locations, UNIQUE)
  - `claim_token` text (UNIQUE, voor token-based access)
  - `claim_status` claim_status DEFAULT 'unclaimed'
  - `claimed_by_email` text
  - `claimed_at` timestamptz
  - `free_until` timestamptz (einde gratis periode)
  - `removed_at` timestamptz
  - `removal_reason` text
  - `created_at` timestamptz DEFAULT NOW()
  - `updated_at` timestamptz DEFAULT NOW()

**Indexen**:
- Index op `location_id` (UNIQUE constraint)
- Index op `claim_token` (voor snelle lookups)
- Index op `claim_status`

**Acceptatie Criteria**:
- [ ] ENUM type bestaat
- [ ] Tabel bestaat met correcte constraints
- [ ] Indexen zijn aangemaakt
- [ ] Migration script in `Infra/supabase/`

**Bestanden om aan te maken**:
- `Infra/supabase/073_location_claims.sql` (nieuwe migration)

**Noot**: Dit komt uit outreach plan Stap 2.3, maar moet nu gebeuren als foundation.

---

#### Stap 3.3: Token Generation en Validatie Service

**Doel**: Service voor het genereren en valideren van claim tokens.

**Token Requirements**:
- Uniek per location
- Cryptographically secure (niet voorspelbaar)
- Lang genoeg voor security (minimaal 32 characters)
- URL-safe (voor gebruik in `/claim/{token}`)

**Token Generation**:
- Gebruik `secrets.token_urlsafe()` of `uuid.uuid4().hex`
- Store in database met location_id
- One-time generation per location (of regeneratie mogelijk?)

**Token Validatie**:
- Check of token bestaat in database
- Check of token nog geldig is (niet expired, status correct)
- Return location_id en claim info

**Acceptatie Criteria**:
- [ ] Token generation service bestaat
- [ ] Tokens zijn uniek en secure
- [ ] Token validatie werkt
- [ ] Error handling (invalid token, expired, etc.)

**Bestanden om aan te maken**:
- `Backend/services/claim_token_service.py` (nieuw)

---

#### Stap 3.4: Token-based Claim API Endpoints Foundation

**Doel**: Backend endpoints voor token-based claims (uit outreach plan Stap 7.2).

**Endpoints** (uit outreach plan):
- `GET /api/v1/claims/{token}` - Haal claim info op (location details)
- `POST /api/v1/claims/{token}/claim` - Claim locatie
- `POST /api/v1/claims/{token}/remove` - Verwijder locatie
- `POST /api/v1/claims/{token}/correct` - Stuur correctie door

**Request/Response Models**:
- Claim: email, logo (optioneel), description (optioneel)
- Remove: reason (optioneel)
- Correct: correction_details (text)

**Acceptatie Criteria**:
- [ ] Alle endpoints bestaan
- [ ] Token validatie werkt
- [ ] Pydantic models zijn correct
- [ ] Error handling werkt
- [ ] Endpoints kunnen worden getest

**Bestanden om aan te maken**:
- `Backend/api/routers/outreach_claims.py` (nieuw, token-based claims)
- Update `Backend/app/main.py` om router te includen

**Noot**: Volledige implementatie (state updates, email triggers) komt later in outreach plan, maar foundation moet nu.

---

#### Stap 3.5: Frontend Routing voor Token-based Claim Pagina

**Doel**: Frontend routing en basis pagina structuur voor `/claim/{token}`.

**Routing**:
- Route: `/claim/:token` (HashRouter compatible: `#/claim/{token}`)
- Component: `ClaimPage.tsx`
- Geen auth vereist (public route)

**Basis UI**:
- Token validatie (API call naar `/api/v1/claims/{token}`)
- Loading state
- Error state (invalid token)
- Placeholder voor claim actions (wordt later geïmplementeerd in outreach plan)

**Acceptatie Criteria**:
- [ ] Route bestaat
- [ ] Component kan token uit URL halen
- [ ] API call werkt
- [ ] Loading en error states werken
- [ ] Responsive design

**Bestanden om aan te maken**:
- `Frontend/src/pages/ClaimPage.tsx` (nieuw, basis structuur)
- Update `Frontend/src/main.tsx` om route toe te voegen

**Noot**: Volledige UI (claim form, remove confirmation, etc.) komt later in outreach plan (Fase 7).

---

### FASE 4: Outreach Infrastructure Foundation

#### Stap 4.1: Outreach Queue Database Schema

**Doel**: Database schema voor outreach queue (uit outreach plan Stap 2.1 en 2.2).

**Database Changes** (uit outreach plan):
- Nieuwe tabel `outreach_contacts`:
  - `id` bigserial PRIMARY KEY
  - `location_id` bigint (FK naar locations)
  - `email` text (NOT NULL)
  - `source` text (website / google / osm / social)
  - `confidence_score` integer (0-100)
  - `discovered_at` timestamptz
  - `created_at` timestamptz DEFAULT NOW()
  - UNIQUE constraint op (location_id, email)

- Nieuwe ENUM type `outreach_email_status`:
  - `queued` (in wachtrij)
  - `sent` (verzonden)
  - `delivered` (afgeleverd)
  - `bounced` (teruggekaatst)
  - `clicked` (link geklikt)
  - `opted_out` (afgemeld)

- Nieuwe tabel `outreach_emails`:
  - `id` bigserial PRIMARY KEY
  - `location_id` bigint (FK naar locations)
  - `contact_id` bigint (FK naar outreach_contacts)
  - `email` text (NOT NULL)
  - `status` outreach_email_status DEFAULT 'queued'
  - `ses_message_id` text (AWS SES message ID)
  - `sent_at` timestamptz
  - `delivered_at` timestamptz
  - `clicked_at` timestamptz
  - `bounced_at` timestamptz
  - `bounce_reason` text
  - `created_at` timestamptz DEFAULT NOW()
  - `updated_at` timestamptz DEFAULT NOW()

**Indexen**:
- Index op `location_id` in beide tabellen
- Index op `email` in outreach_contacts
- Index op `status` in outreach_emails
- Index op `contact_id` in outreach_emails

**Acceptatie Criteria**:
- [ ] Tabellen bestaan
- [ ] ENUM type bestaat
- [ ] Indexen zijn aangemaakt
- [ ] UNIQUE constraints werken
- [ ] Migration script in `Infra/supabase/`

**Bestanden om aan te maken**:
- `Infra/supabase/074_outreach_contacts.sql` (nieuwe migration)
- `Infra/supabase/075_outreach_emails.sql` (nieuwe migration)

**Noot**: Dit komt uit outreach plan Fase 2, maar moet nu als foundation.

---

#### Stap 4.2: Rate Limiting Service voor Emails

**Doel**: Service die rate limiting beheert voor email verzending (uit outreach plan Stap 4.2).

**Rate Limiting Regels** (uit outreach plan):
- Start: 50 mails / dag
- Opschalen naar 100 → 250 → 500 (configureerbaar)
- Max 1 mail per locatie, ooit (geen herhalingen)
- Respecteer SES throttling limits

**Implementatie**:
- Track dagelijkse email count (via database of cache)
- Check tegen limiet voordat email wordt verzonden
- Backoff bij SES throttling errors
- Configuratie via env vars

**Acceptatie Criteria**:
- [ ] Rate limiting service bestaat
- [ ] Dagelijkse limiet wordt gerespecteerd
- [ ] Configuratie via env vars
- [ ] Logging voor monitoring
- [ ] Tests voor verschillende limieten

**Bestanden om aan te maken**:
- `Backend/services/rate_limiting_service.py` (nieuw)
- Update `.env.example` met rate limiting config

---

#### Stap 4.3: Outreach Tracking en Metrics Foundation

**Doel**: Foundation voor outreach tracking en metrics (uit outreach plan Fase 9).

**Metrics Vereist** (uit outreach plan):
- `mails_sent` (totaal aantal verzonden emails)
- `bounce_rate` (percentage bounces)
- `claim_rate` (percentage claims na email)
- `removal_rate` (percentage removals)
- `no_action_rate` (percentage geen actie)
- `click_rate` (percentage clicks op token link)

**Implementatie**:
- Metrics kunnen worden berekend uit `outreach_emails` en `location_claims` data
- Service voor metrics berekening
- Optioneel: Materialized view voor performance

**Acceptatie Criteria**:
- [ ] Metrics service structuur bestaat
- [ ] Metrics kunnen worden berekend
- [ ] Service is uitbreidbaar voor toekomstige metrics

**Bestanden om aan te maken**:
- `Backend/services/outreach_metrics_service.py` (nieuw, foundation)

**Noot**: Volledige implementatie en endpoints komen later in outreach plan (Fase 9).

---

#### Stap 4.4: Outreach Infrastructure Integratie Test

**Doel**: End-to-end test van outreach infrastructure.

**Test Scenarios**:
1. Contact discovery → outreach_contacts insert
2. Queue management → outreach_emails insert
3. Rate limiting check
4. Email verzending (mock)
5. Status updates
6. Metrics berekening

**Acceptatie Criteria**:
- [ ] Alle componenten werken samen
- [ ] Data flow is correct
- [ ] Error handling werkt
- [ ] Performance is acceptabel

**Bestanden om aan te maken**:
- `Backend/tests/test_outreach_infrastructure.py` (nieuw)

---

## 🔄 Workflow voor Incrementele Implementatie

### Voor elke stap:

1. **Lees deze documentatie** voor de specifieke stap
2. **Verken bestaande code** om te begrijpen wat al bestaat
3. **Voor BESLISSING stappen**: Leg beslissing voor aan gebruiker met suggestie, wacht op bevestiging
4. **Implementeer stap** volgens acceptatie criteria
5. **Test lokaal** dat alles werkt
6. **Update status** in dit document (vink checkbox aan)
7. **Commit changes** met duidelijke commit message

### Voor database wijzigingen:

1. Maak migration script in `Infra/supabase/`
2. Test migration lokaal
3. Documenteer wijzigingen
4. Update dit document met migration nummer

### Voor API endpoints:

1. Volg FastAPI patterns uit bestaande code
2. Gebruik Pydantic models voor request/response
3. Implementeer error handling
4. Voeg tests toe
5. Documenteer in API docs (indien beschikbaar)

### Voor BESLISSING stappen:

**Wanneer je een stap tegenkomt met "⚠️ BESLUIT NODIG":**

1. **Stop implementatie**
2. **Presenteer opties** aan gebruiker met:
   - Duidelijke uitleg van elke optie
   - Voordelen en nadelen
   - Jouw suggestie met motivatie
3. **Wacht op bevestiging** van gebruiker
4. **Implementeer** gekozen optie
5. **Documenteer beslissing** in relevante bestanden

**Voorbeeld van hoe besluit voor te leggen:**

```
⚠️ BESLUIT NODIG: Google Places API voor Contact Discovery (Stap 0.1)

Opties:
A) Alleen OSM + Website Scraping - Geen Google API
   ✅ Voordelen: Geen API kosten, volledig open-source
   ❌ Nadelen: Minder complete data, mogelijk lagere confidence scores

B) Google Places API Herintroduceren - Alleen voor contact discovery
   ✅ Voordelen: Rijke contact data, hoge confidence scores
   ❌ Nadelen: API kosten (~$0.017 per locatie), extra dependency

C) Hybride Approach - OSM eerst, Google als fallback
   ✅ Voordelen: Kostenbesparend, beste van beide werelden
   ❌ Nadelen: Complexere logica, nog steeds Google API kosten

💡 Mijn suggestie: Optie A (Alleen OSM + Website Scraping)
   Motivatie: Kostenbesparend voor MVP fase, OSM tags zijn betrouwbaar,
   website scraping kan contact pagina's lezen. Later kunnen we Google
   toevoegen als confidence scores te laag zijn.

Welke optie kiezen we?
```

---

## 📝 Notities & Overwegingen

### Google Places API Considerations

- **Kosten**: ~$0.017 per Place Details request
- **Volume**: 500 locaties = ~$8.50 per stad (eenmalig)
- **Rate Limiting**: Google heeft rate limits, extra complexity
- **Alternatief**: OSM tags + website scraping is gratis en vaak voldoende

### Email Service Considerations

- **SES Sandbox**: Start in sandbox mode (alleen verified emails)
- **Production Access**: Vereist request aan AWS (kan 24-48 uur duren)
- **Domain Verification**: SPF, DKIM, DMARC records nodig
- **Deliverability**: Reputatie opbouwen is belangrijk voor hoge deliverability

### Contact Discovery Considerations

- **Confidence Scoring**: Belangrijk voor kwaliteit over kwantiteit
- **Rate Limiting**: Respecteer externe API limits (OSM, Google, website scraping)
- **Privacy**: Alleen publiek beschikbare contactgegevens gebruiken
- **AVG Compliance**: Gerechtvaardigd belang voor outreach

### Token-based Claims Considerations

- **Security**: Tokens moeten cryptographically secure zijn
- **Uniqueness**: Elke location krijgt unieke token
- **Expiry**: Gratis periode heeft expiratie (configureerbaar)
- **State Management**: Status transitions moeten duidelijk zijn

### Outreach Infrastructure Considerations

- **Queue Management**: Prioritering op basis van verified date
- **Rate Limiting**: Start conservatief (50/dag), opschalen geleidelijk
- **Tracking**: Alle acties moeten worden gelogd voor AVG compliance
- **Metrics**: Belangrijk voor validatie van outreach effectiviteit

### Testing Strategy

- Unit tests voor services
- Integration tests voor API endpoints
- E2E tests voor claim flow
- Mock tests voor email service (geen echte emails in tests)
- Load tests voor rate limiting (voorzichtig, respecteer SES limits)

---

## 🚀 Quick Start voor Cursor

**Om te beginnen met een stap:**

1. Open dit document
2. Kies een stap die nog niet is voltooid (unchecked checkbox)
3. Lees de stap beschrijving en acceptatie criteria
4. **Als stap "⚠️ BESLUIT NODIG" bevat**: Leg beslissing voor aan gebruiker
5. Verken relevante bestaande code
6. Implementeer volgens specificatie
7. Update checkbox wanneer klaar

**Voorbeeld prompt voor Cursor:**

```
Ik wil Stap 0.1 implementeren: Analyse Google Places API Vereisten.
Lees eerst de specificatie in Docs/pre-claim-outreach-implementation-plan.md
en bekijk het outreach plan voor contact discovery vereisten.
Leg de beslissing over Google Places API gebruik voor aan de gebruiker.
```

---

## 📚 Referenties

- Outreach Plan: `Docs/claim-consent-outreach-implementation-plan.md`
- OSM Service: `Backend/services/osm_service.py`
- Locations: `Infra/supabase/0001_init.sql`, `Backend/api/routers/locations.py`
- Business Claims: `Infra/supabase/031_business_accounts.sql`, `Backend/api/routers/claims.py`
- Worker Patterns: `Backend/app/workers/discovery_bot.py`, `Backend/app/workers/verify_locations.py`
- Database Migrations: `Infra/supabase/`
- Design System: `Docs/design-system.md`

---

**Laatste Update**: 2025-01-XX  
**Huidige Status**: 🔴 Niet Gestart  
**Volgende Stap**: Fase 0 - Google Places Service Beslissing (Stap 0.1: Analyse Google Places API vereisten)


