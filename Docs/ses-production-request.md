# AWS SES Production Access Request

**Status**: 📋 Template Klaar  
**Laatste Update**: 2025-01-16  
**Epic**: Business Outreach & Claim System

Dit document bevat de template en informatie voor het aanvragen van AWS SES Production Access. SES start standaard in sandbox mode, wat beperkingen oplegt voor outreach emails.

---

## 📋 Overzicht

### Sandbox Mode Beperkingen
- ❌ Alleen verzenden naar geverifieerde email adressen
- ❌ Maximaal 200 emails per dag
- ❌ Maximaal 1 email per seconde

### Production Access Vereist
Voor outreach emails is **production access** vereist om:
- ✅ Te kunnen verzenden naar niet-geverifieerde email adressen
- ✅ Hogere volumes te ondersteunen (500+ emails/dag)
- ✅ Automatische outreach te kunnen uitvoeren

---

## 🚀 Request Proces

### Stap 1: Access SES Console
1. Log in bij AWS Console
2. Navigeer naar **Simple Email Service (SES)**
3. Selecteer je AWS region (aanbevolen: `eu-west-1` voor EU-based services)
4. Ga naar **Account dashboard**

### Stap 2: Start Request
1. Klik op **"Request production access"** knop
2. Vul het request formulier in (zie hieronder)

---

## 📝 Request Formulier Template

### Mail Type
**Selecteer**: `Transactional`

### Website URL
```
https://turkspot.nl
```

### Use Case Description
```
Service notifications for location owners on Turkspot platform.

We send informational emails to business owners to notify them that their 
location has been added to our platform. These are transactional service 
notifications, not marketing emails.

Emails include:
- One-time notification when location is added to platform
- Claim confirmation emails (after business owner claims their location)
- Claim rejection emails (if claim is rejected by admin)
- Removal confirmation emails (if business owner removes their location)
- Correction confirmation emails (if business owner submits corrections)

We follow AVG/GDPR compliance:
- Only public contact information is used (OSM tags, website scraping)
- Opt-out links are included in all emails
- No marketing content
- Clear service notification purpose
- Gerechtvaardigd belang (legitimate interest) as legal basis
- Audit logging for all email actions (2 year retention)
```

### Expected Sending Volume

**Start Volume**:
- ~50 emails per day

**Growth Plan**:
- Scaling to 250-500 emails per day over 6 months
- Gradual increase: 50 → 100 → 250 → 500 emails/day

**Peak Volume**:
- Maximum 500 emails per day
- No sudden spikes, consistent sending pattern

**Volume Justification**:
- We discover locations via OSM (OpenStreetMap) and add them to our platform
- Each location receives maximum 1 outreach email (one-time notification)
- As we expand to more cities (Rotterdam → The Hague → Amsterdam → Utrecht), volume increases gradually
- We respect rate limiting and build sender reputation gradually

### Bounce and Complaint Handling

**Question**: "Do you have a process to handle bounces and complaints?"

**Answer**: `Yes`

**Process Description**:
```
We have implemented comprehensive bounce and complaint handling:

1. Bounce Tracking:
   - SES bounce events are received via SNS webhooks
   - Bounced emails are immediately marked in our database
   - Invalid email addresses are removed from outreach queue
   - Bounce rate is monitored and kept below 5%

2. Complaint Handling:
   - SES complaint events are received via SNS webhooks
   - Complained emails are immediately opted-out
   - Opt-out status is permanent (never email again)
   - Complaint rate is monitored and kept below 0.1%

3. Opt-out Mechanism:
   - Every email contains opt-out link
   - Opt-out is one-click, immediate
   - Opt-out status is permanent
   - Database check prevents re-emailing after opt-out

4. Monitoring:
   - Daily bounce and complaint rate monitoring
   - Automated alerts for high bounce/complaint rates
   - Regular review of sending practices
   - Sender reputation protection
```

### Additional Information (Optioneel)

Als er ruimte is voor extra informatie, voeg toe:

```
Technical Implementation:
- Email service uses AWS SES via boto3
- Rate limiting implemented at application level (starts at 50/day)
- Exponential backoff for throttling errors
- Email status tracking in database (outreach_emails table)
- Audit logging for AVG compliance

Compliance:
- AVG/GDPR compliant (Dutch/EU privacy law)
- Gerechtvaardigd belang (legitimate interest) as legal basis
- Only public contact information used
- Opt-out always available
- Audit logging (2 year retention)

Sender Reputation:
- We start conservatively (50 emails/day)
- Gradual increase to build reputation
- Consistent sending patterns
- High-quality, relevant content only
- No spam triggers in email content
```

