---
title: Feature Flags Matrix
status: active
last_updated: 2025-01-15
scope: operations, configuration
owners: [tda-core]
---

# Feature Flags Matrix

Complete mapping of feature flags to endpoints, frontend pages, database tables, and workers. Feature flags are controlled via environment variables and checked using the `require_feature()` decorator.

## Feature Flag Configuration

All feature flags are defined in [`Backend/app/core/feature_flags.py`](../../Backend/app/core/feature_flags.py) and configured via environment variables (see [`Docs/env-config.md`](../env-config.md)).

Default value: `false` (disabled). Set to `"true"` to enable.

## Feature Flags Overview

| Flag | Environment Variable | Default | Description |
|------|---------------------|---------|-------------|
| `check_ins_enabled` | `FEATURE_CHECK_INS` | `false` | Location check-in functionality |
| `polls_enabled` | `FEATURE_POLLS` | `false` | Poll creation and responses |
| `trending_enabled` | `FEATURE_TRENDING` | `false` | Trending locations algorithm |
| `gamification_enabled` | `FEATURE_GAMIFICATION` | `false` | XP, streaks, badges, leaderboards |
| `business_accounts_enabled` | `FEATURE_BUSINESS` | `false` | Business accounts and location claiming |
| `reactions_enabled` | `FEATURE_REACTIONS` | `false` | Emoji reactions on locations |
| `notes_enabled` | `FEATURE_NOTES` | `false` | Location notes/comments |

## Feature Flag Usage

### `check_ins_enabled`

**Purpose**: Controls location check-in functionality and related features.

**Backend Endpoints** (via `require_feature("check_ins_enabled")`):
- `POST /api/v1/locations/{location_id}/check-ins` - Create check-in
- `GET /api/v1/locations/{location_id}/check-ins` - List check-ins
- `DELETE /api/v1/locations/{location_id}/check-ins/{check_in_id}` - Delete check-in
- `GET /api/v1/activity` - Activity stream (includes check-ins)
- `GET /api/v1/users/{user_id}/activity` - User activity history
- `GET /api/v1/stats/city/{city_key}` - City statistics (includes check-in counts)
- `GET /api/v1/stats/category/{category_key}` - Category statistics
- `GET /api/v1/events` - Events API (check-in related)
- `GET /api/v1/news` - News API (check-in related)
- `GET /api/v1/users/{user_id}/profile` - User profile (check-in stats)
- `GET /api/v1/favorites` - Favorites (check-in related)

**Frontend Pages**:
- `FeedPage.tsx` - Activity feed with check-ins
- `UnifiedLocationDetail.tsx` - Location detail with check-in button
- `AccountPage.tsx` - User account with check-in history

**Database Tables**:
- `check_ins` - Check-in records
- `activity_stream` - Activity feed (includes check-ins)
- `trending_locations` - Trending scores (includes check-in counts)

**Workers**:
- `activity_stream_ingest_worker.py` - Processes check-ins into activity stream

**Dependencies**: When disabled, check-in related endpoints return 501 (Not Implemented).

---

### `polls_enabled`

**Purpose**: Controls poll creation, responses, and poll-related features.

**Backend Endpoints** (via `require_feature("polls_enabled")`):
- `GET /api/v1/polls` - List polls
- `POST /api/v1/polls/{poll_id}/respond` - Submit poll response
- `GET /api/v1/polls/{poll_id}/results` - Get poll results
- `GET /api/v1/polls/{poll_id}` - Get poll details

**Frontend Pages**:
- `PollDetailPage.tsx` - Poll detail and response
- `FeedPage.tsx` - Poll cards in activity feed
- `admin/AdminPollsPage.tsx` - Admin poll management

**Database Tables**:
- `polls` - Poll definitions
- `poll_responses` - User poll responses
- `activity_stream` - Activity feed (includes poll responses)

**Workers**:
- `poll_generator_bot.py` - Generates daily polls
- `activity_stream_ingest_worker.py` - Processes poll responses into activity stream

**Dependencies**: When disabled, poll endpoints return 501 (Not Implemented).

---

### `trending_enabled`

**Purpose**: Controls trending locations algorithm and trending-related features.

**Backend Endpoints** (via `require_feature("trending_enabled")`):
- `GET /api/v1/locations/trending` - Trending locations by city/category
- `GET /api/v1/trending/locations` - Alternative trending endpoint
- `GET /api/v1/locations/{location_id}/trending` - Location trending score

**Frontend Pages**:
- `FeedPage.tsx` - Trending section ("Öne Çıkanlar")
- `DiasporaPulsePage.tsx` - Trending metrics dashboard
- `BusinessAnalyticsPage.tsx` - Business analytics (trending metrics)

**Database Tables**:
- `trending_locations` - Current trending scores
- `trending_locations_history` - Historical trending snapshots

**Workers**:
- `trending_worker.py` - Calculates trending scores

**Dependencies**: When disabled, trending endpoints return 501 (Not Implemented).

---

### `gamification_enabled`

**Purpose**: Controls XP, streaks, badges, leaderboards, and rewards.

**Backend Endpoints** (via `require_feature("gamification_enabled")`):
- `GET /api/v1/users/{user_id}/xp` - User XP and level
- `GET /api/v1/users/{user_id}/streaks` - User streaks
- `GET /api/v1/users/{user_id}/badges` - User badges
- `GET /api/v1/leaderboards` - Leaderboard rankings
- `GET /api/v1/rewards` - Available rewards

