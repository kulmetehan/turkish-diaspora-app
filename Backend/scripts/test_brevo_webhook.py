#!/usr/bin/env python3
"""
Test script for Brevo webhook endpoint.

This script simulates Brevo webhook events to test the webhook handler.
"""

import asyncio
import sys
import os
import json
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
    print(f"   Make sure BREVO_WEBHOOK_SECRET is set in your environment")

import httpx
from app.core.logging import get_logger

logger = get_logger()


async def test_webhook_endpoint():
    """Test the Brevo webhook endpoint."""
    print("=" * 60)
    print("Brevo Webhook Test")
    print("=" * 60)
    
    # Get configuration
    # Try to detect if we're in production or local
    backend_url = os.getenv("BACKEND_URL") or os.getenv("API_BASE_URL") or "http://localhost:8000"
    webhook_secret = os.getenv("BREVO_WEBHOOK_SECRET")
    webhook_url = f"{backend_url}/api/v1/brevo/webhook"
    
    print(f"\n1. Configuration:")
    print(f"   Backend URL: {backend_url}")
    print(f"   Webhook URL: {webhook_url}")
    print(f"   Webhook Secret: {'✅ Set' if webhook_secret else '❌ Not set'}")
    
    if not webhook_secret:
        print(f"\n❌ BREVO_WEBHOOK_SECRET not set in .env")
        print(f"   Add: BREVO_WEBHOOK_SECRET=your-token-here")
        return False
    
    # Test 1: Delivery event
    print(f"\n2. Testing Delivery Event:")
    delivery_payload = {
        "event": "delivered",
        "email": "test@example.com",
        "message-id": "<202512261653.38010201786@smtp-relay.mailin.fr>",
        "date": "2025-12-26T16:53:35.216+00:00",
        "ts": 1735312415,
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {webhook_secret}",
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                json=delivery_payload,
                headers=headers,
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 200:
                print(f"   ✅ Delivery event processed successfully")
            else:
                print(f"   ❌ Delivery event failed")
                return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Bounce event
    print(f"\n3. Testing Bounce Event:")
    bounce_payload = {
        "event": "hard_bounce",
        "email": "bounce@example.com",
        "message-id": "<202512261654.92642376024@smtp-relay.mailin.fr>",
        "reason": "550 5.1.1 User unknown",
        "date": "2025-12-26T16:54:05.448+00:00",
        "ts": 1735312445,
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                json=bounce_payload,
                headers=headers,
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 200:
                print(f"   ✅ Bounce event processed successfully")
            else:
                print(f"   ❌ Bounce event failed")
                return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Invalid token
    print(f"\n4. Testing Invalid Token (should fail):")
    invalid_headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer invalid-token",
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                json=delivery_payload,
                headers=invalid_headers,
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 401:
                print(f"   ✅ Invalid token correctly rejected (401)")
            else:
                print(f"   ⚠️  Expected 401, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n" + "=" * 60)
    print(f"✅ Webhook tests completed")
    print(f"=" * 60)
    print(f"\nNext steps:")
    print(f"1. Check Brevo dashboard webhook logs:")
    print(f"   https://app.brevo.com/settings/webhooks")
    print(f"2. Send a test email and check if webhook events arrive:")
    print(f"   python -m scripts.test_brevo_email your-email@example.com")
    print(f"3. Check database for status updates:")
    print(f"   SELECT id, email, status, message_id, delivered_at, bounced_at")
    print(f"   FROM outreach_emails")
    print(f"   ORDER BY created_at DESC LIMIT 10;")
    
    return True


if __name__ == "__main__":
    asyncio.run(test_webhook_endpoint())

