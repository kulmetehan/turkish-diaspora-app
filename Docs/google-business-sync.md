---
title: Google Business Sync
status: active
last_updated: 2025-01-XX
scope: integration
owners: [tda-core]
---

# Google Business Sync

## Overview

Google Business Sync allows businesses to connect their Google My Business account and automatically sync business information to their claimed locations in the Turkish Diaspora App.

## API Choice

### Google My Business API (Recommended)
- **Decision**: Use Google My Business API (now part of Business Profile Performance API)
- **Rationale**:
  - Official API for business profile management
  - Access to verified business information
  - Real-time sync capabilities
  - Better data quality than Places API

### Alternative: Places API (New)
- **Status**: Considered but not primary
- **Note**: Places API (New) provides business information but requires different authentication

## OAuth Flow

### 1. Business Opt-In
- Business account owner initiates connection
- Redirects to Google OAuth consent screen
- Requests scopes:
  - `https://www.googleapis.com/auth/business.manage`
  - Read business profile information

### 2. Authorization
- User grants permissions
- Google redirects to callback URL with authorization code
- Backend exchanges code for access token and refresh token
- Stores tokens securely (encrypted)

### 3. Sync Process
- Periodic sync (daily or on-demand)
- Fetches business information from Google
- Maps to locations table
- Updates location data (name, address, hours, photos, etc.)

## Data Mapping

### Google Business → Locations Table

| Google Business Field | Locations Table Field | Notes |
| --- | --- | --- |
| `name` | `name` | Direct mapping |
| `formattedAddress` | `address` | Direct mapping |
| `location.lat` | `lat` | Direct mapping |
| `location.lng` | `lng` | Direct mapping |
| `openingHours` | `google_business_metadata.opening_hours` | JSONB storage |
| `photos` | `google_business_metadata.photos` | JSONB array |
| `phoneNumber` | `google_business_metadata.phone` | JSONB storage |
| `website` | `google_business_metadata.website` | JSONB storage |
| `rating` | `rating` | Direct mapping |
| `userRatingCount` | `user_ratings_total` | Direct mapping |

## Database Schema

### New Tables

1. **google_business_sync**
   - `id`: Primary key
   - `business_account_id`: Foreign key to business_accounts
   - `location_id`: Foreign key to locations
   - `google_business_id`: Google Business Profile ID
   - `access_token`: Encrypted access token
   - `refresh_token`: Encrypted refresh token
   - `token_expires_at`: Token expiration
   - `sync_status`: 'pending', 'synced', 'error'
   - `last_synced_at`: Last successful sync
   - `sync_error`: Error message if sync failed
   - `created_at`, `updated_at`: Timestamps

2. **locations** table updates
   - `google_business_id`: Optional Google Business Profile ID
   - `google_business_metadata`: JSONB column for additional data

## API Endpoints

### `POST /google-business/connect`
Initiates OAuth flow:
- Generates OAuth URL
- Stores state for CSRF protection
- Returns redirect URL

### `GET /google-business/callback`
OAuth callback handler:
- Validates state
- Exchanges code for tokens
- Creates google_business_sync record
- Triggers initial sync

### `POST /google-business/sync/{location_id}`
Manual sync trigger:
- Triggers immediate sync for location
- Returns sync status

### `GET /google-business/status`
Returns sync status for all locations:
```json
{
  "locations": [
    {
      "location_id": 123,
      "sync_status": "synced",
      "last_synced_at": "2025-01-15T10:00:00Z",
      "google_business_id": "abc123"
    }
  ]
}
```

## Worker Implementation

### google_business_sync.py
- Periodic sync job (daily cron)
- Fetches all active sync records
- Refreshes access tokens if needed
- Fetches business data from Google
- Updates locations table
- Logs sync results

## Rate Limiting

- Google My Business API has rate limits
- Implement exponential backoff
- Queue sync requests if rate limited
- Monitor API usage

## Error Handling

- Token expiration: Automatic refresh
- API errors: Log and retry with backoff
- Invalid business ID: Mark as error, notify user
- Network errors: Retry with exponential backoff

## Security

- Encrypt access tokens and refresh tokens
- Secure token storage (environment variables for encryption key)
- HTTPS only for OAuth callbacks
- State parameter for CSRF protection
- Token rotation support

## Privacy & Permissions

- User must explicitly opt-in
- Clear explanation of data access
- Ability to disconnect at any time
- Data deletion on disconnect

## Future Enhancements

- Two-way sync (update Google from TDA)
- Bulk sync for multiple locations
- Sync scheduling (custom intervals)
- Conflict resolution UI
- Sync history and audit log














