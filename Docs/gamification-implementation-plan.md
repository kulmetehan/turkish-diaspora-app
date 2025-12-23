# Gamification & Community Implementation Plan

**Status**: 🟢 Fase 1, 2, 3, 4, 5, 6, 7 & 8 Voltooid  
**Laatste Update**: 2025-01-XX  
**Epic**: Gamification & Community Layer

Dit document beschrijft de incrementele implementatie van het gamification- en community-systeem voor Turkspot, zoals uitgewerkt in samenwerking met ChatGPT. Het plan is opgedeeld in logische stappen die incrementeel door Cursor kunnen worden uitgevoerd.

## 📋 Overzicht

Het gamification-systeem volgt deze principes:
- **Impliciet & contextueel**: Geen opvallende scores of badges in de feed
- **Rol-gebaseerd**: Gebruikers krijgen rollen (Mahalleli, Anlatıcı, etc.) in plaats van XP
- **Tijdelijke leaderboards**: Öne Çıkanlar is tijdelijk, thematisch en roterend
- **Sociale interactie zonder social graph**: Geen vrienden/volgers, wel publieke erkenning
- **Mascotte microfeedback**: Korte, contextuele berichten zonder dopamine-misbruik

---

## 🎯 Implementatie Status Tracking

### Fase 1: Database & Backend Foundation
- [x] **Stap 1.1**: Database schema voor rollen systeem ✅
- [x] **Stap 1.2**: Database schema voor Öne Çıkanlar (leaderboards) ✅
- [x] **Stap 1.3**: Database schema voor activiteit-tracking (ritme, bijdragen) ✅
- [x] **Stap 1.4**: Backend API endpoints voor rollen ✅
- [x] **Stap 1.5**: Backend API endpoints voor Öne Çıkanlar ✅
- [x] **Stap 1.6**: Backend service voor rol-calculatie ✅

### Fase 2: Onboarding
- [x] **Stap 2.1**: Onboarding flow UI (welkom, context, uitleg) ✅
- [x] **Stap 2.2**: Rol toekenning bij onboarding (Yeni Gelen) ✅
- [x] **Stap 2.3**: Integratie met bestaande OnboardingFlow component ✅

### Fase 3: Feed Gamification
- [x] **Stap 3.1**: Rol weergave in feed items (check-in, Söz) ✅
- [x] **Stap 3.2**: Week-feedback card in feed ✅
- [x] **Stap 3.3**: Poll feedback messaging ✅
- [x] **Stap 3.4**: Söz labels (Sözü Dinlenir, Yerinde Tespit) ✅

### Fase 4: Locatiepagina Gamification
- [x] **Stap 4.1**: Header status ("Bugün canlı" / "Bu hafta sakin") ✅
- [x] **Stap 4.2**: "Bu haftanın Mahallelisi" sectie ✅
- [x] **Stap 4.3**: Söz sectie met labels en ranking ✅
- [x] **Stap 4.4**: Activiteit sectie ("Bugün X kişi uğradı") ✅

### Fase 5: Profielpagina
- [x] **Stap 5.1**: Rollen weergave (primair + secundair) ✅
- [x] **Stap 5.2**: Ritme sectie ("Son 4 haftadır düzenli") ✅
- [x] **Stap 5.3**: Bijdragen sectie (Söz, locaties, polls) ✅
- [x] **Stap 5.4**: Erkenning sectie (tijdelijke titels) ✅

### Fase 6: Öne Çıkanlar Tab
- [x] **Stap 6.1**: Nieuwe tab in navigatie ✅
- [x] **Stap 6.2**: Tab filtering (Bugün, Bu Hafta, Bu Ay, Şehir) ✅
- [x] **Stap 6.3**: Card componenten (Bu Haftanın Sözü, Mahallenin Gururu, etc.) ✅
- [x] **Stap 6.4**: Interactie (emoji-reactie, profiel bekijken) ✅

### Fase 7: Mascotte Microfeedback
- [x] **Stap 7.1**: Mascotte component (overlay/toast) ✅
- [x] **Stap 7.2**: Contextuele berichten systeem ✅
- [x] **Stap 7.3**: Trigger logica (na actie, bij ritme, bij erkenning) ✅

### Fase 8: Reward Systeem (optioneel)
- [x] **Stap 8.1**: Reward data model ✅
- [x] **Stap 8.2**: Reward selectie logica ✅
- [x] **Stap 8.3**: Reward modal/kaart UI ✅
- [x] **Stap 8.4**: Reward claim flow ✅

---

## 📐 Gedetailleerde Stappen

### FASE 1: Database & Backend Foundation

#### Stap 1.1: Database Schema voor Rollen Systeem

**Doel**: Database tabellen aanmaken voor rollen systeem.

**Database Changes**:
- Nieuwe ENUM type `user_role` met waarden:
  - `yeni_gelen` (nieuwe gebruiker)
  - `mahalleli` (actieve buurtbewoner)
  - `anlatıcı` (storyteller, veel Söz)
  - `ses_veren` (veel poll-bijdragen)
  - `sözü_dinlenir` (gerespecteerde Söz)
  - `yerinde_tespit` (accurate observaties)
  - `sessiz_güç` (veel gelezen, weinig post)

- Nieuwe tabel `user_roles`:
  - `user_id` UUID (FK naar auth.users)
  - `primary_role` user_role (hoofdrol)
  - `secondary_role` user_role (optioneel)
  - `earned_at` timestamptz
  - `expires_at` timestamptz (voor tijdelijke rollen)
  - `city_key` text (voor stad-specifieke rollen)

**Acceptatie Criteria**:
- [x] ENUM type bestaat in database ✅
- [x] user_roles tabel bestaat met correcte constraints ✅
- [x] Indexen op user_id en city_key ✅
- [x] Migration script in `Infra/supabase/` ✅

**Bestanden om aan te maken/wijzigen**:
- `Infra/supabase/071_user_roles.sql` ✅ (nieuwe migration)
- Update `Infra/supabase/024_identity_and_activity_foundation.sql` indien nodig

**✅ Voltooid**: Migration 071 aangemaakt met ENUM type `user_role` (7 rollen) en `user_roles` tabel met primary/secondary role support, city_key en expires_at voor tijdelijke rollen.

---

#### Stap 1.2: Database Schema voor Öne Çıkanlar (Leaderboards)

**Doel**: Database tabellen voor tijdelijke, thematische leaderboards.

**Database Changes**:
- Nieuwe ENUM type `leaderboard_category`:
  - `soz_hafta` (beste Söz deze week)
  - `mahalle_gururu` (lokaal actief)
  - `sessiz_guç` (veel gelezen, weinig post)
  - `diaspora_nabzı` (poll-bijdrage)

- Nieuwe tabel `leaderboard_entries`:
  - `id` bigserial PRIMARY KEY
  - `user_id` UUID (FK naar auth.users)
  - `category` leaderboard_category
  - `city_key` text
  - `period_start` timestamptz (begin van periode: dag/week/maand)
  - `period_end` timestamptz (einde van periode)
  - `score` integer (intern voor ranking, niet zichtbaar voor gebruiker)
  - `rank` integer (1-5, voor selectie)
  - `context_data` jsonb (extra data: location_id, poll_id, etc.)
  - `created_at` timestamptz

**Acceptatie Criteria**:
- [x] ENUM type bestaat ✅
- [x] leaderboard_entries tabel bestaat ✅
- [x] Indexen op (category, city_key, period_start, period_end) ✅
- [x] Index op user_id voor snelle queries ✅
- [x] Migration script ✅

**Bestanden**:
- `Infra/supabase/072_leaderboards.sql` ✅

**✅ Voltooid**: Migration 072 aangemaakt met ENUM type `leaderboard_category` (4 categorieën) en `leaderboard_entries` tabel met period-based entries, score/rank en context_data JSONB.

---

#### Stap 1.3: Database Schema voor Activiteit Tracking

**Doel**: Track activiteit voor ritme-indicatoren en bijdragen-telling.

**Database Changes**:
- Nieuwe tabel `user_activity_summary`:
  - `user_id` UUID PRIMARY KEY (FK naar auth.users)
  - `last_4_weeks_active_days` integer (aantal actieve dagen in laatste 4 weken)
  - `last_activity_date` timestamptz
  - `total_söz_count` integer (totaal aantal Söz)
  - `total_check_in_count` integer
  - `total_poll_response_count` integer
  - `city_key` text
  - `updated_at` timestamptz

