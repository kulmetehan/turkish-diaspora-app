# Gamification Test Plan

**Status**: 🧪 Test Document  
**Laatste Update**: 2025-01-XX  
**Doel**: Frontend UI tests voor nieuwe gamification functionaliteit

Dit document bevat testscenario's om de nieuwe gamification functionaliteit te testen. Focus ligt op frontend UI verificatie om te zien waar nieuwe features zichtbaar zijn.

---

## 📋 Test Setup

### Voorbereiding
- [X] Backend server draait (`uvicorn app.main:app --reload`)
- [X] Frontend server draait (`npm run dev` in Frontend/)
- [X] Database migrations zijn uitgevoerd (071, 072, 073)
- [X] Test gebruiker account beschikbaar (of nieuwe aanmaken)
- [X] Browser console open voor eventuele errors

### Test Accounts
- **Nieuwe gebruiker**: Voor onboarding flow test
- **Actieve gebruiker**: Met check-ins, Söz, poll responses voor volledige gamification features
- **Gebruiker met rollen**: Voor rol-weergave tests

---

## 🎯 Test Scenario's per Fase

### FASE 2: Onboarding Flow

#### Test 2.1: Onboarding UI Updates
**Locatie**: Onboarding screens (eerste keer inloggen of nieuwe account)

**Stappen**:
1. Start app met nieuwe/ongelogde gebruiker
2. Doorloop onboarding flow

**Verwachte Resultaten**:
- [X] **Screen 0**: Welkom tekst toont "Hoş geldin. Burası tek bir topluluk. Herkes burada."
- [X] **Screen 0**: Button label is "Verder"
- [X] **Screen 1**: Statisch uitleg scherm (geen carousel meer)
- [X] **Screen 1**: 3 bullets zichtbaar:
  - "Uğradım → ben buradaydım"
  - "Söz → deneyim & bilgi"
  - "Nabız → ne hissediyoruz"
- [X] **Screen 1**: Button label is "Klaar → Feed"
- [X] **Screen 5**: Geen XP-indicator (+10 XP) meer zichtbaar
- [X] **Screen 5**: Badge tekst is "Artık bu mahallenin bir parçasısın"

**Waar te vinden**: Eerste keer inloggen of nieuwe account aanmaken

---

### FASE 3: Feed Gamification

#### Test 3.1: Rol Weergave in Feed
**Locatie**: Feed pagina (`/feed`)

**Stappen**:
1. Navigeer naar Feed pagina
2. Bekijk feed items (check-ins en Söz)

**Verwachte Resultaten**:
- [X] Bij check-in items: Rol zichtbaar naast gebruikersnaam (bijv. "Metehan uğradı · Mahalleli")
- [X] Bij Söz items: Rol zichtbaar naast gebruikersnaam
- [X] Rol styling is subtiel (geen grote badges)
- [X] Rollen worden correct vertaald (Mahalleli, Anlatıcı, etc.)

**Waar te vinden**: Feed items in de activity feed

---

#### Test 3.2: Week-Feedback Card
**Locatie**: Feed pagina (`/feed`)

**Stappen**:
1. Log in met actieve gebruiker (deze week actief geweest)
2. Navigeer naar Feed pagina
3. Scroll door feed

**Verwachte Resultaten**:
- [X] Week-feedback card verschijnt in feed (als gebruiker deze week actief was)
- [X] Card tekst: "Bu hafta aktiftin. Mahalle seni gördü."
- [X] Card styling is subtiel (geen opvallende kleuren)
- [X] Card verschijnt max 1x per week (test: refresh pagina, card zou niet opnieuw moeten verschijnen)
- [X] Card verdwijnt na bekijken of na 1 dag

**Waar te vinden**: In de feed tussen andere items

**Notitie**: Als card niet verschijnt, check:
- Is gebruiker deze week actief geweest? (check-in, Söz, poll response)
- Is localStorage key `week_feedback_shown_${week}` al gezet?

---

