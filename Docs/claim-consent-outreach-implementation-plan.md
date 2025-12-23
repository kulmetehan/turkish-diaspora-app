# Claim & Consent Outreach Bot Implementation Plan

**Status**: 🔴 Niet Gestart  
**Laatste Update**: 2025-01-XX  
**Epic**: Business Outreach & Claim System

Dit document beschrijft de incrementele implementatie van het Claim & Consent Outreach Bot systeem voor Turkspot, zoals uitgewerkt in samenwerking met ChatGPT. Het plan is opgedeeld in logische stappen die incrementeel door Cursor kunnen worden uitgevoerd.

## 📋 Overzicht

Het outreach systeem volgt deze principes:
- **AVG-compliant**: Gerechtvaardigd belang, opt-out mogelijkheid, geen spam
- **Automatisch & schaalbaar**: Volledig geautomatiseerde outreach zonder handmatig werk
- **Vertrouwen & validatie**: Focus op service-notificatie, geen agressieve sales
- **Token-based claims**: Geen login vereist voor claim/consent acties
- **Gratis onboarding**: Gratis claim-periode als basis voor latere monetization

---

## 🎯 Implementatie Status Tracking

### Fase 1: Voorbereiding & Randvoorwaarden
- [ ] **Stap 1.1**: Functionele scope vastleggen (bewust beperkt)
- [ ] **Stap 1.2**: Juridisch kader vastzetten (AVG documentatie)

### Fase 2: Datamodel & State Machine
- [ ] **Stap 2.1**: Database schema voor outreach contacts
- [ ] **Stap 2.2**: Database schema voor outreach emails
- [ ] **Stap 2.3**: Database schema voor location claims
- [ ] **Stap 2.4**: Location state uitbreiden (is_claimable, claimed_status)

### Fase 3: Contact Discovery Bot
- [ ] **Stap 3.1**: Contact discovery service (OSM, website, Google, social)
- [ ] **Stap 3.2**: Confidence scoring logica
- [ ] **Stap 3.3**: Contact discovery worker/bot
- [ ] **Stap 3.4**: Integratie met bestaande location pipeline

### Fase 4: Outreach Queue & Rate Limiting
- [ ] **Stap 4.1**: Outreach selectiecriteria logica
- [ ] **Stap 4.2**: Rate limiting service
- [ ] **Stap 4.3**: Queue management systeem

### Fase 5: Amazon SES Setup
- [ ] **Stap 5.1**: SES domain verification (SPF, DKIM, DMARC)
- [ ] **Stap 5.2**: SES production access request
- [ ] **Stap 5.3**: Email service abstraction layer

### Fase 6: Outreach Mailer Bot
- [ ] **Stap 6.1**: Email template systeem
- [ ] **Stap 6.2**: SES mailer service
- [ ] **Stap 6.3**: Email status tracking & error handling
- [ ] **Stap 6.4**: Outreach mailer worker/bot

### Fase 7: Claim & Consent Pagina
- [ ] **Stap 7.1**: Token-based claim page (frontend)
- [ ] **Stap 7.2**: Claim API endpoints (backend)
- [ ] **Stap 7.3**: Claim flow UI (claim, correctie, verwijderen)
- [ ] **Stap 7.4**: Email bevestigingen voor acties

### Fase 8: Expiry & Reminder Bot
- [ ] **Stap 8.1**: Expiry reminder service
- [ ] **Stap 8.2**: Expiry reminder worker/bot
- [ ] **Stap 8.3**: Expiry state management

### Fase 9: Logging & Metrics
- [ ] **Stap 9.1**: Metrics tracking systeem
- [ ] **Stap 9.2**: Dashboard/endpoints voor metrics
- [ ] **Stap 9.3**: Audit logging voor AVG compliance

### Fase 10: Future-proofing
- [ ] **Stap 10.1**: Mail abstraction layer (SES/Brevo)
- [ ] **Stap 10.2**: Consent flags systeem
- [ ] **Stap 10.3**: Migratiepad documentatie

---

## 📐 Gedetailleerde Stappen

### FASE 1: Voorbereiding & Randvoorwaarden

#### Stap 1.1: Functionele Scope Vastleggen

**Doel**: Duidelijke scope vastleggen voor het outreach systeem (bewust beperkt).

**Scope - Wel**:
- 1 informatieve mail per locatie
- Token-based actiepagina (geen login vereist)
- Claim / remove / correctie acties
- Gratis claim-periode met expiratie
- Expiratie & reminder systeem

**Scope - Niet (bewust)**:
- Marketing campagnes
- Bulk follow-ups
- A/B testing
- Dashboards voor ondernemers
- Betaalde flows (in deze fase)

**Focus**: Vertrouwen & validatie

