# Claim & Consent Outreach - Juridisch Kader (AVG)

**Status**: ✅ Gedefinieerd  
**Laatste Update**: 2025-01-16  
**Epic**: Business Outreach & Claim System  
**Compliance**: AVG/GDPR

Dit document beschrijft het juridisch kader voor het Claim & Consent Outreach Bot systeem, met focus op AVG (GDPR) compliance.

---

## 📋 Rechtsgrond: Gerechtvaardigd Belang

### Basis
Het outreach systeem gebruikt **gerechtvaardigd belang** (Artikel 6 lid 1 onder f AVG) als rechtsgrond voor het verwerken van persoonsgegevens.

### Rechtvaardiging
1. **Service-notificatie**: Informeren van locatie-eigenaren dat hun locatie op Turkspot staat
2. **Publiek belang**: Platform voor Turkse diaspora gemeenschap in Nederland
3. **Verwachting**: Locatie-eigenaren kunnen verwachten geïnformeerd te worden over vermelding op publieke platforms
4. **Minimale impact**: Eén informatieve email, geen marketing, opt-out altijd mogelijk

### Belangenafweging
- **Ons belang**: Platform compleetheid, validatie van locaties, service voor gemeenschap
- **Betrokkene belang**: Privacy, geen spam, controle over eigen gegevens
- **Afweging**: Minimale inbreuk (1 email, opt-out mogelijk) vs. groot belang (platform compleetheid)

---

## 📧 Databron: Publiek Gepubliceerde Contactgegevens

### Bronnen
Contactgegevens worden alleen gebruikt indien **publiek beschikbaar**:

1. **OSM Tags**: Email adressen in OpenStreetMap tags (`email`, `contact:email`)
2. **Website Scraping**: Email adressen op publieke contact pagina's (geen achter logins)
3. **Google Business**: Email adressen in Google Business profiles (indien beschikbaar)
4. **Social Media**: Email adressen in publieke bios (indien beschikbaar)

### Regels
- ❌ **Geen guessing**: Geen email@domain.com patterns genereren
- ❌ **Geen scraping achter logins**: Alleen publiek zichtbare informatie
- ❌ **Geen aankoop van lijsten**: Geen externe email lijsten kopen
- ✅ **Alleen hoge confidence**: Alleen contacts met confidence score >= 50

---

## 📨 Communicatietype: Service-Notificatie

### Type
Outreach emails zijn **service-notificaties**, geen marketing emails.

### Kenmerken
- **Informatief**: Informeert locatie-eigenaar dat locatie op platform staat
- **Eénmalig**: Maximaal 1 email per locatie, ooit
- **Geen sales pitch**: Geen agressieve verkoop, geen druk
- **Duidelijk doel**: Duidelijke uitleg waarom email wordt verzonden

### Geen Marketing
- ❌ Geen promotionele content
- ❌ Geen speciale aanbiedingen
- ❌ Geen nieuwsbrief
- ❌ Geen follow-up campagnes

---

## 🔒 Rechten van Betrokkenen

### 1. Opt-out Mogelijkheid
- **Altijd mogelijk**: Elke email bevat opt-out link
- **Direct effect**: Na opt-out wordt locatie gemarkeerd, geen verdere outreach
- **Permanent**: Opt-out is permanent, locatie wordt nooit opnieuw gemaild
- **Eenvoudig**: Eén klik opt-out, geen complex proces

### 2. Verwijdering Mogelijkheid
- **Remove actie**: Locatie-eigenaar kan locatie verwijderen via token link
- **Direct effect**: Locatie wordt gemarkeerd als verwijderd
- **Geen harde delete**: Data blijft voor audit, maar locatie is niet meer zichtbaar
- **Reden optioneel**: Eigenaar kan optioneel reden opgeven

### 3. Correctie Mogelijkheid
- **Correct actie**: Locatie-eigenaar kan correcties doorgeven via token link
- **Admin review**: Correcties worden doorgegeven aan admin voor review
- **Bevestiging**: Eigenaar krijgt bevestiging dat correctie is ontvangen

### 4. Geen Opnieuw Mailen na Opt-out
- **Permanent**: Na opt-out wordt locatie permanent gemarkeerd
- **Database check**: Bij elke outreach selectie wordt opt-out status gecontroleerd
- **Geen uitzonderingen**: Geen herhalingen, zelfs niet bij nieuwe contact discovery

---

## 📝 Logging voor AVG Compliance

### Audit Logging Vereist
Alle outreach en claim acties moeten worden gelogd voor AVG compliance:

1. **Email Verzendingen**:
   - Timestamp
   - Recipient email
   - Status (sent, delivered, bounced)
   - SES message ID

