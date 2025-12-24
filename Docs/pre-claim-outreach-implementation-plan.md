# Pre-Claim & Consent Outreach Implementation Plan

**Status**: 🔴 Niet Gestart  
**Laatste Update**: 2025-01-XX  
**Epic**: Pre-Outreach Foundation  
**Prerequisite voor**: Claim & Consent Outreach Implementation Plan

Dit document beschrijft de incrementele implementatie van de foundation die nodig is voordat we kunnen starten met het Claim & Consent Outreach Bot systeem. Het plan is opgedeeld in logische stappen die incrementeel door Cursor kunnen worden uitgevoerd.

## 📋 Overzicht

Het outreach systeem vereist een solide foundation:
- **Google Places Service Beslissing**: Contact discovery vereist Google Places API of alternatief
- **Transactionele Email Foundation**: Algemene email infrastructuur voor account registratie, welkom emails, etc.
- **Email Service Foundation**: Amazon SES setup en email service abstraction (voor outreach)
- **Contact Discovery Service**: Service voor het ontdekken van contactgegevens (email, website)
- **Token-based Claim System**: Verschillend van bestaand business_account claims systeem
- **Outreach Infrastructure**: Queue, rate limiting, en tracking systemen

---

## 🎯 Implementatie Status Tracking

### Fase 0: Google Places Service Beslissing
- [ ] **Stap 0.1**: Analyse Google Places API vereisten voor contact discovery ⚠️ BESLUIT NODIG
- [ ] **Stap 0.2**: Beslissing over Google Places API gebruik (herintroduceren of alternatief)
- [ ] **Stap 0.3**: Implementeer gekozen approach

### Fase 0.5: Transactionele Email Foundation
- [ ] **Stap 0.5.1**: Email service migratie (SMTP → SES abstraction)
- [ ] **Stap 0.5.2**: Transactionele email template systeem
- [ ] **Stap 0.5.3**: Welkom email bij account registratie
- [ ] **Stap 0.5.4**: Email verificatie systeem (optioneel)
- [ ] **Stap 0.5.5**: Password reset email (optioneel)

### Fase 1: Email Service Foundation (voor Outreach)
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

### Fase 3: Authenticated Claim System Foundation
- [ ] **Stap 3.1**: Analyse claim systemen (business_account, authenticated, token-based)
- [ ] **Stap 3.2**: Database schema voor authenticated location_claims
- [ ] **Stap 3.3**: Claim API endpoints voor authenticated users
- [ ] **Stap 3.4**: Claim knop in location detail card
- [ ] **Stap 3.5**: Claim form UI (1 scherm met logo/Google Business link)
- [ ] **Stap 3.6**: Admin dashboard voor claim requests
- [ ] **Stap 3.7**: Admin claim detail page (logo/Google link preview)
- [ ] **Stap 3.8**: Owner rol systeem en toekenning
- [ ] **Stap 3.9**: Logo en Google Business link opslag
- [ ] **Stap 3.10**: Email bevestigingen voor claim toekenning/afwijzing
- [ ] **Stap 3.11**: "Senin" sectie op account pagina

### Fase 4: Token-based Claim System Foundation (voor Outreach)
- [ ] **Stap 4.1**: Database schema voor token-based location_claims
- [ ] **Stap 4.2**: Token generation en validatie service
- [ ] **Stap 4.3**: Token-based claim API endpoints foundation
- [ ] **Stap 4.4**: Frontend routing voor token-based claim pagina

### Fase 5: Outreach Infrastructure Foundation
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

### FASE 0.5: Transactionele Email Foundation

**Doel**: Algemene transactionele email infrastructuur opzetten die nodig is voor account registratie, welkom emails, en claim flows. Deze foundation wordt gebruikt door zowel de claim flow als outreach emails.

**Prerequisite**: Deze fase moet worden voltooid voordat claim emails (Stap 3.10) kunnen worden geïmplementeerd.

---

#### Stap 0.5.1: Email Service Migratie (SMTP → SES Abstraction)

**Doel**: Bestaande SMTP-based email service migreren naar provider pattern met SES support, terwijl SMTP als fallback behouden blijft.