**Acceptatie Criteria**:
- [ ] Scope documentatie bestaat
- [ ] Scope is goedgekeurd/gedocumenteerd
- [ ] Duidelijke grenzen tussen wel/niet features

**Bestanden om aan te maken/wijzigen**:
- `Docs/claim-outreach-scope.md` (nieuw, documentatie)

---

#### Stap 1.2: Juridisch Kader Vastzetten (AVG)

**Doel**: Intern juridisch kader documenteren voor AVG compliance.

**Documentatie Vereist**:
- **Rechtsgrond**: Gerechtvaardigd belang
- **Databron**: Publiek gepubliceerde contactgegevens
- **Communicatietype**: Service-notificatie
- **Rechten**:
  - Opt-out mogelijkheid
  - Verwijdering mogelijkheid
  - Correctie mogelijkheid
  - Nooit opnieuw mailen na opt-out

**Acceptatie Criteria**:
- [ ] Juridisch kader gedocumenteerd
- [ ] Mailcopy volgt AVG richtlijnen
- [ ] Opt-out mechanisme is duidelijk
- [ ] Logging voor AVG compliance is gepland

**Bestanden om aan te maken/wijzigen**:
- `Docs/claim-outreach-legal-framework.md` (nieuw, documentatie)
- Update mail templates (later in Fase 6) met AVG-compliant teksten

---

### FASE 2: Datamodel & State Machine

#### Stap 2.1: Database Schema voor Outreach Contacts

**Doel**: Database tabel aanmaken voor discovered contact informatie.

**Database Changes**:
- Nieuwe tabel `outreach_contacts`:
  - `id` bigserial PRIMARY KEY
  - `location_id` UUID (FK naar locations)
  - `email` text (NOT NULL)
  - `source` text (website / google / osm / social)
  - `confidence_score` integer (0-100)
  - `discovered_at` timestamptz
  - `created_at` timestamptz DEFAULT NOW()
  - UNIQUE constraint op (location_id, email)

**Acceptatie Criteria**:
- [ ] Tabel bestaat in database
- [ ] Indexen op location_id en email
- [ ] UNIQUE constraint voorkomt duplicaten
- [ ] Migration script in `Infra/supabase/`

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/073_outreach_contacts.sql` (nieuwe migration)

---

#### Stap 2.2: Database Schema voor Outreach Emails

**Doel**: Database tabel voor email tracking en status.

**Database Changes**:
- Nieuwe ENUM type `outreach_email_status`:
  - `queued` (in wachtrij)
  - `sent` (verzonden)
  - `delivered` (afgeleverd)
  - `bounced` (teruggekaatst)
  - `clicked` (link geklikt)
  - `opted_out` (afgemeld)

- Nieuwe tabel `outreach_emails`:
  - `id` bigserial PRIMARY KEY
  - `location_id` UUID (FK naar locations)
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

**Acceptatie Criteria**:
- [ ] ENUM type bestaat
- [ ] Tabel bestaat met correcte constraints
- [ ] Indexen op location_id, contact_id, status, email
- [ ] Migration script

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/074_outreach_emails.sql` (nieuwe migration)

---

#### Stap 2.3: Database Schema voor Location Claims

**Doel**: Database tabel voor claim status en gratis periode tracking.

**Database Changes**:
- Nieuwe ENUM type `claim_status`:
  - `unclaimed` (nog niet geclaimed)
  - `claimed_free` (geclaimed, gratis periode actief)
  - `expired` (gratis periode verlopen)
  - `removed` (verwijderd door eigenaar)

- Nieuwe tabel `location_claims`:
  - `id` bigserial PRIMARY KEY
  - `location_id` UUID (FK naar locations, UNIQUE)
  - `claim_token` text (UNIQUE, voor token-based access)
  - `claim_status` claim_status DEFAULT 'unclaimed'
  - `claimed_by_email` text
  - `claimed_at` timestamptz
  - `free_until` timestamptz (einde gratis periode)
  - `removed_at` timestamptz
  - `removal_reason` text
  - `created_at` timestamptz DEFAULT NOW()
  - `updated_at` timestamptz DEFAULT NOW()

**Acceptatie Criteria**:
- [ ] ENUM type bestaat
- [ ] Tabel bestaat met UNIQUE constraint op location_id
- [ ] Index op claim_token voor snelle lookups
- [ ] Index op claim_status
- [ ] Migration script

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/075_location_claims.sql` (nieuwe migration)

---

#### Stap 2.4: Location State Uitbreiden

**Doel**: Bestaande locations tabel uitbreiden met claim-gerelateerde flags.

**Database Changes**:
- Update `locations` tabel met nieuwe kolommen:
  - `is_claimable` boolean DEFAULT true
  - `claimed_status` text (sync met location_claims.claim_status)
  - `removed_by_owner` boolean DEFAULT false

**Noot**: Geen harde deletes, alleen state updates.

**Acceptatie Criteria**:
- [ ] Kolommen toegevoegd aan locations tabel
- [ ] Default waarden zijn correct
- [ ] Index op is_claimable en claimed_status
- [ ] Migration script

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/076_location_claim_flags.sql` (nieuwe migration)
- Update bestaande location queries indien nodig

