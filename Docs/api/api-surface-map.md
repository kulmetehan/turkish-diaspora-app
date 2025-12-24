---
title: API Surface Map
status: active
last_updated: 2025-01-15
scope: api, reference
owners: [tda-core]
---

# API Surface Map

Complete overview of all API routers and endpoints in the Turkish Diaspora App backend. All routers are mounted under `/api/v1` unless otherwise specified.

## Router Structure

The API is organized into domains:
- **Public API**: Core location, category, news, and event endpoints
- **Admin API**: Administrative operations requiring admin authentication
- **Community API**: User interactions, profiles, gamification, and social features
- **Business API**: Business accounts, claims, analytics, and monetization
- **Dev API**: Development and testing endpoints (local/dev only)

## Public API Routers

### Locations & Categories

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `locations_router` | `/locations` | [`Backend/api/routers/locations.py`](../../Backend/api/routers/locations.py) | Public location queries, search, filtering |
| `categories_router` | `/categories` | [`Backend/api/routers/categories.py`](../../Backend/api/routers/categories.py) | Category metadata and discoverable categories |
| `trending_router` | `/locations` | [`Backend/api/routers/trending.py`](../../Backend/api/routers/trending.py) | Trending locations by city/category |
| `trending_alt_router` | `/trending` | [`Backend/api/routers/trending.py`](../../Backend/api/routers/trending.py) | Alternative trending endpoint |

### News & Events

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `news_router` | `/news` | [`Backend/api/routers/news.py`](../../Backend/api/routers/news.py) | News feeds (diaspora, NL, TR, local, trending) |
| `events_router` | `/events` | [`Backend/api/routers/events.py`](../../Backend/api/routers/events.py) | Public events by city/category |
| `feed_router` | `/feed` | [`Backend/api/routers/feed.py`](../../Backend/api/routers/feed.py) | Curated news feed |

### Activity & Interaction

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `activity_router` | `/activity` | [`Backend/api/routers/activity.py`](../../Backend/api/routers/activity.py) | Activity stream (check-ins, reactions, notes) |
| `check_ins_router` | `/locations` | [`Backend/api/routers/check_ins.py`](../../Backend/api/routers/check_ins.py) | Location check-ins |
| `reactions_router` | `/locations` | [`Backend/api/routers/reactions.py`](../../Backend/api/routers/reactions.py) | Emoji reactions on locations |
| `notes_router` | `/locations` | [`Backend/api/routers/notes.py`](../../Backend/api/routers/notes.py) | Location notes/comments |

## Admin API Routers

All admin routers require Supabase admin authentication via `verify_admin_user` dependency.

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `admin_auth_router` | `/admin` | [`Backend/api/routers/admin_auth.py`](../../Backend/api/routers/admin_auth.py) | Admin authentication (who_am_i) |
| `admin_locations_router` | `/admin/locations` | [`Backend/api/routers/admin_locations.py`](../../Backend/api/routers/admin_locations.py) | Location management (CRUD, state transitions) |
| `admin_metrics_router` | `/admin/metrics` | [`Backend/api/routers/admin_metrics.py`](../../Backend/api/routers/admin_metrics.py) | Metrics snapshot for dashboard |
| `admin_cities_router` | `/admin/cities` | [`Backend/api/routers/admin_cities.py`](../../Backend/api/routers/admin_cities.py) | City and district configuration |
| `admin_discovery_router` | `/admin/discovery` | [`Backend/api/routers/admin_discovery.py`](../../Backend/api/routers/admin_discovery.py) | Discovery job management |
| `admin_event_sources_router` | `/admin/event-sources` | [`Backend/api/routers/admin_event_sources.py`](../../Backend/api/routers/admin_event_sources.py) | Event source configuration |
| `admin_workers_router` | `/admin/workers` | [`Backend/api/routers/admin_workers.py`](../../Backend/api/routers/admin_workers.py) | Worker orchestration and run management |
| `admin_ai_logs_router` | `/admin/ai` | [`Backend/api/routers/admin_ai_logs.py`](../../Backend/api/routers/admin_ai_logs.py) | AI operation audit logs |
| `admin_events_router` | `/admin/events` | [`Backend/api/routers/admin_events.py`](../../Backend/api/routers/admin_events.py) | Event management and moderation |
| `admin_ai_config_router` | `/admin/ai` | [`Backend/api/routers/admin_ai_config.py`](../../Backend/api/routers/admin_ai_config.py) | AI configuration (thresholds, models) |
| `admin_tasks_router` | `/admin/tasks` | [`Backend/api/routers/admin_tasks.py`](../../Backend/api/routers/admin_tasks.py) | Task queue management |
| `admin_polls_router` | `/admin/polls` | [`Backend/api/routers/admin_polls.py`](../../Backend/api/routers/admin_polls.py) | Poll creation and management |
| `admin_bulletin_router` | `/admin/bulletin` | [`Backend/api/routers/admin_bulletin.py`](../../Backend/api/routers/admin_bulletin.py) | Bulletin board management |
| `admin_misc_router` | `/admin` | [`Backend/api/routers/admin_misc.py`](../../Backend/api/routers/admin_misc.py) | Miscellaneous admin utilities |
| `claims_admin_router` | `/admin/claims` | [`Backend/api/routers/claims.py`](../../Backend/api/routers/claims.py) | Location claim moderation |

## Community API Routers