#### Test 3.3: Poll Feedback Messaging
**Locatie**: Feed pagina - Poll modal

**Stappen**:
1. Navigeer naar Feed pagina
2. Open een poll (klik op poll item)
3. Selecteer een antwoord
4. Submit poll

**Verwachte Resultaten**:
- [X] Na succesvolle poll submission: Toast bericht verschijnt
- [X] Toast tekst: "Diaspora Nabzı'na katkı sağladın"
- [X] Toast is niet storend (onderaan of bovenin, niet als modal)
- [X] Toast verdwijnt automatisch na paar seconden

**Waar te vinden**: Toast notification na poll submission

---

#### Test 3.4: Söz Labels
**Locatie**: Feed pagina - Söz items

**Stappen**:
1. Navigeer naar Feed pagina
2. Zoek Söz items met veel reactions (>= 5 reactions)

**Verwachte Resultaten**:
- [X] Söz items met >= 5 reactions tonen label "Sözü Dinlenir"
- [X] Label is zichtbaar als kleine badge onder note content
- [X] Label styling is subtiel
- [X] Label wordt correct vertaald

**Waar te vinden**: Onder Söz content in feed items

---

### FASE 4: Locatiepagina Gamification

#### Test 4.1: Header Status
**Locatie**: Locatie detail pagina (`/locations/{id}`)

**Stappen**:
1. Navigeer naar een locatie detail pagina
2. Bekijk header sectie (bovenaan pagina)

**Verwachte Resultaten**:
- [ ] Status tekst zichtbaar onder locatie naam
- [ ] Als vandaag check-ins: "Bugün canlı"
- [ ] Als weinig activiteit deze week: "Bu hafta sakin"
- [ ] Status styling is subtiel (grijze italic tekst)
- [ ] Status update dynamisch (refresh pagina na nieuwe check-in)

**Waar te vinden**: In header onder locatie naam

---

#### Test 4.2: "Bu haftanın Mahallelisi" Sectie
**Locatie**: Locatie detail pagina (`/locations/{id}`)

**Stappen**:
1. Navigeer naar een locatie met check-ins deze week
2. Scroll naar Mahallelisi sectie

**Verwachte Resultaten**:
- [ ] Sectie titel: "Bu haftanın Mahallelisi"
- [ ] Gebruikersnaam zichtbaar
- [ ] Rol(en) zichtbaar naast naam
- [ ] Card styling is subtiel
- [ ] Als geen check-ins deze week: "Bu hafta henüz kimse uğramadı" of sectie niet zichtbaar

**Waar te vinden**: Midden/beneden op locatie detail pagina

---

#### Test 4.3: Söz Sectie met Labels en Ranking
**Locatie**: Locatie detail pagina - Söz sectie

**Stappen**:
1. Navigeer naar locatie met meerdere Söz
2. Scroll naar Söz sectie

**Verwachte Resultaten**:
- [ ] Söz zijn gesorteerd op reactions (beste eerst)
- [ ] Söz met >= 5 reactions tonen "Sözü Dinlenir" label
- [ ] Labels zijn zichtbaar als kleine badges
- [ ] Sortering werkt correct (meeste reactions bovenaan)

**Waar te vinden**: In Söz sectie op locatie detail pagina

---

#### Test 4.4: Activiteit Sectie
**Locatie**: Locatie detail pagina (`/locations/{id}`)

**Stappen**:
1. Navigeer naar een locatie
2. Zoek activiteit sectie

**Verwachte Resultaten**:
- [X] Activiteit card zichtbaar
- [X] Tekst: "Bugün X kişi uğradı" (X = aantal unieke gebruikers vandaag)
- [X] Alleen aantal getoond, geen namen
- [X] Card verschijnt alleen als check_ins_today > 0
- [X] Styling is simpel en subtiel

**Waar te vinden**: Op locatie detail pagina (mogelijk onder Mahallelisi sectie)

---

### FASE 5: Profielpagina

#### Test 5.1: Rollen Weergave
**Locatie**: Account/Profiel pagina (`/account`)

