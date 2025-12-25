# Claim & Consent Outreach - Functionele Scope

**Status**: ✅ Gedefinieerd  
**Laatste Update**: 2025-01-16  
**Epic**: Business Outreach & Claim System

Dit document definieert de functionele scope voor het Claim & Consent Outreach Bot systeem voor Turkspot. De scope is bewust beperkt gehouden om focus te behouden op vertrouwen en validatie.

---

## 📋 Scope - Wel

Het outreach systeem ondersteunt de volgende functionaliteiten:

### 1. Informatieve Email Notificatie
- **1 informatieve mail per locatie**: Elke locatie krijgt maximaal één outreach email
- **Service-notificatie**: Informatieve email die locatie-eigenaren informeert dat hun locatie op Turkspot staat
- **Mapview link**: Link naar mapview met locatie gecentreerd en tooltip open
- **AVG-compliant**: Gerechtvaardigd belang, opt-out mogelijkheid, geen spam

### 2. Token-based Actiepagina
- **Geen login vereist**: Gebruikers kunnen acties uitvoeren zonder account
- **Secure tokens**: Cryptographically secure tokens per locatie
- **Acties beschikbaar**:
  - Claim locatie (met gratis periode)
  - Verwijder locatie (remove)
  - Correctie doorgeven (correct)

### 3. Claim Systeem
- **Authenticated claims**: Primaire claim flow voor ingelogde gebruikers
  - Admin approval vereist
  - Logo en Google Business link upload mogelijk
  - Owner rol toekenning bij approval
- **Token-based claims**: Fallback voor niet-ingelogde gebruikers (optioneel)
  - Geen admin approval nodig
  - Gratis periode met expiratie
- **Gratis claim-periode**: Alle claims starten met gratis periode (configuratie: standaard 90 dagen)

### 4. Expiratie & Reminder Systeem
- **Expiratie tracking**: Automatische tracking van gratis periode einddatum
- **Reminder emails**: Vriendelijke reminder emails 7 dagen voor expiratie
- **State management**: Automatische status updates naar 'expired' na free_until datum
- **Basisvermelding blijft actief**: Na expiratie blijft locatie zichtbaar, premium features worden uitgeschakeld

### 5. Opt-out & Privacy
- **Opt-out mogelijkheid**: Elke email bevat opt-out link
- **Nooit opnieuw mailen**: Na opt-out wordt locatie gemarkeerd, geen verdere outreach
- **AVG compliance**: Audit logging voor alle acties (2 jaar retention)

---

## 🚫 Scope - Niet (Bewust)

De volgende functionaliteiten zijn **bewust uitgesloten** van deze fase:

### 1. Marketing & Campagnes
- ❌ Marketing campagnes
- ❌ Bulk follow-ups
- ❌ A/B testing van email content
- ❌ Promotionele emails
- ❌ Nieuwsbrief functionaliteit

### 2. Dashboards & Analytics
- ❌ Dashboards voor ondernemers
- ❌ Real-time analytics voor locatie-eigenaren
- ❌ Performance metrics voor ondernemers
- ❌ Custom branding voor ondernemers

### 3. Betaalde Flows
- ❌ Betaalde claim flows (in deze fase)
- ❌ Premium features na gratis periode (in deze fase)
- ❌ Subscription management
- ❌ Payment processing

### 4. Geavanceerde Features
- ❌ Multi-locatie management
- ❌ Team accounts voor ondernemers
- ❌ API access voor ondernemers
- ❌ Custom domain support

---

## 🎯 Focus: Vertrouwen & Validatie

Het outreach systeem is ontworpen met focus op:

1. **Vertrouwen opbouwen**: 
   - Vriendelijke, informatieve communicatie
   - Geen agressieve sales pitch
   - Duidelijke service-notificatie

2. **Validatie**:
   - Claim rate meten (percentage claims na email)
   - Removal rate meten (feedback op product kwaliteit)
   - No action rate meten (mogelijk verbetering nodig in messaging)

3. **AVG Compliance**:
   - Gerechtvaardigd belang als rechtsgrond
   - Publiek beschikbare contactgegevens
   - Opt-out altijd mogelijk
   - Audit logging voor compliance

---

## 📊 Success Metrics

Het outreach systeem wordt geëvalueerd op basis van:

- **Claim Rate**: Percentage locaties dat wordt geclaimed na outreach email
- **Removal Rate**: Percentage locaties dat wordt verwijderd (feedback indicator)
- **No Action Rate**: Percentage zonder actie (mogelijk verbetering messaging)
- **Bounce Rate**: Percentage bounced emails (kwaliteit contactgegevens)
- **Click Rate**: Percentage clicks op mapview link (engagement)

**Doelstellingen** (te valideren):
- Claim rate: > 10%
- Removal rate: < 5%
- Bounce rate: < 5%
- Click rate: > 20%

---

## 🔄 Toekomstige Uitbreidingen

De volgende functionaliteiten kunnen in toekomstige fases worden toegevoegd:

### Fase 2 (Toekomstig)
- Marketing email campagnes (via Brevo)
- Dashboards voor ondernemers
- Premium features na gratis periode
- Betaalde claim flows

### Fase 3 (Toekomstig)
- Multi-locatie management
- Team accounts
- API access voor ondernemers
- Custom branding

---

## 📝 Notities

- **Bewust beperkt**: Scope is bewust beperkt gehouden om focus te behouden
- **MVP fase**: Deze scope is geschikt voor MVP en validatie
- **Iteratief**: Scope kan worden uitgebreid op basis van feedback en metrics
- **AVG-first**: Alle functionaliteiten zijn ontworpen met AVG compliance in gedachten

---

## ✅ Acceptatie Criteria

De scope is gedefinieerd wanneer:
- [x] Dit document bestaat en is goedgekeurd
- [x] Duidelijke grenzen tussen wel/niet features zijn vastgelegd
- [x] Focus (vertrouwen & validatie) is duidelijk
- [x] Success metrics zijn gedefinieerd

---

**Laatste Update**: 2025-01-16  
**Gedefinieerd Door**: Development Team  
**Goedgekeurd**: ✅

