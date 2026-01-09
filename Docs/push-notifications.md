---
title: Push Notifications Implementation
status: active
last_updated: 2025-01-XX
scope: engagement
owners: [tda-core]
---

# Push Notifications Implementation

## Overview

Push notifications enable real-time engagement with users for polls, trending locations, and activity updates. This document outlines the implementation approach and architecture decisions.

## Technology Choice

### Web Push API (Primary)
- **Decision**: Use Web Push API for web platform
- **Rationale**: 
  - Native browser support, no third-party dependencies for web
  - Works across all modern browsers
  - No vendor lock-in
  - Cost-effective (no per-notification fees)
- **Library**: `pywebpush` for Python backend
- **Service Worker**: Required on frontend for receiving notifications

### Firebase Cloud Messaging (Future)
- **Status**: Not implemented in initial version
- **Rationale**: Reserved for future mobile app (iOS/Android)
- **Note**: Backend API designed to support multiple platforms

## Architecture

### Backend Components

1. **Push Service** (`Backend/services/push_service.py`)
   - Web Push payload encryption
   - Notification delivery with retry logic
   - Error handling and logging
   - Support for multiple platforms (extensible)

2. **Push Router** (`Backend/api/routers/push.py`)
   - Device token registration (existing)
   - Preferences management (existing)
   - Internal send endpoint (new)

3. **Notification Workers**
   - Poll notifications worker
   - Trending notifications worker
   - Activity notifications worker

### Database Schema

Existing schema in `Infra/supabase/033_push_notifications.sql`:
- `device_tokens`: Stores Web Push subscriptions
- `push_notification_preferences`: User preferences per notification type
- `push_notification_log`: Audit trail for all sent notifications

### Frontend Components

1. **Service Worker** (`Frontend/public/sw.js`)
   - Receives push notifications
   - Displays notifications
   - Handles notification clicks

2. **Push Library** (`Frontend/src/lib/push.ts`)
   - Service worker registration
   - Subscription management
   - Permission handling

3. **Settings UI** (`Frontend/src/components/push/PushNotificationSettings.tsx`)
   - Toggle notification types
   - Permission request flow
   - Device management

## Notification Types

1. **Poll Notifications**
   - Trigger: New poll published
   - Default: Enabled
   - Content: Poll question and options

2. **Trending Notifications**
   - Trigger: User's favorite location becomes trending
   - Default: Disabled
   - Content: Location name and trending reason

3. **Activity Notifications**
   - Trigger: Activity on user's content (reactions, notes)
   - Default: Disabled
   - Content: Activity type and location

4. **System Notifications**
   - Trigger: Manual broadcast via script
   - Default: Enabled (if notifications enabled)
   - Content: Custom title and body
   - Deep linking: Supports custom URLs via `url` field in data payload

## Implementation Steps

1. Generate VAPID keys for Web Push
2. Implement push service with encryption
3. Create notification workers
4. Implement frontend service worker
5. Build settings UI
6. Test end-to-end delivery

## Security Considerations

- VAPID keys stored in environment variables
- Device tokens validated on registration
- User preferences enforced before sending
- Notification payloads encrypted
- Audit logging for all notifications

## Monitoring

- Track delivery success/failure rates
- Monitor notification log for errors
- Alert on high failure rates
- Track user engagement (click-through rates)

## Deep Linking

Push notifications support deep linking to specific pages within the application. When a user clicks on a notification, they are automatically navigated to the specified URL.

### Implementation

The service worker checks for a `url` field in the notification data payload with highest priority. If present, it navigates to that URL. Otherwise, it falls back to type-specific routing for backward compatibility.

### Usage

#### System Notifications

System notifications can include a custom URL in the data payload:

```bash
# Link to a specific location
python scripts/send_system_notification.py \
  --title "Nieuwe locatie" \
  --body "Bekijk deze locatie!" \
  --data '{"url": "/locations/123"}'

# Link to feed page
python scripts/send_system_notification.py \
  --title "Update" \
  --body "Bekijk de laatste updates" \
  --data '{"url": "/feed"}'

# Link to events page
python scripts/send_system_notification.py \
  --title "Evenement" \
  --body "Nieuw evenement beschikbaar" \
  --data '{"url": "/events/789"}'
```

#### URL Priority

1. **Explicit URL** (`data.url`) - Highest priority, used if present
2. **Type-specific routing** - Falls back to existing type-based routing (poll, trending, activity, chat_message)
3. **Default** - Navigates to home page (`/`) if no URL is specified

#### URL Format

- Use relative paths (e.g., `/locations/123`, `/feed`, `/events/789`)
- Hash fragments are supported (e.g., `/chat/topic/456#message-789`)
- Absolute URLs are not recommended for internal navigation

### Backward Compatibility

- Existing notification types (poll, trending, activity, chat_message) continue to work as before
- The `url` field is optional and only used when present
- Type-specific routing remains as fallback for notifications without explicit URLs

## Future Enhancements

- Rich notifications with images
- Action buttons in notifications
- Scheduled notifications
- Mobile app support (FCM/Expo)

























