# Gamification Deprecation Plan

**Status**: 🟡 In Progress  
**Datum**: 2025-01-XX  
**Beslissing**: Optie A - Volledig Deprecate  
**Deprecation Periode**: 3 maanden (korter dan standaard omdat systeem niet actief is)

---

## Overzicht

Het bestaande XP/badges/streaks gamification systeem wordt volledig gedeprecated en verwijderd. Het systeem is niet actief (feature flag disabled) en heeft geen frontend integratie, dus er is geen user-facing impact.

**Reden voor Deprecation**:
- Feature flag `gamification_enabled` is disabled by default
- Geen actieve frontend integratie
- Nieuw rol-gebaseerd gamification systeem wordt geïmplementeerd
- Geen actieve users die het systeem gebruiken

---

## Timeline

### Fase 1: Deprecation Warnings (Week 1-2) ✅

**Status**: Voltooid

**Acties**:
- [x] Deprecation headers toegevoegd aan alle gamification API endpoints
- [x] Deprecation messages in endpoint docstrings
- [x] Headers: `X-API-Deprecated`, `X-API-Deprecation-Date`, `X-API-Deprecation-Message`

**Endpoints met Deprecation Warnings**:
- `GET /users/{user_id}/profile`
- `GET /users/{user_id}/badges`
- `GET /users/leaderboards/{city_key}`

**Deprecation Date**: 2025-04-XX (3 maanden vanaf implementatie)

---

### Fase 2: Code Cleanup (Week 3-4)

**Status**: Pending

**Acties**:
- [ ] Verwijder `award_xp` calls uit alle endpoints:
  - `Backend/api/routers/check_ins.py` (regel 87)
  - `Backend/api/routers/favorites.py` (regel 86)
  - `Backend/api/routers/notes.py` (regel 69)
  - `Backend/api/routers/polls.py` (regel 245)
  - `Backend/api/routers/profiles.py` (regel 415)
  - `Backend/api/routers/referrals.py` (regel 161, 170)
- [ ] Update `Backend/app/workers/digest_worker.py`:
  - Verwijder `get_user_xp_and_streak()` functie (regel 160-177)
  - Verwijder XP/streak data uit `generate_digest_content()` (regel 197)
- [ ] Verwijder of deprecate services:
  - `Backend/services/xp_service.py` (markeren als deprecated)
  - `Backend/services/badge_service.py` (markeren als deprecated)
  - `Backend/services/streak_service.py` (markeren als deprecated)
- [ ] Verwijder imports van `award_xp` uit alle routers

**Impact**:
- Geen breaking changes voor users (systeem niet actief)
- Code wordt eenvoudiger zonder XP awarding logica

---

### Fase 3: API Endpoint Deprecation (Week 5-6)

**Status**: Pending

**Acties**:
- [ ] Markeer gamification router endpoints als deprecated in OpenAPI schema
- [ ] Update API documentation met deprecation notice
- [ ] Optioneel: Return 410 Gone na deprecation periode (of verwijder endpoints)

**Endpoints te Deprecaten**:
- `GET /users/{user_id}/profile`
- `GET /users/{user_id}/badges`
- `GET /users/leaderboards/{city_key}`

---

### Fase 4: Database Cleanup (Na Deprecation Periode)

**Status**: Pending (Na 3 maanden deprecation periode)

**Acties**:
- [ ] Backup database tabellen (voor veiligheid)
- [ ] Verwijder database tabellen:
  - `user_streaks`
  - `user_xp_log`
  - `user_badges`
  - `badge_type` ENUM type
- [ ] Maak migration script: `Infra/supabase/XXX_remove_gamification_tables.sql`
- [ ] Test migration op staging
- [ ] Run migration op production

**SQL Migration Script** (voorbeeld):

```sql
-- XXX_remove_gamification_tables.sql
-- Remove deprecated gamification tables after deprecation period

-- Drop tables (CASCADE will handle foreign keys)
DROP TABLE IF EXISTS public.user_xp_log CASCADE;
DROP TABLE IF EXISTS public.user_badges CASCADE;
DROP TABLE IF EXISTS public.user_streaks CASCADE;

-- Drop ENUM type
DROP TYPE IF EXISTS public.badge_type CASCADE;
```

**Notitie**: Migration moet worden uitgevoerd na deprecation periode (3 maanden).

---

## Communication Plan

### Internal Communication

**Stakeholders**: Development team, Product team

**Message**:
- Gamification systeem wordt gedeprecated (niet actief, geen user impact)
- Nieuw rol-gebaseerd systeem wordt geïmplementeerd
- Geen actie vereist van users (systeem niet zichtbaar)

### External Communication

**Status**: Niet vereist

**Reden**: 
- Systeem is niet actief (feature flag disabled)
- Geen frontend integratie
- Geen users die het systeem gebruiken
- Geen user-facing impact

**Als er toch vragen komen**:
- Verwijs naar nieuwe rol-gebaseerde gamification systeem
- Leg uit dat oude systeem niet actief was
- Geef timeline voor nieuwe systeem implementatie

---

## Rollback Plan

**Scenario**: Als er onverwachte issues zijn tijdens deprecation.

**Acties**:
1. Herstel deprecation warnings (verwijder headers)
2. Herstel `award_xp` calls in endpoints (als nodig)
3. Database tabellen blijven bestaan (niet verwijderd tot na deprecation periode)
4. Feature flag blijft disabled (systeem niet actief)

**Waarschijnlijkheid**: Zeer laag (systeem niet actief, geen dependencies)

---

## Success Criteria

- [x] Deprecation warnings toegevoegd aan alle endpoints
- [ ] Alle `award_xp` calls verwijderd uit endpoints
- [ ] Services gemarkeerd als deprecated
- [ ] API documentation bijgewerkt
- [ ] Database tabellen verwijderd na deprecation periode
- [ ] Geen breaking changes voor users
- [ ] Codebase is eenvoudiger zonder XP awarding logica

---

## Notities

- **Feature Flag**: `gamification_enabled` blijft disabled (systeem niet actief)
- **Frontend**: Geen wijzigingen nodig (geen integratie)
- **Database**: Tabellen blijven bestaan tijdens deprecation periode voor rollback mogelijkheid
- **Timeline**: 3 maanden deprecation periode (korter dan standaard omdat systeem niet actief is)

---

## Referenties

- Analyse document: `Docs/gamification-migration-analysis.md`
- Gamification implementation plan: `Docs/gamification-implementation-plan.md`
- Pre-gamification plan: `Docs/pre-gamification-implementation-plan.md`
- Database migration: `Infra/supabase/028_gamification.sql`

---

**Laatste Update**: 2025-01-XX  
**Status**: Fase 1 Voltooid, Fase 2-4 Pending