**Huidige Situatie**:
- `Backend/services/email_service.py` gebruikt SMTP (SendGrid/Mailgun/Gmail)
- Template systeem bestaat al (Jinja2)
- Digest emails werken al

**Migratie Strategie**:
- Refactor `EmailService` naar provider pattern
- Abstracte `EmailProvider` interface
- `SMTPEmailProvider` (bestaande functionaliteit)
- `SESEmailProvider` (nieuw, uit Fase 1.2)
- Factory pattern voor provider selectie
- Configuratie via env vars: `EMAIL_PROVIDER=smtp|ses`

**Implementatie**:
- Maak `Backend/services/email/` package
- Abstracte base class `EmailProvider`
- `SMTPEmailProvider` (refactor bestaande code)
- `SESEmailProvider` (nieuw, maar kan later worden geïmplementeerd in Fase 1.2)
- `EmailService` factory die provider selecteert
- Backward compatible: SMTP blijft default

**Acceptatie Criteria**:
- [ ] Provider pattern is geïmplementeerd
- [ ] SMTP provider werkt (bestaande functionaliteit behouden)
- [ ] SES provider interface bestaat (implementatie kan later in Fase 1.2)
- [ ] Factory pattern werkt
- [ ] Configuratie via env vars
- [ ] Bestaande digest emails blijven werken
- [ ] Geen breaking changes

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/email/__init__.py` (nieuw, package)
- `Backend/services/email/base.py` (nieuw, abstract interface)
- `Backend/services/email/smtp_provider.py` (nieuw, refactor bestaande code)
- `Backend/services/email/ses_provider.py` (nieuw, skeleton - volledige implementatie in Fase 1.2)
- `Backend/services/email_service.py` (refactor, factory pattern)
- Update `.env.example` met `EMAIL_PROVIDER=smtp`

---

#### Stap 0.5.2: Transactionele Email Template Systeem

**Doel**: Template systeem uitbreiden voor transactionele emails met base templates en meertaligheid.

**Template Structuur**:
- Base templates voor consistentie:
  - `base.html.j2` (HTML base)
  - `base.txt.j2` (plain text base)
- Template service voor rendering
- Meertaligheid support (NL/TR/EN)
- Variabelen systeem

**Template Features**:
- Consistent branding (Turkspot logo, colors)
- Responsive design
- Plain text fallback
- Privacy-first (geen tracking pixels)
- Meertaligheid via context variabele

**Acceptatie Criteria**:
- [ ] Base templates bestaan
- [ ] Template service kan templates renderen
- [ ] Variabelen worden correct geïnjecteerd
- [ ] Plain text + HTML versies werken
- [ ] Meertaligheid werkt (NL/TR/EN)
- [ ] Responsive design

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/email_template_service.py` (nieuw, of update bestaande)
- `Backend/templates/emails/base.html.j2` (nieuw, base template)
- `Backend/templates/emails/base.txt.j2` (nieuw, plain text base)
- Update `Backend/requirements.txt` met `jinja2` (als nog niet aanwezig)

---

#### Stap 0.5.3: Welkom Email bij Account Registratie

**Doel**: Welkom email verzenden na succesvolle account registratie.

**Trigger**:
- Na succesvolle signup via Supabase Auth
- Integratie in signup flow (frontend of backend hook)

**Email Template**:
- Subject: "Welkom bij Turkspot!" (NL) / "Turkspot'a Hoş Geldiniz!" (TR) / "Welcome to Turkspot!" (EN)
- Body: Vriendelijke welkom, introductie tot platform, eerste stappen
- Taal: Gebaseerd op user preference of browser taal

**Implementatie**:
- Template: `welcome_email.html.j2` en `welcome_email.txt.j2`
- Trigger na signup (Supabase Auth hook of backend endpoint)
- Gebruik email service (Stap 0.5.1)
- Gebruik template service (Stap 0.5.2)

**Integratie Opties**:
- **Optie A**: Supabase Database Trigger (aanbevolen)
  - Trigger op `auth.users` INSERT
  - Call backend endpoint of Edge Function