---

### FASE 3: Contact Discovery Bot

#### Stap 3.1: Contact Discovery Service

**Doel**: Service die contactgegevens ontdekt voor locaties.

**Strategie (in volgorde)**:
1. OSM tags (email, contact:email)
2. Officiële website (scraping van contact pagina)
3. Google Business profile (via Google Places API)
4. Social bio (Facebook / Instagram, indien beschikbaar)

**Regels**:
- Alleen zichtbare e-mails (geen scraping achter logins)
- Geen guessing (geen email@domain.com patterns)
- Confidence score berekenen op basis van bron
- Confidence < drempel (bijv. 50) → skip

**Acceptatie Criteria**:
- [ ] Service functie `discover_contact(location_id)` bestaat
- [ ] Alle 4 strategieën geïmplementeerd
- [ ] Confidence scoring werkt
- [ ] Error handling voor failed requests
- [ ] Logging voor debugging

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/contact_discovery_service.py` (nieuw)
- `Backend/services/osm_service.py` (update, indien nodig)
- `Backend/services/google_places_service.py` (update, indien nodig)

---

#### Stap 3.2: Confidence Scoring Logica

**Doel**: Confidence score berekenen op basis van bron en kwaliteit.

**Scoring Regels**:
- OSM email tag: 90
- OSM contact:email tag: 85
- Website contact pagina: 70
- Google Business profile: 80
- Social bio: 60
- Penalties:
  - Generic email (info@, contact@): -10
  - Onvolledige email: -20

**Acceptatie Criteria**:
- [ ] Scoring functie bestaat
- [ ] Scores zijn consistent
- [ ] Drempelwaarde is configureerbaar (env var)
- [ ] Tests voor verschillende scenario's

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/contact_discovery_service.py` (update, scoring logica)

---

#### Stap 3.3: Contact Discovery Worker/Bot

**Doel**: Worker die automatisch contacts ontdekt voor nieuwe/verified locaties.

**Logica**:
- Selecteer locaties waar:
  - status = VERIFIED
  - is_claimable = true
  - claimed_status = unclaimed
  - Geen entry in outreach_contacts
- Run discovery service
- Sla contact op in outreach_contacts (alleen als confidence >= drempel)
- Log resultaten

**Acceptatie Criteria**:
- [ ] Worker script bestaat
- [ ] Selectie logica werkt correct
- [ ] Geen duplicaten (UNIQUE constraint)
- [ ] Rate limiting voor externe API calls
- [ ] Logging en error handling

**Bestanden om aan te maken/wijzigen**:
- `Backend/app/workers/contact_discovery_bot.py` (nieuw)
- `Backend/scripts/run_contact_discovery.py` (nieuw, CLI script)

---

#### Stap 3.4: Integratie met Bestaande Location Pipeline

**Doel**: Zorg dat contact discovery automatisch triggert bij nieuwe verified locaties.

**Integratie Opties**:
- Option 1: Trigger na OSM discovery (als locatie verified wordt)
- Option 2: Scheduled job (dagelijks, voor nieuwe verified locaties)
- Option 3: Beide (trigger + scheduled backup)

**Acceptatie Criteria**:
- [ ] Integratie werkt met bestaande pipeline
- [ ] Geen breaking changes in bestaande flow
- [ ] Duplicaten worden voorkomen
- [ ] Performance impact is acceptabel

**Bestanden om aan te maken/wijzigen**:
- `Backend/app/workers/discovery_bot.py` (update, trigger contact discovery)
- Of: `Backend/app/workers/scheduled_tasks.py` (nieuw, scheduled jobs)

---

### FASE 4: Outreach Queue & Rate Limiting

#### Stap 4.1: Outreach Selectiecriteria Logica

**Doel**: Service die bepaalt welke locaties in aanmerking komen voor outreach.

**Selectiecriteria**:
- Locatie status = VERIFIED
- is_claimable = true
- claimed_status = unclaimed
- removed_by_owner = false
- Contact gevonden (entry in outreach_contacts)
- Nog nooit gemaild (geen entry in outreach_emails voor deze location_id)

