# Backend/services/google_business_service.py
from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/google-business/callback")


class GoogleBusinessService:
    """
    Service for Google Business Profile sync.
    """
    
    def __init__(self):
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            logger.warning(
                "google_oauth_not_configured",
                message="Google OAuth credentials not configured"
            )
    
    def get_oauth_url(self, state: str) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: CSRF state token
            
        Returns:
            OAuth authorization URL
        """
        scopes = [
            "https://www.googleapis.com/auth/business.manage",
        ]
        
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    
    async def exchange_code_for_tokens(
        self,
        code: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dict with tokens
        """
        import httpx
        
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new tokens
        """
        import httpx
        
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            return response.json()
    
    async def create_sync_record(
        self,
        business_account_id: int,
        location_id: int,
        google_business_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> int:
        """
        Create or update Google Business sync record.
        
        Args:
            business_account_id: Business account ID
            location_id: Location ID
            google_business_id: Google Business Profile ID
            access_token: Encrypted access token
            refresh_token: Encrypted refresh token
            expires_in: Token expiration in seconds
            
        Returns:
            Sync record ID
        """
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        sql = """
            INSERT INTO google_business_sync (
                business_account_id, location_id, google_business_id,
                access_token_encrypted, refresh_token_encrypted,
                token_expires_at, sync_status, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, 'pending', now())
            ON CONFLICT (location_id) DO UPDATE
            SET 
                google_business_id = EXCLUDED.google_business_id,
                access_token_encrypted = EXCLUDED.access_token_encrypted,
                refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                token_expires_at = EXCLUDED.token_expires_at,
                sync_status = 'pending',
                updated_at = now()
            RETURNING id
        """
        
        result = await fetch(sql, business_account_id, location_id, google_business_id, access_token, refresh_token, expires_at)
        return result[0]["id"] if result else None
    
    async def sync_location_data(
        self,
        location_id: int,
    ) -> Dict[str, Any]:
        """
        Sync location data from Google Business Profile.
        
        Args:
            location_id: Location ID to sync
            
        Returns:
            Dict with sync result
        """
        # Get sync record
        sync_sql = """
            SELECT 
                id, google_business_id, access_token_encrypted,
                refresh_token_encrypted, token_expires_at
            FROM google_business_sync
            WHERE location_id = $1
        """
        sync_rows = await fetch(sync_sql, location_id)
        
        if not sync_rows:
            raise ValueError("Sync record not found")
        
        sync = sync_rows[0]
        
        # Check if token needs refresh
        if sync["token_expires_at"] and sync["token_expires_at"] < datetime.now():
            # Refresh token
            tokens = await self.refresh_access_token(sync["refresh_token_encrypted"])
            access_token = tokens["access_token"]
            expires_in = tokens.get("expires_in", 3600)
            
            # Update sync record
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            update_sql = """
                UPDATE google_business_sync
                SET 
                    access_token_encrypted = $1,
                    token_expires_at = $2,
                    updated_at = now()
                WHERE id = $3
            """
            await execute(update_sql, access_token, expires_at, sync["id"])
        else:
            access_token = sync["access_token_encrypted"]
        
        # Fetch business data from Google My Business API
        # Note: This is a placeholder - actual API calls would go here
        # The Google My Business API has been replaced by Business Profile Performance API
        # Implementation would depend on the specific API version being used
        
        try:
            # Placeholder for actual API call
            business_data = await self._fetch_business_profile(
                google_business_id=sync["google_business_id"],
                access_token=access_token,
            )
            
            # Update location with synced data
            await self._update_location_from_google(
                location_id=location_id,
                business_data=business_data,
            )
            
            # Update sync status
            status_sql = """
                UPDATE google_business_sync
                SET 
                    sync_status = 'synced',
                    last_synced_at = now(),
                    sync_error = NULL,
                    updated_at = now()
                WHERE id = $1
            """
            await execute(status_sql, sync["id"])
            
            return {
                "success": True,
                "location_id": location_id,
                "synced_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "google_business_sync_failed",
                location_id=location_id,
                error=error_msg,
                exc_info=True,
            )
            
            # Update sync status with error
            error_sql = """
                UPDATE google_business_sync
                SET 
                    sync_status = 'error',
                    sync_error = $1,
                    updated_at = now()
                WHERE id = $2
            """
            await execute(error_sql, error_msg, sync["id"])
            
            raise
    
    async def _fetch_business_profile(
        self,
        google_business_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch business profile data from Google API.
        
        This is a placeholder - actual implementation would call
        the Google Business Profile Performance API.
        """
        # Placeholder implementation
        # In production, this would make actual API calls to Google
        return {}
    
    async def _update_location_from_google(
        self,
        location_id: int,
        business_data: Dict[str, Any],
    ) -> None:
        """
        Update location table with data from Google Business.
        
        Args:
            location_id: Location ID
            business_data: Business data from Google
        """
        # Extract relevant fields from business_data
        # This is a placeholder - actual mapping would depend on API response format
        
        update_sql = """
            UPDATE locations
            SET 
                google_business_metadata = $1::jsonb,
                updated_at = now()
            WHERE id = $2
        """
        
        await execute(update_sql, json.dumps(business_data), location_id)


# Singleton instance
_google_business_service: Optional[GoogleBusinessService] = None


def get_google_business_service() -> GoogleBusinessService:
    """Get or create GoogleBusinessService singleton."""
    global _google_business_service
    if _google_business_service is None:
        _google_business_service = GoogleBusinessService()
    return _google_business_service


