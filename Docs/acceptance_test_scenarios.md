# Acceptatietest Scenario's - Turkish Diaspora App

Dit document bevat handmatige testscenario's voor alle functionaliteit uit de Roadmap_Backlog.md (EPIC-0.5 t/m EPIC-3).

## Algemene Setup

**Voordat je begint:**
- Zorg dat de backend API draait op `http://127.0.0.1:8000`
- Zorg dat de frontend draait op `http://localhost:5173` (of je lokale dev server)
- Open de app in je browser
- Zorg dat je testdata hebt (minimaal 1 locatie in de database)

---

## EPIC-0.5: Platform Foundation

### Test 1: Soft Identity & Client Tracking

**Doel:** Verifiëren dat anonieme gebruikers een client_id krijgen

**Stappen:**
1. Open de app in een incognito/private browser venster
2. Open Developer Tools (F12) → Network tab
3. Navigeer naar de Map tab (standaard)
4. Zoek naar een API call naar `/api/v1/identity/me` of `/api/v1/locations`
5. Controleer in de Request Headers dat er een `X-Client-Id` header is met een UUID formaat
6. **Verwachte resultaat:** 
   - ✅ Er wordt automatisch een `X-Client-Id` header meegestuurd
   - ✅ De client_id is een geldig UUID formaat
   - ✅ De app werkt zonder authenticatie

---

### Test 2: Admin Authenticatie

**Doel:** Verifiëren dat admin login werkt

**Stappen:**
1. Navigeer naar `#/login` in de browser
2. Vul een geldig admin email en wachtwoord in
3. Klik op "Sign In" of "Login"
4. **Verwachte resultaat:**
   - ✅ Je wordt doorgestuurd naar `#/admin`
   - ✅ Je ziet het admin dashboard
   - ✅ Er verschijnt een success melding

**Negatieve test:**
1. Probeer in te loggen met verkeerde credentials
2. **Verwachte resultaat:**
   - ✅ Er verschijnt een foutmelding
   - ✅ Je blijft op de login pagina

---

## EPIC-1: Interaction Layer MVP

### Test 3: Check-ins

**Doel:** Verifiëren dat gebruikers kunnen inchecken bij locaties

**Stappen:**
1. Ga naar de Map tab
2. Klik op een locatie marker op de kaart (of selecteer een locatie uit de lijst)
3. In het location detail overlay, zoek naar een "Check-in" button of actie
4. Klik op de check-in button
5. **Verwachte resultaat:**
   - ✅ Er verschijnt een success melding ("Check-in successful" of vergelijkbaar)
   - ✅ De check-in wordt getoond in de activity feed
   - ✅ De locatie krijgt een hogere trending score

**Uniqueness test:**
1. Probeer opnieuw in te checken bij dezelfde locatie (binnen 24 uur)
2. **Verwachte resultaat:**
   - ✅ Er verschijnt een foutmelding (409 Conflict) of "Already checked in today"
   - ✅ Je kunt niet opnieuw inchecken

---

### Test 4: Emoji Reactions

**Doel:** Verifiëren dat gebruikers kunnen reageren met emoji's

**Stappen:**
1. Ga naar de Map tab
2. Selecteer een locatie
3. In het location detail, zoek naar reaction buttons (🔥, ❤️, 👍, 😊, ⭐, 🚩)
4. Klik op een reaction (bijvoorbeeld 🔥)
5. **Verwachte resultaat:**
   - ✅ De reaction wordt toegevoegd
   - ✅ Je ziet de reaction count stijgen
   - ✅ De reaction verschijnt in de activity feed

**Uniqueness test:**
1. Probeer dezelfde reaction opnieuw te geven
2. **Verwachte resultaat:**
   - ✅ Je kunt de reaction verwijderen (toggle)
   - ✅ Of je krijgt een melding dat je al gereageerd hebt

