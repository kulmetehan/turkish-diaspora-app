# Email Spam Prevention Guide

## Probleem
Emails komen aan maar belanden in spam folder bij Gmail, Outlook, etc.

## Oplossingen

### 1. DNS Records (SPF, DKIM, DMARC)
**Status**: Zie `Docs/brevo-dmarc-setup.md` voor DMARC setup

**Checklist**:
- [ ] SPF record is correct geconfigureerd (Brevo dashboard toont status)
- [ ] DKIM records zijn correct (Brevo dashboard toont status)
- [ ] DMARC record is geconfigureerd met `rua` tag (zie `brevo-dmarc-setup.md`)

**Verificatie**:
```bash
# Check SPF
dig turkspot.app TXT | grep spf

# Check DKIM (Brevo genereert deze automatisch)
# Check in Brevo dashboard: https://app.brevo.com/settings/senders

# Check DMARC
dig _dmarc.turkspot.app TXT
```

### 2. Email Headers Verbeteren
**Status**: ✅ Geïmplementeerd in `Backend/services/email/brevo_provider.py`

**Headers die zijn toegevoegd**:
- `List-Unsubscribe` - Verplicht voor bulk emails
- `List-Unsubscribe-Post` - One-click unsubscribe (Gmail vereist dit)
- `Reply-To` - Helpt met email reputation
- `Precedence: bulk` - Geeft aan dat het bulk email is
- `X-Mailer` - Identificeert de email service
- `X-Auto-Response-Suppress` - Voorkomt out-of-office loops

### 3. Base64 Images Vermijden
**Probleem**: Base64 encoded images kunnen spam triggers zijn omdat:
- Ze de email grootte enorm verhogen
- Ze kunnen worden gezien als verdacht door spam filters
- Gmail clipt emails > 100KB

**Oplossingen**:
1. **Hosted Images** (aanbevolen):
   - Upload afbeelding naar publieke URL (bijv. `https://turkspot.app/assets/turkspotbot-mailhead.png`)
   - Gebruik `<img src="https://turkspot.app/assets/turkspotbot-mailhead.png">` in plaats van base64
   - Voeg `alt` text toe voor accessibility

2. **Kleinere Afbeeldingen**:
   - Gebruik `turkspotbot-mailhead.png` (73KB) in plaats van `turkspotbot.png` (200KB)
   - Comprimeer afbeelding verder indien mogelijk
   - Overweeg SVG voor logo's (maar niet alle email clients ondersteunen SVG)

3. **Fallback naar Text Logo**:
   - Als afbeelding niet beschikbaar is, gebruik tekst logo ("TS" of "TurkSpot")
   - Dit voorkomt broken images en vermindert email grootte

**Implementatie**:
- Update `Backend/services/email_template_service.py` om hosted image URL te gebruiken
- Of: Upload afbeelding naar publieke CDN/static hosting

### 4. Email Content Optimaliseren
**Spam Trigger Woorden Vermijden**:
- ❌ "Gratis", "Klik hier", "Actie nu", "Beperkte tijd"
- ✅ Gebruik natuurlijke taal: "Welkom", "Overzicht", "Bekijk"

**Content Best Practices**:
- ✅ Duidelijke subject lines (geen ALL CAPS)
- ✅ Balans tussen tekst en HTML
- ✅ Alt text voor alle images
- ✅ Plain text versie altijd aanwezig
- ✅ Geen te veel links (max 3-5 per email)
- ✅ Geen verdachte URL's (gebruik je eigen domain)

**Huidige Status**:
- ✅ Subject lines zijn duidelijk en niet spammy
- ✅ Plain text versie wordt gegenereerd
- ✅ Alt text is aanwezig voor images
- ✅ Links gebruiken eigen domain (turkspot.app)

### 5. Email Reputation Opbouwen
**Strategie**:
1. **Consistent Sender**:
   - ✅ Gebruik altijd `info@turkspot.app` als sender
   - ✅ Consistent sender name ("Turkspot" of "TurkSpot")

2. **Warm-up Period**:
   - Start met kleine volumes (10-20 emails/dag)
   - Verhoog geleidelijk naar hogere volumes
   - Monitor bounce rate en spam complaints

3. **Engagement Tracking**:
   - Monitor open rates (via Brevo dashboard)
   - Monitor click rates
   - Monitor spam complaints (via Brevo webhooks)
   - Monitor bounce rates

4. **List Hygiene**:
   - Verwijder hard bounces direct
   - Verwijder soft bounces na 3 pogingen
   - Respecteer opt-outs direct
   - Verwijder inactieve subscribers na 6-12 maanden

### 6. Brevo Best Practices
**Sender Verification**:
- ✅ Sender email (`info@turkspot.app`) is geverifieerd in Brevo
- ✅ Domain is geverifieerd (SPF, DKIM, DMARC)

**Rate Limiting**:
- Brevo heeft rate limits (check dashboard)
- Implementeer backoff bij rate limits
- Gebruik queue systeem voor bulk emails

**Webhooks**:
- ✅ Configureer webhooks voor bounces en spam complaints
- ✅ Verwerk bounces automatisch
- ✅ Verwerk spam complaints automatisch

### 7. Testen en Monitoring
**Tools**:
- **mail-tester.com**: Test email spam score (doel: > 8/10)
- **Gmail Spam Test**: Stuur test email naar Gmail en check spam folder
- **Brevo Dashboard**: Monitor deliverability metrics

**Test Checklist**:
- [ ] Email komt aan in inbox (niet spam)
- [ ] Images worden correct getoond
- [ ] Links werken correct
- [ ] Unsubscribe link werkt
- [ ] Plain text versie is leesbaar
- [ ] Email grootte < 100KB (voor Gmail)

### 8. Actie Items
**Prioriteit 1 (Direct)**:
- [ ] Check SPF/DKIM/DMARC status in Brevo dashboard
- [ ] Test email met mail-tester.com
- [ ] Monitor spam folder voor test emails

**Prioriteit 2 (Binnen 1 week)**:
- [ ] Overweeg hosted images in plaats van base64
- [ ] Implementeer webhook handlers voor bounces/complaints
- [ ] Setup email reputation monitoring

**Prioriteit 3 (Binnen 1 maand)**:
- [ ] Implementeer list hygiene (verwijder bounces)
- [ ] Setup A/B testing voor subject lines
- [ ] Monitor en verbeter engagement rates

## Troubleshooting

**Emails belanden nog steeds in spam**:
1. Check DNS records (SPF, DKIM, DMARC)
2. Test met mail-tester.com
3. Check Brevo dashboard voor sender reputation
4. Overweeg hosted images in plaats van base64
5. Verminder email grootte (< 100KB)
6. Check content op spam trigger woorden

**Gmail specifiek**:
- Gmail heeft strikte spam filters
- Base64 images kunnen trigger zijn
- Email grootte > 100KB kan clipping veroorzaken
- Te veel links kunnen trigger zijn
- Gebruik Gmail's "Mark as Not Spam" om reputation te verbeteren

**Outlook specifiek**:
- Outlook heeft eigen spam filters
- Check Junk Email folder
- Mark emails als "Not Junk" om reputation te verbeteren

## Referenties
- [Brevo Deliverability Guide](https://help.brevo.com/hc/en-us/articles/209467485)
- [Gmail Bulk Sender Guidelines](https://support.google.com/mail/answer/81126)
- [mail-tester.com](https://www.mail-tester.com/)
- [DMARC Inspector](https://dmarcian.com/dmarc-inspector/)