**Stappen**:
1. Log in met gebruiker
2. Navigeer naar Account pagina
3. Scroll naar rollen sectie

**Verwachte Resultaten**:
- [X] UserRolesSection component zichtbaar (bovenaan, na login sectie)
- [X] Primary role getoond (bijv. "Mahalleli")
- [] Als secondary role aanwezig: "Mahalleli · Anlatıcı" format
- [] Rollen correct vertaald
- [ ] Styling past bij profiel pagina
- [X] Alleen zichtbaar voor ingelogde gebruikers

**Waar te vinden**: Bovenaan Account pagina, direct na login sectie

---

#### Test 5.2: Ritme Sectie
**Locatie**: Account/Profiel pagina (`/account`)

**Stappen**:
1. Log in met actieve gebruiker
2. Navigeer naar Account pagina
3. Scroll naar ritme sectie

**Verwachte Resultaten**:
- [ ] RhythmSection component zichtbaar
- [ ] 4x7 kalender grid zichtbaar (28 dagen)
- [ ] Actieve dagen als gevulde dots (donkere kleur)
- [ ] Inactieve dagen als lege dots (lichte kleur)
- [ ] Titel "Son 4 haftadır düzenli" alleen zichtbaar als 7+ actieve dagen
- [ ] Responsive design werkt (grid past zich aan)

**Waar te vinden**: Op Account pagina, onder rollen sectie

---

#### Test 5.3: Bijdragen Sectie
**Locatie**: Account/Profiel pagina (`/account`)

**Stappen**:
1. Log in met gebruiker met bijdragen
2. Navigeer naar Account pagina
3. Scroll naar bijdragen sectie

**Verwachte Resultaten**:
- [ ] ContributionsSection component zichtbaar
- [ ] **Laatste Söz** subsectie:
  - Laatste 3 notes zichtbaar
  - Location naam getoond
  - Content preview (~50 chars)
  - Relative timestamp (bijv. "2 dagen geleden")
- [ ] **Laatste Check-ins** subsectie:
  - Laatste 3 check-ins zichtbaar
  - Location naam getoond
  - Relative timestamp
- [ ] **Poll-bijdragen** subsectie:
  - Alleen aantal getoond (bijv. "5 poll-bijdragen")
  - Geen details
- [ ] Geen totalen getoond (geen "Totaal 150 Söz")
- [ ] Icons zichtbaar (MessageCircle, MapPin, BarChart3)

**Waar te vinden**: Op Account pagina, onder ritme sectie

---

#### Test 5.4: Erkenning Sectie
**Locatie**: Account/Profiel pagina (`/account`)

**Stappen**:
1. Log in met gebruiker die in leaderboard staat
2. Navigeer naar Account pagina
3. Scroll naar erkenning sectie

