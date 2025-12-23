# Gamification Migration Analysis

**Status**: 🟡 In Progress  
**Datum**: 2025-01-XX  
**Doel**: Analyse van bestaand XP/badges/streaks systeem en beslissing over migration path naar nieuw rol-gebaseerd systeem

---

## 1. Database Analyse

### 1.1 Data Volume Metrics

**SQL Queries voor Analyse**:

```sql
-- XP en Streaks Metrics
SELECT 
  COUNT(DISTINCT user_id) as users_with_xp,
  COUNT(DISTINCT CASE WHEN total_xp > 0 THEN user_id END) as users_with_positive_xp,
  COUNT(DISTINCT CASE WHEN current_streak_days > 0 THEN user_id END) as users_with_streaks,
  SUM(total_xp) as total_xp_awarded,
  AVG(total_xp) as avg_xp_per_user,
  MAX(total_xp) as max_xp,
  MIN(total_xp) as min_xp,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_xp) as median_xp
FROM user_streaks;

-- Badge Metrics
SELECT 
  COUNT(DISTINCT user_id) as users_with_badges,
  COUNT(*) as total_badges,
  badge_type,
  COUNT(*) as count
FROM user_badges
GROUP BY badge_type
ORDER BY count DESC;

-- XP Log Activity Volume
SELECT 
  COUNT(*) as total_xp_events,
  COUNT(DISTINCT user_id) as unique_users_with_xp_events,
  COUNT(DISTINCT client_id) as unique_anonymous_with_xp_events,
  source,
  COUNT(*) as count,
  SUM(xp_amount) as total_xp_by_source
FROM user_xp_log
GROUP BY source
ORDER BY count DESC;

-- Recent Activity (last 30 days)
SELECT 
  COUNT(*) as recent_xp_events,
  COUNT(DISTINCT user_id) as recent_active_users
FROM user_xp_log
WHERE created_at >= NOW() - INTERVAL '30 days';
```

**Notitie**: Deze queries moeten worden uitgevoerd op de productie database om exacte metrics te krijgen. Op basis van de code analyse lijkt het systeem niet actief te zijn (feature flag disabled).

---

## 2. Code Dependencies Analyse

### 2.1 XP Awarding Points

De `award_xp` functie wordt aangeroepen vanuit de volgende endpoints:

1. **`Backend/api/routers/check_ins.py`** (regel 87)
   - Source: `"check_in"`
   - XP Amount: 10 (uit `xp_config.py`)
   - Trigger: Na succesvolle check-in

2. **`Backend/api/routers/favorites.py`** (regel 86)
   - Source: `"favorite"`
   - XP Amount: 5
   - Trigger: Na favorite toevoegen

3. **`Backend/api/routers/notes.py`** (regel 69)
   - Source: `"note"`
   - XP Amount: 20
   - Trigger: Na note creation

4. **`Backend/api/routers/polls.py`** (regel 245)
   - Source: `"poll_response"`
   - XP Amount: 15
   - Trigger: Na poll response

5. **`Backend/api/routers/profiles.py`** (regel 415)
   - Source: `"onboarding"`
   - XP Amount: 10 (hardcoded in endpoint)
   - Trigger: Na onboarding completion

6. **`Backend/api/routers/referrals.py`** (regel 161, 170)
   - Source: `"referral"` (50 XP) en `"referral_welcome"` (25 XP)
   - XP Amount: 50 en 25 (hardcoded)
   - Trigger: Na referral signup

7. **`Backend/api/routers/reactions.py`**
   - **NIET geïmplementeerd**: Import bestaat maar wordt niet aangeroepen
   - Source zou zijn: `"reaction"`
   - XP Amount: 5 (uit config, maar niet gebruikt)

### 2.2 Service Dependencies

**XP Service** (`Backend/services/xp_service.py`):
- Award XP met daily cap (200 XP default)
- Log XP awards in `user_xp_log`
- Automatisch streak update via `streak_service.update_streak()`
- Automatisch badge check via `badge_service.check_and_award_badges()`

**Streak Service** (`Backend/services/streak_service.py`):
- Track daily streaks (48h reset threshold)
- Update `current_streak_days` en `longest_streak_days`
- Wordt aangeroepen na elke XP award

