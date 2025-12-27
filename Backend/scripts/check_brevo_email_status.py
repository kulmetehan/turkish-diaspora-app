#!/usr/bin/env python3
"""
Check the status of a Brevo email by message_id.

This script helps debug why emails aren't being received by:
1. Checking if webhook events were received
2. Checking database for email status
3. Providing links to Brevo dashboard
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

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


async def check_email_status(message_id: str):
    """Check email status in database and provide debugging info."""
    print("=" * 60)
    print("Brevo Email Status Check")
    print("=" * 60)
    print(f"\nMessage ID: {message_id}\n")
    
    # Check database for this message_id
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
            created_at,
            updated_at
        FROM outreach_emails
        WHERE message_id = $1
        ORDER BY created_at DESC
        LIMIT 1
    """
    
    result = await fetch(sql, message_id)
    
    if result:
        row = result[0]
        print("📧 Email found in database:")
        print(f"   ID: {row.get('id')}")
        print(f"   Email: {row.get('email')}")
        print(f"   Status: {row.get('status')}")
        print(f"   Sent at: {row.get('sent_at')}")
        print(f"   Delivered at: {row.get('delivered_at') or 'Not yet'}")
        print(f"   Bounced at: {row.get('bounced_at') or 'No'}")
        if row.get('bounce_reason'):
            print(f"   Bounce reason: {row.get('bounce_reason')}")
        print(f"   Created: {row.get('created_at')}")
        print(f"   Updated: {row.get('updated_at')}")
        
        # Status interpretation
        status = row.get('status', '').lower()
        if status == 'sent' and not row.get('delivered_at'):
            print(f"\n⚠️  Status: Email sent but not yet marked as delivered")
            print(f"   This could mean:")
            print(f"   - Webhook event hasn't arrived yet (wait 1-2 minutes)")
            print(f"   - Webhook is not configured correctly")
            print(f"   - Email is still in transit")
        elif status == 'bounced':
            print(f"\n❌ Status: Email bounced")
            print(f"   Reason: {row.get('bounce_reason', 'Unknown')}")
        elif row.get('delivered_at'):
            print(f"\n✅ Status: Email delivered!")
            print(f"   Delivered at: {row.get('delivered_at')}")
    else:
        print("❌ Email not found in database")
        print(f"   This could mean:")
        print(f"   - Email was sent via test script (not through outreach_mailer)")
        print(f"   - message_id doesn't match")
        print(f"   - Database hasn't been updated yet")
    
    # Check for any recent emails with similar message_id pattern
    print(f"\n" + "=" * 60)
    print("Recent outreach emails (last 5):")
    print("=" * 60)
    
    recent_sql = """
        SELECT 
            id,
            email,
            status,
            message_id,
            sent_at,
            delivered_at,
            bounced_at,
            created_at
        FROM outreach_emails
        ORDER BY created_at DESC
        LIMIT 5
    """
    
    recent = await fetch(recent_sql)
    if recent:
        for row in recent:
            msg_id = row.get('message_id', 'N/A')[:50] if row.get('message_id') else 'N/A'
            print(f"\n  Email: {row.get('email')}")
            print(f"    Status: {row.get('status')}")
            print(f"    Message ID: {msg_id}")
            print(f"    Sent: {row.get('sent_at')}")
            print(f"    Delivered: {row.get('delivered_at') or 'Not yet'}")
    else:
        print("  No outreach emails found in database")
    
    # Provide debugging links
    print(f"\n" + "=" * 60)
    print("🔍 Debugging Links:")
    print("=" * 60)
    print(f"\n1. Brevo Transactional Email Logs:")
    print(f"   https://app.brevo.com/transactional/email/logs")
    print(f"   Search for: {message_id}")
    
    print(f"\n2. Brevo Webhook Events:")
    print(f"   https://app.brevo.com/settings/webhooks")
    print(f"   Check if delivery/bounce events were sent")
    
    print(f"\n3. Brevo Bounces:")
    print(f"   https://app.brevo.com/statistics/bounces")
    print(f"   Check if email bounced")
    
    print(f"\n4. Sender Verification:")
    print(f"   https://app.brevo.com/settings/senders")
    print(f"   Verify info@turkspot.app is verified for Transactional")
    
    print(f"\n5. Check Webhook Configuration:")
    print(f"   - URL: https://api.turkspot.nl/api/v1/brevo/webhook")
    print(f"   - Token: Must match BREVO_WEBHOOK_SECRET in .env")
    print(f"   - Events: delivered, hard_bounce, soft_bounce, unsubscribed")
    
    print(f"\n" + "=" * 60)
    print("💡 Next Steps:")
    print("=" * 60)
    print(f"1. Wait 1-2 minutes for webhook events to arrive")
    print(f"2. Check Brevo dashboard logs (links above)")
    print(f"3. Verify webhook is receiving events")
    print(f"4. Check spam/junk folder in recipient inbox")
    print(f"5. If bounced, check bounce reason in Brevo dashboard")


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_brevo_email_status.py <message_id>")
        print("\nExample:")
        print('  python scripts/check_brevo_email_status.py "<202512261737.46558537389@smtp-relay.mailin.fr>"')
        sys.exit(1)
    
    message_id = sys.argv[1]
    await check_email_status(message_id)


if __name__ == "__main__":
    asyncio.run(main())