**Acceptatie Criteria**:
- [ ] Selectie functie bestaat
- [ ] Alle criteria worden gecontroleerd
- [ ] Performance is acceptabel (indexen)
- [ ] Tests voor edge cases

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/outreach_queue_service.py` (nieuw)

---

#### Stap 4.2: Rate Limiting Service

**Doel**: Service die rate limiting beheert voor email verzending.

**Rate Limiting Regels**:
- Start: 50 mails / dag
- Opschalen naar 100 → 250 → 500 (configureerbaar)
- Max 1 mail per locatie, ooit (geen herhalingen)
- Respecteer SES throttling limits

**Implementatie**:
- Track dagelijkse email count
- Check tegen limiet voordat email wordt verzonden
- Backoff bij SES throttling errors

**Acceptatie Criteria**:
- [ ] Rate limiting service bestaat
- [ ] Dagelijkse limiet wordt gerespecteerd
- [ ] Configuratie via env vars
- [ ] Logging voor monitoring

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/rate_limiting_service.py` (nieuw)
- Update `.env.example` met rate limiting config

---

#### Stap 4.3: Queue Management Systeem

**Doel**: Systeem dat outreach queue beheert en emails klaarzet voor verzending.

**Functionaliteit**:
- Selecteer locaties die in aanmerking komen (via Stap 4.1)
- Check rate limiting (via Stap 4.2)
- Maak outreach_emails entries met status 'queued'
- Prioriteer op basis van:
  - Oudste verified locaties eerst
  - Of: random voor spreiding

**Acceptatie Criteria**:
- [ ] Queue management service bestaat
- [ ] Integratie met selectie en rate limiting
- [ ] Queue entries worden correct aangemaakt
- [ ] Prioritering werkt

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/outreach_queue_service.py` (update, queue management)

---

### FASE 5: Amazon SES Setup

#### Stap 5.1: SES Domain Verification (SPF, DKIM, DMARC)

**Doel**: SES domain verification en email authentication setup.

**Configuratie Vereist**:
- Domain verification in AWS SES console
- SPF record in DNS
- DKIM records in DNS
- DMARC record (p=none → later tighten)

**Acceptatie Criteria**:
- [ ] Domain is geverifieerd in SES
- [ ] SPF record is correct
- [ ] DKIM records zijn correct
- [ ] DMARC record is geconfigureerd
- [ ] Email authentication testen (bijv. via mail-tester.com)

**Bestanden om aan te maken/wijzigen**:
- `Docs/ses-setup-guide.md` (nieuw, documentatie)
- DNS configuratie (extern, documenteren)

---

#### Stap 5.2: SES Production Access Request

**Doel**: Request production access in AWS SES (uit sandbox mode).

**Proces**:
- Use case uitleggen: Service notifications voor locatie-eigenaren
- Verwachte volume: Start 50/dag, groei naar 500/dag
- Opt-out mechanisme beschrijven
- Compliance (AVG) vermelden

**Acceptatie Criteria**:
- [ ] Production access is aangevraagd
- [ ] Access is goedgekeurd
- [ ] Sandbox restrictions zijn opgeheven

**Bestanden om aan te maken/wijzigen**:
- `Docs/ses-production-request.md` (nieuw, documentatie van request)

---

#### Stap 5.3: Email Service Abstraction Layer

**Doel**: Abstracte email service die SES gebruikt, maar later uitbreidbaar is naar Brevo.

**Interface**:
```python
async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    reply_to: str = None
) -> str:  # Returns message_id
```

**Implementatie**:
- SES client setup (boto3)
- Error handling (bounces, throttling)
- Response tracking (message_id)

**Acceptatie Criteria**:
- [ ] Email service bestaat met abstracte interface
- [ ] SES integratie werkt
- [ ] Error handling is robuust
- [ ] Message ID wordt geretourneerd
- [ ] Configuratie via env vars (AWS credentials)

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/email_service.py` (nieuw)
- Update `.env.example` met AWS SES config

---

### FASE 6: Outreach Mailer Bot

#### Stap 6.1: Email Template Systeem

**Doel**: Template systeem voor outreach emails.

**Templates Vereist**:
- **Outreach email** (eerste contact):
  - Subject: "Uw locatie staat op Turkspot"
  - Body: Informatief, vriendelijk, AVG-compliant
  - Token link naar claim pagina
  - Opt-out link

- **Claim bevestiging** (na claim actie)
- **Removal bevestiging** (na verwijdering)
- **Correction bevestiging** (na correctie)

**Template Features**:
- Plain text + HTML versies
- Token variabelen (location_name, claim_token, etc.)
- Geen tracking pixels (privacy-first)

**Acceptatie Criteria**:
- [ ] Template systeem bestaat
- [ ] Alle templates zijn geïmplementeerd
- [ ] AVG-compliant teksten
- [ ] Token variabelen werken
- [ ] Plain text + HTML versies

**Bestanden om aan te maken/wijzigen**:
- `Backend/templates/emails/outreach_email.j2` (nieuw)
- `Backend/templates/emails/claim_confirmation.j2` (nieuw)
- `Backend/templates/emails/removal_confirmation.j2` (nieuw)
- `Backend/templates/emails/correction_confirmation.j2` (nieuw)
- `Backend/services/email_template_service.py` (nieuw)

