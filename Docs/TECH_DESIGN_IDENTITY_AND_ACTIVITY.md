---
title: Identity & Activity Layer - Technical Design
status: design
last_updated: 2025-01-XX
scope: backend + frontend
owners: [tda-core]
---

# Identity & Activity Layer - Technical Design

## Overview

This document defines the technical implementation for the Identity & Activity Layer (Fase 0.5 & 1), enabling user interactions (check-ins, reactions, notes, polls) with soft identity (client_id) and eventual full authentication (Supabase Auth).

## Architecture Decisions

### Identity Model
- **Soft Identity**: UUIDv4 stored in `localStorage["turkspot_client_id"]`, sent as `X-Client-Id` header
- **Full Identity**: Supabase Auth (Email/Google/Apple) with `user_id` from `auth.users`
- **Migration**: One-time job to claim `client_id` activity to `user_id` on account creation

### Activity Stream Pattern
- **Canonical tables** are source of truth: `check_ins`, `location_reactions`, `location_notes`, `favorites`, `poll_responses`
- **Denormalized table**: `activity_stream` for fast feed queries
- **Consistency**: Eventual consistency via batch worker (1-minute intervals)
- **Flag**: `processed_in_activity_stream BOOLEAN DEFAULT false` on all canonical tables

### Rate Limiting
- **Strategy**: Per `client_id`, per `user_id`, per IP (triple layer)
- **Storage**: `rate_limits` table with sliding window
- **Cleanup**: Daily job removes records older than 24h

### Trending Algorithm
- **Formula**: `score = (Wc*C + Wr*R + Wn*N) * exp(-age_hours/half_life)`
  - Wc = 3.0 (check-ins weight)
  - Wr = 1.5 (reactions weight)
  - Wn = 2.0 (notes weight)
  - half_life = 24 hours
- **Aggregation**: Batch worker every 5 minutes (near real-time), hourly (full recalculation)
- **Storage**: `trending_locations` materialized view + `trending_locations_history` for snapshots

## Database Schema

### Foundation (024)
- `user_profiles`: Extended user profiles
- `privacy_settings`: Privacy preferences
- `client_id_sessions`: Telemetry for anonymous users

### Activity Canonical Tables (025)
- `check_ins`: Check-in records
- `location_reactions`: Emoji reactions (fire, heart, thumbs_up, smile, star, flag)
- `location_notes`: User-generated notes (3-1000 chars)
- `favorites`: Bookmark records

### Activity Stream (026)
- `activity_stream`: Denormalized feed table

### Trending (027)
- `trending_locations`: Current trending scores
- `trending_locations_history`: Daily snapshots

### Gamification (028)
- `user_streaks`: XP and streak tracking
- `user_xp_log`: Audit log (optional)
- `user_badges`: Badge records

### Rate Limiting (029)
- `rate_limits`: Sliding window counters

### Polls (030)
- `polls`: Poll definitions
- `poll_options`: Poll options
- `poll_responses`: User responses
- `poll_stats`: Aggregated statistics

### Business Accounts (031)
- `business_accounts`: Business account records
- `business_members`: Team members
- `business_location_claims`: Location claiming
- `business_subscriptions`: Subscription history

## API Endpoints

### Identity
- `GET /api/v1/identity/me`: Get current identity (user_id/client_id) with gamification stats

### Check-ins
- `POST /api/v1/locations/{location_id}/check-ins`: Create check-in
- `GET /api/v1/locations/{location_id}/check-ins`: Get check-in stats
- `GET /api/v1/check-ins/nearby`: Get nearby check-ins

### Reactions
- `POST /api/v1/locations/{location_id}/reactions`: Add reaction
- `DELETE /api/v1/locations/{location_id}/reactions/{reaction_type}`: Remove reaction
- `GET /api/v1/locations/{location_id}/reactions`: Get aggregated reactions

### Notes
- `POST /api/v1/locations/{location_id}/notes`: Create note
- `GET /api/v1/locations/{location_id}/notes`: Get notes
- `PUT /api/v1/notes/{note_id}`: Update own note
- `DELETE /api/v1/notes/{note_id}`: Delete own note

### Polls
- `GET /api/v1/polls`: List active polls
- `GET /api/v1/polls/{poll_id}`: Get poll details
- `POST /api/v1/polls/{poll_id}/responses`: Submit response
- `GET /api/v1/polls/{poll_id}/stats`: Get poll statistics

### Trending
- `GET /api/v1/locations/trending`: Get trending locations
- `GET /api/v1/cities/{city_key}/trending`: Get city trending

### Activity Stream
- `GET /api/v1/activity`: Get own activity
- `GET /api/v1/activity/nearby`: Get nearby activity
- `GET /api/v1/locations/{location_id}/activity`: Get location activity

### Gamification
- `GET /api/v1/users/{user_id}/profile`: Get user profile with XP/streaks
- `GET /api/v1/users/{user_id}/badges`: Get user badges
- `GET /api/v1/leaderboards/{city_key}`: Get leaderboard

## Workers

### activity_stream_ingest_worker
- **Frequency**: Every 1 minute
- **Function**: Processes canonical tables → activity_stream
- **Batch size**: 1000 events per run
- **Processing delay**: 5 seconds (only process events older than 5s)
- **Rebuild mode**: `--rebuild` flag for full stream rebuild

### trending_worker
- **Frequency**: Every 5 minutes (near real-time), hourly (full recalculation)
- **Function**: Calculates trending scores using exponential decay
- **Windows**: 5m, 1h, 24h, 7d
- **Full recalculation**: `--full` flag for all windows

## Feature Flags

All features gated via `FEATURE_*` environment variables:
- `FEATURE_CHECK_INS`
- `FEATURE_REACTIONS`
- `FEATURE_NOTES`
- `FEATURE_POLLS`
- `FEATURE_TRENDING`
- `FEATURE_GAMIFICATION`
- `FEATURE_BUSINESS`

## Error Handling

- **Activity stream**: Retry with exponential backoff, rebuild mode for recovery
- **Rate limiting**: Graceful degradation (429 responses)
- **Trending**: Stale-while-revalidate pattern (serve last successful calculation)

## Monitoring

Key metrics tracked in `metrics_service.generate_metrics_snapshot()`:
- Engagement: check_ins_per_day, reactions_per_day, notes_per_day, poll_responses_per_day
- System: activity_stream_inserts_per_hour, unprocessed_activity_events_count
- Trending: trending_calculation_duration_ms, trending_last_success_at
- Gamification: xp_awarded_per_day, streaks_active_count

## Testing Strategy

- **Unit tests**: Trending algorithm, XP/streak logic, rate limiting helpers
- **Integration tests**: API flows (check-in → activity_stream → trending)
- **E2E tests**: Anonymous user flow, auth migration flow
- **Load tests**: 1000 concurrent users simulating check-in storms

## Rollout Plan

1. **Fase 0.5**: Foundation (identity, activity tables, basic endpoints)
2. **Fase 1**: Interaction MVP (check-ins, reactions, notes, trending)
3. **Fase 1.5**: Engagement boost (polls, push notifications)
4. **Fase 2**: Full community (auth, profiles, gamification)

























