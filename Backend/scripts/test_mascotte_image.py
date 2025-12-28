#!/usr/bin/env python3
"""
Test script om te controleren of de mascotte afbeelding correct geladen wordt.

Dit script:
- Controleert of turkspotbot.png bestaat op alle verwachte paden
- Test of de base64 encoding werkt
- Test of de email template correct rendert met de afbeelding
- Toont waar het probleem zit als de afbeelding niet geladen wordt

Run met: python -m scripts.test_mascotte_image
"""

import sys
import base64
from pathlib import Path

# Add Backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.email_template_service import _get_mascotte_base64, get_email_template_service
from app.core.logging import get_logger

logger = get_logger()


def check_image_paths():
    """Controleer of de afbeelding bestaat op alle verwachte paden."""
    print("=" * 60)
    print("1. Controleren van afbeelding paden")
    print("=" * 60)
    
    mascotte_paths = [
        backend_dir.parent / "Frontend" / "src" / "assets" / "turkspotbot-mailhead.png",
        backend_dir.parent / "Frontend" / "src" / "assets" / "turkspotbot.png",
        backend_dir.parent / "Frontend" / "public" / "turkspotbot.png",
        backend_dir / "static" / "turkspotbot.png",
    ]
    
    found_paths = []
    missing_paths = []
    
    for path in mascotte_paths:
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"✅ Gevonden: {path}")
            print(f"   Grootte: {size_kb:.2f} KB")
            found_paths.append((path, size_kb))
        else:
            print(f"❌ Niet gevonden: {path}")
            missing_paths.append(path)
    
    print()
    if found_paths:
        print(f"✅ {len(found_paths)} pad(en) gevonden met afbeelding")
        # Toon het eerste gevonden pad (dit is wat gebruikt wordt)
        best_path, size_kb = found_paths[0]
        print(f"   Gebruikt pad: {best_path}")
        print(f"   Grootte: {size_kb:.2f} KB")
        
        # Controleer grootte limiet (100KB - Gmail clips emails > 100KB)
        MAX_SIZE_KB = 100
        if size_kb > MAX_SIZE_KB:
            print(f"   ⚠️  WAARSCHUWING: Afbeelding is groter dan {MAX_SIZE_KB}KB!")
            print(f"      Email clients kunnen grote inline images blokkeren.")
        else:
            print(f"   ✅ Grootte is binnen limiet (< {MAX_SIZE_KB}KB)")
    else:
        print(f"❌ GEEN afbeelding gevonden op verwachte paden!")
        print(f"   Controleer of turkspotbot.png bestaat op een van deze locaties:")
        for path in mascotte_paths:
            print(f"   - {path}")
    
    return found_paths, missing_paths


def test_base64_encoding():
    """Test of de base64 encoding werkt."""
    print("\n" + "=" * 60)
    print("2. Testen van base64 encoding")
    print("=" * 60)
    
    try:
        mascotte_base64 = _get_mascotte_base64()
        
        if mascotte_base64:
            # Bereken grootte
            base64_size_kb = len(mascotte_base64.encode('utf-8')) / 1024
            decoded_size_kb = len(base64.b64decode(mascotte_base64)) / 1024
            
            print(f"✅ Base64 encoding succesvol")
            print(f"   Base64 string lengte: {len(mascotte_base64)} karakters")
            print(f"   Base64 grootte: {base64_size_kb:.2f} KB")
            print(f"   Gedecodeerde grootte: {decoded_size_kb:.2f} KB")
            
            # Valideer dat het een geldige PNG is
            try:
                decoded_data = base64.b64decode(mascotte_base64)
                if decoded_data.startswith(b'\x89PNG'):
                    print(f"   ✅ Geldige PNG afbeelding gedetecteerd")
                else:
                    print(f"   ⚠️  WAARSCHUWING: Geen geldige PNG header gevonden")
            except Exception as e:
                print(f"   ❌ Fout bij decoderen: {e}")
            
            return mascotte_base64
        else:
            print(f"❌ Base64 encoding gefaald - lege string geretourneerd")
            print(f"   Dit betekent dat de afbeelding niet gevonden kan worden")
            return None
            
    except Exception as e:
        print(f"❌ Fout bij base64 encoding: {e}")
        logger.error("mascotte_test_failed", error=str(e), exc_info=True)
        return None