- **Optie B**: Backend Endpoint na signup
  - Frontend roept `/api/v1/auth/send-welcome-email` aan na signup
- **Optie C**: Supabase Edge Function
  - Auth hook trigger

**Acceptatie Criteria**:
- [ ] Welkom email template bestaat
- [ ] Email wordt verzonden na signup
- [ ] Meertaligheid werkt
- [ ] Email bevat correcte informatie
- [ ] Error handling (email failure blokkeert niet signup)

**Bestanden om aan te maken/wijzigen**:
- `Backend/templates/emails/welcome_email.html.j2` (nieuw)
- `Backend/templates/emails/welcome_email.txt.j2` (nieuw)
- `Backend/api/routers/auth.py` (update, welkom email trigger)
- Of: `Infra/supabase/078_welcome_email_trigger.sql` (nieuw, database trigger)

---

#### Stap 0.5.4: Email Verificatie Systeem (Optioneel)

**Doel**: Email verificatie systeem voor nieuwe accounts (als Supabase dit niet al doet).

**⚠️ BESLUIT NODIG**: Is email verificatie nodig, of doet Supabase Auth dit al?

**Als Supabase Auth dit al doet**:
- Skip deze stap
- Documenteer dat Supabase email verificatie gebruikt

**Als email verificatie nodig is**:
- Verificatie token generatie
- Verificatie email template
- Verificatie endpoint
- Status tracking in database

**Acceptatie Criteria**:
- [ ] Beslissing genomen
- [ ] Email verificatie werkt (als geïmplementeerd)
- [ ] Verificatie link werkt
- [ ] Status wordt bijgewerkt

**Bestanden om aan te maken/wijzigen**:
- `Backend/templates/emails/email_verification.html.j2` (alleen als nodig)
- `Backend/api/routers/auth.py` (update, verificatie endpoint)
- Database schema voor verificatie tokens (als nodig)

---

#### Stap 0.5.5: Password Reset Email (Optioneel)

**Doel**: Password reset email systeem (als Supabase dit niet al doet).

**⚠️ BESLUIT NODIG**: Is password reset email nodig, of doet Supabase Auth dit al?

**Als Supabase Auth dit al doet**:
- Skip deze stap
- Documenteer dat Supabase password reset gebruikt

**Als password reset nodig is**:
- Reset token generatie
- Reset email template
- Reset endpoint
- Security best practices (token expiry, one-time use)

**Acceptatie Criteria**:
- [ ] Beslissing genomen
- [ ] Password reset email werkt (als geïmplementeerd)
- [ ] Reset link werkt
- [ ] Security best practices gevolgd

**Bestanden om aan te maken/wijzigen**:
- `Backend/templates/emails/password_reset.html.j2` (alleen als nodig)
- `Backend/api/routers/auth.py` (update, reset endpoint)
- Database schema voor reset tokens (als nodig)

---

### FASE 1: Email Service Foundation (voor Outreach)

**Noot**: Deze fase bouwt voort op de transactionele email foundation (Fase 0.5). Focus hier is op SES setup specifiek voor outreach emails (hogere volumes, rate limiting, etc.).

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

**Doel**: SES provider volledig implementeren voor de email service abstraction (interface bestaat al uit Fase 0.5.1).

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
- [ ] SES provider implementatie is compleet (interface bestaat al uit Fase 0.5.1)
- [ ] SES provider werkt correct
- [ ] Error handling is robuust
- [ ] Configuratie via env vars
- [ ] Message ID wordt geretourneerd
- [ ] Unit tests voor provider
- [ ] Integratie met email service factory werkt

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/email/ses_provider.py` (update, volledige implementatie - skeleton bestaat al uit Fase 0.5.1)
- `Backend/services/email_service.py` (update, SES provider registratie)
- Update `.env.example` met AWS SES config (`AWS_SES_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)

**Noot**: 
- Abstracte interface en factory pattern bestaan al uit Fase 0.5.1
- Voor nu alleen SES provider. Brevo provider komt later (Fase 10 van outreach plan)
- SMTP provider blijft beschikbaar als fallback

---