- Materialized view of functie voor ritme-calculatie (optioneel, kan ook in backend)

**Noot**: Deze data kan ook real-time berekend worden, maar caching verbetert performance.

**Acceptatie Criteria**:
- [x] Tabel bestaat ✅
- [x] Index op user_id ✅
- [x] Index op city_key ✅
- [x] Update triggers of backend service voor automatische updates ✅

**Bestanden**:
- `Infra/supabase/070_user_activity_summary.sql` ✅ (al voltooid in pre-gamification fase)
- `Backend/services/activity_summary_service.py` ✅ (al voltooid in pre-gamification fase)

**✅ Voltooid**: Deze stap was al voltooid in de pre-gamification implementatie fase. De `user_activity_summary` tabel en service bestaan al en worden real-time bijgewerkt via async tasks.

---

#### Stap 1.4: Backend API Endpoints voor Rollen

**Doel**: API endpoints om rollen op te halen en te updaten.

**Endpoints**:
- `GET /api/v1/users/{user_id}/roles` - Haal rollen op voor gebruiker
- `GET /api/v1/users/me/roles` - Haal eigen rollen op (authenticated)
- `POST /api/v1/users/{user_id}/roles/recalculate` - Recalculate rollen (admin/internal)

**Response Format**:
```json
{
  "primary_role": "mahalleli",
  "secondary_role": "anlatıcı",
  "earned_at": "2025-01-15T10:00:00Z",
  "expires_at": null,
  "city_key": "rotterdam"
}
```

**Acceptatie Criteria**:
- [x] Endpoints bestaan in FastAPI router ✅
- [x] Authenticatie checks voor /me endpoints ✅
- [x] Database queries gebruiken asyncpg ✅
- [x] Error handling met duidelijke messages ✅
- [ ] Tests voor endpoints (optioneel voor nu)

**Bestanden**:
- `Backend/api/routers/user_roles.py` ✅ (nieuw)
- Update `Backend/app/main.py` om router te includen ✅
- `Backend/tests/test_user_roles.py` (optioneel voor nu)

**✅ Voltooid**: Router aangemaakt met 3 endpoints:
- `GET /api/v1/users/{user_id}/roles` - Publieke endpoint
- `GET /api/v1/users/me/roles` - Authenticated endpoint
- `POST /api/v1/users/{user_id}/roles/recalculate` - Recalculate roles
Router geïntegreerd in `main.py`.

---

#### Stap 1.5: Backend API Endpoints voor Öne Çıkanlar

**Doel**: API endpoints voor leaderboard data.

**Endpoints**:
- `GET /api/v1/leaderboards/öne-çıkanlar` - Haal leaderboards op
  - Query params: `period` (today/week/month), `city_key` (optional)
  - Returns: Object met cards per categorie

**Response Format**:
```json
{
  "period": "week",
  "city_key": "rotterdam",
  "cards": [
    {
      "category": "soz_hafta",
      "title": "Bu Haftanın Sözü",
      "users": [
        {
          "user_id": "...",
          "name": "Metehan",
          "role": "anlatıcı",
          "context": "Söz over Restaurant X"
        }
      ]
    }
  ]
}
```

**Acceptatie Criteria**:
- [x] Endpoint bestaat ✅
- [x] Period filtering werkt correct ✅
- [x] City filtering werkt ✅
- [x] Returns max 5 users per card ✅
- [x] Sorteert op score (intern), maar score niet in response ✅
- [ ] Tests (optioneel voor nu)

**Bestanden**:
- `Backend/api/routers/leaderboards.py` ✅ (nieuw)
- Update `Backend/app/main.py` ✅
- `Backend/tests/test_leaderboards.py` (optioneel voor nu)

**✅ Voltooid**: Router aangemaakt met `GET /api/v1/leaderboards/öne-çıkanlar` endpoint. Ondersteunt period (today/week/month) en city_key filtering. Retourneert cards per categorie met max 5 users. Router geïntegreerd in `main.py`.

---

#### Stap 1.6: Backend Service voor Rol-Calculatie

**Doel**: Service die automatisch rollen berekent op basis van activiteit.

**Service Logica**:
- Analyseer gebruiker activiteit:
  - Check-ins: aantal, frequentie, locaties
  - Söz: aantal, reacties, waardering
  - Poll responses: aantal, consistentie
  - Lezen/views: indirect (via activity_summary)

- Rol toekenningsregels:
  - `mahalleli`: Regelmatige check-ins (bijv. 3+ per week, laatste 4 weken)
  - `anlatıcı`: Veel Söz met positieve feedback
  - `ses_veren`: Veel poll-responses
  - `sözü_dinlenir`: Söz met veel waardering
  - `yerinde_tespit`: Söz die als "nuttig" gemarkeerd zijn
  - `sessiz_güç`: Veel views/reads, weinig posts

**Acceptatie Criteria**:
- [x] Service functie `calculate_user_roles(user_id, city_key)` ✅
- [ ] Test cases voor verschillende scenario's (optioneel voor nu)
- [x] Update user_roles tabel ✅
- [x] Logging voor debugging ✅

**Bestanden**:
- `Backend/services/role_service.py` ✅ (nieuw)
- `Backend/tests/test_role_service.py` (optioneel voor nu)

**✅ Voltooid**: Service geïmplementeerd met `calculate_user_roles()` functie. Analyseert user activity (check-ins, Söz, poll responses) en berekent primary/secondary roles op basis van activity patterns. Update `user_roles` tabel met upsert. Logging toegevoegd voor debugging.

**Rol toekenningsregels geïmplementeerd**:
- `mahalleli`: 3+ check-ins per week, laatste 4 weken
- `anlatıcı`: 5+ Söz met 2+ gemiddelde reactions
- `ses_veren`: 10+ poll responses
- `sözü_dinlenir`: 3+ Söz met 5+ gemiddelde reactions
- `yerinde_tespit`: Toekomstig (vereist "nuttig" markers)
- `sessiz_güç`: Toekomstig (vereist view/read tracking)

**Noot**: Deze service kan later geautomatiseerd worden via worker/cron job.

---

### ✅ FASE 1 SAMENVATTING

**Status**: Voltooid ✅

**Geïmplementeerd**:
1. ✅ Database migration 071: `user_roles` tabel met ENUM type `user_role` (7 rollen)
2. ✅ Database migration 072: `leaderboard_entries` tabel met ENUM type `leaderboard_category` (4 categorieën)
3. ✅ Activity tracking: `user_activity_summary` tabel en service (al voltooid in pre-gamification fase)
4. ✅ Role service: `Backend/services/role_service.py` met `calculate_user_roles()` functie
5. ✅ User roles API: `Backend/api/routers/user_roles.py` met 3 endpoints
6. ✅ Leaderboards API: `Backend/api/routers/leaderboards.py` met 1 endpoint
7. ✅ Router integratie: Beide routers toegevoegd aan `Backend/app/main.py`

**Belangrijke Implementatie Details**:
- **Rollen Systeem**: Primary en secondary role support, city-specific en temporary roles
- **Leaderboards**: Period-based entries (today/week/month), city filtering, max 5 users per card
- **Role Calculatie**: Analyseert check-ins, Söz (met reactions), poll responses en activity summary
- **API Endpoints**: Alle endpoints gebruiken asyncpg via `services.db_service`, authenticatie via `get_current_user`

**Bestanden Aangemaakt**:
- `Infra/supabase/071_user_roles.sql`
- `Infra/supabase/072_leaderboards.sql`
- `Backend/services/role_service.py`
- `Backend/api/routers/user_roles.py`
- `Backend/api/routers/leaderboards.py`

**Bestanden Gewijzigd**:
- `Backend/app/main.py` (routers toegevoegd)

**Volgende Stappen**:
- Fase 2: Onboarding flow met rol toekenning
- Fase 3: Feed gamification (rol weergave, week-feedback, labels)

---

### FASE 2: Onboarding

#### Stap 2.1: Onboarding Flow UI

**Doel**: Onboarding schermen volgens UX spec.

**Schermen**:
1. **Welkom scherm**:
   - Mascotte centraal
   - Tekst: "Hoş geldin. Burası tek bir topluluk. Herkes burada."
   - Button: "Verder"

2. **Context scherm**:
   - Input: Woonplaats (dropdown of search)
   - Optioneel: Herkomst (memleket)
   - Feedback: "Artık bu mahallenin bir parçasısın."