**Aggregatie test:**
1. Bekijk de reaction stats voor een locatie
2. **Verwachte resultaat:**
   - ✅ Je ziet de totale counts per reaction type
   - ✅ De stats zijn correct geaggregeerd

---

### Test 5: Location Notes

**Doel:** Verifiëren dat gebruikers notities kunnen toevoegen bij locaties

**Stappen:**
1. Ga naar de Map tab
2. Selecteer een locatie
3. Zoek naar een "Add Note" of "Write Note" button
4. Klik erop en vul een notitie in (3-1000 karakters)
5. Klik op "Save" of "Submit"
6. **Verwachte resultaat:**
   - ✅ De notitie wordt opgeslagen
   - ✅ De notitie verschijnt in de lijst van notities voor deze locatie
   - ✅ De notitie verschijnt in de activity feed

**Validatie test:**
1. Probeer een notitie te maken met minder dan 3 karakters
2. **Verwachte resultaat:**
   - ✅ Er verschijnt een validatie foutmelding
   - ✅ De notitie wordt niet opgeslagen

**Edit test:**
1. Maak een notitie
2. Klik op "Edit" bij je eigen notitie
3. Wijzig de tekst
4. Sla op
5. **Verwachte resultaat:**
   - ✅ De notitie wordt bijgewerkt
   - ✅ Er is een "edited" indicator zichtbaar

**Delete test:**
1. Klik op "Delete" bij je eigen notitie
2. Bevestig de verwijdering
3. **Verwachte resultaat:**
   - ✅ De notitie wordt verwijderd
   - ✅ De notitie verdwijnt uit de lijst

---

### Test 6: Location Interaction Overview

**Doel:** Verifiëren dat alle interacties zichtbaar zijn op locatiepagina's

**Stappen:**
1. Ga naar de Map tab
2. Selecteer een locatie die interacties heeft
3. Bekijk het location detail overlay
4. **Verwachte resultaat:**
   - ✅ Je ziet check-in stats (totaal, vandaag)
   - ✅ Je ziet reaction counts per type
   - ✅ Je ziet de lijst van notities
   - ✅ Alle interacties zijn correct geaggregeerd

---

### Test 7: Activity Stream & Feed Tab

**Doel:** Verifiëren dat de activity feed werkt

**Stappen:**
1. Ga naar de Feed tab (onderaan de app)
2. Klik op de "Activiteit" tab binnen de Feed
3. **Verwachte resultaat:**
   - ✅ Je ziet een lijst van recente activiteiten
   - ✅ Activiteiten tonen: check-ins, reactions, notes, favorites
   - ✅ Elke activiteit heeft een timestamp
   - ✅ Je kunt klikken op activiteiten om naar de locatie te gaan

**Filter test:**
1. In de activity feed, probeer te filteren op activity type (indien beschikbaar)
2. **Verwachte resultaat:**
   - ✅ De lijst wordt gefilterd op het geselecteerde type

---

### Test 8: Trending Indicator MVP

**Doel:** Verifiëren dat trending locaties worden getoond

**Stappen:**
1. Ga naar de Feed tab
2. Klik op de "Trending" tab
3. **Verwachte resultaat:**
   - ✅ Je ziet een lijst van trending locaties
   - ✅ Locaties zijn gesorteerd op trending score
   - ✅ Je ziet check-ins, reactions, notes counts per locatie
   - ✅ Je kunt klikken op locaties om details te zien

**Filter test:**
1. Filter op stad (indien beschikbaar)
2. Filter op categorie (indien beschikbaar)
3. **Verwachte resultaat:**
   - ✅ De trending lijst wordt gefilterd
   - ✅ Alleen locaties in de geselecteerde stad/categorie worden getoond

---

### Test 9: Diaspora Pulse Lite UI

**Doel:** Verifiëren dat het trending dashboard werkt

**Stappen:**
1. Navigeer naar `#/pulse` of klik op "Diaspora Pulse" (indien beschikbaar)
2. **Verwachte resultaat:**
   - ✅ Je ziet trending metrics
   - ✅ Je ziet statistieken per stad
   - ✅ Je ziet grafieken/visualisaties van activiteit