---

#### Stap 6.2: SES Mailer Service

**Doel**: Service die emails verzendt via SES en status bijwerkt.

**Functionaliteit**:
- Haal queued emails op
- Render templates met context
- Verzend via email_service (Stap 5.3)
- Update outreach_emails status naar 'sent'
- Sla SES message_id op
- Log errors

**Acceptatie Criteria**:
- [ ] Mailer service bestaat
- [ ] Integratie met email_service
- [ ] Template rendering werkt
- [ ] Status updates zijn correct
- [ ] Error handling en logging

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/outreach_mailer_service.py` (nieuw)

---

#### Stap 6.3: Email Status Tracking & Error Handling

**Doel**: Systeem dat email status bijwerkt op basis van SES events.

**Status Updates**:
- SES bounce event → status = 'bounced', bounce_reason
- SES delivery event → status = 'delivered'
- Click tracking (via token link) → status = 'clicked', clicked_at
- Opt-out → status = 'opted_out'

**Error Handling**:
- Bounce → markeer contact als invalid, stop outreach voor deze locatie
- Soft fail → retry max 2x
- SES throttling → backoff, retry later

**Acceptatie Criteria**:
- [ ] Status tracking werkt
- [ ] SES webhooks/events worden verwerkt (of polling)
- [ ] Bounce handling voorkomt verdere outreach
- [ ] Retry logica werkt
- [ ] Logging voor alle status changes

**Bestanden om aan te maken/wijzigen**:
- `Backend/api/routers/ses_webhooks.py` (nieuw, voor SES event webhooks)
- Of: `Backend/services/ses_event_poller.py` (nieuw, als polling)
- `Backend/services/outreach_mailer_service.py` (update, error handling)

---

#### Stap 6.4: Outreach Mailer Worker/Bot

**Doel**: Worker die automatisch emails verzendt uit de queue.

**Logica**:
- Haal queued emails op (via queue service)
- Check rate limiting
- Verzend emails (via mailer service)
- Update status
- Log resultaten

**Acceptatie Criteria**:
- [ ] Worker script bestaat
- [ ] Integratie met alle services
- [ ] Rate limiting wordt gerespecteerd
- [ ] Error handling voorkomt crashes
- [ ] Logging voor monitoring

**Bestanden om aan te maken/wijzigen**:
- `Backend/app/workers/outreach_mailer_bot.py` (nieuw)
- `Backend/scripts/run_outreach_mailer.py` (nieuw, CLI script)

---

### FASE 7: Claim & Consent Pagina

#### Stap 7.1: Token-based Claim Page (Frontend)

**Doel**: Frontend pagina waar ondernemers kunnen claimen/corrigeren/verwijderen via token.

**UI Vereisten**:
- Toegang via unieke token in URL: `/claim/{token}`
- Geen login vereist
- 4 acties:
  1. "Claim mijn locatie"
  2. "Correctie doorgeven"
  3. "Verwijderen uit app"
  4. "Niets doen" (sluit pagina)

**Design**:
- Vriendelijk, duidelijk, vertrouwenwekkend
- Duidelijke uitleg van elke actie
- Bevestiging per actie

**Acceptatie Criteria**:
- [ ] Claim pagina bestaat
- [ ] Token validatie werkt
- [ ] Alle 4 acties zijn beschikbaar
- [ ] Design volgt design system
- [ ] Responsive design

**Bestanden om aan te maken/wijzigen**:
- `Frontend/src/pages/ClaimPage.tsx` (nieuw)
- `Frontend/src/components/claim/ClaimActions.tsx` (nieuw)
- `Frontend/src/components/claim/CorrectionForm.tsx` (nieuw)
- Update routing in `Frontend/src/main.tsx`

---

#### Stap 7.2: Claim API Endpoints (Backend)

**Doel**: Backend endpoints voor claim acties.

**Endpoints**:
- `GET /api/v1/claims/{token}` - Haal claim info op (location details)
- `POST /api/v1/claims/{token}/claim` - Claim locatie
- `POST /api/v1/claims/{token}/remove` - Verwijder locatie
- `POST /api/v1/claims/{token}/correct` - Stuur correctie door

**Request/Response**:
- Claim: email, logo (optioneel), description (optioneel)
- Remove: reason (optioneel)
- Correct: correction_details (text)

**Acceptatie Criteria**:
- [ ] Alle endpoints bestaan
- [ ] Token validatie werkt
- [ ] State updates zijn correct
- [ ] Email bevestigingen worden getriggerd
- [ ] Error handling

**Bestanden om aan te maken/wijzigen**:
- `Backend/api/routers/claims.py` (nieuw)
- Update `Backend/app/main.py` om router te includen

---

#### Stap 7.3: Claim Flow UI

**Doel**: Complete UI flow voor claim acties.

**Claim Flow**:
1. Gebruiker klikt "Claim mijn locatie"
2. Formulier: email, logo upload (optioneel), beschrijving (optioneel)
3. Submit → backend claim endpoint
4. Success: "Uw locatie is geclaimed. Gratis tot {free_until}"
5. Email bevestiging wordt verzonden

**Remove Flow**:
1. Gebruiker klikt "Verwijderen uit app"
2. Bevestiging: "Weet u het zeker?"
3. Optioneel: reden opgeven
4. Submit → backend remove endpoint
5. Success: "Uw locatie wordt verwijderd"
6. Email bevestiging wordt verzonden

**Correction Flow**:
1. Gebruiker klikt "Correctie doorgeven"
2. Formulier: correction details
3. Submit → backend correct endpoint
4. Success: "Bedankt, we verwerken uw correctie"
5. Email bevestiging wordt verzonden

**Acceptatie Criteria**:
- [ ] Alle flows werken
- [ ] Formulieren zijn gebruiksvriendelijk
- [ ] Bevestigingen zijn duidelijk
- [ ] Error states worden getoond
- [ ] Loading states

**Bestanden om aan te maken/wijzigen**:
- `Frontend/src/components/claim/ClaimForm.tsx` (nieuw)
- `Frontend/src/components/claim/RemoveConfirmation.tsx` (nieuw)
- `Frontend/src/components/claim/CorrectionForm.tsx` (update, volledige flow)
- `Frontend/src/pages/ClaimPage.tsx` (update, integratie flows)

---

#### Stap 7.4: Email Bevestigingen voor Acties

**Doel**: Email bevestigingen verzenden na elke claim actie.

**Bevestigingen**:
- **Claim**: "Uw locatie is geclaimed. Gratis tot {free_until}"
- **Remove**: "Uw locatie wordt verwijderd. Bedankt voor uw feedback."
- **Correction**: "Bedankt voor uw correctie. We verwerken dit zo snel mogelijk."

**Implementatie**:
- Trigger email na succesvolle backend actie
- Gebruik email templates (Stap 6.1)
- Verzend via email_service

**Acceptatie Criteria**:
- [ ] Bevestigingen worden verzonden
- [ ] Templates zijn correct
- [ ] Email bevat relevante informatie
- [ ] Error handling (email failure blokkeert niet de actie)

**Bestanden om aan te maken/wijzigen**:
- `Backend/api/routers/claims.py` (update, email triggers)
- `Backend/services/outreach_mailer_service.py` (update, bevestiging emails)

---

### FASE 8: Expiry & Reminder Bot

#### Stap 8.1: Expiry Reminder Service

**Doel**: Service die reminder emails verzendt voor expirerende claims.

**Logica**:
- Selecteer claims waar:
  - claim_status = 'claimed_free'
  - free_until <= NOW() + 7 days (7 dagen voor expiry)
  - Nog geen reminder verzonden (of reminder_sent_at is NULL)
- Verzend vriendelijke reminder email
- Markeer reminder als verzonden

**Reminder Email**:
- Subject: "Uw gratis periode loopt bijna af"
- Body: Vriendelijk, informatief, geen druk
- Link naar verleng optie (toekomstig, voor nu alleen info)

**Acceptatie Criteria**:
- [ ] Reminder service bestaat
- [ ] Selectie logica werkt
- [ ] Email wordt verzonden
- [ ] Duplicaten worden voorkomen
- [ ] Configuratie voor reminder timing (7 dagen)

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/expiry_reminder_service.py` (nieuw)
- Update `location_claims` tabel met `reminder_sent_at` kolom (migration)

