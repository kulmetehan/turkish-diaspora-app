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

## Future Enhancements

- Rich notifications with images
- Action buttons in notifications
- Scheduled notifications
- Mobile app support (FCM/Expo)