**Frontend Pages**:
- `FeedPage.tsx` - Leaderboard section ("Öne Çıkanlar")
- `AccountPage.tsx` - User XP, badges, streaks
- `DiasporaPulsePage.tsx` - Leaderboard display

**Database Tables**:
- `user_xp` - XP records
- `user_streaks` - Streak calculations
- `user_badges` - Badge assignments
- `leaderboards` - Leaderboard rankings
- `rewards` - Reward definitions

**Workers**:
- `activity_stream_ingest_worker.py` - Awards XP for activities
- `trending_worker.py` - Updates leaderboard scores

**Dependencies**: When disabled, gamification endpoints return 501 (Not Implemented).

---

### `business_accounts_enabled`

**Purpose**: Controls business accounts, location claiming, and business-related features.

**Backend Endpoints** (via `require_feature("business_accounts_enabled")`):
- `POST /api/v1/business/accounts` - Create business account
- `GET /api/v1/business/accounts/me` - Get current business account
- `PUT /api/v1/business/accounts/{account_id}` - Update business account
- `POST /api/v1/business/locations/{location_id}/claim` - Claim location
- `GET /api/v1/business/locations/claims` - List location claims
- `GET /api/v1/business/analytics/overview` - Business analytics
- `GET /api/v1/business/analytics/locations/{location_id}` - Location analytics
- `GET /api/v1/premium` - Premium subscription status
- `POST /api/v1/premium/subscribe` - Create premium subscription
- `GET /api/v1/promotions/my` - Business promotions
- `POST /api/v1/promotions` - Create promotion

**Frontend Pages**:
- `BusinessAnalyticsPage.tsx` - Business analytics dashboard
- `BusinessPromotionsPage.tsx` - Promotion management
- `PremiumPage.tsx` - Premium subscription management
- `admin/LocationsPage.tsx` - Location claiming (admin view)

**Database Tables**:
- `business_accounts` - Business account records
- `location_claims` - Location claim requests
- `premium_features` - Premium feature flags per account
- `payment_transactions` - Payment history
- `promoted_locations` - Promoted location records
- `promoted_news` - Promoted news records

**Workers**:
- `google_business_sync.py` - Syncs Google Business Profile data
- `promotion_expiry_worker.py` - Expires promotions

**Dependencies**: When disabled, business endpoints return 501 (Not Implemented).

---

### `reactions_enabled`

**Purpose**: Controls emoji reactions on locations.

**Backend Endpoints** (via `require_feature("reactions_enabled")`):
- `POST /api/v1/locations/{location_id}/reactions` - Add/remove reaction
- `GET /api/v1/locations/{location_id}/reactions` - List reactions

**Frontend Pages**:
- `UnifiedLocationDetail.tsx` - Location detail with reaction buttons
- `FeedPage.tsx` - Activity cards with reactions

**Database Tables**:
- `location_reactions` - Reaction records
- `activity_stream` - Activity feed (includes reactions)

**Workers**:
- `activity_stream_ingest_worker.py` - Processes reactions into activity stream

**Dependencies**: When disabled, reaction endpoints return 501 (Not Implemented).

---

### `notes_enabled`

**Purpose**: Controls location notes/comments functionality.

**Backend Endpoints** (via `require_feature("notes_enabled")`):
- `POST /api/v1/locations/{location_id}/notes` - Create note
- `GET /api/v1/locations/{location_id}/notes` - List notes
- `PUT /api/v1/locations/{location_id}/notes/{note_id}` - Update note
- `DELETE /api/v1/locations/{location_id}/notes/{note_id}` - Delete note

**Frontend Pages**:
- `UnifiedLocationDetail.tsx` - Location detail with notes section
- `FeedPage.tsx` - Activity cards with notes

**Database Tables**:
- `location_notes` - Note records
- `activity_stream` - Activity feed (includes notes)

**Workers**:
- `activity_stream_ingest_worker.py` - Processes notes into activity stream

**Dependencies**: When disabled, note endpoints return 501 (Not Implemented).

---

## Implementation Details

### How Feature Flags Work

1. **Environment Variable**: Set `FEATURE_*` environment variable to `"true"` or `"false"` (default: `false`)
2. **Flag Definition**: Flags are loaded in `Backend/app/core/feature_flags.py` on application startup
3. **Endpoint Protection**: Use `require_feature("flag_name")` decorator in router endpoints
4. **Error Response**: When disabled, endpoints return HTTP 501 (Not Implemented) with message: `"Feature 'flag_name' is not enabled"`

### Example Usage

```python
from app.core.feature_flags import require_feature

@router.post("/locations/{location_id}/check-ins")
async def create_check_in(
    location_id: int,
    user: User = Depends(get_current_user)
):
    require_feature("check_ins_enabled")
    # ... endpoint logic
```

### Frontend Handling

Frontend should handle 501 responses gracefully:
- Hide feature UI when endpoint returns 501
- Show "Feature not available" message
- Disable feature-related navigation items

## Configuration

See [`Docs/env-config.md`](../env-config.md) for complete environment variable documentation.

All feature flags are defined in:
- `.env.template` - Template with default values
- `Backend/app/core/feature_flags.py` - Flag definitions and `require_feature()` function

## Related Documentation

- [`Backend/app/core/feature_flags.py`](../../Backend/app/core/feature_flags.py) - Feature flag implementation
- [`Docs/env-config.md`](../env-config.md) - Environment variable configuration
- [`Docs/api/api-surface-map.md`](../api/api-surface-map.md) - Complete API endpoint reference