#### Stap 1.3: Email Template Systeem Foundation (voor Outreach)

**Doel**: Template systeem uitbreiden voor outreach-specifieke templates (base templates bestaan al uit Fase 0.5.2).

**Template Features** (uitbreiding op Fase 0.5.2):
- Outreach-specifieke variabelen (location_name, mapview_link, claim_token, etc.)
- AVG-compliant teksten
- Opt-out links
- Mapview link generatie

**Template Structuur**:
- Base templates bestaan al (Fase 0.5.2)
- Outreach-specifieke templates komen in outreach plan (Fase 6)

**Acceptatie Criteria**:
- [ ] Template systeem ondersteunt outreach variabelen
- [ ] Base templates kunnen worden gebruikt voor outreach templates
- [ ] Template service is klaar voor outreach templates

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/email_template_service.py` (update, outreach variabelen support)
- Base templates bestaan al uit Fase 0.5.2

**Noot**: 
- Base template systeem bestaat al uit Fase 0.5.2
- Specifieke outreach email templates komen later in outreach plan (Fase 6)
- Claim confirmation templates komen in Stap 3.10

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

### FASE 3: Authenticated Claim System Foundation

#### Stap 3.1: Analyse Claim Systemen

**Doel**: Duidelijk maken wat het verschil is tussen alle claim systemen.

**Bestaand Systeem** (`business_location_claims`):
- Voor authenticated users met business_accounts
- Status: pending → approved/rejected (admin approval)
- Gekoppeld aan business_account_id
- Vereist login en business account
- **Gebruik**: Premium/verified claims (toekomstig)

**Nieuw Systeem 1: Authenticated Claims** (`authenticated_location_claims`):
- Voor authenticated users (geen business account nodig)
- Status: pending → approved/rejected (admin approval)
- Gekoppeld aan user_id
- Vereist login
- Optioneel: Logo upload, Google Business link
- Bij toekenning: gebruiker krijgt owner rol
- **Gebruik**: Primaire claim flow voor outreach emails

**Nieuw Systeem 2: Token-based Claims** (`location_claims` - uit outreach plan):
- Token-based (geen login vereist)
- Status: unclaimed → claimed_free → expired/removed
- Gekoppeld aan email (niet user_id)
- Gratis periode met expiratie
- Geen admin approval nodig
- **Gebruik**: Fallback voor niet-ingelogde gebruikers via outreach

**Conclusie**:
- Drie verschillende systemen voor verschillende use cases
- Alle drie kunnen naast elkaar bestaan
- `business_location_claims` = premium/verified claims (toekomstig)
- `authenticated_location_claims` = primaire outreach claim flow (nieuwe visie)
- `location_claims` = token-based fallback (outreach plan)

**Acceptatie Criteria**:
- [ ] Verschil is duidelijk gedocumenteerd
- [ ] Beide systemen kunnen naast elkaar bestaan
- [ ] Naming is duidelijk (geen verwarring)

**Bestanden om aan te maken**:
- `Docs/claim-systems-comparison.md` (nieuw, documentatie)

---

#### Stap 3.2: Database Schema voor Authenticated location_claims

**Doel**: Database tabel aanmaken voor authenticated claims (nieuwe visie).

**Database Changes**:
- Nieuwe ENUM type `authenticated_claim_status`:
  - `pending` (wachtend op admin approval)
  - `approved` (toegekend, gebruiker is owner)
  - `rejected` (afgewezen)

- Nieuwe tabel `authenticated_location_claims`:
  - `id` bigserial PRIMARY KEY
  - `location_id` bigint (FK naar locations, UNIQUE)
  - `user_id` UUID (FK naar auth.users, NOT NULL)
  - `status` authenticated_claim_status DEFAULT 'pending'
  - `google_business_link` text (optioneel, van gebruiker)
  - `logo_url` text (optioneel, van gebruiker, voor preview)
  - `logo_storage_path` text (optioneel, definitieve opslag na approval)
  - `submitted_at` timestamptz DEFAULT NOW()
  - `reviewed_by` UUID (FK naar auth.users, admin die reviewed)
  - `reviewed_at` timestamptz
  - `rejection_reason` text (optioneel)
  - `created_at` timestamptz DEFAULT NOW()
  - `updated_at` timestamptz DEFAULT NOW()

- Nieuwe tabel `location_owners`:
  - `id` bigserial PRIMARY KEY
  - `location_id` bigint (FK naar locations, UNIQUE)
  - `user_id` UUID (FK naar auth.users, NOT NULL)
  - `google_business_link` text (definitief, na approval)
  - `logo_url` text (definitief, na approval)
  - `claimed_at` timestamptz DEFAULT NOW()
  - `created_at` timestamptz DEFAULT NOW()
  - `updated_at` timestamptz DEFAULT NOW()

**Indexen**:
- Index op `location_id` in beide tabellen (UNIQUE constraint)
- Index op `user_id` in authenticated_location_claims
- Index op `status` in authenticated_location_claims
- Index op `user_id` in location_owners

**Acceptatie Criteria**:
- [ ] ENUM type bestaat
- [ ] Tabellen bestaan met correcte constraints
- [ ] Indexen zijn aangemaakt
- [ ] Migration script in `Infra/supabase/`

**Bestanden om aan te maken**:
- `Infra/supabase/073_authenticated_location_claims.sql` (nieuwe migration)

---

#### Stap 3.3: Claim API Endpoints voor Authenticated Users

**Doel**: Backend endpoints voor authenticated claim flow.

**Endpoints**:
- `POST /api/v1/locations/{location_id}/claim` - Submit claim request (authenticated)
- `GET /api/v1/locations/{location_id}/claim-status` - Check claim status voor locatie
- `GET /api/v1/my-claims` - List eigen claims (authenticated user)

**Request/Response Models**:
- Claim Request:
  - `google_business_link` (optioneel, string)
  - `logo` (optioneel, file upload)
- Claim Response:
  - `id`, `location_id`, `status`, `submitted_at`, etc.

**Implementatie Details**:
- Gebruikersaccount data (naam, email) automatisch uit auth context
- Logo upload via file upload endpoint
- Validatie: locatie moet bestaan, niet al geclaimed
- Status tracking: pending → approved/rejected

**Acceptatie Criteria**:
- [ ] Alle endpoints bestaan
- [ ] Authenticatie vereist
- [ ] Logo upload werkt
- [ ] Pydantic models zijn correct
- [ ] Error handling werkt
- [ ] Gebruikersdata wordt automatisch opgehaald

**Bestanden om aan te maken**:
- `Backend/api/routers/authenticated_claims.py` (nieuw)
- Update `Backend/app/main.py` om router te includen

---

#### Stap 3.4: Claim Knop in Location Detail Card

**Doel**: "Claim" knop toevoegen aan location detail card (naast Google zoek knop).

**UI Vereisten**:
- Knop verschijnt in `UnifiedLocationDetail.tsx` en `OverlayDetailCard.tsx`
- Plaatsing: naast Google zoek knop
- Alleen zichtbaar als:
  - Gebruiker is ingelogd
  - Locatie is nog niet geclaimed door deze gebruiker
  - Locatie is claimable
- Bij klik: start claim flow (Stap 3.5)

**Design**:
- Volg design system
- Duidelijke "Claim" tekst of icon
- Disabled state als al geclaimed

**Acceptatie Criteria**:
- [ ] Knop bestaat in location detail cards
- [ ] Correct geplaatst naast Google zoek knop
- [ ] Alleen zichtbaar voor ingelogde gebruikers
- [ ] Correcte disabled states
- [ ] Click handler start claim flow

**Bestanden om aan te maken/wijzigen**:
- `Frontend/src/components/UnifiedLocationDetail.tsx` (update, claim knop)
- `Frontend/src/components/OverlayDetailCard.tsx` (update, claim knop)

---

#### Stap 3.5: Claim Form UI (1 Scherm)

**Doel**: Claim form component met logo upload en Google Business link.

**UI Vereisten**:
- 1 scherm met alle velden
- Automatisch ingevuld: naam, email (uit gebruikersaccount, niet weergegeven)
- Optioneel veld: Google Business link (text input)
- Optioneel veld: Logo upload (file input met preview)
- Submit/Indienen knop
- Loading state tijdens submit
- Success/error feedback

**Form Validatie**:
- Google Business link: URL format validatie
- Logo: file type validatie (images only), size limit
- Minimaal 1 veld ingevuld (Google link OF logo)

**Acceptatie Criteria**:
- [ ] Form component bestaat
- [ ] Alle velden werken
- [ ] Logo upload met preview
- [ ] Validatie werkt
- [ ] Submit werkt
- [ ] Loading en error states
- [ ] Responsive design

**Bestanden om aan te maken**:
- `Frontend/src/components/claim/ClaimForm.tsx` (nieuw)
- `Frontend/src/components/claim/ClaimDialog.tsx` (nieuw, dialog wrapper)

---

#### Stap 3.6: Admin Dashboard voor Claim Requests

**Doel**: Admin dashboard pagina om claim requests te beheren.

**UI Vereisten**:
- Lijst van alle pending claims
- Sorteerbaar/filterbaar op:
  - Status (pending, approved, rejected)
  - Datum (nieuwste eerst)
  - Locatie naam
- Per claim: locatie naam, gebruiker naam/email, submitted_at
- Link naar claim detail page (Stap 3.7)

**Acceptatie Criteria**:
- [ ] Admin dashboard pagina bestaat
- [ ] Lijst toont alle claims
- [ ] Sorteer/filter functionaliteit
- [ ] Link naar detail page
- [ ] Admin authenticatie vereist

**Bestanden om aan te maken**:
- `Frontend/src/pages/admin/AdminClaimsPage.tsx` (nieuw)
- Update `Frontend/src/main.tsx` om route toe te voegen
- Update admin navigation

---

#### Stap 3.7: Admin Claim Detail Page (Logo/Google Link Preview)

**Doel**: Admin detail pagina om claim request te reviewen en goedkeuren/afwijzen.

**UI Vereisten**:
- Locatie informatie
- Gebruiker informatie (naam, email)
- Google Business link (als ingevuld):
  - Link preview/display
  - Externe link knop om te openen
- Logo (als geüpload):
  - Image preview
  - Download knop (optioneel)
- Actie knoppen:
  - "Toekennen" (approve)
  - "Afwijzen" (reject) met optioneel reden veld
- Bevestiging dialogs voor acties

**Acceptatie Criteria**:
- [ ] Detail page bestaat
- [ ] Alle informatie wordt getoond
- [ ] Logo preview werkt
- [ ] Google link preview werkt
- [ ] Approve/reject acties werken
- [ ] Bevestiging dialogs
- [ ] Admin authenticatie vereist

**Bestanden om aan te maken**:
- `Frontend/src/pages/admin/AdminClaimDetailPage.tsx` (nieuw)
- `Frontend/src/components/admin/ClaimReviewActions.tsx` (nieuw)

---

#### Stap 3.8: Owner Rol Systeem en Toekenning

**Doel**: Rol systeem voor location owners en automatische toekenning bij claim approval.

**Database Changes**:
- Nieuwe ENUM type `user_role` (als nog niet bestaat):
  - `user` (standaard gebruiker)
  - `location_owner` (eigenaar van locatie(s))
  - `admin` (admin gebruiker)
  - etc.

- Update `auth.users` of nieuwe tabel `user_roles`:
  - `user_id` UUID (FK naar auth.users)
  - `role` user_role
  - `granted_at` timestamptz
  - `granted_by` UUID (FK naar auth.users, admin)

**Logica bij Claim Approval**:
1. Update `authenticated_location_claims.status` → 'approved'
2. Maak entry in `location_owners` tabel
3. Kopieer `google_business_link` en `logo_storage_path` naar `location_owners`
4. Verplaats logo van temp storage naar definitieve storage
5. Update gebruiker rol naar `location_owner` (als nog niet)
6. Update `locations` tabel met owner info (optioneel, voor snelle queries)

**Acceptatie Criteria**:
- [ ] Rol systeem bestaat
- [ ] Bij approval wordt owner rol toegekend
- [ ] Location_owners entry wordt aangemaakt
- [ ] Logo wordt verplaatst naar definitieve storage
- [ ] Google link wordt opgeslagen

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/074_user_roles.sql` (nieuwe migration, als nodig)
- `Backend/services/claim_approval_service.py` (nieuw)
- `Backend/api/routers/admin_claims.py` (nieuw, admin endpoints)

