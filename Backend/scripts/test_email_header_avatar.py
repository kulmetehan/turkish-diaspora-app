#!/usr/bin/env python3
"""
Test script om te controleren of de email header met avatar correct werkt.

Dit script:
- Test meerdere email templates (welcome, outreach, weekly_digest)
- Controleert of de mascotte afbeelding correct wordt gebruikt
- Controleert of de fallback correct is (geen emoji meer)
- Stuurt een test email met de nieuwe header

Run met: python -m scripts.test_email_header_avatar <recipient_email> [template_name]
Template opties: welcome, outreach, weekly_digest (default: welcome)
"""

import asyncio
import sys
import os
import base64
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
from services.email_template_service import get_email_template_service, _get_mascotte_base64
from app.core.logging import get_logger

logger = get_logger()


def check_mascotte_image():
    """Controleer of de mascotte afbeelding beschikbaar is."""
    print("=" * 60)
    print("1. Controleren van mascotte afbeelding")
    print("=" * 60)
    
    mascotte_base64 = _get_mascotte_base64()
    
    if mascotte_base64:
        decoded_size_kb = len(base64.b64decode(mascotte_base64)) / 1024
        print(f"✅ Mascotte afbeelding geladen")
        print(f"   Grootte: {decoded_size_kb:.2f} KB")
        
        # Valideer PNG
        try:
            decoded_data = base64.b64decode(mascotte_base64)
            if decoded_data.startswith(b'\x89PNG'):
                print(f"   ✅ Geldige PNG afbeelding")
            else:
                print(f"   ⚠️  Geen geldige PNG header")
        except Exception as e:
            print(f"   ❌ Fout bij validatie: {e}")
        
        return mascotte_base64
    else:
        print(f"❌ Mascotte afbeelding NIET geladen")
        print(f"   Fallback (TS tekstlogo) zal worden gebruikt")
        return None


def check_template_header(html_body: str, template_name: str):
    """Controleer of de header correct is in de gerenderde HTML."""
    print(f"\n2. Controleren van header in {template_name}:")
    print("-" * 60)
    
    # Check voor base64 image
    has_base64_image = "data:image/png;base64," in html_body
    has_emoji_fallback = "🤖" in html_body
    has_text_fallback = "TS" in html_body and "font-size: 20px" in html_body and "color: #e63946" in html_body
    
    if has_base64_image:
        print("   ✅ Base64 afbeelding gevonden in header")
        
        # Extract en check grootte
        base64_start = html_body.find("data:image/png;base64,") + len("data:image/png;base64,")
        base64_end = html_body.find('"', base64_start)
        if base64_end > base64_start:
            base64_data = html_body[base64_start:base64_end]
            image_size_kb = len(base64_data) * 3 / 4 / 1024
            print(f"   Afbeelding grootte: ~{image_size_kb:.2f} KB")
        
        # Check voor oude emoji fallback (mag niet voorkomen als base64 image er is)
        if has_emoji_fallback:
            print("   ⚠️  WAARSCHUWING: Emoji fallback gevonden terwijl base64 image er is!")
        
    elif has_text_fallback:
        print("   ✅ Text fallback (TS) gevonden - dit is correct")
        print("   (Base64 image niet beschikbaar, maar fallback werkt)")
        
    elif has_emoji_fallback:
        print("   ❌ PROBLEEM: Emoji fallback (🤖) gevonden!")
        print("   Dit kan problemen veroorzaken in email clients")
        print("   OPLOSSING: Update template om TS tekstlogo te gebruiken")
        
    else:
        print("   ⚠️  Geen fallback gevonden - header kan leeg zijn")
    
    # Check voor externe image URLs (problematisch)
    if 'src="http' in html_body or 'src="https' in html_body:
        print("   ⚠️  WAARSCHUWING: Externe image URLs gevonden!")
        print("   Deze kunnen geblokkeerd worden door email clients")
    else:
        print("   ✅ Geen externe image URLs gevonden")
    
    # Check voor Turkspot branding
    if "TurkSpot" in html_body or "Turkspot" in html_body:
        print("   ✅ Turkspot branding gevonden")
    else:
        print("   ⚠️  Geen Turkspot branding gevonden")
    
    return has_base64_image or has_text_fallback