---

## EPIC-1.5: Engagement Layer

### Test 10: Push Notifications

**Doel:** Verifiëren dat push notificaties werken

**Stappen:**
1. Ga naar de Account tab
2. Zoek naar "Push Notifications" of "Notificaties" settings
3. Klik op "Enable Notifications" of "Register for Push"
4. Accepteer de browser notificatie prompt
5. **Verwachte resultaat:**
   - ✅ Je krijgt een browser notificatie prompt
   - ✅ Na acceptatie wordt je device geregistreerd
   - ✅ Je ziet een success melding

**Preferences test:**
1. In de push settings, wijzig je notificatie voorkeuren
2. Zet bijvoorbeeld "Poll notifications" uit
3. **Verwachte resultaat:**
   - ✅ Je voorkeuren worden opgeslagen
   - ✅ Je krijgt alleen notificaties voor de ingeschakelde types

---

### Test 11: Referral Program

**Doel:** Verifiëren dat het referral systeem werkt

**Stappen:**
1. Log in (als je nog niet ingelogd bent)
2. Ga naar de Account tab
3. Zoek naar "Referral" of "Uitnodigen" sectie
4. **Verwachte resultaat:**
   - ✅ Je ziet je unieke referral code
   - ✅ Je ziet hoeveel mensen je code hebben gebruikt
   - ✅ Er is een "Share" of "Copy" button

**Share test:**
1. Klik op "Share" of "Copy" bij je referral code
2. **Verwachte resultaat:**
   - ✅ De code wordt gekopieerd naar clipboard
   - ✅ Of er opent een share dialog

**Claim test:**
1. Log uit (of gebruik een incognito venster)
2. Navigeer naar `#/auth` (of gebruik een referral link met `?ref=CODE`)
3. Klik op de "Registreren" tab
4. Vul de signup formulier in (email, wachtwoord, optioneel weergavenaam)
5. Voer een referral code in het "Referral Code (optioneel)" veld in
6. Klik op "Account aanmaken"
7. **Verwachte resultaat:**
   - ✅ Account wordt aangemaakt
   - ✅ Referral code wordt automatisch geclaimd tijdens signup
   - ✅ Je krijgt een success melding "Referral code gebruikt!"
   - ✅ Je krijgt 25 XP welcome bonus
   - ✅ De referrer krijgt 50 XP
   - ✅ De referral wordt geregistreerd in de database

**Opmerking:** Referral codes kunnen alleen worden geclaimd tijdens het aanmaken van een nieuw account. Bestaande gebruikers kunnen geen referral code meer claimen.

---

### Test 12: Weekly Digest Email

**Doel:** Verifiëren dat weekly digest emails worden verstuurd

**Opmerking:** Dit is een backend worker, maar je kunt testen of:
1. De worker draait (check admin dashboard)
2. Er emails worden verstuurd (check email inbox)
3. De email content correct is

**Stappen:**
1. Ga naar Admin dashboard → Workers
2. Zoek naar "digest_worker" of "weekly_digest"
3. Controleer of de worker recent heeft gedraaid
4. **Verwachte resultaat:**
   - ✅ De worker heeft recent gedraaid
   - ✅ Er zijn geen errors

---

### Test 13: Social Sharing UX

**Doel:** Verifiëren dat content shareable is

**Stappen:**
1. Ga naar een locatie detail
2. Zoek naar een "Share" button (meestal rechtsboven)
3. Klik op "Share"
4. **Verwachte resultaat:**
   - ✅ Er opent een share dialog
   - ✅ Je kunt delen via Web Share API (native share)
   - ✅ Of je ziet opties voor social media

**Share vanuit feed:**
1. Ga naar de Feed tab
2. Klik op een activity card
3. Zoek naar share optie
4. **Verwachte resultaat:**
   - ✅ Je kunt de activiteit delen