def test_template_rendering():
    """Test of de email template correct rendert met de afbeelding."""
    print("\n" + "=" * 60)
    print("3. Testen van email template rendering")
    print("=" * 60)
    
    template_service = get_email_template_service()
    
    # Test met base template
    print("\n3a. Testen met base.html.j2 template:")
    try:
        context = {
            "user_name": "Test Gebruiker",
            "location_name": "Test Locatie",
        }
        html_body, text_body = template_service.render_template(
            "welcome_email",
            context=context,
            language="nl"
        )
        
        # Check voor base64 image
        if "data:image/png;base64," in html_body:
            print("   ✅ Base64 afbeelding gevonden in gerenderde HTML")
            
            # Extract en check grootte
            base64_start = html_body.find("data:image/png;base64,") + len("data:image/png;base64,")
            base64_end = html_body.find('"', base64_start)
            if base64_end > base64_start:
                base64_data = html_body[base64_start:base64_end]
                image_size_kb = len(base64_data) * 3 / 4 / 1024
                print(f"   Afbeelding grootte in email: ~{image_size_kb:.2f} KB")
        else:
            print("   ⚠️  GEEN base64 afbeelding gevonden in HTML")
            print("   Dit betekent dat mascotte_base64 leeg is of niet wordt gebruikt")
            
            # Check voor fallback
            if "🤖" in html_body:
                print("   ⚠️  Emoji fallback (🤖) gevonden - dit kan problemen veroorzaken!")
            elif "TS" in html_body and "font-size: 20px" in html_body:
                print("   ✅ Text fallback (TS) gevonden - dit is beter dan emoji")
        
        # Check voor externe image URLs (problematisch)
        if 'src="http' in html_body or 'src="https' in html_body:
            print("   ⚠️  WAARSCHUWING: Externe image URLs gevonden!")
            print("   Deze kunnen geblokkeerd worden door email clients")
        
        print(f"   HTML grootte: {len(html_body.encode('utf-8')) / 1024:.2f} KB")
        
    except Exception as e:
        print(f"   ❌ Fout bij template rendering: {e}")
        logger.error("template_test_failed", error=str(e), exc_info=True)
        return False
    
    # Test met weekly_digest template (heeft eigen header)
    print("\n3b. Testen met weekly_digest.html.j2 template:")
    try:
        context = {
            "user": {"display_name": "Test Gebruiker"},
        }
        html_body, text_body = template_service.render_template(
            "weekly_digest",
            context=context,
            language="nl"
        )
        
        if "data:image/png;base64," in html_body:
            print("   ✅ Base64 afbeelding gevonden in weekly_digest HTML")
        else:
            print("   ⚠️  GEEN base64 afbeelding gevonden in weekly_digest HTML")
            if "🤖" in html_body:
                print("   ⚠️  Emoji fallback (🤖) gevonden!")
            elif "TS" in html_body and "font-size: 20px" in html_body:
                print("   ✅ Text fallback (TS) gevonden")
        
    except Exception as e:
        print(f"   ❌ Fout bij weekly_digest rendering: {e}")
        logger.error("weekly_digest_test_failed", error=str(e), exc_info=True)
        return False
    
    return True


def main():
    """Hoofdfunctie."""
    print("\n" + "=" * 60)
    print("Mascotte Afbeelding Test Script")
    print("=" * 60)
    print()
    
    # 1. Check paden
    found_paths, missing_paths = check_image_paths()
    
    # 2. Test base64 encoding
    mascotte_base64 = test_base64_encoding()
    
    # 3. Test template rendering
    template_ok = test_template_rendering()
    
    # Samenvatting
    print("\n" + "=" * 60)
    print("SAMENVATTING")
    print("=" * 60)
    
    if found_paths and mascotte_base64 and template_ok:
        print("✅ ALLES OK: Mascotte afbeelding wordt correct geladen en gebruikt")
        print("\nAanbevelingen:")
        print("1. Controleer of de afbeelding ook in productie beschikbaar is")
        print("2. Test een echte email om te zien of de afbeelding correct wordt getoond")
        print("3. Overweeg om de emoji fallback te vervangen door tekst (TS)")
    else:
        print("❌ PROBLEMEN GEVONDEN:")
        if not found_paths:
            print("   - Geen afbeelding gevonden op verwachte paden")
            print("   - OPLOSSING: Zorg dat turkspotbot.png bestaat op:")
            print("     * Frontend/src/assets/turkspotbot.png (aanbevolen)")
        if not mascotte_base64:
            print("   - Base64 encoding faalt")
            print("   - OPLOSSING: Controleer bestandsrechten en pad configuratie")
        if not template_ok:
            print("   - Template rendering heeft problemen")
            print("   - OPLOSSING: Controleer template syntax en context variabelen")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