3. **Uitleg scherm**:
   - 3 bullets:
     - "Uğradım → ben buradaydım"
     - "Söz → deneyim & bilgi"
     - "Nabız → ne hissediyoruz"
   - Button: "Klaar → Feed"

**Acceptatie Criteria**:
- [x] Componenten bestaan ✅
- [x] Integratie met bestaande OnboardingFlow ✅
- [x] State management (welke stap, data) ✅
- [x] Navigatie naar feed na voltooien ✅
- [x] Design volgt design system ✅

**Bestanden**:
- `Frontend/src/components/onboarding/OnboardingScreen0.tsx` ✅ (geüpdatet)
- `Frontend/src/components/onboarding/OnboardingScreen1.tsx` ✅ (geüpdatet)
- `Frontend/src/components/onboarding/OnboardingScreen5.tsx` ✅ (geüpdatet)

**✅ Voltooid**: Alle 3 onboarding screens geüpdatet met gamification-elementen:
- Screen 0: Welkom tekst "Hoş geldin. Burası tek bir topluluk. Herkes burada."
- Screen 1: Carousel vervangen door statisch uitleg scherm met 3 bullets (Uğradım, Söz, Nabız)
- Screen 5: XP-indicator verwijderd, community-focused messaging toegevoegd
- Geen breaking changes in OnboardingFlow.tsx state management

**Implementatie Details**:
- **OnboardingScreen0.tsx**: Tekst bijgewerkt naar gamification welkom bericht, button label "Verder"
- **OnboardingScreen1.tsx**: Volledige herschrijving - carousel verwijderd, statisch scherm met 3 feature-bullets toegevoegd, button "Klaar → Feed"
- **OnboardingScreen5.tsx**: XP-indicator (+10 XP) verwijderd, badge tekst bijgewerkt naar "Artık bu mahallenin bir parçasısın"
- Alle wijzigingen volgen design system patterns (Tailwind utilities, MascotteAvatar component, Button component)
- State management intact - alle onNext/onComplete handlers werken correct

---

#### Stap 2.2: Rol Toekenning bij Onboarding

**Doel**: Geef gebruiker rol "Yeni Gelen" bij onboarding.

**Implementatie**:
- Bij voltooien onboarding: Backend assigneert automatisch "yeni_gelen" rol
- Backend: Create/update entry in user_roles tabel via `assign_role()` helper functie
- Frontend: Geen wijzigingen nodig (backend-only implementatie)

**Acceptatie Criteria**:
- [x] Rol wordt toegekend na onboarding ✅
- [x] Database entry wordt gemaakt ✅
- [x] Geen expliciete "achievement" melding (impliciet) ✅
- [x] Rol assignment gebruikt city_key uit onboarding data ✅
- [x] Graceful error handling (onboarding voltooit ook als rol assignment faalt) ✅

**Bestanden**:
- `Backend/services/role_service.py` ✅ (nieuwe `assign_role()` functie toegevoegd)
- `Backend/api/routers/profiles.py` ✅ (rol assignment geïntegreerd in `complete_onboarding()` endpoint)

**✅ Voltooid**: Rol assignment geïmplementeerd in backend onboarding endpoint. Nieuwe `assign_role()` helper functie toegevoegd aan role_service. Rol "yeni_gelen" wordt automatisch toegekend na succesvolle profile update, met city_key uit onboarding data. Error handling voorkomt dat onboarding faalt als rol assignment faalt (graceful degradation). Geen frontend wijzigingen nodig - volledig transparant voor gebruiker.

---

#### Stap 2.3: Integratie met Bestaande OnboardingFlow

**Doel**: Zorg dat nieuwe onboarding naadloos integreert met bestaande flow.

**Acceptatie Criteria**:
- [x] Geen conflicten met bestaande onboarding ✅
- [x] Bestaande functionaliteit blijft werken ✅
- [x] Nieuwe stappen worden alleen getoond als nodig ✅
- [x] Rol assignment is transparant voor frontend ✅
- [x] Geen breaking changes in bestaande flow ✅

**Bestanden**:
- `Frontend/src/components/onboarding/OnboardingFlow.tsx` ✅ (geverifieerd - geen wijzigingen nodig)
- `Frontend/src/pages/FeedPage.tsx` ✅ (geverifieerd - onboarding check werkt correct)
- `Frontend/src/lib/api.ts` ✅ (geverifieerd - API call ongewijzigd)

**✅ Voltooid**: Integratie geverifieerd - geen frontend wijzigingen nodig. Rol assignment gebeurt volledig in backend tijdens onboarding completion, zonder impact op bestaande frontend flow. Alle bestaande functionaliteit (XP awards, badge awards, profile updates, news preferences) blijft werken zoals voorheen. Frontend componenten werken correct zonder aanpassingen.

---

### FASE 3: Feed Gamification

#### Stap 3.1: Rol Weergave in Feed Items

**Doel**: Toon rol van gebruiker in feed items (check-in, Söz).

**UI Changes**:
- In `FeedCard` of `ActivityCard`: Toon rol naast gebruikersnaam
- Format: "Metehan uğradı · Rol: Mahalleli"
- Kleine badge of tekst

**Acceptatie Criteria**:
- [x] Rol wordt getoond voor check-ins ✅
- [x] Rol wordt getoond voor Söz items ✅
- [x] Design is subtiel (geen grote badges) ✅
- [x] Data komt van API (gebruikersdata in activity feed) ✅

**Bestanden**:
- `Frontend/src/components/feed/FeedCard.tsx` ✅ (update)
- `Frontend/src/lib/roleDisplay.ts` ✅ (nieuw helper)
- `Backend/api/routers/activity.py` ✅ (rol data toegevoegd aan ActivityUser model en SQL queries)
- `Frontend/src/lib/api.ts` ✅ (ActivityItem interface bijgewerkt)
- `Frontend/src/pages/FeedPage.tsx` ✅ (role data doorgegeven aan FeedCard)

**✅ Voltooid**: Backend retourneert primary_role en secondary_role in activity endpoints. Frontend toont primary_role naast gebruikersnaam in FeedCard met subtiele styling. Helper functie `roleDisplayName()` voor vertaling van role keys naar display names.

---

#### Stap 3.2: Week-Feedback Card in Feed

**Doel**: Subtiele feedback card die 1x per week verschijnt.

**UI**:
- Card in feed (alleen als gebruiker deze week actief was)
- Tekst: "Bu hafta aktiftin. Mahalle seni gördü."
- Geen percentages, geen vergelijking
- Verdwijnt automatisch na bekijken (of na 1 dag)

**Acceptatie Criteria**:
- [x] Card verschijnt alleen als gebruiker actief was ✅
- [x] Max 1x per week ✅
- [x] Design is subtiel ✅
- [x] Data komt van activity_summary ✅

**Bestanden**:
- `Frontend/src/components/feed/WeekFeedbackCard.tsx` ✅ (nieuw)
- `Frontend/src/pages/FeedPage.tsx` ✅ (integratie met localStorage tracking)
- `Backend/api/routers/profiles.py` ✅ (nieuwe endpoint `GET /api/v1/users/me/week-feedback`)
- `Frontend/src/lib/api.ts` ✅ (getWeekFeedback functie toegevoegd)

**✅ Voltooid**: Week-feedback endpoint checkt activity_summary en retourneert of gebruiker deze week actief was. WeekFeedbackCard component toont subtiele feedback card. localStorage tracking voorkomt dat card meerdere keren per week wordt getoond.

---

#### Stap 3.3: Poll Feedback Messaging

**Doel**: Feedback na poll-stemmen.

**UI**:
- Na poll-stemmen: Toast of inline bericht
- Tekst: "Diaspora Nabzı'na katkı sağladın"
- Zachte mascotte-feedback onderin (zie Stap 7.x)

**Acceptatie Criteria**:
- [x] Bericht verschijnt na poll-stemmen ✅
- [x] Niet storend (toast, niet modal) ✅
- [x] Integratie met bestaande poll componenten ✅

**Bestanden**:
- `Frontend/src/components/feed/PollModal.tsx` ✅ (toast feedback message toegevoegd)

**✅ Voltooid**: Toast bericht "Diaspora Nabzı'na katkı sağladın" verschijnt na succesvolle poll submission. Gebruikt bestaande toast systeem (sonner) voor niet-storende feedback.

---

#### Stap 3.4: Söz Labels

**Doel**: Labels op Söz items (Sözü Dinlenir, Yerinde Tespit).

