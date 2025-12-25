# Claim & Consent Outreach Bot Implementation Plan

**Status**: 🟡 In Uitvoering  
**Laatste Update**: 2025-01-16 (Stap 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 3.3, 3.4, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.3, 8.1, 8.2, 8.3 voltooid)  
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
- [x] **Stap 1.1**: Functionele scope vastleggen (bewust beperkt) ✅
- [x] **Stap 1.2**: Juridisch kader vastzetten (AVG documentatie) ✅

### Fase 2: Datamodel & State Machine
- [x] **Stap 2.1**: Database schema voor outreach contacts ✅
- [x] **Stap 2.2**: Database schema voor outreach emails ✅
- [x] **Stap 2.3**: Database schema voor location claims ✅
- [x] **Stap 2.4**: Location state uitbreiden (is_claimable, claimed_status) ✅

### Fase 3: Contact Discovery Bot
- [x] **Stap 3.1**: Contact discovery service (OSM, website, Google, social) ✅ (voltooid in pre-claim plan)
- [x] **Stap 3.2**: Confidence scoring logica ✅ (voltooid in pre-claim plan)
- [x] **Stap 3.3**: Contact discovery worker/bot ✅
- [x] **Stap 3.4**: Integratie met bestaande location pipeline ✅

### Fase 4: Outreach Queue & Rate Limiting
- [x] **Stap 4.1**: Outreach selectiecriteria logica
- [x] **Stap 4.2**: Rate limiting service ✅
- [x] **Stap 4.3**: Queue management systeem

### Fase 5: Amazon SES Setup (voor Outreach)
- [x] **Stap 5.1**: SES domain verification (SPF, DKIM, DMARC) ✅
- [x] **Stap 5.2**: SES production access request ✅
- [x] **Stap 5.3**: SES provider implementatie (email service abstraction bestaat al uit pre-claim plan Fase 0.5.1) ✅

### Fase 6: Outreach Mailer Bot
- [x] **Stap 6.1**: Email template systeem
- [x] **Stap 6.2**: Mapview link generatie (locatie gecentreerd, tooltip open)
- [x] **Stap 6.3**: SES mailer service
- [x] **Stap 6.4**: Email status tracking & error handling
- [x] **Stap 6.5**: Outreach mailer worker/bot

### Fase 7: Claim Flow Integratie
- [x] **Stap 7.1**: Authenticated claim flow integratie (gebruik bestaande flow uit pre-claim plan) ✅
- [ ] **Stap 7.2**: Token-based claim fallback (optioneel, voor niet-ingelogde gebruikers)
- [x] **Stap 7.3**: Email bevestigingen voor acties (claim, correctie, verwijderen) ✅

### Fase 8: Expiry & Reminder Bot
- [x] **Stap 8.1**: Expiry reminder service ✅
- [x] **Stap 8.2**: Expiry reminder worker/bot ✅
- [x] **Stap 8.3**: Expiry state management ✅

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
- [x] Scope documentatie bestaat ✅
- [x] Scope is goedgekeurd/gedocumenteerd ✅
- [x] Duidelijke grenzen tussen wel/niet features ✅

**Bestanden om aan te maken/wijzigen**:
- `Docs/claim-outreach-scope.md` (nieuw, documentatie) ✅

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
- [x] Juridisch kader gedocumenteerd ✅
- [x] Mailcopy volgt AVG richtlijnen ✅
- [x] Opt-out mechanisme is duidelijk ✅
- [x] Logging voor AVG compliance is gepland ✅

