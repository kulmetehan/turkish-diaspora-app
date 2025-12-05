---
title: Next Steps — Implementation Guide
status: active
last_updated: 2025-01-XX
scope: planning
owners: [tda-core]
---

# Next Steps — Implementation Guide

This document provides clear, actionable next steps for continuing development. Updated after each major milestone.

## Current Status (January 2025)

### Recently Completed
- ✅ Weekly Digest Email automation (GitHub Actions workflow)
- ✅ Roadmap status synchronization (EPIC-1.5, EPIC-2.5, EPIC-3 updates)
- ✅ Engagement layer progress: 3/4 stories done (only Push Notifications remaining)

### Roadmap Status Summary
- **EPIC-1.5 (Engagement Layer)**: In Progress — 3/4 done
- **EPIC-2.5 (Community Layer)**: In Progress — 3/4 done  
- **EPIC-3 (Monetization Layer)**: In Progress — 3/8 done

## Recommended Next Steps (Priority Order)

### 1. Push Notifications Integration (EPIC-1.5 — High Priority)

**Status**: Backend API exists, needs Firebase/Expo integration

**What exists**:
- Backend API: `Backend/api/routers/push.py`
- Database tables: `push_notification_tokens`, `push_notification_preferences`
- Privacy settings integration: `allow_push_notifications` flag

**What's needed**:
1. Firebase Cloud Messaging (FCM) or Expo Push Notification setup
2. Device token registration service
3. Notification delivery service (polls, trending, activity)
4. Frontend integration for token registration
5. Admin UI for sending test notifications

**Files to review**:
- `Backend/api/routers/push.py` — existing API endpoints
- `Backend/api/routers/privacy.py` — notification preferences
- `Backend/services/` — check for existing notification service or create new one
- `Frontend/src/pages/AccountPage.tsx` — add notification settings UI

**Estimated effort**: 8 story points

**Reference implementations**:
- Similar pattern: `Backend/api/routers/business_accounts.py` (CRUD with user auth)
- Email service pattern: `Backend/services/email_service.py`

---

### 2. User Groups Feature (EPIC-2.5 — Low Priority)

**Status**: Not yet implemented

**What's needed**:
1. **Backend**:
   - Groups table (id, name, description, created_by, created_at)
   - Group members table (group_id, user_id, role, joined_at)
   - Groups API: create, list, join, leave, get members
   - Group activity streams (filter activity_stream by group_id)
   - Group permissions (admin, member, viewer roles)

2. **Frontend**:
   - Group creation UI
   - Group list/directory
   - Join/leave group flows
   - Group feed (activity filtered by group)
   - Group settings (admin only)

**Files to reference**:
- `Backend/api/routers/activity.py` — activity stream patterns
- `Backend/api/routers/favorites.py` — user association patterns
- `Backend/api/routers/community.py` — community features
- `Frontend/src/pages/FeedPage.tsx` — feed UI patterns

**Estimated effort**: 8 story points

---

### 3. Premium Features Layer (EPIC-3 — High Priority)

**Status**: Not yet implemented

**What's needed**:
1. **Payment Integration**:
   - Stripe or PayPal integration
   - Subscription management (monthly/yearly)
   - Payment webhooks for subscription events

2. **Premium Features**:
   - Extra location information (detailed hours, menu, photos)
   - Advanced statistics (views, engagement trends)
   - Enhanced visuals (custom markers, featured listings)
   - Betaalmuur implementation (paywall UI)

3. **Backend**:
   - User subscription table (user_id, plan_type, status, expires_at)
   - Premium features API (check access, unlock content)
   - Payment service integration

4. **Frontend**:
   - Subscription management page
   - Paywall UI components
   - Premium badge indicators
   - Upgrade prompts

**Files to reference**:
- `Backend/api/routers/business_accounts.py` — user account patterns
- `Backend/api/routers/claims.py` — verification/status patterns
- `Frontend/src/components/VerifiedBadge.tsx` — badge UI pattern

**Estimated effort**: 13 story points

---

### 4. Business Analytics Dashboard (EPIC-3 — High Priority)

**Status**: Not yet implemented

**What's needed**:
1. **Backend**:
   - Analytics aggregation service (views, likes, trending stats per business)
   - Business-specific metrics API
   - Engagement tracking (check-ins, reactions, notes per location)

2. **Frontend**:
   - Business owner dashboard
   - Charts/graphs (views over time, engagement breakdown)
   - Comparison tools (vs. category average, vs. city average)
   - Export functionality (CSV reports)

**Files to reference**:
- `Frontend/src/pages/DiasporaPulsePage.tsx` — analytics dashboard pattern
- `Backend/api/routers/admin_metrics.py` — metrics aggregation patterns
- `Backend/services/metrics_service.py` — metrics calculation logic
- `Frontend/src/components/admin/MetricsDashboard.tsx` — dashboard UI

**Estimated effort**: 13 story points

---

## Quick Start for Next Session

When starting a new implementation:

1. **Review existing patterns**: Check similar features in the codebase (see "Files to reference" above)
2. **Database schema**: Check `Infra/supabase/` for existing tables, create migrations if needed
3. **API design**: Follow FastAPI patterns in `Backend/api/routers/`
4. **Frontend**: Use shadcn/ui components, follow patterns in `Frontend/src/components/`
5. **Testing**: Add tests in `Backend/tests/` and `Frontend/src/__tests__/`
6. **Documentation**: Update relevant docs in `Docs/` and add to roadmap when complete

## Implementation Checklist Template

For each feature:
- [ ] Database schema/migrations (if needed)
- [ ] Backend API endpoints
- [ ] Backend service layer
- [ ] API tests
- [ ] Frontend components
- [ ] Frontend integration
- [ ] UI tests
- [ ] Documentation update
- [ ] Roadmap status update

## Questions to Answer Before Starting

1. **Push Notifications**: Firebase or Expo? (Check if mobile app exists or planned)
2. **Premium Features**: Which payment provider? (Stripe recommended for EU)
3. **User Groups**: Public or private groups? Or both?
4. **Business Analytics**: Real-time or batch aggregation?

## Related Documents

- [`PROJECT_PROGRESS.md`](../PROJECT_PROGRESS.md) — overall project status
- [`Docs/Roadmap_Backlog.md`](./Roadmap_Backlog.md) — detailed roadmap with story points
- [`Docs/runbook.md`](./runbook.md) — operational guide
- [`PROJECT_CONTEXT.md`](../PROJECT_CONTEXT.md) — architecture overview

---

**Last updated**: After Weekly Digest automation completion (January 2025)