**Badge Service** (`Backend/services/badge_service.py`):
- Check badge conditions na XP award
- Award badges: `streak_7`, `streak_30`, `check_in_100`, `super_supporter`, `poll_master`, `explorer_city`
- Wordt aangeroepen na elke XP award

### 2.3 API Endpoints

**`Backend/api/routers/gamification.py`**:
- `GET /users/{user_id}/profile`: User profile met XP en streaks
- `GET /users/{user_id}/badges`: User badges lijst
- `GET /users/leaderboards/{city_key}`: City leaderboard

**Feature Flag**: Alle endpoints vereisen `gamification_enabled = true` (disabled by default)

### 2.4 Frontend Usage

**Resultaat**: Geen actieve frontend integratie gevonden.
- Feature flag is disabled (`FEATURE_GAMIFICATION=false` by default)
- Geen frontend componenten die gamification endpoints aanroepen
- Geen UI die XP/badges/streaks toont

### 2.5 Other Usage

**`Backend/app/workers/digest_worker.py`** (regel 160-177):
- Functie `get_user_xp_and_streak()` haalt XP/streak data op voor email digests
- Wordt gebruikt in `generate_digest_content()` maar alleen als data beschikbaar is

---

## 3. Impact Assessment

### 3.1 User Impact

**Huidige Status**:
- Feature flag disabled → systeem is **niet actief** in productie
- Geen frontend integratie → users zien geen XP/badges
- Backend code award XP maar data wordt niet gebruikt

**Potentiële Impact bij Deprecation**:
- **Laag**: Systeem is niet zichtbaar voor users
- **Geen breaking changes**: Geen actieve frontend dependencies
- **Data verlies**: XP/badges data zou verloren gaan (maar niet zichtbaar voor users)

### 3.2 Code Impact

**Breaking Changes bij Deprecation**:
- **7 endpoints** roepen `award_xp` aan → moeten worden aangepast
- **1 worker** (digest_worker) gebruikt XP data → moet worden aangepast
- **3 services** (xp_service, badge_service, streak_service) → kunnen worden verwijderd
- **3 API endpoints** (gamification router) → kunnen worden verwijderd of gedeprecated

**Migration Complexity**:
- **Laag-Middel**: Veel code verwijderen/aanpassen maar geen complexe dependencies
- **Geen database constraints**: Tabellen kunnen worden verwijderd zonder breaking changes

### 3.3 Data Volume Estimate

**Geschat op basis van feature flag status**:
- **Zeer laag**: Feature flag disabled → waarschijnlijk < 10 users met XP
- **Mogelijk 0**: Als feature nooit is geactiveerd in productie

**Aanbeveling**: Database queries uitvoeren om exacte metrics te krijgen.

---

## 4. Migration Path Opties

### Optie A: Volledig Deprecate

**Beschrijving**: Verwijder oude systeem volledig na korte deprecation periode.

**Voordelen**:
- Schone codebase
- Geen verwarring tussen oude en nieuwe systeem
- Minder maintenance overhead

**Nadelen**:
- Data verlies (maar niet zichtbaar voor users)
- Vereist code changes in 7 endpoints + 1 worker

**Timeline**:
- Week 1-2: Deprecation warnings toevoegen
- Week 3-4: Code cleanup (verwijder award_xp calls)
- Week 5-6: Database cleanup (verwijder tabellen)

**Aanbevolen als**: < 10 users met XP data

---

### Optie B: Parallel Systeem

**Beschrijving**: Beide systemen naast elkaar draaien.

**Voordelen**:
- Geen data verlies
- Backward compatible
- Geleidelijke overgang mogelijk

**Nadelen**:
- Hoge complexiteit (2 systemen onderhouden)
- Verwarring voor users (als beide zichtbaar zijn)
- Dubbele maintenance overhead
- Niet aanbevolen voor dit scenario

**Aanbevolen als**: > 100 users met actieve XP data

---

### Optie C: Migration Path (Aanbevolen)

**Beschrijving**: Migreer XP/badges naar rollen equivalenten.

