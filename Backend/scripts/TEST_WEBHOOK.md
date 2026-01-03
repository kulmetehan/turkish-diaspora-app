# Brevo Webhook Testen

## Methode 1: Lokaal testen met test script

### Stap 1: Start de backend
```bash
cd Backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Stap 2: In een nieuwe terminal, run het test script
```bash
cd Backend
source .venv/bin/activate
python scripts/test_brevo_webhook.py
```

Dit test:
- ✅ Delivery event verwerking
- ✅ Bounce event verwerking  
- ✅ Token authenticatie (moet 401 geven bij invalid token)

## Methode 2: Echte email sturen en webhook events bekijken

### Stap 1: Stuur een test email
```bash
cd Backend
source .venv/bin/activate
python scripts/test_brevo_email.py jouw-email@example.com
```

### Stap 2: Check Brevo dashboard
1. Ga naar: https://app.brevo.com/transactional/email/logs
2. Kijk of de email is verzonden
3. Kijk of er webhook events zijn: https://app.brevo.com/settings/webhooks
4. Check de webhook logs voor delivery/bounce events

### Stap 3: Check database
```sql
SELECT id, email, status, message_id, delivered_at, bounced_at, created_at
FROM outreach_emails
ORDER BY created_at DESC
LIMIT 10;
```

## Methode 3: Brevo webhook test functie gebruiken

1. Ga naar: https://app.brevo.com/settings/webhooks
2. Klik op je webhook configuratie
3. Klik op "Test" of "Send test webhook"
4. Brevo stuurt een test event naar je endpoint
5. Check je backend logs voor het event

## Troubleshooting

### Webhook wordt niet aangeroepen
- ✅ Check of `BREVO_WEBHOOK_SECRET` in `.env` staat
- ✅ Check of de webhook URL correct is: `https://api.turkspot.nl/api/v1/brevo/webhook`
- ✅ Check of de token in Brevo dashboard overeenkomt met `BREVO_WEBHOOK_SECRET`
- ✅ Check Brevo webhook logs voor errors

### 401 Unauthorized
- ✅ Check of `Authorization: Bearer <token>` header wordt meegestuurd
- ✅ Check of token in Brevo dashboard overeenkomt met `.env`

### Webhook events worden niet verwerkt
- ✅ Check backend logs voor errors
- ✅ Check of `message_id` in database wordt opgeslagen
- ✅ Check of email status wordt geüpdatet (delivered_at, bounced_at)