---

#### Stap 3.9: Logo en Google Business Link Opslag

**Doel**: Architectuur voor logo opslag en Google Business link definitieve opslag.

**Logo Opslag Strategie**:
- **Tijdens claim submission**: Upload naar temp storage (bijv. `claims/temp/{claim_id}/`)
- **Na approval**: Verplaats naar definitieve storage (bijv. `locations/{location_id}/logo.{ext}`)
- **Na rejection**: Verwijder temp storage (cleanup)

**Storage Opties**:
- Supabase Storage (aanbevolen)
- Of: AWS S3 / andere object storage

**Database Schema**:
- `authenticated_location_claims.logo_storage_path`: Temp path tijdens review
- `location_owners.logo_url`: Definitieve public URL na approval
- `location_owners.google_business_link`: Definitieve link na approval

**Acceptatie Criteria**:
- [ ] Logo upload naar temp storage werkt
- [ ] Logo verplaatsing naar definitieve storage werkt
- [ ] Google Business link wordt opgeslagen
- [ ] Cleanup van temp files bij rejection
- [ ] Public URLs werken correct

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/storage_service.py` (nieuw, logo opslag)
- `Backend/api/routers/authenticated_claims.py` (update, logo upload endpoint)
- `Backend/services/claim_approval_service.py` (update, logo verplaatsing)

---

#### Stap 3.10: Email Bevestigingen voor Claim Toekenning/Afwijzing

**Doel**: Email bevestigingen verzenden na claim approval/rejection.

**Prerequisite**: Transactionele email foundation (Fase 0.5) moet voltooid zijn.

**Email Templates Vereist**:
- **Claim Approved**:
  - Subject: "Uw claim is goedgekeurd - {location_name}" (NL) / "Talebiniz onaylandı - {location_name}" (TR) / "Your claim has been approved - {location_name}" (EN)
  - Body: Bevestiging, locatie is nu van jou, link naar account pagina ("Senin" sectie)
- **Claim Rejected**:
  - Subject: "Uw claim is afgewezen - {location_name}" (NL) / "Talebiniz reddedildi - {location_name}" (TR) / "Your claim has been rejected - {location_name}" (EN)
  - Body: Vriendelijke afwijzing, optioneel reden (als opgegeven)

**Implementatie**:
- Trigger email na admin approval/rejection actie
- Gebruik email service (Fase 0.5.1)
- Gebruik email templates (Fase 0.5.2)
- Verzend naar gebruiker email (uit auth.users)
- Meertaligheid support (NL/TR/EN)

**Acceptatie Criteria**:
- [ ] Email templates bestaan
- [ ] Emails worden verzonden bij approval
- [ ] Emails worden verzonden bij rejection
- [ ] Templates bevatten correcte informatie
- [ ] Meertaligheid werkt
- [ ] Error handling (email failure blokkeert niet de actie)

**Bestanden om aan te maken/wijzigen**:
- `Backend/templates/emails/claim_approved.html.j2` (nieuw)
- `Backend/templates/emails/claim_approved.txt.j2` (nieuw)
- `Backend/templates/emails/claim_rejected.html.j2` (nieuw)
- `Backend/templates/emails/claim_rejected.txt.j2` (nieuw)
- `Backend/services/claim_approval_service.py` (update, email triggers)

---

#### Stap 3.11: "Senin" Sectie op Account Pagina

**Doel**: Sectie op account pagina die geclaimde locaties toont.

**UI Vereisten**:
- Nieuwe sectie "Senin" (Turks voor "Jouw")
- Alleen zichtbaar als gebruiker `location_owner` rol heeft
- Toont lijst van geclaimde locaties:
  - Locatie naam (link naar location detail)
  - Locatie categorie
  - Claim datum
  - Status (actief)
- Plaatsing: Onder rollen scherm op account pagina

**Data Fetching**:
- API endpoint: `GET /api/v1/my-locations` (geclaimde locaties voor user)
- Query `location_owners` tabel voor user_id

**Acceptatie Criteria**:
- [ ] Sectie bestaat op account pagina
- [ ] Alleen zichtbaar voor location_owners
- [ ] Lijst toont geclaimde locaties
- [ ] Links naar location details werken
- [ ] Responsive design

**Bestanden om aan te maken/wijzigen**:
- `Frontend/src/components/account/SeninSection.tsx` (nieuw)
- `Frontend/src/pages/AccountPage.tsx` (update, integratie Senin sectie)
- `Backend/api/routers/authenticated_claims.py` (update, my-locations endpoint)

---

### FASE 4: Token-based Claim System Foundation (voor Outreach)

#### Stap 4.1: Database Schema voor Token-based location_claims

**Doel**: Database tabel aanmaken voor token-based claims (uit outreach plan Stap 2.3).

**Database Changes** (uit outreach plan):
- Nieuwe ENUM type `token_claim_status`:
  - `unclaimed` (nog niet geclaimed)
  - `claimed_free` (geclaimed, gratis periode actief)
  - `expired` (gratis periode verlopen)
  - `removed` (verwijderd door eigenaar)

- Nieuwe tabel `token_location_claims`:
  - `id` bigserial PRIMARY KEY
  - `location_id` bigint (FK naar locations, UNIQUE)
  - `claim_token` text (UNIQUE, voor token-based access)
  - `claim_status` token_claim_status DEFAULT 'unclaimed'
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
- `Infra/supabase/075_token_location_claims.sql` (nieuwe migration)

**Noot**: Dit komt uit outreach plan Stap 2.3, maar moet nu gebeuren als foundation. Naam gewijzigd naar `token_location_claims` om verwarring te voorkomen met `authenticated_location_claims`.

---

#### Stap 4.2: Token Generation en Validatie Service

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

#### Stap 4.3: Token-based Claim API Endpoints Foundation

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

#### Stap 4.4: Frontend Routing voor Token-based Claim Pagina

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

### FASE 5: Outreach Infrastructure Foundation

#### Stap 5.1: Outreach Queue Database Schema

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
- `Infra/supabase/076_outreach_contacts.sql` (nieuwe migration)
- `Infra/supabase/077_outreach_emails.sql` (nieuwe migration)

**Noot**: Dit komt uit outreach plan Fase 2, maar moet nu als foundation.

---

#### Stap 5.2: Rate Limiting Service voor Emails

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

#### Stap 5.3: Outreach Tracking en Metrics Foundation

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

#### Stap 5.4: Outreach Infrastructure Integratie Test

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
**Volgende Stap**: Fase 0.5 - Transactionele Email Foundation (Stap 0.5.1: Email service migratie)

---

## 📝 Nieuwe Visie Integratie Notities

### Authenticated Claim Flow (Nieuwe Visie)
De nieuwe visie introduceert een **authenticated claim flow** die de primaire claim methode wordt voor outreach emails:
- Gebruikers moeten inloggen om te claimen
- Admin approval vereist
- Logo en Google Business link kunnen worden geüpload
- Bij approval krijgt gebruiker `location_owner` rol
- "Senin" sectie op account pagina toont geclaimde locaties

### Email Link naar Mapview
Outreach emails bevatten een link naar de mapview met:
- Locatie gecentreerd op de kaart
- Tooltip automatisch open
- Gebruiker kan dan doorklikken naar location detail en claim knop zien

### Claim Knop in Location Detail
- Nieuwe "Claim" knop naast Google zoek knop
- Alleen zichtbaar voor ingelogde gebruikers
- Start authenticated claim flow

### Drie Claim Systemen
1. **business_location_claims**: Premium/verified claims (toekomstig)
2. **authenticated_location_claims**: Primaire outreach claim flow (nieuwe visie)
3. **token_location_claims**: Token-based fallback (outreach plan)


