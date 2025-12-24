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

### Fase 5: Amazon SES Setup (voor Outreach)
- [ ] **Stap 5.1**: SES domain verification (SPF, DKIM, DMARC)
- [ ] **Stap 5.2**: SES production access request
- [ ] **Stap 5.3**: SES provider implementatie (email service abstraction bestaat al uit pre-claim plan Fase 0.5.1)

### Fase 6: Outreach Mailer Bot
- [ ] **Stap 6.1**: Email template systeem
- [ ] **Stap 6.2**: Mapview link generatie (locatie gecentreerd, tooltip open)
- [ ] **Stap 6.3**: SES mailer service
- [ ] **Stap 6.4**: Email status tracking & error handling
- [ ] **Stap 6.5**: Outreach mailer worker/bot

### Fase 7: Claim Flow Integratie
- [ ] **Stap 7.1**: Authenticated claim flow integratie (gebruik bestaande flow uit pre-claim plan)
- [ ] **Stap 7.2**: Token-based claim fallback (optioneel, voor niet-ingelogde gebruikers)
- [ ] **Stap 7.3**: Email bevestigingen voor acties (claim, correctie, verwijderen)

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
- [ ] SES provider implementatie is compleet
- [ ] SES integratie werkt
- [ ] Error handling is robuust
- [ ] Message ID wordt geretourneerd
- [ ] Configuratie via env vars (AWS credentials)
- [ ] Rate limiting werkt voor outreach volumes

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/email/ses_provider.py` (update, volledige implementatie - skeleton bestaat al uit pre-claim plan Fase 0.5.1)
- `Backend/services/email_service.py` (update, SES provider configuratie voor outreach)
- Update `.env.example` met AWS SES config (`AWS_SES_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)

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
- [ ] Outreach email template bestaat
- [ ] Alle templates zijn geïmplementeerd
- [ ] AVG-compliant teksten
- [ ] Variabelen werken
- [ ] Plain text + HTML versies
- [ ] Meertaligheid werkt

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
- [ ] Link generatie service bestaat
- [ ] Links bevatten correcte parameters
- [ ] Frontend leest parameters correct
- [ ] Mapview centreert op locatie
- [ ] Tooltip opent automatisch
- [ ] Test met verschillende locaties

**Bestanden om aan te maken/wijzigen**:
- `Backend/services/mapview_link_service.py` (nieuw)
- `Frontend/src/components/MapTab.tsx` (update, query parameter handling)
- `Frontend/src/components/MapView.tsx` (update, focus/tooltip parameters)

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
- [ ] Mailer service bestaat
- [ ] Integratie met email_service
- [ ] Mapview link generatie werkt
- [ ] Template rendering werkt
- [ ] Status updates zijn correct
- [ ] Error handling en logging

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

#### Stap 6.5: Outreach Mailer Worker/Bot

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
- [ ] Mapview link werkt correct
- [ ] Tooltip opent automatisch
- [ ] Claim knop is zichtbaar in location detail
- [ ] Authenticated claim flow werkt
- [ ] Email bevestigingen werken
- [ ] Owner rol wordt toegekend
- [ ] "Senin" sectie verschijnt

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
- [ ] Claim approval/rejection emails werken (al geïmplementeerd in pre-claim plan Stap 3.10)
- [ ] Optionele remove/correction emails werken (als geïmplementeerd)
- [ ] Templates zijn correct
- [ ] Email bevat relevante informatie
- [ ] Meertaligheid werkt
- [ ] Error handling (email failure blokkeert niet de actie)

**Bestanden om aan te maken/wijzigen**:
- Geen nieuwe bestanden voor claim emails (al in pre-claim plan Stap 3.10)
- Optioneel: `Backend/templates/emails/removal_confirmation.html.j2` (als remove functionaliteit wordt toegevoegd)
- Optioneel: `Backend/templates/emails/correction_confirmation.html.j2` (als correction functionaliteit wordt toegevoegd)

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

- **Pre-Claim Plan**: `Docs/pre-claim-outreach-implementation-plan.md` (Fase 0.5: Transactionele Email Foundation)
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
**Prerequisite**: Pre-Claim & Consent Outreach Implementation Plan (Fase 0.5: Transactionele Email Foundation) moet voltooid zijn  
**Volgende Stap**: Fase 1 - Voorbereiding & Randvoorwaarden (Stap 1.1: Functionele scope vastleggen)

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