---

## ⏱️ Review Tijd

### Verwachte Review Tijd
- **Typisch**: 24-48 uur
- **Kan langer duren**: Bij complexe use cases of eerste request
- **Email notificatie**: Je ontvangt email wanneer access is goedgekeurd

### Mogelijke Vragen van AWS
AWS kan aanvullende informatie vragen:
- Meer details over bounce/complaint handling
- Verificatie van website en use case
- Uitleg over volume groei
- Compliance documentatie

**Tip**: Houd dit document bij de hand voor eventuele follow-up vragen.

---

## ✅ Na Goedkeuring

### Wat Verandert
1. **Sandbox restrictions opgeheven**:
   - Je kunt nu verzenden naar niet-geverifieerde email adressen
   - Rate limits worden verhoogd (typisch 200 emails/seconde, 50.000/dag voor nieuwe accounts)

2. **Nieuwe Rate Limits**:
   - **Sending Rate**: 200 emails per seconde (typisch)
   - **Daily Quota**: 50.000 emails per dag (typisch)
   - **Note**: Limits kunnen variëren per account en regio

3. **Best Practices**:
   - Start conservatief (50 emails/dag)
   - Bouw geleidelijk op naar 100 → 250 → 500 emails/dag
   - Monitor bounce/complaint rates
   - Behoud consistente sending patterns

### Volgende Stappen
1. **Test Email Verzending**:
   - Verzend test email naar niet-geverifieerd adres
   - Controleer deliverability
   - Test opt-out mechanisme

2. **Monitor Metrics**:
   - Bounce rate (doel: < 5%)
   - Complaint rate (doel: < 0.1%)
   - Sending statistics in SES console

3. **Gradual Scale-up**:
   - Start met 50 emails/dag
   - Verhoog geleidelijk naar 100 → 250 → 500 emails/dag
   - Monitor voor problemen bij elke stap

---

## 📋 Checklist voor Request

Voordat je de request indient, controleer:

- [ ] Domain is geverifieerd in SES (zie `ses-setup-guide.md`)
- [ ] SPF record is geconfigureerd
- [ ] DKIM records zijn geconfigureerd
- [ ] DMARC record is geconfigureerd (optioneel, maar aanbevolen)
- [ ] Use case description is compleet en duidelijk
- [ ] Volume estimates zijn realistisch
- [ ] Bounce/complaint handling proces is beschreven
- [ ] Website URL is correct en actief
- [ ] Email templates zijn AVG-compliant (opt-out links, etc.)

---

## 🔄 Request Status Tracking

### Status Updates
- **Submitted**: Request is ingediend
- **Under Review**: AWS beoordeelt request
- **Additional Info Requested**: AWS vraagt aanvullende informatie
- **Approved**: Production access is goedgekeurd ✅
- **Denied**: Request is afgewezen (herzien en opnieuw indienen)

### Na Afwijzing
Als request wordt afgewezen:
1. **Review feedback**: Lees AWS feedback zorgvuldig
2. **Verbeter request**: Voeg ontbrekende informatie toe
3. **Herindienen**: Dien verbeterde request in
4. **Contact AWS**: Bij twijfel, contact AWS support

---

## 📚 Referenties

- **SES Setup Guide**: `Docs/ses-setup-guide.md`
- **AWS SES Documentation**: https://docs.aws.amazon.com/ses/
- **SES Best Practices**: https://docs.aws.amazon.com/ses/latest/dg/best-practices.html
- **Moving Out of SES Sandbox**: https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html

---

## ✅ Acceptatie Criteria

De SES production access request is klaar wanneer:
- [x] Dit document bestaat met complete template
- [x] Alle benodigde informatie is gedocumenteerd
- [x] Use case description is duidelijk
- [x] Volume estimates zijn realistisch
- [x] Bounce/complaint handling is beschreven
- [x] Checklist is compleet
- [x] Request kan worden ingediend met deze documentatie

---

**Laatste Update**: 2025-01-16  
**Gemaakt Door**: Development Team  
**Status**: 📋 Template Klaar (Request nog niet ingediend)  
**Volgende Stap**: Indienen request in AWS SES Console wanneer klaar

