#!/usr/bin/env python3
"""
Monitor Brevo webhook events in real-time.

This script helps debug why emails aren't appearing in Brevo logs
by checking if webhook events are being received.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add Backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load environment variables
env_file = backend_dir / ".env"
try:
    if env_file.exists():
        load_dotenv(env_file, override=False)
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

from services.db_service import fetch
from app.core.logging import get_logger

logger = get_logger()


async def monitor_webhook_events(message_id: str, wait_minutes: int = 5):
    """Monitor for webhook events related to a message_id."""
    print("=" * 60)
    print("Brevo Webhook Event Monitor")
    print("=" * 60)
    print(f"\nMessage ID: {message_id}")
    print(f"Monitoring for: {wait_minutes} minutes")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=wait_minutes)
    check_interval = 10  # seconds
    
    print("Checking for webhook events every 10 seconds...")
    print("(Press Ctrl+C to stop early)\n")
    
    last_status = None
    
    try:
        while datetime.now() < end_time:
            # Check database for any updates
            sql = """
                SELECT 
                    id,
                    email,
                    status,
                    message_id,
                    sent_at,
                    delivered_at,
                    bounced_at,
                    bounce_reason,
                    updated_at
                FROM outreach_emails
                WHERE message_id = $1
                ORDER BY updated_at DESC
                LIMIT 1
            """
            
            result = await fetch(sql, message_id)
            
            if result:
                row = result[0]
                current_status = row.get('status')
                delivered = row.get('delivered_at')
                bounced = row.get('bounced_at')
                
                # Only print if status changed
                status_str = f"Status: {current_status}"
                if delivered:
                    status_str += f" | Delivered: {delivered}"
                if bounced:
                    status_str += f" | Bounced: {bounced} ({row.get('bounce_reason', 'Unknown')})"
                
                if status_str != last_status:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_str}")
                    last_status = status_str
                    
                    if delivered:
                        print(f"\n✅ Email delivered! Check your inbox.")
                        return True
                    elif bounced:
                        print(f"\n❌ Email bounced. Reason: {row.get('bounce_reason', 'Unknown')}")
                        return False
            else:
                # Email not in database yet (test email, not through outreach_mailer)
                if last_status != "not_in_db":
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Email not in database (test email)")
                    last_status = "not_in_db"
            
            # Wait before next check
            await asyncio.sleep(check_interval)
            
            # Show progress
            elapsed = (datetime.now() - start_time).total_seconds()
            remaining = (end_time - datetime.now()).total_seconds()
            if int(elapsed) % 30 == 0 and int(elapsed) > 0:  # Every 30 seconds
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Still monitoring... ({int(remaining)}s remaining)")
        
        print(f"\n⏱️  Monitoring period ended ({wait_minutes} minutes)")
        print(f"\n💡 Next steps:")
        print(f"1. Check Brevo Transactional Logs manually:")
        print(f"   https://app.brevo.com/transactional/email/logs")
        print(f"   Search for: {message_id}")
        print(f"\n2. Check Brevo Webhook Events:")
        print(f"   https://app.brevo.com/settings/webhooks")
        print(f"   Look for delivery/bounce events")
        print(f"\n3. Check spam/junk folder")
        print(f"\n4. Wait a bit longer - email delivery can take up to 10 minutes")
        
        return None
        
    except KeyboardInterrupt:
        print(f"\n\n⏸️  Monitoring stopped by user")
        return None


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/monitor_brevo_webhook.py <message_id> [wait_minutes]")
        print("\nExample:")
        print('  python scripts/monitor_brevo_webhook.py "<202512261808.65918364285@smtp-relay.mailin.fr>" 5')
        sys.exit(1)
    
    message_id = sys.argv[1]
    wait_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    await monitor_webhook_events(message_id, wait_minutes)


if __name__ == "__main__":
    asyncio.run(main())