---

## EPIC-2: Interaction Layer 2.0

### Test 14: Supabase Auth Implementatie

**Doel:** Verifiëren dat user login/signup werkt

**Stappen:**
1. Navigeer naar `#/auth`
2. Klik op "Sign Up" of "Registreren"
3. Vul email en wachtwoord in
4. Klik op "Create Account"
5. **Verwachte resultaat:**
   - ✅ Account wordt aangemaakt
   - ✅ Je wordt ingelogd
   - ✅ Je wordt doorgestuurd naar de app

**Login test:**
1. Log uit
2. Ga naar `#/auth`
3. Klik op "Sign In"
4. Vul je credentials in
5. **Verwachte resultaat:**
   - ✅ Je wordt ingelogd
   - ✅ Je ziet je account info in Account tab

**Google login test:**
1. Klik op "Sign in with Google" (indien beschikbaar)
2. **Verwachte resultaat:**
   - ✅ Google OAuth flow opent
   - ✅ Na authenticatie ben je ingelogd

---

### Test 15: User Profiles API

**Doel:** Verifiëren dat gebruikers hun profiel kunnen beheren

**Stappen:**
1. Log in
2. Ga naar Account tab
3. Zoek naar "Profile" of "Profiel" sectie
4. Klik op "Edit Profile"
5. Wijzig je display name, avatar, bio (indien beschikbaar)
6. Sla op
7. **Verwachte resultaat:**
   - ✅ Profiel wordt bijgewerkt
   - ✅ Wijzigingen zijn direct zichtbaar
   - ✅ Je ziet je nieuwe display name in activiteiten

---

### Test 16: Favorites API

**Doel:** Verifiëren dat gebruikers favorieten kunnen toevoegen

**Stappen:**
1. Ga naar een locatie detail
2. Zoek naar een "Favorite" of "⭐" button
3. Klik erop om toe te voegen aan favorieten
4. **Verwachte resultaat:**
   - ✅ Locatie wordt toegevoegd aan favorieten
   - ✅ Button verandert van state (gevuld/lege ster)
   - ✅ Locatie verschijnt in je favorieten lijst

**Favorieten lijst:**
1. Ga naar Account tab
2. Zoek naar "Favorites" of "Favorieten"
3. **Verwachte resultaat:**
   - ✅ Je ziet alle favoriete locaties
   - ✅ Je kunt klikken om naar de locatie te gaan
   - ✅ Je kunt favorieten verwijderen

---

### Test 17: XP Awarding Engine

**Doel:** Verifiëren dat XP wordt toegekend bij activiteiten

**Stappen:**
1. Log in
2. Noteer je huidige XP (in Account tab of profiel)
3. Voer een activiteit uit (check-in, reaction, note, poll response)
4. **Verwachte resultaat:**
   - ✅ Je XP stijgt
   - ✅ Je ziet een melding "XP earned" (indien geïmplementeerd)
   - ✅ Je nieuwe XP is zichtbaar in je profiel

**XP per activiteit:**
- Check-in: +10 XP (voorbeeld)
- Reaction: +5 XP
- Note: +15 XP
- Poll response: +10 XP
- Favorite: +5 XP

---

### Test 18: Streaks & Badges Engine

**Doel:** Verifiëren dat streaks en badges werken

**Stappen:**
1. Log in
2. Ga naar Account tab
3. Zoek naar "Streaks" of "Badges"
4. **Verwachte resultaat:**
   - ✅ Je ziet je huidige streak (dagen)
   - ✅ Je ziet je langste streak
   - ✅ Je ziet je badges

**Streak test:**
1. Voer elke dag een activiteit uit (check-in, note, etc.)
2. Controleer je streak na meerdere dagen
3. **Verwachte resultaat:**
   - ✅ Je streak stijgt elke dag
   - ✅ Als je een dag overslaat, reset de streak

