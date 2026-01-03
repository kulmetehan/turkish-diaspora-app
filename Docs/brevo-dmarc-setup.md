# DMARC DNS Setup voor Brevo

## Probleem
Brevo dashboard toont: `'rua' tag is missing` voor `turkspot.app`

Dit kan emails blokkeren bij Gmail, Yahoo en Microsoft.

## Oplossing: DMARC DNS Record toevoegen/updaten

### Stap 1: Check huidige DMARC record

Check of je al een DMARC record hebt:

```bash
# Via terminal
dig _dmarc.turkspot.app TXT

# Of online
# https://mxtoolbox.com/dmarc.aspx
```

### Stap 2: DMARC Record aanmaken/updaten

**Als je nog GEEN DMARC record hebt:**

Voeg deze DNS TXT record toe aan `_dmarc.turkspot.app`:

```
v=DMARC1; p=none; rua=mailto:dmarc@turkspot.app; ruf=mailto:dmarc@turkspot.app; fo=1
```

**Als je WEL al een DMARC record hebt:**

Update je bestaande DMARC record en voeg de `rua` tag toe:

```
v=DMARC1; p=quarantine; rua=mailto:dmarc@turkspot.app; ruf=mailto:dmarc@turkspot.app
```

### Stap 3: DMARC Record uitleg

- `v=DMARC1` - DMARC versie 1
- `p=none` - Policy: geen actie (start met none voor testing)
  - Later kun je `p=quarantine` (spam folder) of `p=reject` (blokkeer) gebruiken
- `rua=mailto:dmarc@turkspot.app` - Aggregate reports email (dit was missing!)
- `ruf=mailto:dmarc@turkspot.app` - Forensic reports email (optioneel)
- `fo=1` - Failure options (optioneel)

### Stap 4: DNS Record toevoegen

**Bij je DNS provider (bijv. Cloudflare, Namecheap, etc.):**

1. Ga naar DNS Management
2. Voeg een nieuwe TXT record toe:
   - **Name/Host**: `_dmarc`
   - **Type**: `TXT`
   - **Value/Content**: `v=DMARC1; p=none; rua=mailto:dmarc@turkspot.app; ruf=mailto:dmarc@turkspot.app; fo=1`
   - **TTL**: 3600 (of default)

3. Sla op

### Stap 5: Verificatie

Na 5-15 minuten (DNS propagation):

1. Check of record actief is:
   ```bash
   dig _dmarc.turkspot.app TXT
   ```

2. Of gebruik online tool:
   - https://mxtoolbox.com/dmarc.aspx
   - https://dmarcian.com/dmarc-inspector/

3. Check Brevo dashboard:
   - https://app.brevo.com/settings/senders
   - DMARC status zou nu "OK" moeten zijn

### Stap 6: Email adres voor reports (optioneel)

Je kunt een email adres `dmarc@turkspot.app` aanmaken om DMARC reports te ontvangen, maar dit is niet verplicht. De `rua` tag moet gewoon bestaan, ook al check je de reports niet.

### Stap 7: Test opnieuw

Na DNS propagation (15-30 minuten):

```bash
cd Backend
source .venv/bin/activate
python scripts/test_brevo_email.py m.kul@lamarka.nl
```

## Belangrijk

- **DNS propagation**: Kan 15 minuten tot 48 uur duren (meestal 15-30 minuten)
- **Start met `p=none`**: Test eerst voordat je `p=quarantine` of `p=reject` gebruikt
- **Brevo check**: Wacht 15-30 minuten na DNS update voordat Brevo het detecteert

## Troubleshooting

**DMARC record wordt niet gedetecteerd:**
- Wacht langer (DNS propagation)
- Check of record correct is toegevoegd: `dig _dmarc.turkspot.app TXT`
- Check of er geen typo's zijn in het record

**Emails worden nog steeds geblokkeerd:**
- Check ook DKIM en SPF records (Brevo dashboard toont deze)
- Wacht tot DNS volledig gepropageerd is
- Check spam folder (kan tijdelijk in spam komen tijdens testing)