---

#### Stap 8.2: Expiry Reminder Worker/Bot

**Doel**: Worker die dagelijks expiry reminders verzendt.

**Logica**:
- Run reminder service
- Verzend reminders
- Log resultaten

**Acceptatie Criteria**:
- [ ] Worker script bestaat
- [ ] Dagelijkse run werkt
- [ ] Integratie met reminder service
- [ ] Error handling en logging

**Bestanden om aan te maken/wijzigen**:
- `Backend/app/workers/expiry_reminder_bot.py` (nieuw)
- `Backend/scripts/run_expiry_reminder.py` (nieuw, CLI script)

---

#### Stap 8.3: Expiry State Management

**Doel**: Systeem dat claim status bijwerkt naar 'expired' na free_until datum.

**Logica**:
- Selecteer claims waar:
  - claim_status = 'claimed_free'
  - free_until < NOW()
- Update claim_status naar 'expired'
- Update locations.claimed_status
- Premium features uitschakelen (toekomstig)
- Basisvermelding blijft actief

**Acceptatie Criteria**:
- [ ] Expiry service bestaat
- [ ] State updates zijn correct
- [ ] Geen data loss
- [ ] Logging voor monitoring

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/expiry_service.py` (nieuw)
- `Backend/app/workers/expiry_bot.py` (nieuw, scheduled worker)

---

### FASE 9: Logging & Metrics

#### Stap 9.1: Metrics Tracking Systeem

**Doel**: Systeem dat metrics verzamelt voor monitoring en validatie.

**Metrics Vereist**:
- `mails_sent` (totaal aantal verzonden emails)
- `bounce_rate` (percentage bounces)
- `claim_rate` (percentage claims na email)
- `removal_rate` (percentage removals)
- `no_action_rate` (percentage geen actie)
- `click_rate` (percentage clicks op token link)

**Implementatie**:
- Bereken metrics op basis van outreach_emails en location_claims data
- Optioneel: Materialized view voor performance
- Of: Real-time berekening via service

**Acceptatie Criteria**:
- [ ] Metrics service bestaat
- [ ] Alle metrics worden berekend
- [ ] Performance is acceptabel
- [ ] Metrics zijn accuraat

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/outreach_metrics_service.py` (nieuw)