**Badge test:**
1. Bereik een milestone (bijv. 100 XP, 10 check-ins)
2. **Verwachte resultaat:**
   - ✅ Je krijgt een badge
   - ✅ Badge verschijnt in je profiel

---

### Test 19: Activity History UI

**Doel:** Verifiëren dat gebruikers hun activiteit kunnen zien

**Stappen:**
1. Log in
2. Ga naar Account tab
3. Scroll naar "Activiteitsgeschiedenis" sectie
4. **Verwachte resultaat:**
   - ✅ Je ziet een lijst van je eigen activiteiten
   - ✅ Activiteiten zijn gesorteerd op datum (nieuwste eerst)
   - ✅ Je kunt klikken om naar locaties te gaan

---

### Test 20: Polls - Admin Creation UI

**Doel:** Verifiëren dat admins polls kunnen maken

**Stappen:**
1. Log in als admin
2. Ga naar Admin dashboard
3. Navigeer naar "Polls" of "Admin Polls"
4. Klik op "Create Poll" of "Nieuwe Poll"
5. Vul in:
   - Titel
   - Vraag
   - Opties (minimaal 2)
   - Start/eind datum
6. Klik op "Create" of "Save"
7. **Verwachte resultaat:**
   - ✅ Poll wordt aangemaakt
   - ✅ Poll verschijnt in de lijst
   - ✅ Poll is actief (indien start datum in verleden)

---

### Test 21: Poll Response Logic

**Doel:** Verifiëren dat gebruikers kunnen stemmen op polls

**Stappen:**
1. Ga naar Feed tab
2. Klik op "Polls" tab
3. Selecteer een actieve poll
4. Kies een optie
5. Klik op "Vote" of "Stem"
6. **Verwachte resultaat:**
   - ✅ Je stem wordt opgeslagen
   - ✅ Je ziet de poll stats (indien privacy threshold is bereikt)
   - ✅ Je krijgt XP voor het stemmen
   - ✅ Je kunt niet opnieuw stemmen

**Stats test:**
1. Bekijk poll stats (indien beschikbaar)
2. **Verwachte resultaat:**
   - ✅ Je ziet totale responses
   - ✅ Je ziet counts per optie
   - ✅ Stats zijn alleen zichtbaar als >= 10 responses

---

### Test 22: City & Category Stats

**Doel:** Verifiëren dat statistieken per stad en categorie werken

**Stappen:**
1. Navigeer naar `#/pulse`
2. Selecteer een stad uit de dropdown
3. **Verwachte resultaat:**
   - ✅ Je ziet statistieken voor die stad
   - ✅ Je ziet check-ins, reactions, notes, favorites counts
   - ✅ Grafieken worden bijgewerkt

**Categorie filter:**
1. Filter op categorie (indien beschikbaar)
2. **Verwachte resultaat:**
   - ✅ Stats worden gefilterd op categorie

---

### Test 23: Diaspora Pulse Dashboard

**Doel:** Verifiëren dat het volledige analytics dashboard werkt

**Stappen:**
1. Navigeer naar `#/pulse`
2. **Verwachte resultaat:**
   - ✅ Je ziet overview tab met algemene stats
   - ✅ Je ziet trending tab met trending locaties
   - ✅ Je ziet cities tab met per-stad vergelijking
   - ✅ Grafieken en visualisaties laden correct

---

## EPIC-2.5: Community Layer

### Test 24: User Groups

**Doel:** Verifiëren dat gebruikers groepen kunnen aanmaken en joinen

**Stappen:**
1. Log in
2. Navigeer naar `#/groups` (indien beschikbaar) of zoek naar "Groups" in de app
3. Klik op "Create Group"
4. Vul in:
   - Groepsnaam (minimaal 3 karakters)
   - Beschrijving (optioneel)
   - Public/Private
5. Klik op "Create"
6. **Verwachte resultaat:**
   - ✅ Groep wordt aangemaakt
   - ✅ Je wordt doorgestuurd naar groep detail pagina
   - ✅ Je bent automatisch lid