### Identity & Authentication

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `identity_router` | `/identity` | [`Backend/api/routers/identity.py`](../../Backend/api/routers/identity.py) | Client ID tracking and soft identity |
| `auth_router` | `/auth` | [`Backend/api/routers/auth.py`](../../Backend/api/routers/auth.py) | Supabase authentication helpers |

### User Profiles & Social

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `profiles_router` | `/users` | [`Backend/api/routers/profiles.py`](../../Backend/api/routers/profiles.py) | User profile management |
| `favorites_router` | `/favorites` | [`Backend/api/routers/favorites.py`](../../Backend/api/routers/favorites.py) | User favorites list |
| `location_favorites_router` | `/locations` | [`Backend/api/routers/favorites.py`](../../Backend/api/routers/favorites.py) | Location favorite operations |
| `user_groups_router` | `/groups` | [`Backend/api/routers/user_groups.py`](../../Backend/api/routers/user_groups.py) | User groups (create, join, activity) |
| `user_roles_router` | `/users` | [`Backend/api/routers/user_roles.py`](../../Backend/api/routers/user_roles.py) | User role management |

### Gamification

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `gamification_router` | `/users` | [`Backend/api/routers/gamification.py`](../../Backend/api/routers/gamification.py) | XP, streaks, badges |
| `leaderboards_router` | `/leaderboards` | [`Backend/api/routers/leaderboards.py`](../../Backend/api/routers/leaderboards.py) | Leaderboard rankings |
| `rewards_router` | `/rewards` | [`Backend/api/routers/rewards.py`](../../Backend/api/routers/rewards.py) | Rewards and achievements |
| `stats_router` | `/stats` | [`Backend/api/routers/stats.py`](../../Backend/api/routers/stats.py) | City and category statistics |

### Community Features

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `polls_router` | `/polls` | [`Backend/api/routers/polls.py`](../../Backend/api/routers/polls.py) | Poll responses and results |
| `privacy_router` | `/privacy` | [`Backend/api/routers/privacy.py`](../../Backend/api/routers/privacy.py) | Privacy settings |
| `referrals_router` | `/referrals` | [`Backend/api/routers/referrals.py`](../../Backend/api/routers/referrals.py) | Referral program |
| `push_router` | `/push` | [`Backend/api/routers/push.py`](../../Backend/api/routers/push.py) | Push notification subscriptions |
| `community_router` | `/community` | [`Backend/api/routers/community.py`](../../Backend/api/routers/community.py) | Community guidelines and moderation |
| `reports_router` | `/reports` | [`Backend/api/routers/reports.py`](../../Backend/api/routers/reports.py) | Content reporting |
| `bulletin_router` | `/bulletin` | [`Backend/api/routers/bulletin.py`](../../Backend/api/routers/bulletin.py) | Public bulletin board |

## Business API Routers

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `business_accounts_router` | `/business/accounts` | [`Backend/api/routers/business_accounts.py`](../../Backend/api/routers/business_accounts.py) | Business account management |
| `claims_router` | `/business/locations` | [`Backend/api/routers/claims.py`](../../Backend/api/routers/claims.py) | Location claiming flow |
| `business_analytics_router` | `/business/analytics` | [`Backend/api/routers/business_analytics.py`](../../Backend/api/routers/business_analytics.py) | Business analytics dashboard |
| `premium_router` | `/premium` | [`Backend/api/routers/premium.py`](../../Backend/api/routers/premium.py) | Premium subscription management |
| `promotions_router` | `/promotions` | [`Backend/api/routers/promotions.py`](../../Backend/api/routers/promotions.py) | Promoted locations and news |
| `google_business_router` | `/google-business` | [`Backend/api/routers/google_business.py`](../../Backend/api/routers/google_business.py) | Google Business Profile sync |

## Dev API Routers

These routers are mounted at the top level (not under `/api/v1`) and are only available in local/dev environments.

| Router | Prefix | File | Description |
|--------|--------|------|-------------|
| `dev_classify_router` | `/dev/ai` | [`Backend/api/routers/dev_classify.py`](../../Backend/api/routers/dev_classify.py) | AI classification testing |
| `dev_ai_router` | `/dev/ai` | [`Backend/api/routers/dev_ai.py`](../../Backend/api/routers/dev_ai.py) | AI demo endpoints (optional) |
| `admin_router` | `/admin` | [`Backend/api/routers/admin.py`](../../Backend/api/routers/admin.py) | Legacy admin endpoints (local only) |

## API Versioning

All public, admin, community, and business routers are mounted under the `/api/v1` prefix via `api_v1_router` in [`Backend/app/main.py`](../../Backend/app/main.py).

Example endpoints:
- `GET /api/v1/locations` - Public locations
- `GET /api/v1/admin/metrics/snapshot` - Admin metrics
- `POST /api/v1/business/accounts` - Business account creation
- `GET /api/v1/users/me` - User profile

## Authentication

- **Public endpoints**: No authentication required (locations, categories, news, events)
- **User endpoints**: Require Supabase JWT token (profiles, favorites, check-ins, etc.)
- **Admin endpoints**: Require Supabase admin JWT token and email in `ALLOWED_ADMIN_EMAILS`
- **Business endpoints**: Require authenticated business account
- **Dev endpoints**: Only available when `ENVIRONMENT=local|dev|development`

## Related Documentation

- [`Backend/app/main.py`](../../Backend/app/main.py) - Router mounting and API structure
- [`Docs/runbook.md`](../runbook.md) - API setup and operations
- [`Docs/env-config.md`](../env-config.md) - Environment configuration for API

