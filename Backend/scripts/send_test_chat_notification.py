#!/usr/bin/env python3
"""
Script om een test chat push notification naar een specifieke gebruiker te sturen.

Dit simuleert een chat notificatie zoals die wordt verstuurd wanneer iemand
een bericht in een chat topic plaatst waar je geabonneerd bent.

Usage:
    # Met user_id (UUID)
    python scripts/send_test_chat_notification.py \
        --user-id "123e4567-e89b-12d3-a456-426614174000" \
        --topic-title "Test Chat Topic" \
        --sender-name "Test Gebruiker" \
        --message "Dit is een test chat bericht"

    # Met email
    python scripts/send_test_chat_notification.py \
        --email "jouw@email.com" \
        --topic-title "Test Chat Topic" \
        --sender-name "Test Gebruiker" \
        --message "Dit is een test chat bericht"

    # Met topic_id (voor realistische data)
    python scripts/send_test_chat_notification.py \
        --email "jouw@email.com" \
        --topic-id 123 \
        --sender-name "Test Gebruiker" \
        --message "Dit is een test bericht"

    # Dry run (test zonder te verzenden)
    python scripts/send_test_chat_notification.py \
        --email "jouw@email.com" \
        --topic-title "Test" \
        --sender-name "Test" \
        --message "Test" \
        --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from services.db_service import init_db_pool, fetchrow
from services.push_service import get_push_service
from services.chat_service import get_chat_service

configure_logging(service_name="script")
logger = get_logger()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Send a test chat push notification to a specific user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using email
  python scripts/send_test_chat_notification.py \\
      --email "user@example.com" \\
      --topic-title "Test Chat" \\
      --sender-name "John Doe" \\
      --message "Hello, this is a test message!"

  # Using user_id (UUID)
  python scripts/send_test_chat_notification.py \\
      --user-id "123e4567-e89b-12d3-a456-426614174000" \\
      --topic-title "Test Chat" \\
      --sender-name "John Doe" \\
      --message "Test message"

  # Using existing topic_id
  python scripts/send_test_chat_notification.py \\
      --email "user@example.com" \\
      --topic-id 42 \\
      --sender-name "John Doe" \\
      --message "Test message"

  # Dry run (test without sending)
  python scripts/send_test_chat_notification.py \\
      --email "user@example.com" \\
      --topic-title "Test" \\
      --sender-name "Test" \\
      --message "Test" \\
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
    
    # Topic identification (mutually exclusive, but topic-id is optional)
    topic_group = ap.add_mutually_exclusive_group()
    topic_group.add_argument(
        "--topic-id",
        type=int,
        help="Existing chat topic ID (if provided, topic-title will be fetched from database)"
    )
    topic_group.add_argument(
        "--topic-title",
        help="Chat topic title (required if --topic-id not provided)"
    )
    
    # Message details
    ap.add_argument(
        "--sender-name",
        default="Test Gebruiker",
        help="Sender display name (default: 'Test Gebruiker')"
    )
    ap.add_argument(
        "--message",
        default="Dit is een test chat bericht voor notificatie testing.",
        help="Message content (default: 'Dit is een test chat bericht voor notificatie testing.')"
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


async def get_topic_title_by_id(topic_id: int) -> Optional[str]:
    """Get topic title from topic_id."""
    chat_service = get_chat_service()
    topic = await chat_service.get_topic(topic_id)
    if topic:
        return topic.get("title")
    return None


async def main_async() -> None:
    args = parse_args()
    
    # Validate arguments
    if not args.topic_id and not args.topic_title:
        print("ERROR: Either --topic-id or --topic-title is required")
        sys.exit(1)
    
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
    
    # Get topic title
    topic_id = args.topic_id
    topic_title = args.topic_title
    
    if topic_id:
        print(f"🔍 Ophalen van topic {topic_id}...")
        fetched_title = await get_topic_title_by_id(topic_id)
        if fetched_title:
            topic_title = fetched_title
            print(f"✅ Topic gevonden: '{topic_title}'")
        else:
            print(f"⚠️  Topic {topic_id} niet gevonden, gebruik --topic-title als fallback")
            if not topic_title:
                print("ERROR: --topic-title is required when topic_id is not found")
                sys.exit(1)
    else:
        # Use provided topic_title
        topic_id = None  # Will use a dummy ID for notification
    
    # Build notification payload
    # For chat messages, use "Turkbot" as title
    notification_title = "Turkbot"
    notification_body = "Je hebt een nieuw bericht ontvangen."
    notification_data = {
        "type": "chat_message",
        "topic_id": topic_id or 0,  # Use 0 if no topic_id provided
        "message_id": 0,  # Dummy message ID for testing
        "topic_title": topic_title,
        "url": f"/chat/topic/{topic_id}" if topic_id else "/chat",
    }
    
    # Show what will be sent
    print("\n" + "=" * 70)
    print("CHAT NOTIFICATION TEST")
    print("=" * 70)
    print(f"User ID:      {user_id}")
    print(f"Topic ID:     {topic_id or 'N/A'}")
    print(f"Topic Title:  {topic_title}")
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
        SELECT enabled, chat_notifications
        FROM push_notification_preferences
        WHERE user_id = $1::uuid
    """
    prefs_row = await fetchrow(prefs_sql, user_id)
    
    if prefs_row:
        enabled = prefs_row.get("enabled", True)
        chat_notifications = prefs_row.get("chat_notifications", True)
        if not enabled:
            print(f"⚠️  WAARSCHUWING: Push notifications zijn uitgeschakeld voor deze gebruiker")
            print(f"   (enabled = false)")
        elif not chat_notifications:
            print(f"⚠️  WAARSCHUWING: Chat notifications zijn uitgeschakeld voor deze gebruiker")
            print(f"   (chat_notifications = false)")
    else:
        print("ℹ️  Geen notification preferences gevonden, defaults worden gebruikt:")
        print("   - enabled: true (default)")
        print("   - chat_notifications: true (default)")
    
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
    print("⚠️  Je staat op het punt een chat notificatie te verzenden!")
    try:
        response = input("   Typ 'JA' om door te gaan, of druk Enter om te annuleren: ").strip()
        if response.upper() != "JA":
            print("\n❌ Geannuleerd door gebruiker.")
            return
    except KeyboardInterrupt:
        print("\n\n❌ Geannuleerd door gebruiker.")
        return
    
    print("\n📤 Verzenden van chat notificatie...\n")
    
    # Send notification
    push_service = get_push_service()
    
    try:
        result = await push_service.send_notification(
            user_id=user_id,
            notification_type="chat_message",
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
            print(f"\n✅ Chat notificatie succesvol verzonden!")
            print(f"   Check je device voor de notificatie.")
        
        if failed > 0:
            print(f"\n⚠️  Sommige notificaties zijn mislukt.")
            print(f"   Check de logs voor meer details.")
        
        if skipped > 0:
            reason = result.get("reason", "unknown")
            print(f"\nℹ️  {skipped} notificatie(s) overgeslagen: {reason}")
        
        logger.info(
            "test_chat_notification_sent",
            user_id=user_id,
            topic_id=topic_id,
            topic_title=topic_title,
            sent=sent,
            failed=failed,
            skipped=skipped,
        )
        
    except Exception as e:
        print(f"\n❌ ERROR bij verzenden: {e}")
        logger.error(
            "test_chat_notification_failed",
            user_id=user_id,
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
        logger.exception("send_test_chat_notification_script_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