---

#### Stap 9.2: Dashboard/Endpoints voor Metrics

**Doel**: API endpoints of dashboard voor metrics weergave.

**Endpoints**:
- `GET /api/v1/outreach/metrics` - Haal alle metrics op
- Optioneel: Admin dashboard in frontend

**Response Format**:
```json
{
  "mails_sent": 150,
  "bounce_rate": 2.5,
  "claim_rate": 15.0,
  "removal_rate": 3.0,
  "no_action_rate": 82.0,
  "click_rate": 25.0
}
```

**Acceptatie Criteria**:
- [ ] Endpoints bestaan
- [ ] Metrics zijn accuraat
- [ ] Authenticatie voor admin endpoints
- [ ] Response format is duidelijk

**Bestanden om aan te maken/wijzigen**:
- `Backend/api/routers/outreach_metrics.py` (nieuw)
- Update `Backend/app/main.py` om router te includen
- Optioneel: `Frontend/src/pages/AdminOutreachMetricsPage.tsx` (nieuw)

---

#### Stap 9.3: Audit Logging voor AVG Compliance

**Doel**: Audit logging voor alle outreach en claim acties (AVG compliance).

**Logging Vereist**:
- Alle email verzendingen (timestamp, recipient, status)
- Alle claim acties (timestamp, action, user_email)
- Alle opt-outs (timestamp, email, reason)
- Alle removals (timestamp, location_id, reason)

**Implementatie**:
- Nieuwe tabel `outreach_audit_log`:
  - `id` bigserial
  - `action_type` text (email_sent, claim, remove, opt_out, etc.)
  - `location_id` UUID
  - `email` text
  - `details` jsonb
  - `created_at` timestamptz

**Acceptatie Criteria**:
- [ ] Audit log tabel bestaat
- [ ] Alle acties worden gelogd
- [ ] Logs zijn onveranderbaar (append-only)
- [ ] Retention policy (bijv. 2 jaar)

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/077_outreach_audit_log.sql` (nieuwe migration)
- `Backend/services/audit_service.py` (update, outreach logging)

---

### FASE 10: Future-proofing

#### Stap 10.1: Mail Abstraction Layer (SES/Brevo)

**Doel**: Abstracte mail service die later uitbreidbaar is naar Brevo voor marketing.

**Architectuur**:
- Abstracte interface: `EmailProvider`
- Implementaties: `SESEmailProvider`, `BrevoEmailProvider`
- Factory pattern voor provider selectie
- Configuratie via env vars

**Use Cases**:
- Service mails (outreach, confirmations) → SES
- Marketing mails (toekomstig) → Brevo

**Acceptatie Criteria**:
- [ ] Abstracte interface bestaat
- [ ] SES provider werkt
- [ ] Brevo provider skeleton (toekomstig)
- [ ] Provider switching via config
- [ ] Geen breaking changes

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/email/__init__.py` (nieuw, package)
- `Backend/services/email/base.py` (nieuw, abstract interface)
- `Backend/services/email/ses_provider.py` (nieuw, SES implementatie)
- `Backend/services/email/brevo_provider.py` (nieuw, skeleton)
- `Backend/services/email_service.py` (refactor, gebruik providers)

---

#### Stap 10.2: Consent Flags Systeem

**Doel**: Systeem voor consent tracking (service vs marketing).

**Database Changes**:
- Update `outreach_contacts` of nieuwe tabel `user_consents`:
  - `email` text (UNIQUE)
  - `service_consent` boolean DEFAULT true (implicit voor outreach)
  - `marketing_consent` boolean DEFAULT false
  - `opted_out_at` timestamptz
  - `opt_out_reason` text