**Bestanden om aan te maken/wijzigen**:
- `Docs/claim-outreach-legal-framework.md` (nieuw, documentatie) ✅
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
- [x] Tabel bestaat in database ✅
- [x] Indexen op location_id en email ✅
- [x] UNIQUE constraint voorkomt duplicaten ✅
- [x] Migration script in `Infra/supabase/` ✅

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/078_outreach_contacts.sql` (nieuwe migration) ✅

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
- [x] ENUM type bestaat ✅
- [x] Tabel bestaat met correcte constraints ✅
- [x] Indexen op location_id, contact_id, status, email ✅
- [x] Migration script ✅

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/079_outreach_emails.sql` (nieuwe migration) ✅

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
- [x] ENUM type bestaat ✅
- [x] Tabel bestaat met UNIQUE constraint op location_id ✅
- [x] Index op claim_token voor snelle lookups ✅
- [x] Index op claim_status ✅
- [x] Migration script ✅

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/077_token_location_claims.sql` (nieuwe migration) ✅

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
- [x] Kolommen toegevoegd aan locations tabel ✅
- [x] Default waarden zijn correct ✅
- [x] Index op is_claimable en claimed_status ✅
- [x] Migration script ✅

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/080_location_claim_flags.sql` (nieuwe migration) ✅
- Update bestaande location queries indien nodig ✅

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
- [x] Worker script bestaat ✅
- [x] Selectie logica werkt correct ✅
- [x] Geen duplicaten (UNIQUE constraint) ✅
- [x] Rate limiting voor externe API calls ✅
- [x] Logging en error handling ✅

**Bestanden om aan te maken/wijzigen**:
- `Backend/app/workers/contact_discovery_bot.py` (nieuw) ✅
- `Backend/scripts/run_contact_discovery.py` (nieuw, CLI script) ✅

---

#### Stap 3.4: Integratie met Bestaande Location Pipeline

**Doel**: Zorg dat contact discovery automatisch triggert bij nieuwe verified locaties.

**Integratie Opties**:
- Option 1: Trigger na OSM discovery (als locatie verified wordt)
- Option 2: Scheduled job (dagelijks, voor nieuwe verified locaties)
- Option 3: Beide (trigger + scheduled backup)

**Acceptatie Criteria**:
- [x] Integratie werkt met bestaande pipeline ✅
- [x] Geen breaking changes in bestaande flow ✅
- [x] Duplicaten worden voorkomen ✅
- [x] Performance impact is acceptabel ✅

**Bestanden om aan te maken/wijzigen**:
- `.github/workflows/tda_contact_discovery.yml` (nieuw, scheduled job) ✅
- `Backend/services/worker_orchestrator.py` (update, contact_discovery bot support) ✅

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
- [x] Selectie functie bestaat
- [x] Alle criteria worden gecontroleerd
- [x] Performance is acceptabel (indexen)
- [x] Tests voor edge cases

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
- [x] Rate limiting service bestaat ✅
- [x] Dagelijkse limiet wordt gerespecteerd ✅
- [x] Configuratie via env vars ✅
- [x] Logging voor monitoring ✅

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
- [x] Queue management service bestaat
- [x] Integratie met selectie en rate limiting
- [x] Queue entries worden correct aangemaakt
- [x] Prioritering werkt

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
- [x] Domain is geverifieerd in SES (documentatie beschikbaar) ✅
- [x] SPF record is correct (documentatie beschikbaar) ✅
- [x] DKIM records zijn correct (documentatie beschikbaar) ✅
- [x] DMARC record is geconfigureerd (documentatie beschikbaar) ✅
- [x] Email authentication testen (bijv. via mail-tester.com) (documentatie beschikbaar) ✅

**Bestanden om aan te maken/wijzigen**:
- `Docs/ses-setup-guide.md` (nieuw, documentatie) ✅
- DNS configuratie (extern, documenteren) ✅

---

#### Stap 5.2: SES Production Access Request

**Doel**: Request production access in AWS SES (uit sandbox mode).

**Proces**:
- Use case uitleggen: Service notifications voor locatie-eigenaren
- Verwachte volume: Start 50/dag, groei naar 500/dag
- Opt-out mechanisme beschrijven
- Compliance (AVG) vermelden