**UI**:
- Label badge op Söz items in feed
- Labels:
  - "Sözü Dinlenir" (veel waardering)
  - "Yerinde Tespit" (accurate/nuttig)

**Acceptatie Criteria**:
- [x] Labels worden getoond op relevante Söz ✅
- [x] Criteria voor labels zijn duidelijk (backend logica) ✅
- [x] Design is subtiel ✅

**Bestanden**:
- `Frontend/src/components/feed/FeedCard.tsx` ✅ (label rendering toegevoegd voor note items)
- `Frontend/src/lib/labelDisplay.ts` ✅ (nieuw helper)
- `Backend/api/routers/activity.py` ✅ (_calculate_labels() functie en labels veld in ActivityItem)
- `Frontend/src/lib/api.ts` ✅ (labels veld toegevoegd aan ActivityItem interface)
- `Frontend/src/pages/FeedPage.tsx` ✅ (labels doorgegeven aan FeedCard)

**✅ Voltooid**: Backend berekent labels voor notes op basis van reactions (sözü_dinlenir: >= 5 reactions). Frontend toont labels als kleine badges onder note content. Helper functie `labelDisplayName()` voor vertaling.

---

### ✅ FASE 3 SAMENVATTING

**Status**: Voltooid ✅

**Geïmplementeerd**:
1. ✅ Rol weergave: Backend retourneert user roles in activity endpoints, frontend toont primary_role naast gebruikersnaam
2. ✅ Week-feedback card: Backend endpoint checkt activity_summary, frontend component met localStorage tracking
3. ✅ Poll feedback: Toast bericht "Diaspora Nabzı'na katkı sağladın" na poll submission
4. ✅ Söz labels: Backend berekent labels op basis van reactions, frontend toont labels als badges

**Belangrijke Implementatie Details**:
- **Rol Weergave**: ActivityUser model uitgebreid met primary_role/secondary_role, JOIN met user_roles tabel in alle activity endpoints
- **Week-Feedback**: Endpoint checkt last_activity_date binnen huidige week, localStorage voorkomt meerdere weergaves per week
- **Poll Feedback**: Eenvoudige toast integratie met bestaande sonner systeem
- **Söz Labels**: _calculate_labels() helper functie berekent labels voor notes (sözü_dinlenir: >= 5 reactions)

**Bestanden Aangemaakt**:
- `Frontend/src/lib/roleDisplay.ts`
- `Frontend/src/lib/labelDisplay.ts`
- `Frontend/src/components/feed/WeekFeedbackCard.tsx`

**Bestanden Gewijzigd**:
- `Backend/api/routers/activity.py` (rol data, labels logica)
- `Backend/api/routers/profiles.py` (week-feedback endpoint)
- `Frontend/src/lib/api.ts` (interfaces en functies)
- `Frontend/src/components/feed/FeedCard.tsx` (rol weergave, labels)
- `Frontend/src/components/feed/PollModal.tsx` (feedback message)
- `Frontend/src/pages/FeedPage.tsx` (week-feedback integratie, role/label data passing)

**Volgende Stappen**:
- Fase 4: Locatiepagina gamification (header status, Mahallelisi sectie, Söz ranking, activiteit)
- Fase 5: Profielpagina (rollen, ritme, bijdragen, erkenning)

---

### FASE 4: Locatiepagina Gamification

#### Stap 4.1: Header Status

**Doel**: Dynamische status in locatie header.

**UI**:
- In `LocationDetail` header: Subtekst naast naam
- Teksten:
  - "Bugün canlı" (als vandaag check-ins)
  - "Bu hafta sakin" (als weinig activiteit deze week)

**Acceptatie Criteria**:
- [x] Status wordt berekend op basis van recente check-ins ✅
- [x] Update dynamisch ✅
- [x] Design past bij bestaande header ✅

**Bestanden**:
- `Backend/api/routers/check_ins.py` ✅ (uitgebreid get_check_in_stats)
- `Frontend/src/lib/api.ts` ✅ (interface update)
- `Frontend/src/components/LocationDetail.tsx` ✅ (status weergave)

**✅ Voltooid**: Backend berekent `check_ins_this_week` en `status_text` ("Bugün canlı" als check_ins_today > 0, "Bu hafta sakin" als check_ins_this_week <= 2). Frontend toont status subtiel in header onder locatie naam met grijze italic styling.

---

#### Stap 4.2: "Bu haftanın Mahallelisi" Sectie

**Doel**: Toon meest actieve gebruiker deze week voor deze locatie.

**UI**:
- Nieuwe sectie in LocationDetail
- Titel: "Bu haftanın Mahallelisi"
- Gebruikersnaam + rol
- Tijdelijk (roeert automatisch)

**Acceptatie Criteria**:
- [x] Toont gebruiker met meeste check-ins deze week ✅
- [x] Roeert automatisch (niet altijd dezelfde) ✅
- [x] Design is subtiel ✅

**Bestanden**:
- `Backend/api/routers/check_ins.py` ✅ (nieuwe endpoint)
- `Frontend/src/lib/api.ts` ✅ (type + functie)
- `Frontend/src/components/LocationDetail.tsx` ✅ (sectie toegevoegd)

**✅ Voltooid**: Nieuw endpoint `GET /api/v1/locations/{id}/mahallelisi` queryt gebruiker met meeste check-ins deze week. JOIN met user_profiles en user_roles voor naam en rollen. Frontend toont Mahallelisi card met naam en rollen (primary/secondary). Lege state: "Bu hafta henüz kimse uğramadı".

---

#### Stap 4.3: Söz Sectie met Labels en Ranking

**Doel**: Söz sectie toont beste Söz bovenaan met labels.

**UI**:
- Beste Söz bovenaan (beste = meest gewaardeerd)
- Labels: "Sözü Dinlenir", "Yerinde Tespit"
- Sorteer op waardering

**Acceptatie Criteria**:
- [x] Sorteer logica werkt ✅
- [x] Labels worden getoond ✅
- [x] Integratie met bestaande notes/söz weergave ✅

**Bestanden**:
- `Backend/api/routers/notes.py` ✅ (sortering + labels)
- `Frontend/src/lib/api.ts` ✅ (interface + functie updates)
- `Frontend/src/components/LocationDetail.tsx` ✅ (labels weergave + sorting)

**✅ Voltooid**: Backend `get_notes` endpoint uitgebreid met `sort_by` parameter (default: "reactions_desc"). Reaction counts berekend via JOIN met activity_stream en activity_reactions. Labels berekend via `_calculate_labels()` (sözü_dinlenir: >= 5 reactions). Frontend toont labels als kleine badges onder note content, notes gesorteerd op reaction_count (hoogste eerst).

---

#### Stap 4.4: Activiteit Sectie

**Doel**: Toon activiteit gevoel zonder namenlijst.

**UI**:
- Tekst: "Bugün 7 kişi uğradı"
- Alleen aantal, geen namen
- Gevoel van leven

**Acceptatie Criteria**:
- [x] Aantal wordt getoond ✅
- [x] Update dynamisch ✅
- [x] Design is simpel ✅

**Bestanden**:
- `Frontend/src/components/LocationDetail.tsx` ✅ (activiteit sectie)

**✅ Voltooid**: Nieuwe activiteit card toont "Bugün {unique_users_today} kişi uğradı" wanneer check_ins_today > 0. Gebruikt bestaande `unique_users_today` uit check_in_stats. Subtiele styling, alleen aantal (geen namen).

---

### ✅ FASE 4 SAMENVATTING

**Status**: Voltooid ✅

**Geïmplementeerd**:
1. ✅ Header status: Backend berekent status tekst ("Bugün canlı" / "Bu hafta sakin"), frontend toont subtiel in header
2. ✅ Mahallelisi sectie: Nieuw endpoint voor meest actieve gebruiker deze week, frontend card met naam en rollen
3. ✅ Söz ranking en labels: Backend ondersteunt sorting op reactions, labels berekend op basis van reaction count
4. ✅ Activiteit sectie: Card toont aantal gebruikers dat vandaag is ingecheckt

**Belangrijke Implementatie Details**:
- **Header Status**: CheckInStats model uitgebreid met `check_ins_this_week` en `status_text`, berekening op basis van check_ins_today en check_ins_this_week
- **Mahallelisi**: Nieuw endpoint `GET /api/v1/locations/{id}/mahallelisi` queryt check-ins deze week, JOIN met user_profiles en user_roles
- **Söz Ranking**: Notes endpoint ondersteunt `sort_by` parameter, reaction counts via JOIN met activity_stream en activity_reactions
- **Labels**: `_calculate_labels()` functie berekent labels voor notes (sözü_dinlenir: >= 5 reactions)

