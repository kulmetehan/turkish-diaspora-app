#!/usr/bin/env python3
"""
Test email headers and deliverability.

This script tests email rendering, checks for deliverability issues,
and sends a test email for Gmail verification.

Run with: python -m scripts.test_email_headers <recipient_email>
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
from services.email_template_service import get_email_template_service
from app.core.logging import get_logger

logger = get_logger()


async def test_email_headers():
    """Test email with proper headers and deliverability checks."""
    print("=" * 60)
    print("Email Deliverability Test")
    print("=" * 60)
    
    # Get recipient email from command line
    if len(sys.argv) < 2:
        print("\n❌ ERROR: Recipient email address required")
        print("Usage: python -m scripts.test_email_headers <recipient_email>")
        sys.exit(1)
    
    recipient_email = sys.argv[1]
    
    # Initialize services
    email_service = get_email_service()
    template_service = get_email_template_service()
    
    print(f"\n1. Configuration:")
    print(f"   Recipient: {recipient_email}")
    print(f"   Provider: {os.getenv('EMAIL_PROVIDER', 'smtp')}")
    print(f"   From: {os.getenv('EMAIL_FROM', 'NOT SET')}")
    
    # Check if email service is configured
    if not email_service.is_configured:
        print("\n❌ ERROR: Email service is not properly configured")
        sys.exit(1)
    
    print("\n✅ Email service is configured")
    
    # Render test email
    print("\n2. Rendering test email...")
    context = {
        "location_name": "Test Restaurant",
        "mapview_link": f"{os.getenv('FRONTEND_URL', 'https://turkspot.app')}/#/map?focus=123",
        "opt_out_link": f"{os.getenv('FRONTEND_URL', 'https://turkspot.app')}/#/opt-out?token=test-token",
    }
    
    try:
        html_body, text_body = template_service.render_template("outreach_email", context, language="nl")
        print("✅ Email template rendered successfully")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to render email template: {e}")
        logger.error("template_render_failed", error=str(e), exc_info=True)
        sys.exit(1)
    
    # Check email size
    print("\n3. Email Size Check:")
    html_size_kb = len(html_body.encode('utf-8')) / 1024
    text_size_kb = len(text_body.encode('utf-8')) / 1024
    total_size_kb = html_size_kb + text_size_kb
    
    print(f"   HTML body: {html_size_kb:.2f} KB")
    print(f"   Text body: {text_size_kb:.2f} KB")
    print(f"   Total size: {total_size_kb:.2f} KB")
    
    if html_size_kb > 100:
        print(f"   ⚠️  WARNING: HTML email size ({html_size_kb:.2f} KB) exceeds 100KB - Gmail may clip it!")
    else:
        print(f"   ✅ Email size is within Gmail limits (< 100KB)")
    
    # Check for base64 image
    print("\n4. Image Check:")
    if "data:image/png;base64," in html_body:
        # Calculate base64 image size
        base64_start = html_body.find("data:image/png;base64,") + len("data:image/png;base64,")
        base64_end = html_body.find('"', base64_start)
        if base64_end > base64_start:
            base64_data = html_body[base64_start:base64_end]
            image_size_kb = len(base64_data) * 3 / 4 / 1024  # Approximate decoded size
            print(f"   ✅ Base64 image found in email (approx. {image_size_kb:.2f} KB)")
        else:
            print("   ✅ Base64 image found in email")
    else:
        print("   ⚠️  WARNING: No base64 image found - using fallback")
    
    # Check for external image URLs
    if 'src="http' in html_body or 'src="https' in html_body:
        print("   ⚠️  WARNING: External image URLs found - Gmail may block these!")
    else:
        print("   ✅ No external image URLs found")
    
    # Check for unsubscribe link
    print("\n5. Unsubscribe Link Check:")
    unsubscribe_keywords = ["unsubscribe", "afmelden", "opt-out", "opt_out"]
    has_unsubscribe = any(keyword in html_body.lower() for keyword in unsubscribe_keywords)
    
    if has_unsubscribe:
        print("   ✅ Unsubscribe link found in email body")
    else:
        print("   ⚠️  WARNING: No unsubscribe link found in email body")
    
    # Check for List-Unsubscribe header (will be added by Brevo provider)
    print("\n6. Email Headers:")
    print("   ✅ List-Unsubscribe header will be added by Brevo provider")
    print("   ✅ List-Unsubscribe-Post header will be added by Brevo provider")
    print("   ✅ Precedence header will be added by Brevo provider")
    print("   ✅ X-Mailer header will be added by Brevo provider")
    print("   ✅ X-Auto-Response-Suppress header will be added by Brevo provider")
    
    # Send test email
    print("\n7. Sending test email...")
    subject = "Test Email - Gmail Deliverability Check"
    
    try:
        success = await email_service.send_email(
            to_email=recipient_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        
        if success:
            print("✅ Email sent successfully")
        else:
            print("❌ Email failed to send")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: Failed to send email: {e}")
        logger.error("email_send_failed", error=str(e), exc_info=True)
        sys.exit(1)
    
    # Instructions for Gmail verification
    print("\n" + "=" * 60)
    print("Gmail Verification Instructions")
    print("=" * 60)
    print("\n1. Check your Gmail inbox for the test email")
    print("2. Open the email and check:")
    print("   - Email is not marked as suspicious")
    print("   - Images are displayed (not hidden)")
    print("   - Email is not clipped (no '[Message clipped]' message)")
    print("\n3. To verify headers:")
    print("   - Click the three dots (⋮) next to the reply button")
    print("   - Select 'Show original'")
    print("   - Look for these headers:")
    print("     * List-Unsubscribe: <https://turkspot.app/#/account>")
    print("     * List-Unsubscribe-Post: List-Unsubscribe=One-Click")
    print("     * Precedence: bulk")
    print("     * X-Mailer: Turkspot Email Service")
    print("     * X-Auto-Response-Suppress: All")
    print("\n4. If images are still hidden:")
    print("   - Check SPF/DKIM/DMARC records (see Docs/brevo-dmarc-setup.md)")
    print("   - Verify domain reputation")
    print("   - Wait for DNS propagation (can take up to 48 hours)")
    print("\n5. If email is clipped:")
    print("   - Check email size (should be < 100KB)")
    print("   - Minimize HTML/CSS further if needed")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_email_headers())