**Join test:**
1. Ga naar de groups lijst
2. Klik op "Join" bij een publieke groep
3. **Verwachte resultaat:**
   - ✅ Je wordt lid van de groep
   - ✅ Je ziet de groep in je groups lijst

**Activity feed test:**
1. Ga naar een groep detail pagina
2. Bekijk de activity feed
3. **Verwachte resultaat:**
   - ✅ Je ziet activiteiten van groep leden
   - ✅ Activiteiten zijn relevant voor de groep

---

### Test 25: Moderation Tools

**Doel:** Verifiëren dat admins content kunnen modereren

**Stappen:**
1. Log in als admin
2. Ga naar Admin dashboard → Reports of Moderation
3. **Verwachte resultaat:**
   - ✅ Je ziet een lijst van reports
   - ✅ Je kunt reports filteren op status (pending, resolved, dismissed)

**Action test:**
1. Selecteer een pending report
2. Kies een actie: "Approve", "Dismiss", "Remove Content"
3. **Verwachte resultaat:**
   - ✅ De actie wordt uitgevoerd
   - ✅ Report status wordt bijgewerkt
   - ✅ Content wordt verwijderd (indien gekozen)

---

### Test 26: Reporting System

**Doel:** Verifiëren dat gebruikers content kunnen rapporteren

**Stappen:**
1. Ga naar een locatie detail
2. Zoek naar een "Report" button (meestal rechtsboven, naast Share)
3. Klik op "Report"
4. Selecteer een reden (spam, inappropriate, etc.)
5. Voeg optioneel details toe
6. Klik op "Submit Report"
7. **Verwachte resultaat:**
   - ✅ Report wordt ingediend
   - ✅ Je krijgt een success melding
   - ✅ Report verschijnt in admin dashboard

**Report note/reaction:**
1. Ga naar een note of reaction
2. Klik op report (indien beschikbaar)
3. **Verwachte resultaat:**
   - ✅ Je kunt ook notes en reactions rapporteren

---

### Test 27: Community Guidelines

**Doel:** Verifiëren dat community guidelines zichtbaar zijn

**Stappen:**
1. Navigeer naar `#/guidelines`
2. **Verwachte resultaat:**
   - ✅ Je ziet de community guidelines
   - ✅ Guidelines zijn duidelijk geformatteerd
   - ✅ Er zijn links naar guidelines vanuit Account tab

---

## EPIC-3: Monetization Layer

### Test 28: Business Accounts API

**Doel:** Verifiëren dat bedrijven accounts kunnen aanmaken

**Stappen:**
1. Log in
2. Navigeer naar Business sectie (indien beschikbaar) of Account → Business
3. Klik op "Create Business Account"
4. Vul in:
   - Company name
   - VAT/KVK nummer (optioneel)
   - Country
   - Website (optioneel)
   - Contact email
   - Contact phone (optioneel)
5. Klik op "Create"
6. **Verwachte resultaat:**
   - ✅ Business account wordt aangemaakt
   - ✅ Je ziet je business account details
   - ✅ Je kunt team members toevoegen

**Members test:**
1. In business account, klik op "Add Member"
2. Voer een user ID of email in
3. Selecteer een rol (owner, admin, editor)
4. **Verwachte resultaat:**
   - ✅ Member wordt toegevoegd
   - ✅ Member verschijnt in de lijst

---

### Test 29: Location Claiming Flow

**Doel:** Verifiëren dat bedrijven locaties kunnen claimen

**Stappen:**
1. Log in met een business account
2. Ga naar een locatie detail
3. Zoek naar "Claim Location" of "Claim deze locatie" button
4. Klik erop
5. Vul verificatie informatie in (optioneel)
6. Klik op "Submit Claim"
7. **Verwachte resultaat:**
   - ✅ Claim wordt ingediend
   - ✅ Status is "pending"
   - ✅ Claim verschijnt in je claims lijst

