#!/usr/bin/env python3
"""
Script om de push notification status te controleren.

Dit script toont:
- Aantal gebruikers met device tokens
- Aantal gebruikers met push preferences
- Status van push notifications setup

Usage:
    python scripts/check_push_status.py
"""

import asyncio
import sys
from pathlib import Path

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from services.db_service import init_db_pool, fetch, fetchrow

configure_logging(service_name="script")
logger = get_logger()


async def main_async() -> None:
    await init_db_pool()
    
    print("\n" + "=" * 70)
    print("PUSH NOTIFICATION STATUS CHECK")
    print("=" * 70 + "\n")
    
    # Check device tokens
    device_tokens_sql = """
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(*) FILTER (WHERE is_active = true) as active_tokens,
            COUNT(DISTINCT user_id) FILTER (WHERE is_active = true) as users_with_active_tokens
        FROM device_tokens
    """
    device_stats = await fetchrow(device_tokens_sql)
    
    print("📱 DEVICE TOKENS:")
    print(f"   Totaal tokens:        {device_stats.get('total', 0)}")
    print(f"   Unieke gebruikers:    {device_stats.get('unique_users', 0)}")
    print(f"   Actieve tokens:        {device_stats.get('active_tokens', 0)}")
    print(f"   Gebruikers met actieve tokens: {device_stats.get('users_with_active_tokens', 0)}")
    print()
    
    # Check push preferences
    preferences_sql = """
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE enabled = true) as enabled_count,
            COUNT(*) FILTER (WHERE enabled = false) as disabled_count
        FROM push_notification_preferences
    """
    prefs_stats = await fetchrow(preferences_sql)
    
    print("⚙️  PUSH PREFERENCES:")
    print(f"   Totaal voorkeuren:    {prefs_stats.get('total', 0)}")
    print(f"   Ingeschakeld:         {prefs_stats.get('enabled_count', 0)}")
    print(f"   Uitgeschakeld:        {prefs_stats.get('disabled_count', 0)}")
    print()
    
    # Check users with both active tokens AND enabled preferences
    eligible_sql = """
        SELECT COUNT(DISTINCT dt.user_id) as eligible_users
        FROM device_tokens dt
        LEFT JOIN push_notification_preferences p ON p.user_id = dt.user_id
        WHERE dt.is_active = true
            AND (p.enabled IS NULL OR p.enabled = true)
    """
    eligible = await fetchrow(eligible_sql)
    eligible_count = eligible.get('eligible_users', 0) if eligible else 0
    
    print("✅ GEBRUIKERS DIE NOTIFICATIES KUNNEN ONTVANGEN:")
    print(f"   {eligible_count} gebruikers")
    print()
    
    # Show detailed breakdown
    if device_stats.get('users_with_active_tokens', 0) > 0:
        print("📋 DETAILED BREAKDOWN:")
        print()
        
        # Users with tokens but no preferences
        no_prefs_sql = """
            SELECT dt.user_id, COUNT(*) as token_count
            FROM device_tokens dt
            LEFT JOIN push_notification_preferences p ON p.user_id = dt.user_id
            WHERE dt.is_active = true
                AND p.user_id IS NULL
            GROUP BY dt.user_id
            LIMIT 5
        """
        no_prefs = await fetch(no_prefs_sql)
        
        if no_prefs:
            print(f"   Gebruikers met tokens maar geen preferences ({len(no_prefs)} gevonden):")
            for row in no_prefs:
                print(f"     - User {row['user_id']} ({row.get('token_count', 0)} tokens)")
            if len(no_prefs) >= 5:
                print(f"     ... (meer beschikbaar)")
            print()
        
        # Users with disabled preferences
        disabled_sql = """
            SELECT dt.user_id, COUNT(*) as token_count
            FROM device_tokens dt
            INNER JOIN push_notification_preferences p ON p.user_id = dt.user_id
            WHERE dt.is_active = true
                AND p.enabled = false
            GROUP BY dt.user_id
            LIMIT 5
        """
        disabled = await fetch(disabled_sql)
        
        if disabled:
            print(f"   Gebruikers met tokens maar notifications uitgeschakeld ({len(disabled)} gevonden):")
            for row in disabled:
                print(f"     - User {row['user_id']} ({row.get('token_count', 0)} tokens)")
            if len(disabled) >= 5:
                print(f"     ... (meer beschikbaar)")
            print()
    
    # Recommendations
    print("💡 AANBEVELINGEN:")
    if eligible_count == 0:
        print("   ❌ Geen gebruikers kunnen notificaties ontvangen.")
        print("   → Gebruikers moeten:")
        print("     1. Push notifications inschakelen in de app (Account > Push Notifications)")
        print("     2. Toestemming geven in de browser")
        print("     3. Device token wordt dan automatisch geregistreerd")
    elif eligible_count < 5:
        print(f"   ⚠️  Slechts {eligible_count} gebruiker(s) kunnen notificaties ontvangen.")
        print("   → Overweeg gebruikers te informeren over push notifications")
    else:
        print(f"   ✅ {eligible_count} gebruikers kunnen notificaties ontvangen.")
        print("   → Je kunt nu notifications verzenden met send_system_notification.py")
    
    print("\n" + "=" * 70 + "\n")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\n❌ Geannuleerd door gebruiker.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.exception("check_push_status_script_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()


