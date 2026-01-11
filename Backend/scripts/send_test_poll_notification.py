#!/usr/bin/env python3
"""
Script om een test poll push notification naar een specifieke gebruiker te sturen.

Dit simuleert een poll notificatie zoals die wordt verstuurd wanneer een nieuwe poll
wordt gegenereerd door de poll generator bot.

Usage:
    # Met email en bestaande poll ID
    python scripts/send_test_poll_notification.py \
        --email "jouw@email.com" \
        --poll-id 123

    # Met email en laat poll ID automatisch vinden (nieuwste actieve poll)
    python scripts/send_test_poll_notification.py \
        --email "jouw@email.com"

    # Met user_id (UUID)
    python scripts/send_test_poll_notification.py \
        --user-id "123e4567-e89b-12d3-a456-426614174000" \
        --poll-id 123

    # Dry run (test zonder te verzenden)
    python scripts/send_test_poll_notification.py \
        --email "jouw@email.com" \
        --poll-id 123 \
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
        description="Send a test poll push notification to a specific user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using email with existing poll ID
  python scripts/send_test_poll_notification.py \\
      --email "user@example.com" \\
      --poll-id 42

  # Using email, automatically find newest active poll
  python scripts/send_test_poll_notification.py \\
      --email "user@example.com"

  # Using user_id (UUID)
  python scripts/send_test_poll_notification.py \\
      --user-id "123e4567-e89b-12d3-a456-426614174000" \\
      --poll-id 42

  # Dry run (test without sending)
  python scripts/send_test_poll_notification.py \\
      --email "user@example.com" \\
      --poll-id 42 \\
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
    
    # Poll identification (optional, will use newest active poll if not provided)
    ap.add_argument(
        "--poll-id",
        type=int,
        help="Existing poll ID (if not provided, will use newest active poll)"
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


async def get_poll_by_id(poll_id: int) -> Optional[Dict[str, Any]]:
    """Get poll details from poll_id."""
    sql = """
        SELECT id, title, question, status, starts_at, ends_at
        FROM polls
        WHERE id = $1
    """
    row = await fetchrow(sql, poll_id)
    if row:
        return dict(row)
    return None


async def get_newest_active_poll() -> Optional[Dict[str, Any]]:
    """Get the newest active poll."""
    sql = """
        SELECT id, title, question, status, starts_at, ends_at
        FROM polls
        WHERE status = 'active'
        ORDER BY created_at DESC
        LIMIT 1
    """
    row = await fetchrow(sql)
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
    
    # Get poll
    poll = None
    poll_id = args.poll_id
    
    if poll_id:
        print(f"🔍 Ophalen van poll {poll_id}...")
        poll = await get_poll_by_id(poll_id)
        if poll:
            print(f"✅ Poll gevonden: '{poll['title']}'")
            print(f"   Vraag: {poll['question']}")
            print(f"   Status: {poll['status']}")
        else:
            print(f"❌ Poll {poll_id} niet gevonden")
            sys.exit(1)
    else:
        print(f"🔍 Zoeken naar nieuwste actieve poll...")
        poll = await get_newest_active_poll()
        if poll:
            poll_id = poll['id']
            print(f"✅ Nieuwste actieve poll gevonden:")
            print(f"   ID: {poll_id}")
            print(f"   Titel: '{poll['title']}'")
            print(f"   Vraag: {poll['question']}")
        else:
            print(f"❌ Geen actieve poll gevonden in database")
            print("   Gebruik --poll-id om een specifieke poll te gebruiken")
            sys.exit(1)
    
    # Build notification payload (same structure as poll_generator_bot.py)
    notification_title = "Nieuwe Poll"
    
    notification_body = poll['title'][:100]
    if len(poll['title']) > 100:
        notification_body = f"{poll['title'][:97]}..."
    
    # Deep link URL to feed with timeline filter and pollId (same as poll_generator_bot.py)
    deep_link_url = f"/feed?filter=timeline&pollId={poll_id}"
    
    notification_data = {
        "type": "poll",
        "poll_id": poll_id,
        "url": deep_link_url,  # Deep link naar feed met timeline filter en pollId
    }
    
    # Show what will be sent
    print("\n" + "=" * 70)
    print("POLL NOTIFICATION TEST")
    print("=" * 70)
    print(f"User ID:      {user_id}")
    print(f"Poll ID:      {poll_id}")
    print(f"Poll Title:   {poll['title']}")
    print(f"Poll Question: {poll['question']}")
    print(f"\nNotification:")
    print(f"  Title: {notification_title}")
    print(f"  Body:  {notification_body}")
    print(f"  Data:  {notification_data}")
    print(f"Mode:   {'DRY RUN (no notification will be sent)' if args.dry_run else 'LIVE'}")
    print("=" * 70 + "\n")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No notification will be sent\n")
        print("💡 Remove --dry-run to actually send the notification.")
        return
    
    # Check if user has notifications enabled
    prefs_sql = """
        SELECT enabled, poll_notifications
        FROM push_notification_preferences
        WHERE user_id = $1::uuid
    """
    prefs_row = await fetchrow(prefs_sql, user_id)
    
    if prefs_row:
        enabled = prefs_row.get("enabled", True)
        poll_notifications = prefs_row.get("poll_notifications", True)
        if not enabled:
            print(f"⚠️  WAARSCHUWING: Push notifications zijn uitgeschakeld voor deze gebruiker")
            print(f"   (enabled = false)")
        elif not poll_notifications:
            print(f"⚠️  WAARSCHUWING: Poll notifications zijn uitgeschakeld voor deze gebruiker")
            print(f"   (poll_notifications = false)")
    else:
        print("ℹ️  Geen notification preferences gevonden, defaults worden gebruikt:")
        print("   - enabled: true (default)")
        print("   - poll_notifications: true (default)")
    
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
    print("⚠️  Je staat op het punt een poll notificatie te verzenden!")
    try:
        response = input("   Typ 'JA' om door te gaan, of druk Enter om te annuleren: ").strip()
        if response.upper() != "JA":
            print("\n❌ Geannuleerd door gebruiker.")
            return
    except KeyboardInterrupt:
        print("\n\n❌ Geannuleerd door gebruiker.")
        return
    
    print("\n📤 Verzenden van poll notificatie...\n")
    
    # Send notification (same logic as poll_generator_bot.py)
    push_service = get_push_service()
    
    try:
        result = await push_service.send_notification(
            user_id=user_id,
            notification_type="poll",
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
            print(f"\n✅ Poll notificatie succesvol verzonden!")
            print(f"   Check je device voor de notificatie.")
            print(f"   Deep link URL: {deep_link_url}")
            print(f"   (Service worker converteert dit naar: #/feed?filter=timeline&pollId={poll_id})")
        
        if failed > 0:
            print(f"\n⚠️  Sommige notificaties zijn mislukt.")
            print(f"   Check de logs voor meer details.")
        
        if skipped > 0:
            reason = result.get("reason", "unknown")
            print(f"\nℹ️  {skipped} notificatie(s) overgeslagen: {reason}")
        
        logger.info(
            "test_poll_notification_sent",
            user_id=user_id,
            poll_id=poll_id,
            poll_title=poll['title'],
            sent=sent,
            failed=failed,
            skipped=skipped,
        )
        
    except Exception as e:
        print(f"\n❌ ERROR bij verzenden: {e}")
        logger.error(
            "test_poll_notification_failed",
            user_id=user_id,
            poll_id=poll_id,
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
        logger.exception("send_test_poll_notification_script_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