**Admin approval:**
1. Log in als admin
2. Ga naar Admin → Claims of Location Claims
3. Selecteer een pending claim
4. Klik op "Approve" of "Reject"
5. **Verwachte resultaat:**
   - ✅ Claim status wordt bijgewerkt
   - ✅ Bij approval: locatie krijgt verified badge
   - ✅ Business krijgt notificatie

---

### Test 30: Verified Badge System

**Doel:** Verifiëren dat verified badges zichtbaar zijn

**Stappen:**
1. Ga naar een locatie die een approved claim heeft
2. **Verwachte resultaat:**
   - ✅ Je ziet een verified badge (✓) naast de locatienaam
   - ✅ Badge is zichtbaar in location detail
   - ✅ Badge is zichtbaar in location cards
   - ✅ Badge is zichtbaar in trending lijst

---

### Test 31: Premium Features Layer

**Doel:** Verifiëren dat premium subscriptions werken

**Stappen:**
1. Log in met een business account
2. Navigeer naar Premium of Subscription sectie
3. Klik op "Subscribe" of "Upgrade to Premium"
4. Selecteer een tier (Premium of Pro)
5. Je wordt doorgestuurd naar Stripe checkout
6. **Verwachte resultaat:**
   - ✅ Stripe checkout opent
   - ✅ Na betaling wordt subscription geactiveerd
   - ✅ Je ziet premium features beschikbaar

**Features test:**
1. Bekijk beschikbare features voor je tier
2. **Verwachte resultaat:**
   - ✅ Je ziet welke features beschikbaar zijn
   - ✅ Premium features zijn geactiveerd (indien subscribed)

---

### Test 32: Promoted Locations

**Doel:** Verifiëren dat locaties kunnen worden gepromoot

**Stappen:**
1. Log in met een business account
2. Navigeer naar `#/business/promotions` of Business → Promotions
3. Klik op "Promote Location"
4. Selecteer een locatie
5. Kies promotion type (trending, feed, both)
6. Kies duur (7, 14, of 30 dagen)
7. Klik op "Create Promotion"
8. Je wordt doorgestuurd naar Stripe payment
9. **Verwachte resultaat:**
   - ✅ Na betaling wordt promotion geactiveerd
   - ✅ Locatie verschijnt bovenaan trending lijst
   - ✅ Locatie verschijnt bovenaan activity feed
   - ✅ Locatie heeft "Promoted" indicator

**Expiry test:**
1. Wacht tot promotion verloopt (of check admin)
2. **Verwachte resultaat:**
   - ✅ Promotion wordt automatisch gedeactiveerd
   - ✅ Locatie verliest promoted status

---

### Test 33: Promoted News

**Doel:** Verifiëren dat news posts kunnen worden gepromoot

**Stappen:**
1. Log in met een business account
2. Ga naar Business → Promotions
3. Klik op "Promote News"
4. Vul in:
   - Titel
   - Content
   - URL (optioneel)
   - Image URL (optioneel)
   - Duur
5. Klik op "Create"
6. Betaal via Stripe
7. **Verwachte resultaat:**
   - ✅ News post wordt aangemaakt
   - ✅ News post verschijnt bovenaan news feed
   - ✅ News post heeft "Promoted" indicator

---

### Test 34: Business Analytics Dashboard

**Doel:** Verifiëren dat business analytics werken

**Stappen:**
1. Log in met een business account
2. Navigeer naar `#/business/analytics` of Business → Analytics
3. **Verwachte resultaat:**
   - ✅ Je ziet overview metrics:
     - Total locations
     - Approved locations
     - Total views
     - Total check-ins, reactions, notes, favorites
     - Trending locations count
   - ✅ Je kunt filteren op periode (7, 30, 90 dagen)
   - ✅ Je ziet per-location analytics
   - ✅ Je ziet engagement metrics
   - ✅ Je ziet trending metrics

