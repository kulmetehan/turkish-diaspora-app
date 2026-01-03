# Brevo Webhook Setup Guide

## Webhook Configuration in Brevo Dashboard

### Step 1: Navigate to Webhooks
Go to: https://app.brevo.com/settings/webhooks

### Step 2: Create New Webhook
Click "Add a webhook" or "Create webhook"

### Step 3: Configure Webhook

**URL:**
```
https://api.turkspot.nl/api/v1/brevo/webhook
```

**Type:**
- Select **Outbound** (Brevo sends events to your server)

**Authentication Method:**
- **Recommended: Token**
  - Generate a secure token in Brevo
  - Save this token - you'll need it for webhook signature verification
  - Store in environment variable: `BREVO_WEBHOOK_SECRET` (optional, for future verification)

**Category:**
- Select **Transactional emails**

**Events to Track:**
Select the following events:
- ✅ `delivered` - Email successfully delivered
- ✅ `hard_bounce` - Permanent bounce (invalid email)
- ✅ `soft_bounce` - Temporary bounce (mailbox full, etc.)
- ✅ `unsubscribed` - User unsubscribed
- ⚠️ `opened` - Email opened (optional, for analytics)
- ⚠️ `clicked` - Link clicked (optional, for analytics)

### Step 4: Save Webhook
Click "Save" or "Create"

### Step 5: Test Webhook
Brevo will send a test webhook to verify the endpoint works.

## Webhook Endpoint

The webhook endpoint is already implemented at:
- **Path**: `/api/v1/brevo/webhook`
- **Method**: POST
- **Handler**: `Backend/api/routers/brevo_webhooks.py`

## Webhook Events Handled

1. **Bounce Events** (`hard_bounce`, `soft_bounce`):
   - Updates `outreach_emails` status to `bounced`
   - Sets `bounced_at` timestamp
   - Records `bounce_reason`

2. **Delivery Events** (`delivered`):
   - Updates `outreach_emails` status to `delivered`
   - Sets `delivered_at` timestamp

3. **Unsubscribe Events** (`unsubscribed`):
   - Updates `outreach_emails` status to `opted_out`
   - Updates consent flags in `user_consents` table

## Troubleshooting

### Webhook Not Receiving Events

1. **Check Webhook URL is accessible:**
   ```bash
   curl -X POST https://api.turkspot.nl/api/v1/brevo/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
   ```

2. **Check Brevo webhook logs:**
   - Go to: https://app.brevo.com/settings/webhooks
   - Click on your webhook
   - Check "Webhook logs" or "Event history"
   - Look for failed delivery attempts

3. **Verify authentication:**
   - If using Token authentication, verify the token matches
   - Check webhook signature in request headers

### Webhook Receiving Events But Not Processing

1. **Check backend logs:**
   ```bash
   # Look for brevo_webhook events in logs
   grep "brevo_webhook" /path/to/logs
   ```

2. **Check database:**
   - Verify `outreach_emails` table is being updated
   - Check `message_id` matches between sent emails and webhook events

## Security

### Webhook Signature Verification (Future Enhancement)

Currently, webhook signature verification is not implemented. For production, you should:

1. Enable Token authentication in Brevo
2. Store token in `BREVO_WEBHOOK_SECRET` environment variable
3. Implement signature verification in `brevo_webhooks.py`

Example verification (to be implemented):
```python
import hmac
import hashlib

def verify_brevo_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
```

## Testing

After setting up the webhook:

1. Send a test email via the test script:
   ```bash
   python -m scripts.test_brevo_email your-email@example.com
   ```

2. Check webhook events in Brevo dashboard
3. Check database for status updates:
   ```sql
   SELECT id, email, status, message_id, delivered_at, bounced_at
   FROM outreach_emails
   ORDER BY created_at DESC
   LIMIT 10;
   ```










