#!/usr/bin/env python3
"""
Script om een test activity push notification naar een specifieke gebruiker te sturen.

Dit simuleert een activity notificatie zoals die wordt verstuurd wanneer iemand
reageert op jouw Söz of een nieuwe note plaatst op een locatie waar jij actief bent.

Usage:
    # Met email en reaction activity
    python scripts/send_test_activity_notification.py \
        --email "jouw@email.com" \
        --activity-type "reaction" \
        --location-name "Test Locatie"

    # Met email en note activity
    python scripts/send_test_activity_notification.py \
        --email "jouw@email.com" \
        --activity-type "note" \
        --location-name "Test Locatie"

    # Met user_id (UUID)
    python scripts/send_test_activity_notification.py \
        --user-id "123e4567-e89b-12d3-a456-426614174000" \
        --activity-type "reaction" \
        --location-name "Test Locatie"

    # Met bestaande location_id (haalt location name automatisch op)
    python scripts/send_test_activity_notification.py \
        --email "jouw@email.com" \
        --activity-type "reaction" \
        --location-id 123

    # Dry run (test zonder te verzenden)
    python scripts/send_test_activity_notification.py \
        --email "jouw@email.com" \
        --activity-type "reaction" \
        --location-name "Test Locatie" \
        --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from services.db_service import init_db_pool, fetchrow, fetch
from services.push_service import get_push_service

configure_logging(service_name="script")
logger = get_logger()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Send a test activity push notification to a specific user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using email with reaction activity
  python scripts/send_test_activity_notification.py \\
      --email "user@example.com" \\
      --activity-type "reaction" \\
      --location-name "Test Locatie"

  # Using email with note activity
  python scripts/send_test_activity_notification.py \\
      --email "user@example.com" \\
      --activity-type "note" \\
      --location-name "Test Locatie"

  # Using user_id (UUID)
  python scripts/send_test_activity_notification.py \\
      --user-id "123e4567-e89b-12d3-a456-426614174000" \\
      --activity-type "reaction" \\
      --location-name "Test Locatie"

  # Using existing location_id (fetches location name automatically)
  python scripts/send_test_activity_notification.py \\
      --email "user@example.com" \\
      --activity-type "reaction" \\
      --location-id 123

  # Dry run (test without sending)
  python scripts/send_test_activity_notification.py \\
      --email "user@example.com" \\
      --activity-type "reaction" \\
      --location-name "Test Locatie" \\
      --dry-run
        """
    )
    
    # User identification (mutually exclusive)
    user_group = ap.add_mutually_exclusive_group(required=True)
    user_group.add_argument(
        "--user-id",
        help="User UUID (e.g., '123e4567-e89b-12d3-a456-426614174000')"
    )
    user_group.add_argument(
        "--email",
        help="User email address"
    )
    
    # Activity type (required)
    ap.add_argument(
        "--activity-type",
        choices=["reaction", "note"],
        required=True,
        help="Type of activity: 'reaction' (someone reacted to your Söz) or 'note' (new note on location)"
    )
    
    # Location identification (mutually exclusive)
    location_group = ap.add_mutually_exclusive_group(required=True)
    location_group.add_argument(
        "--location-id",
        type=int,
        help="Existing location ID (will fetch location name automatically)"
    )
    location_group.add_argument(
        "--location-name",
        help="Location name (for testing purposes)"
    )
    
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually send notification, just show what would be sent"
    )
    
    return ap.parse_args()


async def get_user_id_by_email(email: str) -> Optional[str]:
    """Get user_id (UUID) from email address."""
    sql = """
        SELECT id FROM auth.users WHERE email = $1 LIMIT 1
    """
    row = await fetchrow(sql, email.lower().strip())
    if row:
        return str(row["id"])
    return None


async def get_location_by_id(location_id: int) -> Optional[Dict[str, Any]]:
    """Get location details from location_id."""
    sql = """
        SELECT id, name
        FROM locations
        WHERE id = $1
    """
    row = await fetchrow(sql, location_id)
    if row:
        return dict(row)
    return None


