# Claim Systems Comparison

**Status**: Documentatie  
**Laatste Update**: 2025-01-15  
**Doel**: Duidelijk maken wat het verschil is tussen alle claim systemen in Turkspot

## Overzicht

Turkspot heeft drie verschillende claim systemen die naast elkaar bestaan voor verschillende use cases. Dit document legt de verschillen uit tussen deze systemen en wanneer welke gebruikt wordt.

---

## 1. Business Location Claims (`business_location_claims`)

**Type**: Premium/Verified Claims  
**Status**: ✅ Bestaand systeem (geïmplementeerd in migration 031)

### Kenmerken

- **Voor wie**: Authenticated users met `business_accounts`
- **Vereisten**: 
  - Login vereist
  - Business account vereist (`business_accounts` tabel)
- **Status flow**: `pending` → `approved` / `rejected` / `revoked`
- **Admin approval**: Vereist
- **Koppeling**: Gekoppeld aan `business_account_id` (niet direct aan `user_id`)

### Database Schema

- Tabel: `business_location_claims`
- Foreign keys: `location_id` → `locations.id`, `business_account_id` → `business_accounts.id`
- Status ENUM: `claim_status` ('pending', 'approved', 'rejected', 'revoked')
- UNIQUE constraint: één claim per `location_id`

### Use Case

- **Doel**: Premium/verified claims voor bedrijven
- **Toekomstig**: Voor betalende business accounts met premium features
- **Niet voor**: Outreach emails (gebruik `authenticated_location_claims`)

### Bestanden

- Database: `Infra/supabase/031_business_accounts.sql`
- API: `Backend/api/routers/claims.py`

---

## 2. Authenticated Location Claims (`authenticated_location_claims`)

**Type**: Primaire Outreach Claim Flow  
**Status**: 🚧 In ontwikkeling (Fase 3 pre-claim plan)

### Kenmerken

- **Voor wie**: Authenticated users (geen business account nodig)
- **Vereisten**: 
  - Login vereist
  - Geen business account vereist
- **Status flow**: `pending` → `approved` / `rejected`
- **Admin approval**: Vereist
- **Koppeling**: Gekoppeld aan `user_id` (directe gebruiker)
- **Optioneel**: Logo upload, Google Business link

### Database Schema

- Tabel: `authenticated_location_claims`
- Foreign keys: `location_id` → `locations.id`, `user_id` → `auth.users.id`
- Status ENUM: `authenticated_claim_status` ('pending', 'approved', 'rejected')
- UNIQUE constraint: één claim per `location_id`

### Na Approval

- Gebruiker krijgt `location_owner` rol (in `user_role` ENUM)
- Entry wordt aangemaakt in `location_owners` tabel
- Logo wordt verplaatst van temp storage naar definitieve storage
- Google Business link wordt opgeslagen in `location_owners`

### Use Case

- **Doel**: Primaire claim flow voor outreach emails
- **Gebruik**: Gebruikers die via outreach emails locaties claimen
- **Flow**: Email → Mapview → Location Detail → Claim knop → Claim form → Admin approval → Owner rol

### Bestanden

- Database: `Infra/supabase/076_authenticated_location_claims.sql` (to be created)
- API: `Backend/api/routers/authenticated_claims.py` (to be created)
- Frontend: Claim form, admin dashboard (to be created)

---

## 3. Token Location Claims (`token_location_claims`)

**Type**: Token-based Fallback  
**Status**: 🔴 Niet gestart (uitreach plan Fase 4)

### Kenmerken

- **Voor wie**: Iedereen (geen login vereist)
- **Vereisten**: 
  - Geen login vereist
  - Claim token uit email
- **Status flow**: `unclaimed` → `claimed_free` → `expired` / `removed`
- **Admin approval**: Niet vereist (automatisch goedgekeurd)
- **Koppeling**: Gekoppeld aan email (niet `user_id`)
- **Gratis periode**: Met expiratie datum (`free_until`)

### Database Schema

- Tabel: `token_location_claims`
- Foreign keys: `location_id` → `locations.id`
- Status ENUM: `token_claim_status` ('unclaimed', 'claimed_free', 'expired', 'removed')
- UNIQUE constraint: één claim per `location_id`

### Use Case

- **Doel**: Fallback voor niet-ingelogde gebruikers via outreach
- **Gebruik**: Gebruikers die niet willen inloggen maar wel willen claimen
- **Flow**: Email → Token link → Claim pagina → Automatische claim → Gratis periode

### Bestanden

- Database: `Infra/supabase/075_token_location_claims.sql` (to be created)
- API: `Backend/api/routers/outreach_claims.py` (to be created)
- Frontend: Token-based claim page (to be created)

---

## Vergelijking Tabel

| Feature | Business Claims | Authenticated Claims | Token Claims |
|---------|----------------|---------------------|--------------|
| **Login vereist** | ✅ Ja | ✅ Ja | ❌ Nee |
| **Business account vereist** | ✅ Ja | ❌ Nee | ❌ Nee |
| **Admin approval** | ✅ Vereist | ✅ Vereist | ❌ Nee |
| **Koppeling** | `business_account_id` | `user_id` | `email` |
| **Status types** | pending, approved, rejected, revoked | pending, approved, rejected | unclaimed, claimed_free, expired, removed |
| **Logo upload** | ❌ Nee | ✅ Optioneel | ❌ Nee |
| **Google Business link** | ❌ Nee | ✅ Optioneel | ❌ Nee |
| **Owner rol** | ❌ Nee | ✅ `location_owner` | ❌ Nee |
| **Gratis periode** | ❌ Nee | ❌ Nee | ✅ Ja (met expiratie) |
| **Use case** | Premium/verified | Primaire outreach | Fallback outreach |

---

## Wanneer Welke Gebruiken?

### Voor Outreach Emails

1. **Primaire flow**: `authenticated_location_claims`
   - Email link → Mapview → Location Detail → Claim knop (als ingelogd)
   - Gebruiker moet inloggen
   - Admin approval vereist
   - Owner rol wordt toegekend

2. **Fallback flow**: `token_location_claims` (optioneel)
   - Email link → Token claim pagina (geen login)
   - Automatische claim zonder admin approval
   - Gratis periode met expiratie

### Voor Premium/Verified Claims

- **Gebruik**: `business_location_claims`
- Alleen voor bedrijven met business accounts
- Toekomstige premium features

---

## Co-existentie

Alle drie de systemen kunnen naast elkaar bestaan:

- Een locatie kan zowel een `business_location_claim` als een `authenticated_location_claim` hebben (verschillende use cases)
- Een locatie kan slechts één claim per type hebben (UNIQUE constraint op `location_id` per tabel)
- `location_owners` tabel bevat definitieve ownership na approval van `authenticated_location_claims`

---

## Referenties

- Pre-Claim Plan: `Docs/pre-claim-outreach-implementation-plan.md` (Fase 3)
- Outreach Plan: `Docs/claim-consent-outreach-implementation-plan.md` (Fase 4)
- Database Migrations: `Infra/supabase/`
- Business Claims API: `Backend/api/routers/claims.py`

---

**Laatste Update**: 2025-01-15  
**Volgende Stap**: Database schema implementatie voor authenticated_location_claims