**Acceptatie Criteria**:
- [x] Production access is aangevraagd (template klaar) ✅
- [ ] Access is goedgekeurd (nog niet ingediend)
- [ ] Sandbox restrictions zijn opgeheven (na goedkeuring)

**Bestanden om aan te maken/wijzigen**:
- `Docs/ses-production-request.md` (nieuw, documentatie van request) ✅

---

#### Stap 5.3: SES Provider Implementatie (voor Outreach)

**Doel**: SES provider volledig implementeren voor outreach emails (email service abstraction bestaat al uit pre-claim plan Fase 0.5.1).

**Prerequisite**: 
- Email service abstraction layer bestaat al (pre-claim plan Fase 0.5.1)
- Provider pattern bestaat al
- SMTP provider werkt al

**Implementatie**:
- Volledige SES provider implementatie (skeleton bestaat al uit Fase 0.5.1)
- SES client setup (boto3)
- Error handling (bounces, throttling)
- Response tracking (message_id)
- Rate limiting voor outreach volumes

**Acceptatie Criteria**:
- [x] SES provider implementatie is compleet ✅
- [x] SES integratie werkt ✅
- [x] Error handling is robuust ✅
- [x] Message ID wordt geretourneerd ✅
- [x] Configuratie via env vars (AWS credentials) ✅
- [x] Rate limiting werkt voor outreach volumes ✅

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/email/ses_provider.py` (update, volledige implementatie - skeleton bestaat al uit pre-claim plan Fase 0.5.1) ✅
- `Backend/services/email_service.py` (update, SES provider configuratie voor outreach) ✅
- Update `.env.example` met AWS SES config (`AWS_SES_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) ✅

**Noot**: 
- Email service abstraction bestaat al uit pre-claim plan Fase 0.5.1
- Template systeem bestaat al uit pre-claim plan Fase 0.5.2
- Focus hier is op SES setup specifiek voor outreach (hogere volumes, rate limiting)

---

### FASE 6: Outreach Mailer Bot

#### Stap 6.1: Email Template Systeem (voor Outreach)

**Doel**: Outreach-specifieke email templates maken (template systeem bestaat al uit pre-claim plan Fase 0.5.2).

**Prerequisite**: 
- Template systeem foundation bestaat al (pre-claim plan Fase 0.5.2)
- Base templates bestaan al

**Templates Vereist**:
- **Outreach email** (eerste contact):
  - Subject: "Uw locatie staat op Turkspot" (NL) / "Konumunuz Turkspot'ta" (TR) / "Your location is on Turkspot" (EN)
  - Body: Informatief, vriendelijk, AVG-compliant
  - **Link naar mapview** (locatie gecentreerd, tooltip open) - primaire CTA
  - Opt-out link
  - **Noot**: Token link wordt niet meer gebruikt (authenticated claim flow is primair)

- **Claim bevestiging** (na claim actie) - gebruikt al bestaande templates uit pre-claim plan Stap 3.10
- **Removal bevestiging** (na verwijdering) - optioneel
- **Correction bevestiging** (na correctie) - optioneel

**Template Features** (uitbreiding op Fase 0.5.2):
- Outreach-specifieke variabelen (location_name, mapview_link, opt_out_link)
- AVG-compliant teksten
- Meertaligheid (NL/TR/EN)
- Plain text + HTML versies
- Geen tracking pixels (privacy-first)

**Acceptatie Criteria**:
- [x] Outreach email template bestaat
- [x] Alle templates zijn geïmplementeerd
- [x] AVG-compliant teksten
- [x] Variabelen werken
- [x] Plain text + HTML versies
- [x] Meertaligheid werkt

**Bestanden om aan te maken/wijzigen**:
- `Backend/templates/emails/outreach_email.html.j2` (nieuw)
- `Backend/templates/emails/outreach_email.txt.j2` (nieuw)
- `Backend/templates/emails/removal_confirmation.html.j2` (nieuw, optioneel)
- `Backend/templates/emails/correction_confirmation.html.j2` (nieuw, optioneel)
- `Backend/services/email_template_service.py` (update, outreach variabelen - bestaat al uit Fase 0.5.2)

