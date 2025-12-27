#!/usr/bin/env python3
"""
Test script for Brevo email provider.

This script tests the Brevo email provider configuration and sends a test email.
Run with: python -m scripts.test_brevo_email <recipient_email>
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


async def test_brevo_configuration():
    """Test if Brevo provider is properly configured."""
    print("=" * 60)
    print("Testing Brevo Email Provider Configuration")
    print("=" * 60)
    
    # Check environment variables
    email_provider = os.getenv("EMAIL_PROVIDER", "smtp")
    brevo_api_key = os.getenv("BREVO_API_KEY")
    email_from = os.getenv("EMAIL_FROM")
    email_from_name = os.getenv("EMAIL_FROM_NAME", "Turkspot")
    
    print(f"\n1. Environment Variables:")
    print(f"   EMAIL_PROVIDER: {email_provider}")
    print(f"   BREVO_API_KEY: {'***' + brevo_api_key[-4:] if brevo_api_key else 'NOT SET'}")
    print(f"   EMAIL_FROM: {email_from}")
    print(f"   EMAIL_FROM_NAME: {email_from_name}")
    
    if email_provider != "brevo":
        print(f"\n❌ ERROR: EMAIL_PROVIDER is set to '{email_provider}', but should be 'brevo'")
        print("   Please set EMAIL_PROVIDER=brevo in your .env file")
        return False
    
    if not brevo_api_key:
        print(f"\n❌ ERROR: BREVO_API_KEY is not set")
        print("   Please set BREVO_API_KEY in your .env file")
        return False
    
    if not email_from:
        print(f"\n❌ ERROR: EMAIL_FROM is not set")
        print("   Please set EMAIL_FROM in your .env file")
        return False
    
    print(f"\n✅ All environment variables are set")
    
    # Test email service configuration
    print(f"\n2. Email Service Configuration:")
    email_service = get_email_service()
    
    print(f"   Provider name: {email_service._provider_name}")
    
    # Check if Brevo SDK is available
    try:
        from sib_api_v3_sdk import TransactionalEmailsApi
        print(f"   ✅ Brevo SDK (sib-api-v3-sdk) is available")
    except ImportError as e:
        print(f"   ❌ Brevo SDK (sib-api-v3-sdk) import failed: {e}")
        print(f"   Please install: pip install sib-api-v3-sdk")
        return False
    
    # Get the provider to check its configuration
    provider = email_service._get_provider()
    print(f"   Provider type: {type(provider).__name__}")
    
    # Check provider-specific configuration
    if hasattr(provider, 'api_key'):
        print(f"   Provider API key: {'***' + provider.api_key[-4:] if provider.api_key else 'NOT SET'}")
    if hasattr(provider, 'from_email'):
        print(f"   Provider from_email: {provider.from_email}")
    
    # Check BREVO_AVAILABLE flag (module-level variable)
    try:
        from services.email.brevo_provider import BREVO_AVAILABLE
        print(f"   BREVO_AVAILABLE (module): {BREVO_AVAILABLE}")
    except ImportError:
        print(f"   Could not check BREVO_AVAILABLE flag")
    
    if not email_service.is_configured:
        print(f"\n❌ ERROR: Email service is not configured")
        print("   Debugging info:")
        print(f"   - Provider: {type(provider).__name__}")
        if hasattr(provider, 'api_key'):
            print(f"   - API key set: {bool(provider.api_key)}")
        if hasattr(provider, 'from_email'):
            print(f"   - From email set: {bool(provider.from_email)}")
        if hasattr(provider, 'BREVO_AVAILABLE'):
            print(f"   - SDK available: {provider.BREVO_AVAILABLE}")
        return False
    
    print(f"✅ Email service is configured")
    print(f"   Provider: {email_service._provider_name}")
    
    return True


async def test_send_email(recipient_email: str):
    """Send a test email via Brevo."""
    print("\n" + "=" * 60)
    print("Sending Test Email")
    print("=" * 60)
    
    email_service = get_email_service()
    
    if not email_service.is_configured:
        print("❌ Email service is not configured. Cannot send test email.")
        return False
    
    subject = "Test Email from Turkspot - Brevo Integration"
    html_body = """
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #2563eb;">Brevo Email Test</h2>
        <p>This is a test email sent via Brevo to verify the integration.</p>
        <p>If you receive this email, the Brevo integration is working correctly! ✅</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            Sent from: {sender}<br>
            Provider: Brevo (formerly Sendinblue)
        </p>
    </body>
    </html>
    """.format(sender=os.getenv("EMAIL_FROM", "info@turkspot.app"))
    
    text_body = """