2. **Claim Acties**:
   - Timestamp
   - Action type (claim, remove, correct)
   - User email (indien beschikbaar)
   - Location ID

3. **Opt-outs**:
   - Timestamp
   - Email
   - Reason (indien opgegeven)

4. **Removals**:
   - Timestamp
   - Location ID
   - Reason (indien opgegeven)

### Retention Policy
- **Retention periode**: 2 jaar (AVG vereiste)
- **Append-only**: Logs zijn onveranderbaar (append-only)
- **Secure storage**: Logs worden veilig opgeslagen
- **Access control**: Alleen admin toegang tot audit logs

### Implementatie
- Database tabel: `outreach_audit_log`
- Automatische logging bij alle acties
- Geen handmatige logging vereist

---

## 📋 Mailcopy Richtlijnen voor AVG Compliance

### Vereiste Elementen
Elke outreach email moet bevatten:

1. **Duidelijke Identificatie**:
   - Wie verzendt de email (Turkspot)
   - Waarom wordt email verzonden (service-notificatie)

2. **Rechtsgrond Uitleg**:
   - Korte uitleg: "Uw locatie staat op Turkspot"
   - Gerechtvaardigd belang vermelden (optioneel, maar transparant)

3. **Opt-out Link**:
   - Duidelijke opt-out link
   - Eenvoudig proces (één klik)
   - Bevestiging na opt-out

4. **Contact Informatie**:
   - Contact email voor vragen
   - Privacy policy link (indien beschikbaar)

5. **Geen Misleidende Content**:
   - Geen valse urgentie
   - Geen misleidende subject lines
   - Duidelijke, eerlijke communicatie

### Voorbeeld Subject Lines
- ✅ "Uw locatie staat op Turkspot" (NL)
- ✅ "Konumunuz Turkspot'ta" (TR)
- ✅ "Your location is on Turkspot" (EN)

### Voorbeeld Body Elementen
- ✅ Duidelijke uitleg waarom email wordt verzonden
- ✅ Link naar mapview met locatie
- ✅ Opt-out link
- ✅ Contact informatie

---

## 🚫 Wat We NIET Doen

### Spam Preventie
- ❌ Geen bulk emails zonder opt-out
- ❌ Geen emails naar niet-geverifieerde adressen
- ❌ Geen emails na opt-out
- ❌ Geen emails naar bounced adressen

### Privacy Respect
- ❌ Geen sharing van email adressen met derden
- ❌ Geen tracking pixels (privacy-first)
- ❌ Geen profiling zonder toestemming
- ❌ Geen data verkoop

### Transparantie
- ❌ Geen verborgen doelen
- ❌ Geen misleidende content
- ❌ Geen verborgen tracking
- ❌ Geen verborgen data verzameling

---

## ✅ Compliance Checklist

Voor elke outreach email moet worden gecontroleerd:

- [ ] Email bevat opt-out link
- [ ] Email bevat duidelijke identificatie (wie, waarom)
- [ ] Email is service-notificatie, geen marketing
- [ ] Recipient heeft niet eerder ge-opt-out
- [ ] Email adres is niet gebounced
- [ ] Contact is publiek beschikbaar (confidence >= 50)
- [ ] Audit log entry is aangemaakt
- [ ] Email volgt mailcopy richtlijnen

---

## 📚 Referenties

- **AVG/GDPR**: [Autoriteit Persoonsgegevens](https://autoriteitpersoonsgegevens.nl/)
- **Gerechtvaardigd Belang**: Artikel 6 lid 1 onder f AVG
- **Rechten Betrokkenen**: Hoofdstuk 3 AVG (Artikelen 15-22)
- **Privacy by Design**: Artikel 25 AVG

---

## 🔄 Review & Updates

Dit juridisch kader wordt regelmatig gereviewd en bijgewerkt:

- **Quarterly review**: Elke 3 maanden review
- **Legal consultation**: Bij twijfel juridisch advies inwinnen
- **Updates**: Document wordt bijgewerkt bij wijzigingen in wetgeving of proces

---

## ✅ Acceptatie Criteria

Het juridisch kader is gedefinieerd wanneer:
- [x] Dit document bestaat en is goedgekeurd
- [x] Rechtsgrond is duidelijk (gerechtvaardigd belang)
- [x] Databron regels zijn gedefinieerd (publiek beschikbaar)
- [x] Rechten van betrokkenen zijn gedocumenteerd
- [x] Logging voor AVG compliance is gepland
- [x] Mailcopy richtlijnen zijn gedefinieerd
- [x] Compliance checklist bestaat

---

**Laatste Update**: 2025-01-16  
**Gedefinieerd Door**: Development Team  
**Legal Review**: Aanbevolen (bij twijfel juridisch advies inwinnen)  
**Goedgekeurd**: ✅