**Noot**: 
- Template systeem foundation bestaat al uit pre-claim plan Fase 0.5.2
- Base templates bestaan al
- Claim confirmation templates bestaan al uit pre-claim plan Stap 3.10

---

#### Stap 6.2: Mapview Link Generatie (Locatie Gecentreerd, Tooltip Open)

**Doel**: Service die mapview links genereert met locatie gecentreerd en tooltip open.

**Link Format**:
- URL: `{frontend_url}/#/map?location={location_id}&center={lat},{lng}&zoom={zoom}&tooltip={location_id}`
- Of: `{frontend_url}/#/map?focus={location_id}` (als focus parameter ondersteund wordt)

**Implementatie**:
- Service functie: `generate_mapview_link(location_id, location_lat, location_lng)`
- Berekent optimale zoom level voor locatie
- Genereert URL met query parameters
- Test dat link correct werkt (locatie gecentreerd, tooltip open)

**Mapview Integratie**:
- Frontend moet query parameters lezen
- Bij `focus={location_id}`: center map op locatie, open tooltip
- Bij `tooltip={location_id}`: open tooltip voor locatie

**Acceptatie Criteria**:
- [x] Link generatie service bestaat
- [x] Links bevatten correcte parameters
- [x] Frontend leest parameters correct (frontend ondersteunt al focus parameter via viewMode.ts)
- [x] Mapview centreert op locatie (via focus parameter)
- [x] Tooltip opent automatisch (via focus parameter)
- [ ] Test met verschillende locaties (kan later getest worden)

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/mapview_link_service.py` (nieuw)

**Noot**: Frontend ondersteunt al `focus={location_id}` parameter via `viewMode.ts`, dus geen frontend wijzigingen nodig.

---

#### Stap 6.3: SES Mailer Service

**Doel**: Service die emails verzendt via SES en status bijwerkt.

**Functionaliteit**:
- Haal queued emails op
- Genereer mapview link voor locatie (via Stap 6.2)
- Render templates met context (inclusief mapview_link)
- Verzend via email_service (Stap 5.3)
- Update outreach_emails status naar 'sent'
- Sla SES message_id op
- Log errors

**Acceptatie Criteria**:
- [x] Mailer service bestaat
- [x] Integratie met email_service
- [x] Mapview link generatie werkt
- [x] Template rendering werkt
- [x] Status updates zijn correct
- [x] Error handling en logging

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/outreach_mailer_service.py` (nieuw)
- Integratie met `mapview_link_service.py` (Stap 6.2)

---

#### Stap 6.4: Email Status Tracking & Error Handling

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
- [x] Status tracking werkt
- [x] SES webhooks/events worden verwerkt (SNS notifications)
- [x] Bounce handling voorkomt verdere outreach
- [x] Retry logica werkt (max 2 retries met exponential backoff)
- [x] Click tracking werkt via frontend integratie
- [x] Opt-out mechanisme werkt via secure tokens
- [x] Logging voor alle status changes

**Bestanden om aan te maken/wijzigen**:
- `Backend/api/routers/ses_webhooks.py` (nieuw, voor SES event webhooks via SNS) ✅
- `Backend/api/routers/outreach_tracking.py` (nieuw, click tracking & opt-out endpoints) ✅
- `Backend/services/outreach_mailer_service.py` (update, error handling, retry logica, opt-out tokens) ✅
- `Infra/supabase/080_outreach_emails_opt_out_token.sql` (nieuwe migration) ✅
- `Infra/supabase/081_outreach_emails_retry_fields.sql` (nieuwe migration) ✅
- `Frontend/src/lib/api.ts` (update, trackOutreachClick functie) ✅
- `Frontend/src/components/MapTab.tsx` (update, click tracking integratie) ✅

---

#### Stap 6.5: Outreach Mailer Worker/Bot