Brevo Email Test

This is a test email sent via Brevo to verify the integration.

If you receive this email, the Brevo integration is working correctly!

Sent from: {sender}
Provider: Brevo (formerly Sendinblue)
    """.format(sender=os.getenv("EMAIL_FROM", "info@turkspot.app"))
    
    print(f"\nSending test email to: {recipient_email}")
    print(f"Subject: {subject}")
    print(f"From: {os.getenv('EMAIL_FROM', 'info@turkspot.app')}")
    
    try:
        # Use send_email_with_message_id to get the message ID
        message_id = await email_service.send_email_with_message_id(
            to_email=recipient_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        
        if message_id:
            print(f"\n✅ Email accepted by Brevo API!")
            print(f"   Message ID: {message_id}")
            print(f"   Check your inbox at: {recipient_email}")
            print(f"\n   ⚠️  If email doesn't arrive, check:")
            print(f"   1. Brevo Transactional Logs:")
            print(f"      https://app.brevo.com/transactional/email/logs")
            print(f"      (Look for message_id: {message_id})")
            print(f"   2. Brevo Bounces:")
            print(f"      https://app.brevo.com/statistics/bounces")
            print(f"   3. Sender Verification:")
            print(f"      https://app.brevo.com/settings/senders")
            print(f"      (info@turkspot.app must be 'Verified' for Transactional)")
            print(f"   4. DMARC Issue:")
            print(f"      Your sender shows 'rua tag is missing'")
            print(f"      This can cause Gmail/Yahoo/Microsoft to bounce emails")
            print(f"      Fix: Add rua=mailto:dmarc@turkspot.app to DMARC DNS record")
            print(f"   5. Spam/Junk folders:")
            print(f"      Check spam/junk in both email accounts")
            print(f"   6. Wait a few minutes:")
            print(f"      Email delivery can take 1-5 minutes")
            return True
        else:
            print(f"\n❌ Email sending failed (no message ID returned)")
            print(f"   This means Brevo API rejected the email")
            print(f"   Check the logs above for error details")
            print(f"   Common causes:")
            print(f"   - Sender email not verified")
            print(f"   - Invalid API key")
            print(f"   - IP not whitelisted")
            return False
            
    except Exception as e:
        print(f"\n❌ Error sending email: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("Brevo Email Provider Test Script")
    print("=" * 60)
    
    # Test configuration
    config_ok = await test_brevo_configuration()
    
    if not config_ok:
        print("\n❌ Configuration test failed. Please fix the issues above.")
        sys.exit(1)
    
    # Test sending email if recipient is provided
    if len(sys.argv) > 1:
        recipient_email = sys.argv[1]
        print(f"\n3. Sending Test Email:")
        email_ok = await test_send_email(recipient_email)
        
        if email_ok:
            print("\n" + "=" * 60)
            print("✅ All tests passed!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Check your email inbox for the test email")
            print("2. Verify the email was sent via Brevo (check email headers)")
            print("3. If successful, you're ready to use Brevo for outreach emails!")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("❌ Email sending test failed")
            print("=" * 60)
            sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("✅ Configuration test passed!")
        print("=" * 60)
        print("\nTo test sending an email, run:")
        print(f"  python -m scripts.test_brevo_email <recipient_email>")
        print("\nExample:")
        print(f"  python -m scripts.test_brevo_email your-email@example.com")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