async def main_async() -> None:
    args = parse_args()
    
    await init_db_pool()
    
    # Get user_id
    user_id = None
    if args.user_id:
        user_id = args.user_id.strip()
        # Validate UUID format (basic check)
        if len(user_id) != 36 or user_id.count('-') != 4:
            print(f"ERROR: Invalid UUID format: {user_id}")
            print("   Expected format: 123e4567-e89b-12d3-a456-426614174000")
            sys.exit(1)
    elif args.email:
        print(f"🔍 Zoeken naar gebruiker met email: {args.email}")
        user_id = await get_user_id_by_email(args.email)
        if not user_id:
            print(f"❌ Geen gebruiker gevonden met email: {args.email}")
            print("   Controleer of:")
            print("   - De email correct is gespeld")
            print("   - De gebruiker bestaat in auth.users")
            sys.exit(1)
        print(f"✅ Gebruiker gevonden: {user_id}")
    
    # Get location name
    location_name = None
    location_id = None
    
    if args.location_id:
        print(f"🔍 Ophalen van locatie {args.location_id}...")
        location = await get_location_by_id(args.location_id)
        if location:
            location_name = location['name']
            location_id = location['id']
            print(f"✅ Locatie gevonden: '{location_name}'")
            print(f"   ID: {location_id}")
        else:
            print(f"❌ Locatie {args.location_id} niet gevonden")
            sys.exit(1)
    elif args.location_name:
        location_name = args.location_name.strip()
        print(f"✅ Locatie naam: '{location_name}'")
    
    # Build notification payload (same structure as push_notifications.py worker)
    activity_type = args.activity_type
    
    notification_title = "Turkbot"
    notification_body = f"Er is nieuwe activiteit bij {location_name}"
    
    # Deep link URL to location detail page
    if location_id:
        deep_link_url = f"/locations/{location_id}"
    else:
        # If no location_id, just link to feed
        deep_link_url = "/feed"
    
    notification_data = {
        "type": "activity",
        "activity_type": activity_type,
        "location_name": location_name,
        "url": deep_link_url,  # Deep link naar locatie detail pagina
    }
    
    if location_id:
        notification_data["location_id"] = location_id
    
    # Show what will be sent
    print("\n" + "=" * 70)
    print("ACTIVITY NOTIFICATION TEST")
    print("=" * 70)
    print(f"User ID:        {user_id}")
    print(f"Activity Type:  {activity_type}")
    print(f"Location Name:  {location_name}")
    if location_id:
        print(f"Location ID:    {location_id}")
    print(f"\nNotification:")
    print(f"  Title: {notification_title}")
    print(f"  Body:  {notification_body}")
    print(f"  Data:  {notification_data}")
    print(f"  URL:   {deep_link_url}")
    print(f"Mode:   {'DRY RUN (no notification will be sent)' if args.dry_run else 'LIVE'}")
    print("=" * 70 + "\n")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No notification will be sent\n")
        print("💡 Remove --dry-run to actually send the notification.")
        return
    
    # Check if user has notifications enabled
    prefs_sql = """
        SELECT enabled, activity_notifications
        FROM push_notification_preferences
        WHERE user_id = $1::uuid
    """
    prefs_row = await fetchrow(prefs_sql, user_id)
    
    if prefs_row:
        enabled = prefs_row.get("enabled", True)
        activity_notifications = prefs_row.get("activity_notifications", False)
        if not enabled:
            print(f"⚠️  WAARSCHUWING: Push notifications zijn uitgeschakeld voor deze gebruiker")
            print(f"   (enabled = false)")
        elif not activity_notifications:
            print(f"⚠️  WAARSCHUWING: Activity notifications zijn uitgeschakeld voor deze gebruiker")
            print(f"   (activity_notifications = false)")
            print(f"   Standaard zijn activity notifications UIT (false)")
            print(f"   De gebruiker moet deze handmatig aanzetten in de app instellingen")
    else:
        print("ℹ️  Geen notification preferences gevonden, defaults worden gebruikt:")
        print("   - enabled: true (default)")
        print("   - activity_notifications: false (default - UIT)")
        print("   ⚠️  Let op: Activity notifications zijn standaard UIT!")
    
    # Check if user has active device tokens
    tokens_sql = """
        SELECT COUNT(*) as count
        FROM device_tokens
        WHERE user_id = $1::uuid AND is_active = true
    """
    tokens_row = await fetchrow(tokens_sql, user_id)
    token_count = tokens_row.get("count", 0) if tokens_row else 0
    
    if token_count == 0:
        print(f"\n❌ GEEN ACTIEVE DEVICE TOKENS GEVONDEN")
        print(f"   Deze gebruiker heeft geen actieve device tokens geregistreerd.")
        print(f"   Zorg ervoor dat:")
        print(f"   1. De gebruiker push notifications heeft toegestaan in de browser/app")
        print(f"   2. Device tokens zijn geregistreerd in device_tokens tabel")
        print(f"   3. Device tokens zijn actief (is_active = true)")
        sys.exit(1)
    
    print(f"✅ {token_count} actieve device token(s) gevonden\n")
    
    # Confirm before sending
    print("⚠️  Je staat op het punt een activity notificatie te verzenden!")
    try:
        response = input("   Typ 'JA' om door te gaan, of druk Enter om te annuleren: ").strip()
        if response.upper() != "JA":
            print("\n❌ Geannuleerd door gebruiker.")
            return
    except KeyboardInterrupt:
        print("\n\n❌ Geannuleerd door gebruiker.")
        return
    
    print("\n📤 Verzenden van activity notificatie...\n")
    
    # Send notification (same logic as push_notifications.py worker)
    push_service = get_push_service()
    
    try:
        result = await push_service.send_notification(
            user_id=user_id,
            notification_type="activity",
            title=notification_title,
            body=notification_body,
            data=notification_data,
        )
        
        sent = result.get("sent", 0)
        failed = result.get("failed", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", [])
        
        # Summary
        print("\n" + "=" * 70)
        print("RESULTATEN")
        print("=" * 70)
        print(f"✅ Verzonden:     {sent} notification(s)")
        print(f"❌ Mislukt:       {failed} notification(s)")
        print(f"⏭️  Overgeslagen:  {skipped} notification(s)")
        print("=" * 70)
        
        if errors:
            print(f"\n⚠️  Fouten:")
            for error in errors[:5]:
                print(f"   - {error}")
            if len(errors) > 5:
                print(f"   ... en {len(errors) - 5} meer fouten")
        
        if sent > 0:
            print(f"\n✅ Activity notificatie succesvol verzonden!")
            print(f"   Check je device voor de notificatie.")
            if location_id:
                print(f"   Deep link URL: {deep_link_url}")
                print(f"   (Service worker converteert dit naar: #/locations/{location_id})")
            else:
                print(f"   Deep link URL: {deep_link_url}")
        
        if failed > 0:
            print(f"\n⚠️  Sommige notificaties zijn mislukt.")
            print(f"   Check de logs voor meer details.")
        
        if skipped > 0:
            reason = result.get("reason", "unknown")
            print(f"\nℹ️  {skipped} notificatie(s) overgeslagen: {reason}")
            if reason == "activity_notifications_disabled":
                print(f"   💡 Tip: Zet activity notifications aan in de app instellingen")
        
        logger.info(
            "test_activity_notification_sent",
            user_id=user_id,
            activity_type=activity_type,
            location_name=location_name,
            location_id=location_id,
            sent=sent,
            failed=failed,
            skipped=skipped,
        )
        
    except Exception as e:
        print(f"\n❌ ERROR bij verzenden: {e}")
        logger.error(
            "test_activity_notification_failed",
            user_id=user_id,
            activity_type=activity_type,
            location_name=location_name,
            error=str(e),
            exc_info=True
        )
        sys.exit(1)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\n❌ Geannuleerd door gebruiker.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.exception("send_test_activity_notification_script_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
