# Backend/scripts/test_transactional_emails.py
"""
Test script voor het verzenden van transactionele emails.

Gebruik:
    python -m scripts.test_transactional_emails test@example.com --all
    python -m scripts.test_transactional_emails test@example.com --welcome --claim_approved
    python -m scripts.test_transactional_emails test@example.com --language tr
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import uuid4

# Path setup
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from services.email_service import get_email_service
from services.email_template_service import get_email_template_service
from services.db_service import init_db_pool

configure_logging(service_name="script")
logger = get_logger()

# Email type definitions
EMAIL_TYPES = {
    "welcome": {
        "template": "welcome_email",
        "context": {"user_name": "Test Gebruiker"},
        "subject_nl": "Welkom bij Turkspot!",
        "subject_tr": "Turkspot'a Hoş Geldiniz!",
        "subject_en": "Welcome to Turkspot!",
    },
    "claim-approved": {
        "template": "claim_approved",
        "context": {"user_name": "Test Gebruiker", "location_name": "Test Restaurant"},
        "subject_nl": "Uw claim is goedgekeurd - Test Restaurant",
        "subject_tr": "Talebiniz onaylandı - Test Restaurant",
        "subject_en": "Your claim has been approved - Test Restaurant",
    },
    "claim-rejected": {
        "template": "claim_rejected",
        "context": {
            "user_name": "Test Gebruiker",
            "location_name": "Test Restaurant",
            "rejection_reason": "Test reden voor afwijzing",
        },
        "subject_nl": "Uw claim is afgewezen - Test Restaurant",
        "subject_tr": "Talebiniz reddedildi - Test Restaurant",
        "subject_en": "Your claim has been rejected - Test Restaurant",
    },
    "outreach": {
        "template": "outreach_email",
        "context": {
            "location_name": "Test Restaurant",
            "mapview_link": "https://turkspot.app/#/map?focus=123",
            "opt_out_link": "https://turkspot.app/#/opt-out?token=test-token",
        },
        "subject_nl": "Uw locatie staat op Turkspot - Test Restaurant",
        "subject_tr": "Konumunuz Turkspot'ta - Test Restaurant",
        "subject_en": "Your location is on Turkspot - Test Restaurant",
    },
    "expiry-reminder": {
        "template": "expiry_reminder",
        "context": {
            "location_name": "Test Restaurant",
            "mapview_link": "https://turkspot.app/#/map?focus=123",
            "expiry_date": (datetime.now() + timedelta(days=7)).strftime("%d-%m-%Y"),
            "free_until": (datetime.now() + timedelta(days=7)).isoformat(),
        },
        "subject_nl": "Uw gratis periode loopt bijna af - Test Restaurant",
        "subject_tr": "Ücretsiz döneminiz yakında sona eriyor - Test Restaurant",
        "subject_en": "Your free period is ending soon - Test Restaurant",
    },
    "removal-confirmation": {
        "template": "removal_confirmation",
        "context": {
            "location_name": "Test Restaurant",
            "removal_reason": "Test reden voor verwijdering",
        },
        "subject_nl": "Uw locatie wordt verwijderd - Test Restaurant",
        "subject_tr": "Konumunuz kaldırılıyor - Test Restaurant",
        "subject_en": "Your location is being removed - Test Restaurant",
    },
    "correction-confirmation": {
        "template": "correction_confirmation",
        "context": {"location_name": "Test Restaurant"},
        "subject_nl": "Bedankt voor uw correctie - Test Restaurant",
        "subject_tr": "Düzeltmeniz için teşekkürler - Test Restaurant",
        "subject_en": "Thank you for your correction - Test Restaurant",
    },
    "weekly-digest": {
        "template": "weekly_digest",
        "context": None,  # Will be generated dynamically
        "subject_nl": f"Weekoverzicht Turkspot - {datetime.now(timezone.utc).strftime('%d %B')}",
        "subject_tr": f"Turkspot Haftalık Özet - {datetime.now(timezone.utc).strftime('%d %B')}",
        "subject_en": f"Turkspot Weekly Summary - {datetime.now(timezone.utc).strftime('%B %d')}",
    },
    "location-submission-received": {
        "template": "location_submission_received",
        "context": {"user_name": "Test Gebruiker", "location_name": "Test Restaurant"},
        "subject_nl": "Uw locatie is ingediend - Test Restaurant",
        "subject_tr": "Konumunuz gönderildi - Test Restaurant",
        "subject_en": "Your location has been submitted - Test Restaurant",
    },
    "location-submission-approved": {
        "template": "location_submission_approved",
        "context": {
            "user_name": "Test Gebruiker",
            "location_name": "Test Restaurant",
            "is_owner": True,
        },
        "subject_nl": "Uw locatie is goedgekeurd - Test Restaurant",
        "subject_tr": "Konumunuz onaylandı - Test Restaurant",
        "subject_en": "Your location has been approved - Test Restaurant",
    },
    "location-submission-rejected": {
        "template": "location_submission_rejected",
        "context": {
            "user_name": "Test Gebruiker",
            "location_name": "Test Restaurant",
            "rejection_reason": "Test reden voor afwijzing",
        },
        "subject_nl": "Uw locatie is afgewezen - Test Restaurant",
        "subject_tr": "Konumunuz reddedildi - Test Restaurant",
        "subject_en": "Your location has been rejected - Test Restaurant",
    },
}


def generate_weekly_digest_context(language: str = "nl") -> Dict[str, Any]:
    """
    Generate mock context data for weekly_digest email.
    
    Matches the structure expected by digest_worker.py
    """
    frontend_url = os.getenv("FRONTEND_URL", "https://turkspot.app")
    
    return {
        "user": {
            "user_id": str(uuid4()),
            "email": "test@example.com",
            "display_name": "Test Gebruiker",
            "city_key": "rotterdam",
        },
        "trending_locations": [
            {
                "name": "Test Restaurant 1",
                "city": "Rotterdam",
                "category": "restaurant",
                "score": 8.5,
                "check_ins_count": 42,
                "reactions_count": 15,
                "notes_count": 8,
            },
            {
                "name": "Test Bakkerij 2",
                "city": "Amsterdam",
                "category": "bakery",
                "score": 7.8,
                "check_ins_count": 28,
                "reactions_count": 12,
                "notes_count": 5,
            },
            {
                "name": "Test Supermarkt 3",
                "city": "Utrecht",
                "category": "supermarket",
                "score": 6.9,
                "check_ins_count": 35,
                "reactions_count": 8,
                "notes_count": 3,
            },
        ],
        "new_polls": [
            {
                "id": 1,
                "title": "Test Poll 1",
                "question": "Wat is je favoriete Turkse gerecht?",
                "poll_type": "multiple_choice",
                "is_sponsored": False,
                "created_at": datetime.now(timezone.utc) - timedelta(days=2),
                "option_count": 4,
            },
            {
                "id": 2,
                "title": "Test Poll 2",
                "question": "Waar shop je het liefst voor Turkse producten?",
                "poll_type": "multiple_choice",
                "is_sponsored": False,
                "created_at": datetime.now(timezone.utc) - timedelta(days=1),
                "option_count": 3,
            },
        ],
        "activity": {
            "notes_added": 5,
            "reactions_given": 12,
            "check_ins": 8,
            "locations_discovered": 3,
        },
        "gamification": {
            "total_xp": 1250,
            "current_streak": 7,
            "badges_earned": 3,
        },
        "language": language,
        "base_url": frontend_url,
        "unsubscribe_url": f"{frontend_url}/#/account",
    }


def get_subject(email_type: str, language: str) -> str:
    """Get subject for email type and language."""
    email_config = EMAIL_TYPES[email_type]
    if language == "tr":
        return email_config["subject_tr"]
    elif language == "en":
        return email_config["subject_en"]
    else:
        return email_config["subject_nl"]


async def send_test_email(
    email_type: str,
    recipient_email: str,
    language: str = "nl",
) -> bool:
    """Send a test transactional email."""
    if email_type not in EMAIL_TYPES:
        logger.error(f"Unknown email type: {email_type}")
        return False

    email_config = EMAIL_TYPES[email_type]
    template_service = get_email_template_service()
    email_service = get_email_service()

    try:
        # Get context - use dynamic generator for weekly-digest
        if email_type == "weekly-digest":
            context = generate_weekly_digest_context(language)
        else:
            context = email_config["context"]

        # Render template
        html_body, text_body = template_service.render_template(
            template_name=email_config["template"],
            context=context,
            language=language,
        )

        # Get subject
        subject = get_subject(email_type, language)

        # Send email
        success = await email_service.send_email(
            to_email=recipient_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

        if success:
            logger.info(
                "test_email_sent",
                email_type=email_type,
                recipient=recipient_email,
                language=language,
            )
            print(f"✅ {email_type} email sent successfully to {recipient_email}")
        else:
            logger.warning(
                "test_email_failed",
                email_type=email_type,
                recipient=recipient_email,
            )
            print(f"❌ {email_type} email failed to send")

        return success

    except Exception as e:
        logger.error(
            "test_email_error",
            email_type=email_type,
            recipient=recipient_email,
            error=str(e),
            exc_info=True,
        )
        print(f"❌ Error sending {email_type} email: {str(e)}")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="Test transactional emails by sending them to a test email address"
    )
    parser.add_argument(
        "recipient",
        type=str,
        help="Email address to send test emails to",
    )
    parser.add_argument(
        "--language",
        type=str,
        choices=["nl", "tr", "en"],
        default="nl",
        help="Language for emails (default: nl)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Send all transactional emails",
    )

    # Add flags for each email type
    for email_type in EMAIL_TYPES.keys():
        flag_name = email_type.replace("-", "_")
        parser.add_argument(
            f"--{flag_name}",
            action="store_true",
            help=f"Send {email_type} email",
        )

    args = parser.parse_args()

    # Determine which emails to send
    emails_to_send = []
    if args.all:
        emails_to_send = list(EMAIL_TYPES.keys())
    else:
        for email_type in EMAIL_TYPES.keys():
            flag_name = email_type.replace("-", "_")
            if getattr(args, flag_name, False):
                emails_to_send.append(email_type)

    if not emails_to_send:
        print("❌ No emails selected. Use --all or specify individual email types.")
        print("\nAvailable email types:")
        for email_type in EMAIL_TYPES.keys():
            print(f"  --{email_type.replace('-', '_')}")
        return

    # Initialize database pool (needed for some email types, though we use mock data)
    await init_db_pool()

    print("=" * 60)
    print("Transactional Email Test Script")
    print("=" * 60)
    print(f"Recipient: {args.recipient}")
    print(f"Language: {args.language}")
    print(f"Emails to send: {', '.join(emails_to_send)}")
    print("=" * 60)
    print()

    # Send emails
    results = {}
    for email_type in emails_to_send:
        print(f"Sending {email_type} email...")
        success = await send_test_email(email_type, args.recipient, args.language)
        results[email_type] = success
        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    print(f"Successfully sent: {successful}/{total}")
    print()
    for email_type, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {email_type}")


if __name__ == "__main__":
    asyncio.run(main())

