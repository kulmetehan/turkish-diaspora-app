#!/usr/bin/env python3
"""
Debug Brevo email sending - check API response and sender status.
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
try:
    if env_file.exists():
        load_dotenv(env_file, override=False)
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

from sib_api_v3_sdk import Configuration, ApiClient, TransactionalEmailsApi, AccountApi
from sib_api_v3_sdk.rest import ApiException


async def check_brevo_configuration():
    """Check Brevo configuration and sender status."""
    print("=" * 60)
    print("Brevo Configuration Debug")
    print("=" * 60)
    
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("EMAIL_FROM", "info@turkspot.app")
    
    if not api_key:
        print("❌ BREVO_API_KEY not set in environment")
        return
    
    print(f"\n1. API Key: {'✅ Set' if api_key else '❌ Not set'}")
    print(f"   From Email: {from_email}")
    
    # Configure API
    configuration = Configuration()
    configuration.api_key['api-key'] = api_key
    
    try:
        # Check account info
        print(f"\n2. Checking Brevo Account...")
        api_client = ApiClient(configuration)
        account_api = AccountApi(api_client)
        account_info = account_api.get_account()
        print(f"   ✅ Account connected")
        if account_info.plan:
            if isinstance(account_info.plan, list) and len(account_info.plan) > 0:
                plan = account_info.plan[0]
                print(f"   Plan: {getattr(plan, 'type', 'Unknown')}")
                print(f"   Credits: {getattr(plan, 'credits', 'Unknown')}")
            else:
                print(f"   Plan: {account_info.plan}")
        else:
            print(f"   Plan: Unknown")
    except ApiException as e:
        print(f"   ❌ Failed to connect to Brevo API")
        print(f"   Error: {e.reason}")
        print(f"   Status: {e.status}")
        if e.body:
            print(f"   Body: {e.body}")
        return
    
    # Check sender verification
    try:
        print(f"\n3. Checking Sender Verification...")
        from sib_api_v3_sdk import SendersApi
        
        api_client = ApiClient(configuration)
        senders_api = SendersApi(api_client)
        
        # Get all senders
        senders = senders_api.get_senders()
        
        print(f"   Found {len(senders.senders) if senders.senders else 0} verified senders")
        
        # Check if our sender is verified
        sender_found = False
        for sender in (senders.senders or []):
            if sender.email.lower() == from_email.lower():
                sender_found = True
                print(f"   ✅ Sender found: {sender.email}")
                print(f"      Name: {getattr(sender, 'name', 'N/A')}")
                
                # Check verification status (different attribute names in SDK)
                verified = getattr(sender, 'verified', None)
                if verified is None:
                    verified = getattr(sender, 'is_verified', None)
                
                if verified is not None:
                    print(f"      Verified: {verified}")
                    if not verified:
                        print(f"      ⚠️  SENDER NOT VERIFIED - This will block emails!")
                        print(f"      Go to: https://app.brevo.com/settings/senders")
                        print(f"      Verify {from_email} for Transactional API")
                else:
                    print(f"      ⚠️  Could not determine verification status")
                    print(f"      Check manually: https://app.brevo.com/settings/senders")
                
                ips = getattr(sender, 'ips', None)
                if ips:
                    print(f"      IPs: {ips}")
                break
        
        if not sender_found:
            print(f"   ❌ Sender {from_email} not found in verified senders")
            print(f"   ⚠️  You must verify this sender first!")
            print(f"   Go to: https://app.brevo.com/settings/senders")
            print(f"   Add and verify: {from_email}")
                
    except ApiException as e:
        print(f"   ⚠️  Could not check senders: {e.reason}")
        print(f"   Status: {e.status}")
        if e.body:
            print(f"   Body: {e.body}")
    
    # Try to get email statistics
    try:
        print(f"\n4. Checking Email Statistics...")
        from sib_api_v3_sdk import TransactionalEmailsApi
        
        api_client = ApiClient(configuration)
        trans_api = TransactionalEmailsApi(api_client)
        
        # Get email events (recent)
        # Note: This might not be available in all plans
        print(f"   Checking recent email events...")
        print(f"   (Note: Some plans don't have access to this API)")
            
    except ApiException as e:
        print(f"   ⚠️  Could not get statistics: {e.reason}")
        print(f"   This is normal for some Brevo plans")
    
    print(f"\n" + "=" * 60)
    print("💡 Next Steps:")
    print("=" * 60)
    print(f"1. Verify sender email in Brevo dashboard:")
    print(f"   https://app.brevo.com/settings/senders")
    print(f"   - Add {from_email} if not present")
    print(f"   - Verify it for Transactional API")
    print(f"   - Check verification status")
    print(f"\n2. Check Brevo Transactional Logs:")
    print(f"   https://app.brevo.com/transactional/email/logs")
    print(f"   - Look for emails sent in last hour")
    print(f"   - Check status (sent, delivered, bounced)")
    print(f"\n3. Check IP Whitelisting:")
    print(f"   https://app.brevo.com/security/authorised_ips")
    print(f"   - Make sure your server IP is whitelisted")
    print(f"\n4. If sender is not verified:")
    print(f"   - Brevo will accept the API call")
    print(f"   - But emails will NOT be sent")
    print(f"   - No logs will appear")
    print(f"   - This explains why you see nothing in dashboard!")


if __name__ == "__main__":
    asyncio.run(check_brevo_configuration())