**Doel**: Worker die automatisch emails verzendt uit de queue.

**Logica**:
- Haal queued emails op (via queue service)
- Check rate limiting
- Verzend emails (via mailer service)
- Update status
- Log resultaten

**Acceptatie Criteria**:
- [x] Worker script bestaat
- [x] Integratie met alle services
- [x] Rate limiting wordt gerespecteerd
- [x] Error handling voorkomt crashes
- [x] Graceful shutdown support
- [x] Logging voor monitoring
- [x] CLI script voor easy execution

**Bestanden om aan te maken/wijzigen**:
- `Backend/app/workers/outreach_mailer_bot.py` (nieuw) ✅
- `Backend/scripts/run_outreach_mailer.py` (nieuw, CLI script) ✅

---

### FASE 7: Claim Flow Integratie

#### Stap 7.1: Authenticated Claim Flow Integratie

**Doel**: Zorg dat authenticated claim flow (uit pre-claim plan Fase 3) werkt met outreach emails.

**Integratie**:
- Gebruiker klikt op mapview link in email
- Mapview opent met locatie gecentreerd en tooltip open
- Gebruiker klikt op tooltip → location detail card opent
- Gebruiker ziet "Claim" knop (als ingelogd)
- Gebruiker klikt "Claim" → authenticated claim flow start
- Claim form met logo/Google Business link
- Submit → claim request naar admin
- Admin keurt goed/af → gebruiker krijgt email bevestiging
- Bij goedkeuring: gebruiker krijgt owner rol, "Senin" sectie verschijnt

**Flow Validatie**:
- Test complete flow van email → mapview → claim
- Test met ingelogde gebruiker
- Test met niet-ingelogde gebruiker (moet login prompt zien)

**Acceptatie Criteria**:
- [x] Mapview link werkt correct ✅
- [x] Tooltip opent automatisch ✅
- [x] Claim knop is zichtbaar in location detail ✅
- [x] Authenticated claim flow werkt ✅
- [x] Email bevestigingen werken ✅
- [x] Owner rol wordt toegekend ✅
- [x] "Senin" sectie verschijnt ✅

**Bestanden om aan te maken/wijzigen**:
- Geen nieuwe bestanden (gebruik bestaande authenticated claim flow uit pre-claim plan)
- Test integratie tussen email → mapview → claim flow

---

#### Stap 7.2: Token-based Claim Fallback (Optioneel)

**Doel**: Token-based claim flow als fallback voor niet-ingelogde gebruikers (optioneel).

**⚠️ BESLUIT NODIG**: Token-based claim flow implementeren als fallback?

**Opties**:
- **Optie A**: Skip token-based flow (alleen authenticated claims)
  - ✅ Simpler architectuur
  - ✅ Minder code te onderhouden
  - ❌ Niet-ingelogde gebruikers kunnen niet claimen via email
- **Optie B**: Implementeer token-based fallback
  - ✅ Niet-ingelogde gebruikers kunnen claimen
  - ✅ Meer flexibiliteit
  - ❌ Extra complexiteit, twee claim flows

**💡 Suggestie**: Optie A (Skip token-based flow)
- **Motivatie**: Focus op authenticated claims, gebruikers kunnen altijd inloggen
- Authenticated claims zijn primair, token-based is alleen nodig als we echt niet-ingelogde claims willen ondersteunen

**Als Optie B gekozen**:
- Implementeer token-based claim endpoints (uit pre-claim plan Fase 4)
- Token-based claim pagina
- Fallback logica: authenticated eerst, token als fallback

**Acceptatie Criteria**:
- [ ] Beslissing genomen
- [ ] Token-based flow werkt (als gekozen)
- [ ] Fallback logica werkt (als gekozen)

**Bestanden om aan te maken/wijzigen**:
- `Backend/api/routers/outreach_claims.py` (alleen als Optie B)
- `Frontend/src/pages/ClaimPage.tsx` (alleen als Optie B)

