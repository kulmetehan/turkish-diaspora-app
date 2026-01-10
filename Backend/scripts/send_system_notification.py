#!/usr/bin/env python3
"""
Script om een system push notification naar alle gebruikers te sturen.

Dit script stuurt een system notification naar alle gebruikers die:
- Een actief device token hebben geregistreerd
- Push notifications hebben ingeschakeld (enabled = true)

Usage:
    # Basis gebruik
    python scripts/send_system_notification.py --title "Belangrijke update!" --body "We hebben een nieuwe functie toegevoegd."

    # Met extra data (JSON)
    python scripts/send_system_notification.py --title "Welkom!" --body "Bedankt voor het gebruiken van onze app." --data '{"type":"announcement","url":"/"}'

    # Dry run (test zonder te verzenden)
    python scripts/send_system_notification.py --title "Test" --body "Dit is een test" --dry-run
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from services.db_service import init_db_pool, fetch
from services.push_service import get_push_service

configure_logging(service_name="script")
logger = get_logger()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Send a system push notification to all users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic notification
  python scripts/send_system_notification.py --title "Update!" --body "Nieuwe functie beschikbaar"
  
  # With data payload
  python scripts/send_system_notification.py --title "Event" --body "Nieuw evenement" --data '{"type":"event","id":123}'
  
  # Dry run (test without sending)
  python scripts/send_system_notification.py --title "Test" --body "Test bericht" --dry-run
        """
    )
    ap.add_argument(
        "--title",
        required=True,
        help="Notification title (required)"
    )
    ap.add_argument(
        "--body",
        required=True,
        help="Notification body text (required)"
    )
    ap.add_argument(
        "--data",
        help="Optional JSON data payload (e.g., '{\"type\":\"announcement\",\"url\":\"/\"}')"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually send notifications, just show what would be sent"
    )
    return ap.parse_args()


async def main_async() -> None:
    args = parse_args()
    
    title = args.title.strip()
    body = args.body.strip()
    dry_run = args.dry_run
    
    # Parse optional data
    data = None
    if args.data:
        try:
            data = json.loads(args.data)
            if not isinstance(data, dict):
                print(f"ERROR: --data must be a JSON object (dict), got: {type(data).__name__}")
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in --data: {e}")
            print(f"  Provided: {args.data}")
            sys.exit(1)
    
    # Validate inputs
    if not title:
        print("ERROR: --title cannot be empty")
        sys.exit(1)
    
    if not body:
        print("ERROR: --body cannot be empty")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("SYSTEM NOTIFICATION BROADCAST")
    print("=" * 70)
    print(f"Title: {title}")
    print(f"Body: {body}")
    if data:
        print(f"Data: {json.dumps(data, indent=2)}")
    print(f"Mode: {'DRY RUN (no notifications will be sent)' if dry_run else 'LIVE'}")
    print("=" * 70 + "\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No notifications will be sent\n")
    
    await init_db_pool()
    
    # Get all users with active device tokens
    users_sql = """
        SELECT DISTINCT dt.user_id, COUNT(*) as device_count
        FROM device_tokens dt
        LEFT JOIN push_notification_preferences p ON p.user_id = dt.user_id
        WHERE dt.is_active = true
            AND (p.enabled IS NULL OR p.enabled = true)
        GROUP BY dt.user_id
        ORDER BY dt.user_id
    """
    users = await fetch(users_sql)
    
    if not users:
        print("❌ Geen gebruikers gevonden met actieve device tokens en ingeschakelde notifications.")
        print("   Zorg ervoor dat gebruikers:")
        print("   - Push notifications hebben geregistreerd (device_tokens)")
        print("   - Push notifications hebben ingeschakeld (push_notification_preferences.enabled = true)")
        return
    
    total_users = len(users)
    total_devices = sum(row.get("device_count", 0) for row in users)
    
    print(f"📊 Gevonden: {total_users} gebruikers met {total_devices} actieve devices\n")
    
    if dry_run:
        print("✅ DRY RUN: Zou notifications verzenden naar:")
        for i, user_row in enumerate(users[:10], 1):  # Show first 10
            print(f"   {i}. User {user_row['user_id']} ({user_row.get('device_count', 0)} devices)")
        if total_users > 10:
            print(f"   ... en {total_users - 10} meer gebruikers")
        print("\n💡 Gebruik zonder --dry-run om daadwerkelijk te verzenden.")
        return
    
    # Confirm before sending
    print("⚠️  Je staat op het punt notifications te verzenden naar ALLE gebruikers!")
    print(f"   Dit kan niet ongedaan worden gemaakt.\n")
    
    try:
        response = input("   Typ 'JA' om door te gaan, of druk Enter om te annuleren: ").strip()
        if response.upper() != "JA":
            print("\n❌ Geannuleerd door gebruiker.")
            return
    except KeyboardInterrupt:
        print("\n\n❌ Geannuleerd door gebruiker.")
        return
    
    print("\n📤 Verzenden van notifications...\n")
    
    push_service = get_push_service()
    
    total_sent = 0
    total_failed = 0
    total_skipped = 0
    errors = []
    
    # Send to each user
    for i, user_row in enumerate(users, 1):
        user_id = str(user_row["user_id"])
        device_count = user_row.get("device_count", 0)
        
        try:
            result = await push_service.send_notification(
                user_id=user_id,
                notification_type="system",  # System notifications worden altijd verzonden
                title=title,
                body=body,
                data=data,
            )
            
            sent = result.get("sent", 0)
            failed = result.get("failed", 0)
            skipped = result.get("skipped", 0)
            
            total_sent += sent
            total_failed += failed
            total_skipped += skipped
            
            if result.get("errors"):
                errors.extend(result.get("errors", []))
            
            # Progress indicator
            if total_users > 10:
                if i % max(1, total_users // 10) == 0 or i == total_users:
                    progress = (i / total_users) * 100
                    print(f"   Verwerkt: {i}/{total_users} gebruikers ({progress:.0f}%)...")
        except Exception as e:
            error_msg = f"User {user_id}: {str(e)}"
            errors.append(error_msg)
            logger.error(
                "send_notification_failed",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            total_failed += device_count
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTATEN")
    print("=" * 70)
    print(f"✅ Verzonden:     {total_sent} notifications")
    print(f"❌ Mislukt:       {total_failed} notifications")
    print(f"⏭️  Overgeslagen:  {total_skipped} notifications")
    print(f"👥 Gebruikers:    {total_users} gebruikers verwerkt")
    print("=" * 70)
    
    if errors:
        print(f"\n⚠️  Fouten (eerste 10):")
        for error in errors[:10]:
            print(f"   - {error}")
        if len(errors) > 10:
            print(f"   ... en {len(errors) - 10} meer fouten")
    
    if total_failed > 0:
        print(f"\n💡 Tip: Controleer de logs voor meer details over mislukte verzendingen.")
        print(f"   Mislukte subscriptions worden automatisch als inactief gemarkeerd.")
    
    logger.info(
        "broadcast_notification_completed",
        total_users=total_users,
        total_sent=total_sent,
        total_failed=total_failed,
        total_skipped=total_skipped,
        title=title,
    )


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\n❌ Geannuleerd door gebruiker.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.exception("send_system_notification_script_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()