**Logica**:
- Service consent = implicit (voor outreach)
- Marketing consent = explicit opt-in (toekomstig)
- Opt-out = beide consents false

**Acceptatie Criteria**:
- [ ] Consent systeem bestaat
- [ ] Flags worden correct bijgewerkt
- [ ] Opt-out voorkomt verdere emails
- [ ] Migratie van bestaande data

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/078_user_consents.sql` (nieuwe migration)
- `Backend/services/consent_service.py` (nieuw)

---

#### Stap 10.3: Migratiepad Documentatie

**Doel**: Documentatie voor toekomstige uitbreidingen (marketing, premium features).

**Documentatie Vereist**:
- Migratiepad naar Brevo voor marketing
- Premium features integratie (na expiry)
- Monetization flows (toekomstig)
- Scaling considerations

**Acceptatie Criteria**:
- [ ] Documentatie bestaat
- [ ] Migratiepad is duidelijk
- [ ] Architectuur is toekomstbestendig

**Bestanden om aan te maken/wijzigen**:
- `Docs/claim-outreach-future-extensions.md` (nieuw, documentatie)

---

## 🔄 Workflow voor Incrementele Implementatie

### Voor elke stap:

1. **Lees deze documentatie** voor de specifieke stap
2. **Verken bestaande code** om te begrijpen wat al bestaat
3. **Implementeer stap** volgens acceptatie criteria
4. **Test lokaal** dat alles werkt
5. **Update status** in dit document (vink checkbox aan)
6. **Commit changes** met duidelijke commit message

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

### Voor Frontend componenten:

1. Volg design system (`Docs/design-system.md`)
2. Gebruik bestaande UI components (`Frontend/src/components/ui/`)
3. Implementeer TypeScript types
4. Test responsive design
5. Test in verschillende browsers

### Voor Workers/Bots:

1. Volg bestaande worker patterns (`Backend/app/workers/`)
2. Implementeer error handling en retry logica
3. Voeg logging toe voor monitoring
4. Test met kleine datasets eerst
5. Documenteer rate limiting en scheduling

---

## 📝 Notities & Overwegingen

### Juridische Overwegingen

- **AVG Compliance**: Alle outreach moet voldoen aan AVG richtlijnen
- **Opt-out**: Altijd mogelijk, nooit opnieuw mailen na opt-out
- **Rechtsgrond**: Gerechtvaardigd belang (service-notificatie)
- **Audit Logging**: Vereist voor compliance (2 jaar retention)

### Technische Overwegingen

- **SES Reputatie**: Rate limiting en bounce handling zijn cruciaal
- **Email Deliverability**: SPF, DKIM, DMARC correct configureren
- **Performance**: Indexen op alle foreign keys en status kolommen
- **Scalability**: Queue systeem moet schalen naar 500+ emails/dag

### Business Overwegingen

- **Gratis Periode**: Basis voor latere monetization
- **Claim Rate**: Validatie van product-market fit
- **Removal Rate**: Feedback op product kwaliteit
- **No Action Rate**: Mogelijk verbetering nodig in messaging

### Testing Strategy

- Unit tests voor services
- Integration tests voor API endpoints
- E2E tests voor claim flow
- Load tests voor email verzending (voorzichtig, respecteer SES limits)

---

## 🚀 Quick Start voor Cursor

**Om te beginnen met een stap:**

1. Open dit document
2. Kies een stap die nog niet is voltooid (unchecked checkbox)
3. Lees de stap beschrijving en acceptatie criteria
4. Verken relevante bestaande code
5. Implementeer volgens specificatie
6. Update checkbox wanneer klaar

**Voorbeeld prompt voor Cursor:**

```
Ik wil Stap 2.1 implementeren: Database Schema voor Outreach Contacts.
Lees eerst de specificatie in Docs/claim-consent-outreach-implementation-plan.md
en bekijk de bestaande database migrations in Infra/supabase/.
Maak dan de nieuwe migration volgens de specificatie.
```

---

## 📚 Referenties

- AWS SES Documentation: https://docs.aws.amazon.com/ses/
- AVG/GDPR Guidelines: https://autoriteitpersoonsgegevens.nl/
- Design System: `Docs/design-system.md`
- Database Migrations: `Infra/supabase/`
- API Patterns: `Backend/api/routers/`
- Frontend Components: `Frontend/src/components/`
- Worker Patterns: `Backend/app/workers/`

---

**Laatste Update**: 2025-01-XX  
**Huidige Status**: 🔴 Niet Gestart  
**Volgende Stap**: Fase 1 - Voorbereiding & Randvoorwaarden (Stap 1.1: Functionele scope vastleggen)


