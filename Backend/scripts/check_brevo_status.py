#!/usr/bin/env python3
"""
Check Brevo email status and configuration.

This script helps diagnose why emails might not be arriving.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add Backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load environment variables
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)

from services.email_service import get_email_service
from app.core.logging import get_logger

logger = get_logger()


async def check_brevo_status():
    """Check Brevo configuration and provide troubleshooting tips."""
    print("=" * 60)
    print("Brevo Email Status Check")
    print("=" * 60)
    
    # Check environment variables
    email_provider = os.getenv("EMAIL_PROVIDER", "smtp")
    brevo_api_key = os.getenv("BREVO_API_KEY")
    email_from = os.getenv("EMAIL_FROM")
    
    print(f"\n1. Configuration Check:")
    print(f"   EMAIL_PROVIDER: {email_provider}")
    print(f"   BREVO_API_KEY: {'✅ Set' if brevo_api_key else '❌ Not set'}")
    print(f"   EMAIL_FROM: {email_from}")
    
    if email_provider != "brevo":
        print(f"\n❌ EMAIL_PROVIDER is not set to 'brevo'")
        return
    
    if not brevo_api_key:
        print(f"\n❌ BREVO_API_KEY is not set")
        return
    
    if not email_from:
        print(f"\n❌ EMAIL_FROM is not set")
        return
    
    # Check email service
    email_service = get_email_service()
    print(f"\n2. Email Service Status:")
    print(f"   Configured: {'✅ Yes' if email_service.is_configured else '❌ No'}")
    print(f"   Provider: {email_service._provider_name}")
    
    if not email_service.is_configured:
        print(f"\n❌ Email service is not configured")
        return
    
    print(f"\n3. Troubleshooting Checklist:")
    print(f"\n   ✅ Configuration is correct")
    print(f"\n   Next steps to check:")
    print(f"   1. Verify sender email in Brevo dashboard:")
    print(f"      - Go to: https://app.brevo.com/settings/senders")
    print(f"      - Check if '{email_from}' is verified (should show 'Verified' status)")
    print(f"      - If not verified, click 'Verify' and follow the instructions")
    print(f"\n   2. Check email delivery status in Brevo:")
    print(f"      - Go to: https://app.brevo.com/statistics/transactional")
    print(f"      - Look for recent emails sent to your test addresses")
    print(f"      - Check delivery status (sent, delivered, bounced, etc.)")
    print(f"\n   3. Check spam/junk folders:")
    print(f"      - Emails might be filtered as spam")
    print(f"      - Check both inbox and spam folders")
    print(f"      - Add info@turkspot.app to your contacts to prevent spam filtering")
    print(f"\n   4. Check email headers (if email arrived):")
    print(f"      - Open the email and view 'Show original' or 'View source'")
    print(f"      - Look for 'X-Mailin-Sender' or 'X-Brevo-Sender' header")
    print(f"      - This confirms the email came from Brevo")
    print(f"\n   5. Check Brevo account limits:")
    print(f"      - Go to: https://app.brevo.com/account/usage")
    print(f"      - Verify you haven't exceeded daily/monthly limits")
    print(f"      - Free plan has limits (300 emails/day)")
    print(f"\n   6. Check IP whitelisting:")
    print(f"      - Go to: https://app.brevo.com/security/authorised_ips")
    print(f"      - If IP whitelisting is enabled, make sure your IP is authorized")
    print(f"      - Or disable IP whitelisting for development")
    print(f"\n   7. Wait a few minutes:")
    print(f"      - Email delivery can take 1-5 minutes")
    print(f"      - Brevo processes emails asynchronously")
    print(f"\n   8. Test with a different email address:")
    print(f"      - Try sending to a different email provider (Gmail, Outlook, etc.)")
    print(f"      - Some email providers have stricter spam filters")
    
    print(f"\n" + "=" * 60)
    print(f"✅ Configuration check complete")
    print(f"=" * 60)


if __name__ == "__main__":
    asyncio.run(check_brevo_status())