---

#### Stap 7.3: Email Bevestigingen voor Acties

**Doel**: Email bevestigingen verzenden na elke claim actie.

**Prerequisite**: Transactionele email foundation (pre-claim plan Fase 0.5) moet voltooid zijn.

**Bevestigingen**:
- **Claim Approved** (uit pre-claim plan Stap 3.10): "Uw claim is goedgekeurd - {location_name}" (NL) / "Talebiniz onaylandı - {location_name}" (TR) / "Your claim has been approved - {location_name}" (EN)
- **Claim Rejected** (uit pre-claim plan Stap 3.10): "Uw claim is afgewezen - {location_name}" (NL) / "Talebiniz reddedildi - {location_name}" (TR) / "Your claim has been rejected - {location_name}" (EN)
- **Remove** (optioneel, als remove functionaliteit wordt toegevoegd): "Uw locatie wordt verwijderd. Bedankt voor uw feedback." (NL/TR/EN)
- **Correction** (optioneel, als correction functionaliteit wordt toegevoegd): "Bedankt voor uw correctie. We verwerken dit zo snel mogelijk." (NL/TR/EN)

**Implementatie**:
- Claim approval/rejection emails worden al getriggerd in authenticated claim flow (pre-claim plan Stap 3.10)
- Gebruik transactionele email foundation (pre-claim plan Fase 0.5)
- Optionele remove/correction emails kunnen worden toegevoegd als functionaliteit wordt geïmplementeerd
- Gebruik email templates (Stap 6.1)
- Verzend via email_service (pre-claim plan Fase 0.5.1)

**Acceptatie Criteria**:
- [x] Claim approval/rejection emails werken (al geïmplementeerd in pre-claim plan Stap 3.10) ✅
- [x] Optionele remove/correction emails werken ✅ (geïmplementeerd voor token-based claims)
- [x] Templates zijn correct ✅
- [x] Email bevat relevante informatie ✅
- [x] Meertaligheid werkt ✅ (NL/TR/EN)
- [x] Error handling (email failure blokkeert niet de actie) ✅

**Bestanden om aan te maken/wijzigen**:
- Geen nieuwe bestanden voor claim emails (al in pre-claim plan Stap 3.10)
- ✅ `Backend/templates/emails/removal_confirmation.html.j2` (geïmplementeerd voor token-based remove endpoint)
- ✅ `Backend/templates/emails/removal_confirmation.txt.j2` (geïmplementeerd)
- ✅ `Backend/templates/emails/correction_confirmation.html.j2` (geïmplementeerd voor token-based correct endpoint)
- ✅ `Backend/templates/emails/correction_confirmation.txt.j2` (geïmplementeerd)
- ✅ `Backend/api/routers/outreach_claims.py` (update, email triggers toegevoegd aan remove en correct endpoints)

**Notitie**: 
- Claim approval/rejection emails werken al via `claim_approval_service.py` (authenticated claims)
- Remove en correction confirmation emails zijn geïmplementeerd voor token-based claims in `outreach_claims.py`
- Alle emails ondersteunen meertaligheid (NL/TR/EN) en hebben proper error handling

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
- [x] Reminder service bestaat ✅
- [x] Selectie logica werkt ✅
- [x] Email wordt verzonden ✅
- [x] Duplicaten worden voorkomen ✅
- [x] Configuratie voor reminder timing (7 dagen) ✅

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/expiry_reminder_service.py` (nieuw) ✅
- `Infra/supabase/081_token_claims_reminder_sent.sql` (nieuwe migration) ✅
- `Backend/templates/emails/expiry_reminder.html.j2` (nieuw) ✅
- `Backend/templates/emails/expiry_reminder.txt.j2` (nieuw) ✅

---

#### Stap 8.2: Expiry Reminder Worker/Bot

**Doel**: Worker die dagelijks expiry reminders verzendt.

**Logica**:
- Run reminder service
- Verzend reminders
- Log resultaten

**Acceptatie Criteria**:
- [x] Worker script bestaat ✅
- [x] Dagelijkse run werkt ✅
- [x] Integratie met reminder service ✅
- [x] Error handling en logging ✅

**Bestanden om aan te maken/wijzigen**:
- `Backend/app/workers/expiry_reminder_bot.py` (nieuw) ✅
- `Backend/scripts/run_expiry_reminder.py` (nieuw, CLI script) ✅

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
- [x] Expiry service bestaat ✅
- [x] State updates zijn correct ✅
- [x] Geen data loss ✅
- [x] Logging voor monitoring ✅

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/expiry_service.py` (nieuw) ✅
- `Backend/app/workers/expiry_bot.py` (nieuw, scheduled worker) ✅
- `Backend/scripts/run_expiry_bot.py` (nieuw, CLI script) ✅

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