**Verwachte Resultaten**:
- [ ] RecognitionSection component zichtbaar (alleen als erkenning aanwezig)
- [ ] Erkenningen getoond met:
  - Display titel (bijv. "Bu Haftanın Sözü")
  - Rank (#1, #2, etc.)
  - Context (location naam of note ID)
  - Period (today/week/month)
- [ ] Award icon zichtbaar
- [ ] Subtiele border styling
- [ ] Als geen erkenning: Sectie niet zichtbaar (null return)

**Waar te vinden**: Op Account pagina, onder bijdragen sectie

**Notitie**: Als sectie niet zichtbaar is, check of gebruiker actieve leaderboard entries heeft (period_start <= NOW() en period_end >= NOW())

---

### FASE 6: Öne Çıkanlar Tab

#### Test 6.1: Nieuwe Tab in Navigatie
**Locatie**: Footer navigatie (onderaan scherm)

**Stappen**:
1. Open app
2. Bekijk footer navigatie

**Verwachte Resultaten**:
- [ ] Nieuwe tab "ÖNE ÇIKANLAR" zichtbaar in footer
- [ ] Award icon zichtbaar bij tab
- [ ] Tab is klikbaar
- [ ] Navigatie naar Öne Çıkanlar pagina werkt

**Waar te vinden**: Footer navigatie, meestal onderaan scherm

---

#### Test 6.2: Tab Filtering
**Locatie**: Öne Çıkanlar pagina (`/onecikanlar`)

**Stappen**:
1. Navigeer naar Öne Çıkanlar pagina
2. Bekijk filter tabs bovenaan

**Verwachte Resultaten**:
- [ ] PeriodTabs component zichtbaar
- [ ] 4 tabs zichtbaar: "Bugün", "Bu Hafta", "Bu Ay", "Şehir"
- [ ] Default tab is "Bu Hafta" (actief)
- [ ] Klik op andere tab: Content update
- [ ] Actieve tab heeft andere styling (highlighted)

**Waar te vinden**: Bovenaan Öne Çıkanlar pagina

---

#### Test 6.3: Leaderboard Cards
**Locatie**: Öne Çıkanlar pagina (`/onecikanlar`)

**Stappen**:
1. Navigeer naar Öne Çıkanlar pagina
2. Bekijk leaderboard cards

**Verwachte Resultaten**:
- [ ] LeaderboardCards component zichtbaar
- [ ] Cards getoond per categorie:
  - "Bu Haftanın Sözü" (beste Söz deze week)
  - "Mahallenin Gururu" (lokaal actief)
  - "Sessiz Güç" (veel gelezen, weinig post)
  - "Diaspora Nabzı" (poll-bijdrage)
- [ ] Max 5 gebruikers per card
- [ ] Per gebruiker: Naam + rol zichtbaar
- [ ] Geen ranking nummers (geen #1, #2)
- [ ] Geen scores zichtbaar
- [ ] Context getoond (location naam, note ID, etc.)
- [ ] Styling is duidelijk maar niet competitief
- [ ] Empty state als geen data (bijv. "Geen data beschikbaar")

**Waar te vinden**: Op Öne Çıkanlar pagina, onder filter tabs

---

#### Test 6.4: Interactie
**Locatie**: Öne Çıkanlar pagina - Leaderboard cards

**Stappen**:
1. Navigeer naar Öne Çıkanlar pagina
2. Hover over gebruiker in leaderboard card
3. Klik op gebruikersnaam

**Verwachte Resultaten**:
- [ ] Hover effect zichtbaar (cursor change, highlight)
- [ ] Klik op naam: Navigatie naar account pagina
- [ ] Geen DM/volgen features zichtbaar
- [ ] Geen social graph features

**Waar te vinden**: Gebruikers items in leaderboard cards

**Notitie**: Emoji-reacties zijn niet geïmplementeerd (zoals opgemerkt in plan)

---

### FASE 7: Mascotte Microfeedback

#### Test 7.1: Mascotte Component
**Locatie**: Overal in app (toast notifications)

**Stappen**:
1. Voer actie uit die mascotte feedback triggert (zie Test 7.3)
2. Bekijk toast notification

**Verwachte Resultaten**:
- [ ] MascotteFeedback component verschijnt als toast
- [ ] Mascotte avatar zichtbaar
- [ ] Bericht tekst zichtbaar
- [ ] Toast positionering: top-center of bottom-center
- [ ] Auto-dismiss na 4 seconden
- [ ] Styling is subtiel (geen confetti, geen grote animaties)

**Waar te vinden**: Toast notification (meestal bovenin scherm)

---

#### Test 7.2: Contextuele Berichten
**Locatie**: Toast notifications (na verschillende acties)

**Stappen**:
1. Voer verschillende acties uit (check-in, Söz plaatsen, etc.)
2. Bekijk mascotte berichten

**Verwachte Resultaten**:
- [ ] Berichten zijn contextueel relevant
- [ ] Berichten zijn kort (max 1 zin)
- [ ] Berichten zijn in Turks
- [ ] Verschillende berichten voor verschillende triggers
- [ ] Random selectie werkt (niet altijd zelfde bericht)

**Voorbeelden van berichten**:
- Na check-in: "Buraları iyi biliyor gibisin."
- Na goede Söz: "Bu söz tutuldu."
- Na week actief: "Bu hafta görünürdün."
- Bij pauze: "Ara vermek de olur."

**Waar te vinden**: Toast notifications na acties

---

#### Test 7.3: Trigger Logica
**Locatie**: Verschillende locaties in app

**Stappen en Verwachte Resultaten**:

**Trigger 1: Check-in**
- [ ] Check-in op locatie detail pagina
- [ ] Mascotte feedback verschijnt na succesvolle check-in
- [ ] Bericht is relevant (bijv. "Buraları iyi biliyor gibisin.")

**Trigger 2: Note Creation**
- [ ] Plaats nieuwe Söz op locatie detail pagina
- [ ] Mascotte feedback verschijnt na succesvolle note creation
- [ ] Bericht is relevant

**Trigger 3: Popular Note**
- [ ] Plaats Söz die >= 5 reactions krijgt
- [ ] Mascotte feedback verschijnt (mogelijk met delay)
- [ ] Bericht is relevant (bijv. "Bu söz tutuldu.")

**Trigger 4: Week-Feedback**
- [ ] WeekFeedbackCard verschijnt in feed
- [ ] Mascotte feedback verschijnt tegelijkertijd
- [ ] Bericht is relevant (bijv. "Bu hafta görünürdün.")

**Trigger 5: Role Change**
- [ ] Wacht 5 minuten na login (polling interval)
- [ ] Als rol wijzigt: Mascotte feedback verschijnt
- [ ] Bericht is relevant

**Rate Limiting**:
- [ ] Min 30 seconden tussen berichten (test: voer snel meerdere acties uit)
- [ ] Max 5 berichten per sessie (test: voer 6+ acties uit)
- [ ] Rate limiting werkt correct

**Waar te vinden**: Toast notifications na verschillende acties

---

### FASE 8: Reward Systeem

#### Test 8.1: Reward Modal/Kaart UI
**Locatie**: Account pagina (`/account`)

**Stappen**:
1. Log in met gebruiker die reward heeft (pending)
2. Navigeer naar Account pagina
3. Bekijk reward modal (zou automatisch moeten verschijnen)

**Verwachte Resultaten**:
- [ ] RewardModal component verschijnt automatisch (als pending reward)
- [ ] Modal tekst: "Küçük bir teşekkür var."
- [ ] Sponsor details zichtbaar
- [ ] Reward details zichtbaar (titel, beschrijving, type)
- [ ] "Nasıl alırım?" button zichtbaar
- [ ] "Teşekkürler" button zichtbaar
- [ ] Geen countdown timer
- [ ] Styling is vriendelijk (geen claim-stress)

**Waar te vinden**: Modal overlay op Account pagina

**Notitie**: Als modal niet verschijnt, check:
- Heeft gebruiker pending reward? (check database: `user_rewards` tabel)
- Is polling actief? (elke 5 minuten)

---

#### Test 8.2: Reward Claim Flow
**Locatie**: Reward modal op Account pagina

**Stappen**:
1. Open reward modal (zie Test 8.1)
2. Klik op "Nasıl alırım?" button
3. Bekijk claim flow
4. Klik op claim button
5. Bekijk confirmation

**Verwachte Resultaten**:
- [ ] "Nasıl alırım?" button opent claim flow
- [ ] Instructies zichtbaar in modal
- [ ] Claim button zichtbaar
- [ ] Na claim: Confirmation feedback
- [ ] Status update naar "claimed"
- [ ] Modal sluit of update na claim

**Waar te vinden**: In reward modal

---

#### Test 8.3: Reward Card (Account Page)
**Locatie**: Account pagina (`/account`)

**Stappen**:
1. Log in met gebruiker die reward heeft
2. Navigeer naar Account pagina
3. Zoek reward card (als niet in modal)

**Verwachte Resultaten**:
- [ ] RewardCard component zichtbaar (als reward aanwezig)
- [ ] Reward details getoond
- [ ] Status badge zichtbaar (pending/claimed)
- [ ] Styling past bij account pagina

**Waar te vinden**: Op Account pagina (mogelijk onder erkenning sectie)

---

## 🔍 Algemene UI Checks

### Design Consistency
- [ ] Alle nieuwe componenten volgen design system
- [ ] Styling is consistent met bestaande UI
- [ ] Kleuren en spacing zijn consistent
- [ ] Typography volgt design system

### Responsive Design
- [ ] Alle nieuwe componenten werken op mobile
- [ ] Alle nieuwe componenten werken op tablet
- [ ] Alle nieuwe componenten werken op desktop
- [ ] Layout past zich aan schermgrootte aan

### Error Handling
- [ ] Loading states zichtbaar tijdens data fetch
- [ ] Error states zichtbaar bij API errors
- [ ] Empty states zichtbaar bij geen data
- [ ] Geen console errors (check browser console)

### Performance
- [ ] Geen merkbare performance impact
- [ ] API calls zijn geoptimaliseerd
- [ ] Geen onnodige re-renders
- [ ] Images/assets laden correct

---

## 🐛 Bekende Issues / Notities

### Test Data Vereisten
- Voor volledige tests: Zorg dat test gebruiker:
  - Check-ins heeft (deze week en vandaag)
  - Söz heeft (met verschillende reaction counts)
  - Poll responses heeft
  - Rollen heeft (primary + secondary)
  - Leaderboard entries heeft (voor Öne Çıkanlar)
  - Rewards heeft (voor reward tests)

### Database Checks
Als features niet werken, check:
- [ ] Migrations 071, 072, 073 zijn uitgevoerd
- [ ] `user_roles` tabel heeft data
- [ ] `leaderboard_entries` tabel heeft data
- [ ] `user_activity_summary` tabel heeft data
- [ ] `rewards` en `user_rewards` tabellen hebben data

### API Checks
Als data niet laadt, check:
- [ ] Backend server draait
- [ ] API endpoints zijn bereikbaar
- [ ] Authenticatie werkt
- [ ] CORS is correct geconfigureerd
- [ ] Browser console voor API errors

---

## ✅ Test Checklist Samenvatting

### Quick Smoke Test (5 minuten)
- [ ] Onboarding flow werkt (nieuwe gebruiker)
- [ ] Feed toont rollen bij items
- [ ] Account pagina toont rollen sectie
- [ ] Öne Çıkanlar tab bestaat en werkt
- [ ] Mascotte feedback verschijnt na check-in

### Medium Test (15 minuten)
- [ ] Alle bovenstaande + 
- [ ] Week-feedback card verschijnt
- [ ] Locatie detail pagina toont alle gamification features
- [ ] Account pagina toont alle 4 gamification secties
- [ ] Öne Çıkanlar pagina toont leaderboard cards

### Full Test (30+ minuten)
- [ ] Alle bovenstaande +
- [ ] Alle mascotte triggers werken
- [ ] Reward systeem werkt (als rewards in database)
- [ ] Alle edge cases getest
- [ ] Responsive design op alle devices
- [ ] Error handling getest

---

## 📝 Test Resultaten Template

```
Test Datum: [DATUM]
Tester: [NAAM]
Browser: [CHROME/FIREFOX/SAFARI]
Device: [MOBILE/TABLET/DESKTOP]

Fase 2: Onboarding
- [ ] Test 2.1: Pass/Fail
  Notities: [NOTITIES]

Fase 3: Feed Gamification
- [ ] Test 3.1: Pass/Fail
  Notities: [NOTITIES]
- [ ] Test 3.2: Pass/Fail
  Notities: [NOTITIES]
...

Algemene Issues:
- [ISSUE 1]
- [ISSUE 2]
...
```

---

**Laatste Update**: 2025-01-XX  
**Status**: 🧪 Ready for Testing