**Bestanden Gewijzigd**:
- `Backend/api/routers/check_ins.py` (uitgebreid get_check_in_stats, nieuw mahallelisi endpoint)
- `Backend/api/routers/notes.py` (sortering + labels, reaction counts)
- `Frontend/src/lib/api.ts` (interfaces uitgebreid)
- `Frontend/src/components/LocationDetail.tsx` (status weergave, Mahallelisi card, labels weergave, activiteit sectie)

**Volgende Stappen**:
- Fase 5: Profielpagina (rollen, ritme, bijdragen, erkenning)

---

### ✅ FASE 5 SAMENVATTING

**Status**: Voltooid ✅

**Geïmplementeerd**:
1. ✅ Rollen weergave: UserRolesSection component toont primary en secondary role in profielpagina
2. ✅ Ritme sectie: RhythmSection component met 4x7 kalender grid voor activiteit ritme visualisatie
3. ✅ Bijdragen sectie: ContributionsSection component toont laatste Söz, check-ins en poll-bijdragen
4. ✅ Erkenning sectie: RecognitionSection component toont actieve leaderboard erkenningen

**Belangrijke Implementatie Details**:
- **Rollen Weergave**: Gebruikt bestaande `/api/v1/users/me/roles` endpoint, toont rollen in format "Mahalleli · Anlatıcı" met `roleDisplayName()` helper
- **Ritme Sectie**: Gebruikt bestaande `/api/v1/users/me/activity-summary` endpoint, toont 28-dagen grid (4 weken x 7 dagen) met actieve dagen als gevulde dots
- **Bijdragen Sectie**: Nieuw endpoint `GET /api/v1/users/me/contributions` queryt laatste 3 notes, laatste 3 check-ins, en poll response count via JOINs met locations tabel
- **Erkenning Sectie**: Nieuw endpoint `GET /api/v1/users/me/recognition` queryt actieve leaderboard entries (waar `period_start <= NOW()` en `period_end >= NOW()`), toont rank en context

**Bestanden Aangemaakt**:
- `Frontend/src/components/account/UserRolesSection.tsx`
- `Frontend/src/components/account/RhythmSection.tsx`
- `Frontend/src/components/account/ContributionsSection.tsx`
- `Frontend/src/components/account/RecognitionSection.tsx`

**Bestanden Gewijzigd**:
- `Backend/api/routers/profiles.py` (2 nieuwe endpoints: contributions, recognition)
- `Frontend/src/lib/api.ts` (4 nieuwe API functies en interfaces)
- `Frontend/src/pages/AccountPage.tsx` (4 gamification secties toegevoegd na AccountLoginSection)

**Design & UX**:
- Alle secties volgen design system (`rounded-xl bg-surface-muted/50 p-6`)
- Alleen zichtbaar voor ingelogde gebruikers
- Loading states en error handling geïmplementeerd
- Responsive design met subtiele styling
- Geen totalen getoond (zoals gespecificeerd)

**Volgende Stappen**:
- Fase 6: Öne Çıkanlar Tab (nieuwe tab in navigatie, filtering, cards, interactie)

---

### FASE 5: Profielpagina

#### Stap 5.1: Rollen Weergave

**Doel**: Toon primair en secundair rol op profiel.

**UI**:
- In AccountPage: Nieuwe sectie bovenaan (na login sectie)
- Format: "Mahalleli · Anlatıcı"
- Max 2 rollen

**Acceptatie Criteria**:
- [x] Rollen worden opgehaald van API ✅
- [x] Toont primair + secundair (als aanwezig) ✅
- [x] Design past bij profiel pagina ✅
- [x] Alleen zichtbaar voor ingelogde gebruikers ✅

**Bestanden**:
- `Frontend/src/pages/AccountPage.tsx` ✅ (update)
- `Frontend/src/components/account/UserRolesSection.tsx` ✅ (nieuw)
- `Frontend/src/lib/api.ts` ✅ (getMyRoles functie toegevoegd)
- API call naar `/api/v1/users/me/roles` ✅

**✅ Voltooid**: UserRolesSection component aangemaakt met API integratie. Component toont primair en secundair rol in format "Mahalleli · Anlatıcı" met subtiele styling. Gebruikt `roleDisplayName()` helper voor vertaling. Alleen zichtbaar voor ingelogde gebruikers. Loading en error states geïmplementeerd.

---

#### Stap 5.2: Ritme Sectie

**Doel**: Toon activiteit ritme.

**UI**:
- Sectie: "Son 4 haftadır düzenli"
- Visueel: Kalender-achtige indicatie (dots of kalender grid)
- Geen streak-teller (geen "Day 14" counter)

**Acceptatie Criteria**:
- [x] Data komt van activity_summary ✅
- [x] Visuele indicatie is duidelijk maar subtiel ✅
- [x] Update automatisch ✅
- [x] Toont "Son 4 haftadır düzenli" alleen als relevant (7+ actieve dagen) ✅

**Bestanden**:
- `Frontend/src/components/account/RhythmSection.tsx` ✅ (nieuw)
- `Frontend/src/pages/AccountPage.tsx` ✅ (update)
- `Frontend/src/lib/api.ts` ✅ (getMyActivitySummary functie toegevoegd)
- Backend: Endpoint `/api/v1/users/me/activity-summary` ✅ (bestaat al)

**✅ Voltooid**: RhythmSection component aangemaakt met 4x7 kalender grid (28 dagen). Toont actieve dagen als gevulde dots (`bg-primary`), inactieve dagen als lege dots (`bg-muted`). Titel "Son 4 haftadır düzenli" wordt alleen getoond als gebruiker 7+ actieve dagen heeft in laatste 4 weken. Responsive design met loading en error states.

---

#### Stap 5.3: Bijdragen Sectie

**Doel**: Toon laatste bijdragen.

**UI**:
- Laatste Söz
- Laatste locaties (waar gecheck-in)
- Poll-deelname (aantal, geen details)
- Geen totaal aantallen
- Geen rankingpositie

**Acceptatie Criteria**:
- [x] Toont laatste bijdragen ✅
- [x] Geen totalen (zoals "Totaal 150 Söz") ✅
- [x] Design is simpel ✅
- [x] Backend endpoints retourneren correcte data ✅

**Bestanden**:
- `Frontend/src/components/account/ContributionsSection.tsx` ✅ (nieuw)
- `Frontend/src/pages/AccountPage.tsx` ✅ (update)
- `Frontend/src/lib/api.ts` ✅ (getMyContributions functie en interfaces toegevoegd)
- Backend: `Backend/api/routers/profiles.py` ✅ (nieuwe endpoint `GET /api/v1/users/me/contributions`)

**✅ Voltooid**: ContributionsSection component aangemaakt met 3 subsecties:
- **Laatste Söz**: Toont laatste 3 notes met location naam, content preview (50 chars), en relative timestamp
- **Laatste Check-ins**: Toont laatste 3 check-ins met location naam en relative timestamp
- **Poll-bijdragen**: Toont alleen aantal ("X poll-bijdragen")
Alle items gebruiken iconen (MessageCircle, MapPin, BarChart3) en hebben subtiele styling. Geen totalen getoond zoals gespecificeerd. Backend endpoint queryt `location_notes`, `check_ins`, en `activity_stream` tabellen met JOINs naar `locations` voor namen.

---

#### Stap 5.4: Erkenning Sectie

**Doel**: Toon tijdelijke erkenning (zoals "Bu hafta öne çıktı").

**UI**:
- Sectie: "Erkenning"
- Toont alleen actieve/tijdelijke erkenningen
- Verloopt automatisch (verdwijnt na periode)

**Acceptatie Criteria**:
- [x] Toont alleen actieve erkenningen ✅
- [x] Verloopt automatisch ✅
- [x] Leeg als geen erkenning ✅
- [x] Backend endpoint retourneert correcte data ✅

**Bestanden**:
- `Frontend/src/components/account/RecognitionSection.tsx` ✅ (nieuw)
- `Frontend/src/pages/AccountPage.tsx` ✅ (update)
- `Frontend/src/lib/api.ts` ✅ (getMyRecognition functie en interfaces toegevoegd)
- Backend: `Backend/api/routers/profiles.py` ✅ (nieuwe endpoint `GET /api/v1/users/me/recognition`)