- **Pre-Claim Plan**: `Docs/pre-claim-outreach-implementation-plan.md` (Fase 0.5: Transactionele Email Foundation)
- AWS SES Documentation: https://docs.aws.amazon.com/ses/
- AVG/GDPR Guidelines: https://autoriteitpersoonsgegevens.nl/
- Design System: `Docs/design-system.md`
- Database Migrations: `Infra/supabase/`
- API Patterns: `Backend/api/routers/`
- Frontend Components: `Frontend/src/components/`
- Worker Patterns: `Backend/app/workers/`

---

**Laatste Update**: 2025-01-16  
**Huidige Status**: 🟡 In Uitvoering (Stap 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 3.3, 3.4, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.3, 8.1, 8.2, 8.3 voltooid)  
**Prerequisite**: Pre-Claim & Consent Outreach Implementation Plan (Fase 0.5: Transactionele Email Foundation) moet voltooid zijn  
**Volgende Stap**: Fase 7 - Stap 7.2 (Token-based claim fallback - optioneel, beslissing nodig), of Fase 9: Logging & Metrics

---

## 📝 Nieuwe Visie Integratie Notities

### Email Link naar Mapview (Nieuwe Visie)
Outreach emails bevatten nu een **link naar mapview** in plaats van direct naar claim pagina:
- Link format: `/#/map?focus={location_id}` of `/#/map?location={location_id}&center={lat},{lng}&tooltip={location_id}`
- Mapview centreert automatisch op locatie
- Tooltip opent automatisch
- Gebruiker kan dan doorklikken naar location detail
- In location detail ziet gebruiker "Claim" knop (als ingelogd)
- Claim flow start via authenticated claim systeem

### Authenticated Claim Flow als Primaire Methode
De nieuwe visie maakt **authenticated claims** de primaire claim methode:
- Gebruikers moeten inloggen om te claimen
- Admin approval vereist
- Logo en Google Business link kunnen worden geüpload
- Bij approval krijgt gebruiker `location_owner` rol
- "Senin" sectie op account pagina toont geclaimde locaties
- Token-based claims zijn nu optioneel fallback (beslissing nodig)

### Claim Knop in Location Detail
- Nieuwe "Claim" knop naast Google zoek knop
- Alleen zichtbaar voor ingelogde gebruikers
- Start authenticated claim flow
- Geïmplementeerd in pre-claim plan Fase 3

### Drie Claim Systemen
1. **business_location_claims**: Premium/verified claims (toekomstig)
2. **authenticated_location_claims**: Primaire outreach claim flow (nieuwe visie)
3. **token_location_claims**: Token-based fallback (optioneel, beslissing nodig)

### Transactionele Email Foundation (Prerequisite)
Voordat outreach emails kunnen worden geïmplementeerd, moet de **transactionele email foundation** (pre-claim plan Fase 0.5) voltooid zijn:
- Email service abstraction layer (provider pattern)
- Template systeem met base templates
- Welkom emails bij account registratie
- Deze foundation wordt gebruikt door zowel claim emails als outreach emails