**Voordelen**:
- Users behouden "progress" (als data bestaat)
- Schone overgang naar nieuw systeem
- Geen data verlies

**Nadelen**:
- Mapping kan arbitrair zijn
- Vereist migration script
- Vereist dat `user_roles` tabel eerst bestaat

**Migration Mapping Rules** (voorstel):

```python
# Primary Role Mapping
if total_xp >= 500 OR current_streak_days >= 7:
    primary_role = "mahalleli"
elif total_xp >= 100:
    primary_role = "yeni_gelen"  # Upgrade from default
else:
    primary_role = "yeni_gelen"  # Default for new users

# Secondary Role Mapping (from badges)
if badge "super_supporter":
    secondary_role = "anlatıcı"
elif badge "poll_master":
    secondary_role = "ses_veren"
elif badge "explorer_city":
    # City-specific role, could be primary for that city
    primary_role = "mahalleli"  # city-specific
```

**Timeline**:
- Week 1-2: Migration script ontwikkelen
- Week 3: Test op staging
- Week 4: Run op production (na user_roles tabel bestaat)
- Week 5-6: Deprecation warnings
- Week 7-12: Deprecation periode (6 maanden)
- Week 13+: Code cleanup

**Aanbevolen als**: 10-100 users met XP data

---

## 5. Aanbeveling & Beslissing

**Geschatte situatie** (op basis van feature flag status):
- Feature flag disabled → systeem niet actief
- Geen frontend integratie → users zien niets
- Waarschijnlijk < 10 users met XP data (mogelijk 0)

**BESLISSING**: **Optie A (Volledig Deprecate)** met korte deprecation periode

**Reden**:
1. Systeem is niet actief (feature flag disabled)
2. Geen user-facing impact (geen frontend integratie)
3. Lage data volume verwacht
4. Eenvoudigste migration path
5. Nieuw rol-gebaseerd systeem is fundamenteel anders (geen XP nodig)
6. Geen actieve users die het systeem gebruiken

**Migration Mapping Rules**: Niet van toepassing (Optie A gekozen)

**Timeline**:
- **Week 1-2**: Deprecation warnings toevoegen aan API endpoints
- **Week 3-4**: Code cleanup (verwijder `award_xp` calls uit endpoints)
- **Week 5-6**: Database cleanup (verwijder tabellen na deprecation periode)
- **Deprecation Periode**: 3 maanden (korter dan standaard 6 maanden omdat systeem niet actief is)

---

## 6. Volgende Stappen

1. **Database queries uitvoeren** om exacte data volume te bepalen
2. **Beslissing nemen** op basis van data volume:
   - < 10 users → Optie A (Deprecate)
   - 10-100 users → Optie C (Migration)
   - > 100 users → Optie C met extended timeline
3. **Implementeren** gekozen approach
4. **Documenteren** beslissing en implementatie

---

## 7. Database Schema Reference

**Bestaande Tabellen** (uit `028_gamification.sql`):

```sql
-- user_streaks
- user_id (PK, FK naar auth.users)
- total_xp (INTEGER, default 0)
- daily_xp (INTEGER, default 0, resets daily)
- daily_xp_cap (INTEGER, default 200)
- current_streak_days (INTEGER, default 0)
- longest_streak_days (INTEGER, default 0)
- last_active_at (TIMESTAMPTZ)
- last_xp_reset_at (TIMESTAMPTZ)

-- user_xp_log
- id (PK, BIGSERIAL)
- user_id (FK naar auth.users)
- client_id (UUID, voor anonymous users)
- xp_amount (INTEGER)
- source (TEXT: 'check_in', 'reaction', 'note', etc.)
- source_id (BIGINT, reference naar source record)
- created_at (TIMESTAMPTZ)

-- user_badges
- id (PK, BIGSERIAL)
- user_id (FK naar auth.users)
- badge_type (ENUM: explorer_city, early_adopter, poll_master, etc.)
- city_key (TEXT, voor city-specific badges)
- earned_at (TIMESTAMPTZ)
- UNIQUE(user_id, badge_type, city_key)
```

---

**Laatste Update**: 2025-01-XX  
**Status**: Analyse compleet, wacht op database queries voor finale beslissing