async def test_email_template(template_name: str, recipient_email: str):
    """Test een specifieke email template."""
    print("\n" + "=" * 60)
    print(f"Test Email Template: {template_name}")
    print("=" * 60)
    
    template_service = get_email_template_service()
    
    # Prepare context based on template
    context = {
        "user_name": "Test Gebruiker",
        "location_name": "Test Restaurant",
        "mapview_link": f"{os.getenv('FRONTEND_URL', 'https://turkspot.app')}/#/map?focus=123",
        "opt_out_link": f"{os.getenv('FRONTEND_URL', 'https://turkspot.app')}/#/opt-out?token=test-token",
    }
    
    if template_name == "weekly_digest":
        context = {
            "user": {"display_name": "Test Gebruiker"},
        }
    
    try:
        html_body, text_body = template_service.render_template(
            template_name,
            context=context,
            language="nl"
        )
        print("✅ Template gerenderd")
    except Exception as e:
        print(f"❌ Fout bij template rendering: {e}")
        logger.error("template_render_failed", template=template_name, error=str(e), exc_info=True)
        return False
    
    # Check header
    header_ok = check_template_header(html_body, template_name)
    
    # Check email size
    html_size_kb = len(html_body.encode('utf-8')) / 1024
    print(f"\n3. Email grootte: {html_size_kb:.2f} KB")
    
    if html_size_kb > 300:
        print(f"   ⚠️  WAARSCHUWING: Email is groter dan 300KB - kan problemen veroorzaken")
    elif html_size_kb > 100:
        print(f"   ⚠️  Gmail kan email clippen bij > 100KB")
    else:
        print(f"   ✅ Email grootte is acceptabel")
    
    # Send test email
    print(f"\n4. Verzenden van test email naar {recipient_email}...")
    # Use production-like subject line (no "Test" word to avoid spam filters)
    subject_map = {
        "weekly_digest": "Weekoverzicht Turkspot",
        "welcome": "Welkom bij Turkspot",
        "outreach": "Je locatie op Turkspot",
    }
    subject = subject_map.get(template_name, f"Turkspot - {template_name}")
    
    email_service = get_email_service()
    try:
        success = await email_service.send_email(
            to_email=recipient_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        
        if success:
            print("✅ Email verzonden")
            return True
        else:
            print("❌ Email verzending gefaald")
            return False
    except Exception as e:
        print(f"❌ Fout bij verzenden: {e}")
        logger.error("email_send_failed", error=str(e), exc_info=True)
        return False


async def main():
    """Hoofdfunctie."""
    print("\n" + "=" * 60)
    print("Email Header Avatar Test Script")
    print("=" * 60)
    
    # Parse arguments
    if len(sys.argv) < 2:
        print("\n❌ ERROR: Recipient email address required")
        print("\nUsage: python -m scripts.test_email_header_avatar <recipient_email> [template_name]")
        print("\nTemplate opties:")
        print("  - welcome (default)")
        print("  - outreach")
        print("  - weekly_digest")
        print("\nVoorbeeld:")
        print("  python -m scripts.test_email_header_avatar test@example.com welcome")
        sys.exit(1)
    
    recipient_email = sys.argv[1]
    template_name = sys.argv[2] if len(sys.argv) > 2 else "welcome"
    
    # Validate template name
    valid_templates = ["welcome", "outreach", "weekly_digest"]
    if template_name not in valid_templates:
        print(f"\n❌ ERROR: Ongeldige template naam: {template_name}")
        print(f"Geldige opties: {', '.join(valid_templates)}")
        sys.exit(1)
    
    print(f"\nConfiguratie:")
    print(f"   Recipient: {recipient_email}")
    print(f"   Template: {template_name}")
    print(f"   Provider: {os.getenv('EMAIL_PROVIDER', 'smtp')}")
    print(f"   From: {os.getenv('EMAIL_FROM', 'NOT SET')}")
    
    # Check email service
    email_service = get_email_service()
    if not email_service.is_configured:
        print("\n❌ ERROR: Email service is not properly configured")
        sys.exit(1)
    
    print("\n✅ Email service is configured")
    
    # Check mascotte image
    mascotte_base64 = check_mascotte_image()
    
    # Test template
    success = await test_email_template(template_name, recipient_email)
    
    # Summary
    print("\n" + "=" * 60)
    print("SAMENVATTING")
    print("=" * 60)
    
    if success:
        print("✅ Test email verzonden")
        print(f"\nControleer je inbox ({recipient_email}):")
        print("1. Open de email en controleer:")
        print("   - Header bevat Turkspot logo met avatar (of TS fallback)")
        print("   - Geen emoji (🤖) in de header")
        print("   - Afbeelding wordt correct getoond (niet broken link)")
        print("\n2. Als je een broken link ziet:")
        print("   - Controleer of base64 image correct is geladen")
        print("   - Check email client instellingen (images kunnen geblokkeerd zijn)")
        print("\n3. Als je nog steeds een emoji ziet:")
        print("   - Template is mogelijk niet geüpdatet")
        print("   - Run: python -m scripts.test_mascotte_image om te controleren")
    else:
        print("❌ Test gefaald")
        print("   Controleer de logs voor meer informatie")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