**Per-location test:**
1. Klik op een specifieke locatie
2. **Verwachte resultaat:**
   - ✅ Je ziet gedetailleerde stats voor die locatie
   - ✅ Je ziet views, check-ins, reactions, notes, favorites
   - ✅ Je ziet trending score

---

### Test 35: Google Business Sync

**Doel:** Verifiëren dat Google Business sync werkt

**Stappen:**
1. Log in met een business account
2. Navigeer naar Business → Google Business of Settings
3. Klik op "Connect Google Business"
4. Autoriseer OAuth flow
5. **Verwachte resultaat:**
   - ✅ Google Business account wordt gekoppeld
   - ✅ Je ziet connected status

**Sync test:**
1. Selecteer een geclaimde locatie
2. Klik op "Sync with Google Business"
3. **Verwachte resultaat:**
   - ✅ Google Business data wordt gesynchroniseerd
   - ✅ Locatie informatie wordt bijgewerkt
   - ✅ Sync status is zichtbaar

---

## Algemene UI/UX Tests

### Test 36: Responsive Design

**Doel:** Verifiëren dat de app werkt op verschillende schermformaten

**Stappen:**
1. Test op desktop (1920x1080)
2. Test op tablet (768x1024)
3. Test op mobile (375x667)
4. **Verwachte resultaat:**
   - ✅ Layout past zich aan
   - ✅ Alle functionaliteit is toegankelijk
   - ✅ Geen horizontale scroll
   - ✅ Touch targets zijn groot genoeg op mobile

---

### Test 37: Navigation

**Doel:** Verifiëren dat navigatie werkt

**Stappen:**
1. Test alle footer tabs (Map, News, Events, Feed, Account)
2. Test browser back/forward buttons
3. Test directe URL navigatie (bijv. `#/feed`)
4. **Verwachte resultaat:**
   - ✅ Alle tabs werken
   - ✅ Browser history werkt correct
   - ✅ Directe URLs werken
   - ✅ Active tab is correct gehighlight

---

### Test 38: Error Handling

**Doel:** Verifiëren dat errors netjes worden afgehandeld

**Stappen:**
1. Stop de backend API
2. Probeer een actie uit te voeren
3. **Verwachte resultaat:**
   - ✅ Er verschijnt een duidelijke error melding
   - ✅ App crasht niet
   - ✅ Je kunt blijven navigeren

**Network error test:**
1. Zet network throttling aan (Chrome DevTools)
2. Test verschillende acties
3. **Verwachte resultaat:**
   - ✅ Loading states zijn zichtbaar
   - ✅ Timeouts worden netjes afgehandeld

---

## Test Checklist

Gebruik deze checklist om bij te houden welke tests je hebt uitgevoerd:

- [ ] EPIC-0.5: Platform Foundation (3 tests)
- [ ] EPIC-1: Interaction Layer MVP (7 tests)
- [ ] EPIC-1.5: Engagement Layer (4 tests)
- [ ] EPIC-2: Interaction Layer 2.0 (10 tests)
- [ ] EPIC-2.5: Community Layer (4 tests)
- [ ] EPIC-3: Monetization Layer (8 tests)
- [ ] Algemene UI/UX Tests (3 tests)

**Totaal: 39 testscenario's**

---

## Bug Reporting Template

Wanneer je een bug vindt, documenteer het als volgt:

**Bug #: [nummer]**
- **Test:** [welke test]
- **Stappen om te reproduceren:**
  1. ...
  2. ...
- **Verwacht gedrag:** ...
- **Werkelijk gedrag:** ...
- **Screenshot:** [indien relevant]
- **Browser/OS:** ...
- **Prioriteit:** [High/Medium/Low]

---

## Notes

- Sommige features vereisen specifieke setup (bijv. Stripe test keys voor payments)
- Admin features vereisen admin credentials
- Business features vereisen een business account
- Push notifications vereisen HTTPS (of localhost)
- Test data moet aanwezig zijn voor sommige tests