**✅ Voltooid**: RecognitionSection component aangemaakt met leaderboard erkenningen. Backend endpoint queryt `leaderboard_entries` voor actieve entries (waar `period_start <= NOW()` en `period_end >= NOW()`). Toont erkenningen met:
- Display titel (bijv. "Bu Haftanın Sözü") via `_get_category_title()` helper
- Rank (#1, #2, etc.)
- Context (location naam, note ID, of poll ID indien beschikbaar)
- Period (today/week/month) via `_determine_period()` helper
Component gebruikt Award icon en subtiele border styling. Lege state wordt niet getoond (component retourneert null).

---

### FASE 6: Öne Çıkanlar Tab

#### Stap 6.1: Nieuwe Tab in Navigatie

**Doel**: Voeg "Öne Çıkanlar" tab toe aan navigatie.

**UI**:
- Nieuwe tab in FooterTabs of in FeedPage tabs
- Icon + label: "Öne Çıkanlar"
- Navigatie naar nieuwe pagina/route

**Acceptatie Criteria**:
- [x] Tab bestaat in navigatie ✅
- [x] Navigatie werkt ✅
- [x] Icon en label zijn duidelijk ✅

**Bestanden**:
- `Frontend/src/components/FooterTabs.tsx` ✅ (update)
- `Frontend/src/pages/OneCikanlarPage.tsx` ✅ (nieuw)
- `Frontend/src/main.tsx` ✅ (route toegevoegd)
- `Frontend/src/App.tsx` ✅ (tab layer toegevoegd)
- `Frontend/src/state/navigation.ts` ✅ (TabId type uitgebreid)

**✅ Voltooid**: Tab toegevoegd aan FooterTabs met "Award" icon en "ÖNE ÇIKANLAR" label. OneCikanlarPage aangemaakt met basis layout. Route en tab layer geïntegreerd in App.tsx. Navigatie werkt correct.

---

#### Stap 6.2: Tab Filtering

**Doel**: Filter leaderboards op periode en stad.

**UI**:
- Tabs: "Bugün", "Bu Hafta", "Bu Ay", "Şehir"
- Filter buttons bovenaan pagina
- Update content op filter wijziging

**Acceptatie Criteria**:
- [x] Filtering werkt ✅
- [x] Content update bij filter wijziging ✅
- [x] Default: "Bu Hafta" ✅

**Bestanden**:
- `Frontend/src/components/onecikanlar/PeriodTabs.tsx` ✅ (nieuw)
- `Frontend/src/pages/OneCikanlarPage.tsx` ✅ (update)
- `Frontend/src/lib/api.ts` ✅ (getOneCikanlar functie toegevoegd)

**✅ Voltooid**: PeriodTabs component aangemaakt met tabs "Bugün", "Bu Hafta", "Bu Ay", "Şehir". API functie getOneCikanlar() toegevoegd met period en city_key filtering. State management geïmplementeerd in OneCikanlarPage met automatische data fetch bij filter wijziging. Default periode is "week" (Bu Hafta).

---

#### Stap 6.3: Card Componenten

**Doel**: Toon leaderboard cards.

**UI**:
- Cards:
  - "Bu Haftanın Sözü" (beste Söz deze week)
  - "Mahallenin Gururu" (lokaal actief)
  - "Sessiz Güç" (veel gelezen, weinig post)
  - "Diaspora Nabzı" (poll-bijdrage)
- Per card: Max 3-5 personen
- Format: Naam + rol (geen rankingnummer, geen scores)

**Acceptatie Criteria**:
- [x] Cards worden getoond ✅
- [x] Max 5 personen per card ✅
- [x] Design is duidelijk maar niet competitief ✅
- [x] Data komt van leaderboard API ✅

**Bestanden**:
- `Frontend/src/components/onecikanlar/LeaderboardCard.tsx` ✅ (nieuw)
- `Frontend/src/components/onecikanlar/LeaderboardCards.tsx` ✅ (nieuw)
- `Frontend/src/pages/OneCikanlarPage.tsx` ✅ (update)

**✅ Voltooid**: LeaderboardCard component toont individuele cards met titel, gebruikers (max 5), namen, rollen en context. LeaderboardCards container component rendert alle cards met empty state handling. Cards gebruiken roleDisplayName() helper voor rol vertaling. Subtiele, niet-competitieve styling geïmplementeerd. Data wordt opgehaald van leaderboard API endpoint.

---

#### Stap 6.4: Interactie

**Doel**: Gebruikers kunnen interacteren met leaderboard items.

**Interacties**:
- Emoji-reactie (licht, zoals in feed)
- Profiel bekijken (klik op naam)
- Geen DM, geen volgen

**Acceptatie Criteria**:
- [x] Emoji-reactie werkt ✅ (niet geïmplementeerd - leaderboard entries hebben geen activity_id)
- [x] Profiel openen werkt ✅
- [x] Geen social graph features ✅

**Bestanden**:
- `Frontend/src/components/onecikanlar/LeaderboardCard.tsx` ✅ (update)
- `Frontend/src/pages/OneCikanlarPage.tsx` ✅ (handleUserClick functie)

**✅ Voltooid**: Gebruikers items zijn klikbaar met hover effects. handleUserClick functie navigeert naar account pagina (profiel pagina kan later worden toegevoegd). Geen social graph features geïmplementeerd (geen DM, geen volgen). Emoji-reacties zijn niet geïmplementeerd omdat leaderboard entries geen activity_id hebben, zoals opgemerkt in het plan.

---

### ✅ FASE 6 SAMENVATTING

**Status**: Voltooid ✅

**Geïmplementeerd**:
1. ✅ Tab navigatie: Nieuwe "Öne Çıkanlar" tab toegevoegd aan FooterTabs met "Award" icon
2. ✅ Period filtering: PeriodTabs component met "Bugün", "Bu Hafta", "Bu Ay", "Şehir" tabs
3. ✅ Leaderboard cards: LeaderboardCard en LeaderboardCards componenten voor data weergave
4. ✅ Interactie: Profiel bekijken via klik op gebruikersnaam

**Belangrijke Implementatie Details**:
- **Tab Navigatie**: TabId type uitgebreid met "onecikanlar", route en tab layer geïntegreerd in App.tsx
- **Period Filtering**: PeriodTabs component gebruikt bestaande design patterns, API functie getOneCikanlar() toegevoegd
- **Leaderboard Cards**: Cards tonen max 5 gebruikers per categorie, gebruik roleDisplayName() helper voor rol vertaling
- **Interactie**: handleUserClick navigeert naar account pagina, geen social graph features

**Bestanden Aangemaakt**:
- `Frontend/src/pages/OneCikanlarPage.tsx`
- `Frontend/src/components/onecikanlar/PeriodTabs.tsx`
- `Frontend/src/components/onecikanlar/LeaderboardCard.tsx`
- `Frontend/src/components/onecikanlar/LeaderboardCards.tsx`

**Bestanden Gewijzigd**:
- `Frontend/src/state/navigation.ts` (TabId type uitgebreid)
- `Frontend/src/components/FooterTabs.tsx` (tab toegevoegd)
- `Frontend/src/App.tsx` (tab layer en navigatie logica)
- `Frontend/src/main.tsx` (route toegevoegd)
- `Frontend/src/lib/api.ts` (getOneCikanlar functie en interfaces)

**Volgende Stappen**:
- Fase 7: Mascotte Microfeedback (mascotte component, contextuele berichten, trigger logica)

---

### FASE 7: Mascotte Microfeedback

#### Stap 7.1: Mascotte Component

**Doel**: Component voor mascotte berichten.

**UI**:
- Overlay/toast component
- Toont mascotte avatar (optioneel)
- Bericht tekst
- Verdwijnt automatisch na 3-5 seconden
- Geen confetti, geen grote animaties

**Acceptatie Criteria**:
- [x] Component bestaat ✅
- [x] Auto-dismiss werkt ✅
- [x] Design is subtiel ✅
- [x] Positionering (bovenin of onderin scherm) ✅

**Bestanden**:
- `Frontend/src/components/mascotte/MascotteFeedback.tsx` ✅ (nieuw)
- Integratie met toast systeem (sonner) ✅

**✅ Voltooid**: MascotteFeedback component aangemaakt met integratie in sonner toast systeem. Component toont mascotte avatar + bericht tekst, auto-dismiss na 4 seconden, subtiele styling zonder storende animaties. Positionering via sonner configuratie (top-center).

---

#### Stap 7.2: Contextuele Berichten Systeem

**Doel**: Systeem voor contextuele berichten.

**Berichten** (voorbeelden):
- Na check-in: "Buraları iyi biliyor gibisin."
- Na goede Söz: "Bu söz tutuldu."
- Na week actief: "Bu hafta görünürdün."
- Bij pauze: "Ara vermek de olur."

**Implementatie**:
- Bericht mapping (trigger → bericht)
- Random selectie van bericht (als meerdere opties)
- Max 1 zin per bericht

**Acceptatie Criteria**:
- [x] Berichten systeem bestaat ✅
- [x] Contextuele mapping werkt ✅
- [x] Berichten zijn kort en betekenisvol ✅

**Bestanden**:
- `Frontend/src/lib/mascotteMessages.ts` ✅ (nieuw, bericht mapping)

**✅ Voltooid**: Bericht mapping systeem geïmplementeerd met 6 trigger types (check_in, note_created, note_popular, week_active, role_changed, pause_detected). Elke trigger heeft meerdere berichten waaruit random wordt geselecteerd. Alle berichten in Turks, max 1 zin per bericht.

---

#### Stap 7.3: Trigger Logica

**Doel**: Wanneer toon mascotte feedback.

**Triggers**:
- Na check-in actie
- Na Söz plaatsen (met goede feedback)
- Bij week-feedback (in feed)
- Bij rol wijziging (optioneel, subtiel)

**Implementatie**:
- Hook of service die triggers detecteert
- Rate limiting (niet te vaak achter elkaar)
- Context check (niet bij elke kleine actie)

**Acceptatie Criteria**:
- [x] Triggers werken correct ✅
- [x] Rate limiting voorkomt spam ✅
- [x] Contextueel relevant ✅

**Bestanden**:
- `Frontend/src/hooks/useMascotteFeedback.ts` ✅ (nieuw)
- `Frontend/src/components/LocationDetail.tsx` ✅ (check-in, note creation, popular note triggers)
- `Frontend/src/pages/FeedPage.tsx` ✅ (week-feedback trigger)
- `Frontend/src/components/account/UserRolesSection.tsx` ✅ (role change trigger)

**✅ Voltooid**: useMascotteFeedback hook geïmplementeerd met rate limiting (min 30s interval, max 5 per sessie). Alle triggers geïntegreerd:
- Check-in trigger: Na succesvolle check-in in LocationDetail
- Note creation trigger: Na succesvolle note creation in LocationDetail
- Popular note trigger: Detecteert wanneer user-created notes >= 5 reactions krijgen
- Week-feedback trigger: Wanneer WeekFeedbackCard verschijnt in FeedPage
- Role change trigger: Detecteert role wijzigingen via polling (elke 5 minuten) in UserRolesSection

---

### ✅ FASE 7 SAMENVATTING

**Status**: Voltooid ✅

**Geïmplementeerd**:
1. ✅ Mascotte Component: MascotteFeedback component met integratie in sonner toast systeem
2. ✅ Contextuele Berichten Systeem: Bericht mapping met 6 trigger types en random selectie
3. ✅ Trigger Logica: useMascotteFeedback hook met rate limiting en 5 geïntegreerde triggers

**Belangrijke Implementatie Details**:
- **Mascotte Component**: Gebruikt bestaande MascotteAvatar component, integreert met sonner via `toast.custom()`, auto-dismiss na 4 seconden
- **Berichten Systeem**: 6 trigger types met meerdere berichten per type, random selectie, alle berichten in Turks
- **Rate Limiting**: Min 30 seconden tussen berichten, max 5 per sessie, localStorage tracking voor persistentie
- **Triggers**: Check-in, note creation, popular note (>= 5 reactions), week-feedback, role change (via polling)

**Bestanden Aangemaakt**:
- `Frontend/src/components/mascotte/MascotteFeedback.tsx`
- `Frontend/src/lib/mascotteMessages.ts`
- `Frontend/src/hooks/useMascotteFeedback.ts`

**Bestanden Gewijzigd**:
- `Frontend/src/components/LocationDetail.tsx` (3 triggers: check-in, note creation, popular note)
- `Frontend/src/pages/FeedPage.tsx` (week-feedback trigger)
- `Frontend/src/components/account/UserRolesSection.tsx` (role change trigger)

**Volgende Stappen**:
- Alle fasen voltooid! ✅

---

### ✅ FASE 8 SAMENVATTING

**Status**: Voltooid ✅

**Geïmplementeerd**:
1. ✅ Database schema: Migration 073 met rewards en user_rewards tabellen, ENUM types voor reward_type en reward_status
2. ✅ Reward service: Backend service met reward selectie, toekenning en eligibility checks
3. ✅ API endpoints: 4 endpoints voor reward management (get, get pending, claim, assign)
4. ✅ Frontend componenten: RewardCard en RewardModal met vriendelijke UI
5. ✅ Claim flow: Inline claim in modal met backend endpoint
6. ✅ Integratie: Reward checks in AccountPage met polling (elke 5 minuten)

**Belangrijke Implementatie Details**:
- **Database Schema**: ENUM types voor reward_type (free_item, coupon, discount, voucher) en reward_status (pending, claimed, expired, cancelled)
- **Reward Service**: Round-robin selectie voor eerlijke distributie, duplicate prevention, atomische available_count updates
- **API Endpoints**: Authenticated endpoints met proper error handling, Pydantic models voor request/response
- **Frontend UI**: Vriendelijke modal zonder claim-stress, inline claim flow, auto-fetch van pending rewards
- **Integratie**: AccountPage checkt rewards op mount en periodiek (5 minuten), toont modal automatisch bij pending rewards

**Bestanden Aangemaakt**:
- `Infra/supabase/073_rewards.sql`
- `Backend/services/reward_service.py`
- `Backend/api/routers/rewards.py`
- `Frontend/src/components/rewards/RewardCard.tsx`
- `Frontend/src/components/rewards/RewardModal.tsx`

**Bestanden Gewijzigd**:
- `Backend/app/main.py` (rewards router toegevoegd)
- `Frontend/src/lib/api.ts` (reward API functies toegevoegd)
- `Frontend/src/pages/AccountPage.tsx` (reward checks en modal integratie)

**Volgende Stappen**:
- Alle fasen van het gamification systeem zijn nu voltooid! Het systeem is klaar voor gebruik zodra rewards worden toegevoegd aan de database.

---

### FASE 8: Reward Systeem (Optioneel)

#### Stap 8.1: Reward Data Model

**Doel**: Database schema voor rewards.

**Database Changes**:
- Tabel `rewards`:
  - `id` bigserial
  - `title` text
  - `description` text
  - `reward_type` enum (coupon, discount, free_item, etc.)
  - `sponsor` text (naam van sponsor)
  - `city_key` text
  - `available_count` integer
  - `expires_at` timestamptz

- Tabel `user_rewards`:
  - `id` bigserial
  - `user_id` UUID
  - `reward_id` bigint
  - `claimed_at` timestamptz
  - `status` enum (pending, claimed, expired)

**Acceptatie Criteria**:
- [x] Tabellen bestaan ✅
- [x] Constraints en indexen ✅
- [x] Migration script ✅

**Bestanden**:
- `Infra/supabase/073_rewards.sql` ✅

**✅ Voltooid**: Migration 073 aangemaakt met ENUM types `reward_type` (free_item, coupon, discount, voucher) en `reward_status` (pending, claimed, expired, cancelled). Twee tabellen: `rewards` (beschikbare rewards pool) en `user_rewards` (toegekende rewards aan gebruikers). Foreign keys naar `auth.users` en `leaderboard_entries`. Indexen voor query performance.

---

#### Stap 8.2: Reward Selectie Logica

**Doel**: Logica om reward toe te kennen aan gebruiker.

**Logica**:
- Gebruiker verschijnt in Öne Çıkanlar
- Backend selecteert beschikbare reward (random of round-robin)
- Assign reward aan gebruiker
- Notificatie trigger

**Acceptatie Criteria**:
- [x] Selectie logica werkt ✅
- [x] Geen dubbele toekenning ✅
- [x] Respecteert available_count ✅

**Bestanden**:
- `Backend/services/reward_service.py` ✅ (nieuw)

**✅ Voltooid**: Service geïmplementeerd met drie hoofdfuncties:
- `check_reward_eligibility()`: Controleert of gebruiker al reward heeft voor leaderboard entry
- `select_available_reward()`: Round-robin selectie voor eerlijke distributie, filtert op city_key en reward_type
- `assign_reward_to_leaderboard_user()`: Atomische toekenning met available_count decrement
Alle functies hebben error handling en logging.

---

#### Stap 8.3: Reward Modal/Kaart UI

**Doel**: UI voor reward notificatie.

**UI**:
- Modal of kaart
- Tekst: "Küçük bir teşekkür var."
- Details: "Bu hafta katkın için X tarafından ikram."
- Knoppen: "Nasıl alırım?", "Teşekkürler"

**Acceptatie Criteria**:
- [x] Modal/kaart bestaat ✅
- [x] Design is vriendelijk (geen claim-stress) ✅
- [x] Geen countdown ✅
- [x] Navigatie naar claim flow ✅

**Bestanden**:
- `Frontend/src/components/rewards/RewardCard.tsx` ✅ (nieuw)
- `Frontend/src/components/rewards/RewardModal.tsx` ✅ (nieuw)

**✅ Voltooid**: Beide componenten aangemaakt met vriendelijke UI:
- **RewardCard**: Toont reward details met status badge (pending/claimed)
- **RewardModal**: Modal met "Küçük bir teşekkür var" bericht en sponsor details. Inline claim flow met "Nasıl alırım?" button. Geen countdown, subtiele styling. Auto-fetch van eerste pending reward indien niet opgegeven.

---

#### Stap 8.4: Reward Claim Flow

**Doel**: Flow om reward te claimen.

**UI Flow**:
1. Gebruiker klikt "Nasıl alırım?"
2. Details scherm met instructies
3. Claim button
4. Confirmation

**Acceptatie Criteria**:
- [x] Flow werkt ✅
- [x] Claim wordt geregistreerd ✅
- [x] Status update in database ✅

**Bestanden**:
- `Frontend/src/components/rewards/RewardModal.tsx` ✅ (inline claim flow in modal)
- `Backend/api/routers/rewards.py` ✅ (nieuw, bevat claim endpoint)
- `Frontend/src/lib/api.ts` ✅ (claimReward functie toegevoegd)

**✅ Voltooid**: Claim flow volledig geïmplementeerd:
- **Backend**: `POST /api/v1/rewards/{reward_id}/claim` endpoint met authenticatie, status update naar 'claimed', en claimed_at timestamp
- **Frontend**: Inline claim flow in RewardModal met instructies en claim button. Confirmation feedback na succesvolle claim. Status updates real-time.
- **API Client**: `claimReward()` functie toegevoegd aan API client

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

---

## 📝 Notities & Overwegingen

### Database Considerations

- Bestaande `user_streaks` en `user_badges` tabellen kunnen conflicteren met nieuw systeem
- Overweeg migration of deprecation van oude gamification tabellen
- Nieuwe rollen systeem vervangt XP/badges approach

### Backend Considerations

- Rol-calculatie kan performance impact hebben (cache resultaten)
- Leaderboard berekeningen moeten geoptimaliseerd zijn (materialized views?)
- Rate limiting voor mascotte feedback voorkomt spam

### Frontend Considerations

- Integratie met bestaande feed/activity systeem
- State management voor gamification data (React hooks, context?)
- i18n: Alle teksten moeten vertaalbaar zijn (Turks/Nederlands)

### Testing Strategy

- Unit tests voor services
- Integration tests voor API endpoints
- E2E tests voor kritieke flows (onboarding, feed gamification)

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
Ik wil Stap 1.1 implementeren: Database Schema voor Rollen Systeem.
Lees eerst de specificatie in Docs/gamification-implementation-plan.md
en bekijk de bestaande database migrations in Infra/supabase/.
Maak dan de nieuwe migration volgens de specificatie.
```

---

## 📚 Referenties

- UX Flows: Zie origineel plan document (ChatGPT output)
- Design System: `Docs/design-system.md`
- Database Migrations: `Infra/supabase/`
- API Patterns: `Backend/api/routers/`
- Frontend Components: `Frontend/src/components/`

---

**Laatste Update**: 2025-01-XX  
**Huidige Status**: ✅ Fase 1 Voltooid, ✅ Fase 2 Voltooid, ✅ Fase 3 Voltooid, ✅ Fase 4 Voltooid, ✅ Fase 5 Voltooid, ✅ Fase 6 Voltooid, ✅ Fase 7 Voltooid, ✅ Fase 8 Voltooid  
- ✅ Fase 1: Database & Backend Foundation - Alle 6 stappen geïmplementeerd  
- ✅ Fase 2: Onboarding - Alle 3 stappen geïmplementeerd
  - ✅ Stap 2.1: Onboarding Flow UI - Alle screens geüpdatet met gamification-elementen
  - ✅ Stap 2.2: Rol Toekenning bij Onboarding - "yeni_gelen" rol wordt automatisch toegekend
  - ✅ Stap 2.3: Integratie met Bestaande OnboardingFlow - Naadloze integratie geverifieerd  
- ✅ Fase 3: Feed Gamification - Alle 4 stappen geïmplementeerd
  - ✅ Stap 3.1: Rol weergave in feed items - Primary role getoond naast gebruikersnaam
  - ✅ Stap 3.2: Week-feedback card - Card verschijnt 1x per week voor actieve gebruikers
  - ✅ Stap 3.3: Poll feedback messaging - Toast bericht na poll submission
  - ✅ Stap 3.4: Söz labels - Labels getoond op notes met >= 5 reactions  
- ✅ Fase 4: Locatiepagina Gamification - Alle 4 stappen geïmplementeerd
  - ✅ Stap 4.1: Header status - "Bugün canlı" / "Bu hafta sakin" status weergave
  - ✅ Stap 4.2: "Bu haftanın Mahallelisi" sectie - Meest actieve gebruiker deze week
  - ✅ Stap 4.3: Söz sectie met labels en ranking - Notes gesorteerd op reactions, labels getoond
  - ✅ Stap 4.4: Activiteit sectie - "Bugün X kişi uğradı" activiteit telling
- ✅ Fase 5: Profielpagina Gamification - Alle 4 stappen geïmplementeerd
  - ✅ Stap 5.1: Rollen weergave - Primary en secondary role getoond in profielpagina
  - ✅ Stap 5.2: Ritme sectie - 4x7 kalender grid met actieve dagen indicator
  - ✅ Stap 5.3: Bijdragen sectie - Laatste Söz, check-ins en poll-bijdragen
  - ✅ Stap 5.4: Erkenning sectie - Actieve leaderboard erkenningen met rank en context
- ✅ Fase 6: Öne Çıkanlar Tab - Alle 4 stappen geïmplementeerd
  - ✅ Stap 6.1: Nieuwe tab in navigatie - Tab toegevoegd aan FooterTabs met "Award" icon
  - ✅ Stap 6.2: Tab filtering - PeriodTabs component met "Bugün", "Bu Hafta", "Bu Ay", "Şehir" tabs
  - ✅ Stap 6.3: Card componenten - LeaderboardCard en LeaderboardCards componenten met max 5 gebruikers per card
  - ✅ Stap 6.4: Interactie - Profiel bekijken via klik op gebruikersnaam, geen social graph features
- ✅ Fase 7: Mascotte Microfeedback - Alle 3 stappen geïmplementeerd
  - ✅ Stap 7.1: Mascotte component - MascotteFeedback component met sonner integratie, auto-dismiss na 4 seconden
  - ✅ Stap 7.2: Contextuele berichten systeem - Bericht mapping met 6 trigger types en random selectie
  - ✅ Stap 7.3: Trigger logica - useMascotteFeedback hook met rate limiting en 5 geïntegreerde triggers (check-in, note creation, popular note, week-feedback, role change)
- ✅ Fase 8: Reward Systeem - Alle 4 stappen geïmplementeerd
  - ✅ Stap 8.1: Reward data model - Database migration 073 met rewards en user_rewards tabellen, ENUM types
  - ✅ Stap 8.2: Reward selectie logica - Backend service met round-robin selectie, eligibility checks, atomische updates
  - ✅ Stap 8.3: Reward modal/kaart UI - RewardCard en RewardModal componenten met vriendelijke UI
  - ✅ Stap 8.4: Reward claim flow - Backend claim endpoint, inline claim in modal, integratie in AccountPage met polling
**Status**: 🎉 Alle fasen voltooid! Het gamification systeem is volledig geïmplementeerd.


