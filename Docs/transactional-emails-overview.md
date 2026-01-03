# Transactionele Emails Overzicht

Dit document geeft een volledig overzicht van alle transactionele emails die worden verzonden door de Turkspot applicatie, inclusief wanneer ze worden getriggerd, welke context variabelen ze gebruiken, en hoe ze te testen.

## Inhoudsopgave

1. [Overzicht Tabel](#overzicht-tabel)
2. [Email Types](#email-types)
   - [Welcome Email](#1-welcome-email)
   - [Claim Approved](#2-claim-approved)
   - [Claim Rejected](#3-claim-rejected)
   - [Outreach Email](#4-outreach-email)
   - [Expiry Reminder](#5-expiry-reminder)
   - [Removal Confirmation](#6-removal-confirmation)
   - [Correction Confirmation](#7-correction-confirmation)
   - [Weekly Digest](#8-weekly-digest)
3. [Test Script Gebruik](#test-script-gebruik)
4. [Context Variabelen](#context-variabelen)

---

## Overzicht Tabel

| Email Type | Template | Trigger | Taal Support | Context Variabelen |
|------------|----------|--------|--------------|---------------------|
| Welcome | `welcome_email` | Na registratie | NL/TR/EN | `user_name` |
| Claim Approved | `claim_approved` | Admin keurt claim goed | NL/TR/EN | `user_name`, `location_name` |
| Claim Rejected | `claim_rejected` | Admin wijst claim af | NL/TR/EN | `user_name`, `location_name`, `rejection_reason` |
| Outreach | `outreach_email` | Outreach mailer bot | NL/TR/EN | `location_name`, `mapview_link`, `opt_out_link` |
| Expiry Reminder | `expiry_reminder` | Expiry reminder bot | NL/TR/EN | `location_name`, `mapview_link`, `expiry_date`, `free_until` |
| Removal Confirmation | `removal_confirmation` | Gebruiker verwijdert locatie | NL/TR/EN | `location_name`, `removal_reason` |
| Correction Confirmation | `correction_confirmation` | Gebruiker dient correctie in | NL/TR/EN | `location_name` |
| Weekly Digest | `weekly_digest` | Weekly digest worker | NL/TR/EN | `user`, `trending_locations`, `new_polls`, `activity`, `gamification` |

---

## Email Types

### 1. Welcome Email

**Template Bestanden:**
- `Backend/templates/emails/welcome_email.html.j2`
- `Backend/templates/emails/welcome_email.txt.j2`

**Trigger Locatie:**
```184:292:Backend/api/routers/auth.py
@router.post("/send-welcome-email")
async def send_welcome_email(
    user: User = Depends(get_current_user),
    language: str = "nl",
):
```

**Wanneer Getriggerd:**
- Na succesvolle account registratie
- Wordt aangeroepen via `/api/v1/auth/send-welcome-email` endpoint
- Kan handmatig worden getriggerd na signup

**Subject Lines:**
- **NL:** "Welkom bij Turkspot!"
- **TR:** "Turkspot'a Hoş Geldiniz!"
- **EN:** "Welcome to Turkspot!"

**Context Variabelen:**
- `user_name` (string): Naam van de gebruiker (display_name of email prefix)

**Taal:**
- Wordt bepaald via `language` parameter (default: "nl")
- Ondersteunt: `nl`, `tr`, `en`

---

### 2. Claim Approved

**Template Bestanden:**
- `Backend/templates/emails/claim_approved.html.j2`
- `Backend/templates/emails/claim_approved.txt.j2`

**Trigger Locatie:**
```210:265:Backend/services/claim_approval_service.py
    # Send approval email
    try:
        
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Get location name
            location_name_sql = """
                SELECT name FROM locations WHERE id = $1
            """
            location_rows = await fetch(location_name_sql, claim["location_id"])
            location_name = location_rows[0]["name"] if location_rows else "Locatie"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "claim_approved",
                context={
                    "user_name": user_name,
                    "location_name": location_name,
                },
                language=language,
            )
```

**Wanneer Getriggerd:**
- Wanneer een admin een location claim goedkeurt via `approve_claim()` functie
- Automatisch na claim approval in admin interface

**Subject Lines:**
- **NL:** "Uw claim is goedgekeurd - {location_name}"
- **TR:** "Talebiniz onaylandı - {location_name}"
- **EN:** "Your claim has been approved - {location_name}"

**Context Variabelen:**
- `user_name` (string): Naam van de gebruiker die de claim heeft ingediend
- `location_name` (string): Naam van de locatie

**Taal:**
- Default: "nl" (TODO: Get from user preferences)

---

### 3. Claim Rejected

**Template Bestanden:**
- `Backend/templates/emails/claim_rejected.html.j2`
- `Backend/templates/emails/claim_rejected.txt.j2`

**Trigger Locatie:**
```380:435:Backend/services/claim_approval_service.py
    # Send rejection email
    try:
        
        if user_rows and user_rows[0].get("email"):
            user_email = user_rows[0]["email"]
            user_name = user_rows[0].get("user_name") or "Gebruiker"
            
            # Get location name
            location_name_sql = """
                SELECT name FROM locations WHERE id = $1
            """
            location_rows = await fetch(location_name_sql, claim["location_id"])
            location_name = location_rows[0]["name"] if location_rows else "Locatie"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "claim_rejected",
                context={
                    "user_name": user_name,
                    "location_name": location_name,
                    "rejection_reason": rejection_reason,
                },
                language=language,
            )
```

**Wanneer Getriggerd:**
- Wanneer een admin een location claim afwijst via `reject_claim()` functie
- Automatisch na claim rejection in admin interface

**Subject Lines:**
- **NL:** "Uw claim is afgewezen - {location_name}"
- **TR:** "Talebiniz reddedildi - {location_name}"
- **EN:** "Your claim has been rejected - {location_name}"

**Context Variabelen:**
- `user_name` (string): Naam van de gebruiker die de claim heeft ingediend
- `location_name` (string): Naam van de locatie
- `rejection_reason` (string, optional): Reden voor afwijzing

**Taal:**
- Default: "nl" (TODO: Get from user preferences)

---

### 4. Outreach Email

**Template Bestanden:**
- `Backend/templates/emails/outreach_email.html.j2`
- `Backend/templates/emails/outreach_email.txt.j2`

**Trigger Locatie:**
```277:300:Backend/services/outreach_mailer_service.py
                html_body, text_body = template_service.render_template(
                    template_name="outreach_email",
                    context=template_context,
                    language=language,
                )
            except Exception as e:
                error_msg = f"Template rendering failed for location {email_record['location_id']}: {str(e)}"
                errors.append(error_msg)
                logger.error(
                    "outreach_template_render_failed",
                    location_id=email_record["location_id"],
                    email=email_record["email"],
                    error=str(e),
                    exc_info=True,
                )
                failed_count += 1
                continue
            
            # Determine email subject based on language
            if language == "tr":
                subject = f"Konumunuz Turkspot'ta - {email_record['location_name']}"
            elif language == "en":
                subject = f"Your location is on Turkspot - {email_record['location_name']}"
            else:
                subject = f"Uw locatie staat op Turkspot - {email_record['location_name']}"
```

**Wanneer Getriggerd:**
- Via `outreach_mailer_bot` worker die queued emails uit `outreach_emails` tabel verwerkt
- Wordt automatisch verzonden wanneer een locatie wordt gemaild via outreach systeem
- Kan handmatig worden getriggerd via admin endpoint `/api/v1/admin/outreach-emails/send`

**Subject Lines:**
- **NL:** "Uw locatie staat op Turkspot - {location_name}"
- **TR:** "Konumunuz Turkspot'ta - {location_name}"
- **EN:** "Your location is on Turkspot - {location_name}"

**Context Variabelen:**
- `location_name` (string): Naam van de locatie
- `mapview_link` (string): Link naar mapview met focus parameter
- `opt_out_link` (string): Link voor opt-out functionaliteit

**Taal:**
- Default: "nl"
- Kan worden uitgebreid met user preferences

---

### 5. Expiry Reminder

**Template Bestanden:**
- `Backend/templates/emails/expiry_reminder.html.j2`
- `Backend/templates/emails/expiry_reminder.txt.j2`

**Trigger Locatie:**
```94:180:Backend/services/expiry_reminder_service.py
async def send_expiry_reminder(
    claim_id: int,
    location_id: int,
    email: str,
    location_name: str,
    free_until: datetime,
    location_lat: Optional[float] = None,
    location_lng: Optional[float] = None,
    language: str = "nl",
) -> bool:
    """
    Send expiry reminder email to claim owner.
    
    Args:
        claim_id: Token location claim ID
        location_id: Location ID
        email: Recipient email address
        location_name: Name of the location
        free_until: Expiry date
        location_lat: Location latitude (optional)
        location_lng: Location longitude (optional)
        language: Language code (nl, tr, en)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Generate mapview link
        mapview_link = generate_mapview_link(location_id, location_lat, location_lng)
        
        # Format expiry date
        expiry_date_str = free_until.strftime("%d-%m-%Y") if free_until else "binnenkort"
        
        # Prepare template context
        context = {
            "location_name": location_name,
            "mapview_link": mapview_link,
            "expiry_date": expiry_date_str,
            "free_until": free_until.isoformat() if free_until else None,
        }
        
        # Get email template service
        template_service = get_email_template_service()
        
        # Render templates
        html_body, text_body = template_service.render_template(
            "expiry_reminder",
            context=context,
            language=language,
        )
```

**Wanneer Getriggerd:**
- Via `expiry_reminder_bot` worker die expirerende claims detecteert
- Wordt automatisch verzonden wanneer een claim binnen X dagen verloopt
- Kan handmatig worden getriggerd via `run_expiry_reminder.py` script

**Subject Lines:**
- **NL:** "Uw gratis periode loopt bijna af - {location_name}"
- **TR:** "Ücretsiz döneminiz yakında sona eriyor - {location_name}"
- **EN:** "Your free period is ending soon - {location_name}"

**Context Variabelen:**
- `location_name` (string): Naam van de locatie
- `mapview_link` (string): Link naar mapview met focus parameter
- `expiry_date` (string): Geformatteerde expiry datum (DD-MM-YYYY)
- `free_until` (string, ISO format): Expiry datum in ISO format

**Taal:**
- Wordt bepaald via `language` parameter (default: "nl")
- Ondersteunt: `nl`, `tr`, `en`

---

### 6. Removal Confirmation

**Template Bestanden:**
- `Backend/templates/emails/removal_confirmation.html.j2`
- `Backend/templates/emails/removal_confirmation.txt.j2`

**Trigger Locatie:**
```282:333:Backend/api/routers/outreach_claims.py
    # Send removal confirmation email
    if claim_info.claimed_by_email:
        try:
            # Get location name
            location_name_sql = """
                SELECT name FROM locations WHERE id = $1
            """
            location_row = await fetchrow(location_name_sql, claim_info.location_id)
            location_name = location_row.get("name") if location_row else "Locatie"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences or email domain
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "removal_confirmation",
                context={
                    "location_name": location_name,
                    "removal_reason": request.reason,
                },
                language=language,
            )
```

**Wanneer Getriggerd:**
- Wanneer een gebruiker een locatie verwijdert via token-based claim endpoint
- Wordt getriggerd via `/api/v1/outreach-claims/{token}/remove` endpoint

**Subject Lines:**
- **NL:** "Uw locatie wordt verwijderd - {location_name}"
- **TR:** "Konumunuz kaldırılıyor - {location_name}"
- **EN:** "Your location is being removed - {location_name}"

**Context Variabelen:**
- `location_name` (string): Naam van de locatie
- `removal_reason` (string, optional): Reden voor verwijdering

**Taal:**
- Default: "nl" (TODO: Get from user preferences or email domain)

---

### 7. Correction Confirmation

**Template Bestanden:**
- `Backend/templates/emails/correction_confirmation.html.j2`
- `Backend/templates/emails/correction_confirmation.txt.j2`

**Trigger Locatie:**
```368:427:Backend/api/routers/outreach_claims.py
    # Send correction confirmation email
    # Use claimed_by_email if available, otherwise we can't send email
    recipient_email = claim_info.claimed_by_email
    if not recipient_email:
        # Try to get email from token if it's a claim token
        # For now, we'll skip email if no email is available
        logger.warning(
            "correction_email_skipped_no_email",
            location_id=claim_info.location_id,
        )
    else:
        try:
            # Get location name
            location_name_sql = """
                SELECT name FROM locations WHERE id = $1
            """
            location_row = await fetchrow(location_name_sql, claim_info.location_id)
            location_name = location_row.get("name") if location_row else "Locatie"
            
            # Determine language (default to NL)
            language = "nl"  # TODO: Get from user preferences or email domain
            
            # Render email template
            template_service = get_email_template_service()
            html_body, text_body = template_service.render_template(
                "correction_confirmation",
                context={
                    "location_name": location_name,
                },
                language=language,
            )
```

**Wanneer Getriggerd:**
- Wanneer een gebruiker een correctie indient via token-based claim endpoint
- Wordt getriggerd via `/api/v1/outreach-claims/{token}/correct` endpoint

**Subject Lines:**
- **NL:** "Bedankt voor uw correctie - {location_name}"
- **TR:** "Düzeltmeniz için teşekkürler - {location_name}"
- **EN:** "Thank you for your correction - {location_name}"

**Context Variabelen:**
- `location_name` (string): Naam van de locatie

**Taal:**
- Default: "nl" (TODO: Get from user preferences or email domain)

---

### 8. Weekly Digest

**Template Bestanden:**
- `Backend/templates/emails/weekly_digest.html.j2`
- `Backend/templates/emails/weekly_digest.txt.j2`

**Trigger Locatie:**
```209:265:Backend/app/workers/digest_worker.py
async def send_digest_email(user: Dict[str, Any], content: Dict[str, Any]) -> bool:
    """
    Send weekly digest email to a user.
    """
    email_service = get_email_service()
    
    # Generate email subject based on language
    language = content.get("language", "nl")
    subjects = {
        "nl": f"Weekoverzicht Turkspot - {datetime.now(timezone.utc).strftime('%d %B')}",
        "tr": f"Turkspot Haftalık Özet - {datetime.now(timezone.utc).strftime('%d %B')}",
        "en": f"Turkspot Weekly Summary - {datetime.now(timezone.utc).strftime('%B %d')}",
    }
    subject = subjects.get(language, subjects["nl"])
    
    # Render email template
    context = {
        **content,
        "base_url": os.getenv("FRONTEND_URL", "https://turkspot.nl"),
        "unsubscribe_url": f"{os.getenv('FRONTEND_URL', 'https://turkspot.nl')}/#/account",
    }
    
    try:
        html_body, text_body = email_service.render_template("weekly_digest", context)
```

**Wanneer Getriggerd:**
- Via `digest_worker` die wekelijks draait (meestal op maandag)
- Wordt automatisch verzonden naar gebruikers die hebben ingeschakeld voor email digests
- Kan handmatig worden getriggerd via `digest_worker.py` script

**Subject Lines:**
- **NL:** "Weekoverzicht Turkspot - {date}"
- **TR:** "Turkspot Haftalık Özet - {date}"
- **EN:** "Turkspot Weekly Summary - {date}"

**Context Variabelen:**
- `user` (dict): User informatie met `user_id`, `email`, `display_name`, `city_key`
- `trending_locations` (list): Lijst van trending locaties met:
  - `name` (string)
  - `city` (string)
  - `category` (string)
  - `score` (float)
  - `check_ins_count` (int)
  - `reactions_count` (int)
  - `notes_count` (int)
- `new_polls` (list): Lijst van nieuwe polls met:
  - `id` (int)
  - `title` (string)
  - `question` (string)
  - `poll_type` (string)
  - `is_sponsored` (bool)
  - `created_at` (datetime)
  - `option_count` (int)
- `activity` (dict): Activity summary met:
  - `notes_added` (int)
  - `reactions_given` (int)
  - `check_ins` (int)
  - `locations_discovered` (int)
- `gamification` (dict): Gamification data met:
  - `total_xp` (int)
  - `current_streak` (int)
  - `badges_earned` (int)
- `language` (string): Taal code
- `base_url` (string): Frontend base URL
- `unsubscribe_url` (string): URL voor unsubscribe

**Taal:**
- Wordt bepaald via user preferences (`language_pref` in user_profiles)
- Ondersteunt: `nl`, `tr`, `en`

---

## Test Script Gebruik

Het test script `Backend/scripts/test_transactional_emails.py` kan worden gebruikt om alle transactionele emails te testen.

### Basis Gebruik

```bash
# Alle emails verzenden naar een test emailadres
python -m scripts.test_transactional_emails test@example.com --all

# Specifieke emails verzenden
python -m scripts.test_transactional_emails test@example.com --welcome --claim_approved

# Met andere taal
python -m scripts.test_transactional_emails test@example.com --all --language tr

# Alle beschikbare email types
python -m scripts.test_transactional_emails test@example.com --welcome
python -m scripts.test_transactional_emails test@example.com --claim_approved
python -m scripts.test_transactional_emails test@example.com --claim_rejected
python -m scripts.test_transactional_emails test@example.com --outreach
python -m scripts.test_transactional_emails test@example.com --expiry_reminder
python -m scripts.test_transactional_emails test@example.com --removal_confirmation
python -m scripts.test_transactional_emails test@example.com --correction_confirmation
python -m scripts.test_transactional_emails test@example.com --weekly_digest
```

### Command Line Opties

- `recipient` (required): Email adres om test emails naar te verzenden
- `--all`: Verzend alle transactionele emails
- `--language {nl|tr|en}`: Taal voor emails (default: nl)
- `--{email_type}`: Verzend specifieke email type (bijv. `--welcome`, `--claim_approved`)

### Output

Het script geeft een summary weer met:
- Welke emails zijn verzonden
- Success/failure status per email
- Totaal aantal succesvol verzonden emails

---

## Context Variabelen

### Standaard Context Variabelen

Alle emails krijgen automatisch de volgende context variabelen via `EmailTemplateService._get_default_context()`:

- `language` (string): Taal code (nl, tr, en)
- `base_url` (string): Frontend base URL (van `FRONTEND_URL` env var)
- `unsubscribe_url` (string): URL naar account preferences pagina

### Email-specifieke Context Variabelen

Zie de individuele email type secties hierboven voor specifieke context variabelen per email type.

### Voorbeelden

**Welcome Email Context:**
```python
{
    "user_name": "Test Gebruiker",
    "language": "nl",
    "base_url": "https://turkspot.nl",
    "unsubscribe_url": "https://turkspot.nl/#/account"
}
```

**Outreach Email Context:**
```python
{
    "location_name": "Test Restaurant",
    "mapview_link": "https://turkspot.nl/#/map?focus=123",
    "opt_out_link": "https://turkspot.nl/#/opt-out?token=abc123",
    "language": "nl",
    "base_url": "https://turkspot.nl",
    "unsubscribe_url": "https://turkspot.nl/#/account"
}
```

**Weekly Digest Context:**
```python
{
    "user": {
        "user_id": "uuid",
        "email": "user@example.com",
        "display_name": "Test User",
        "city_key": "rotterdam"
    },
    "trending_locations": [...],
    "new_polls": [...],
    "activity": {...},
    "gamification": {...},
    "language": "nl",
    "base_url": "https://turkspot.nl",
    "unsubscribe_url": "https://turkspot.nl/#/account"
}
```

---

## Template Systeem

Alle emails gebruiken het Jinja2 template systeem met base template inheritance:

- **Base Template:** `Backend/templates/emails/base.html.j2` (HTML) en `base.txt.j2` (plain text)
- **Template Service:** `Backend/services/email_template_service.py`
- **Email Service:** `Backend/services/email_service.py`

Templates ondersteunen:
- Meertaligheid (NL/TR/EN)
- Consistent branding
- Responsive design
- Plain text fallback

---

## Email Provider

Emails worden verzonden via Brevo (voorheen Sendinblue) email provider:

- **Provider:** `Backend/services/email/brevo_provider.py`
- **Configuratie:** Via environment variables (`EMAIL_PROVIDER=brevo`, `BREVO_API_KEY`)
- **From Email:** `info@turkspot.app` (moet geverifieerd zijn in Brevo)

---

## Notities

- Alle emails worden asynchroon verzonden en falen niet de hoofdoperatie
- Email failures worden gelogd maar blokkeren niet de business logic
- Taal wordt momenteel meestal default naar "nl" gezet, maar kan worden uitgebreid met user preferences
- Weekly digest heeft complexe context data die wordt gegenereerd door `digest_worker.py`









