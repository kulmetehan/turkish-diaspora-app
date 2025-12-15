# Remaining Work Summary

## ✅ Completed in This Session

### 1. User-Facing Polls UI (Story - Polls Frontend)
- ✅ Poll API functions added to `Frontend/src/lib/api.ts`
- ✅ `PollCard` component with voting and stats display
- ✅ `PollsFeed` component for listing polls
- ✅ Integrated into FeedPage as a third tab

**Files Created:**
- `Frontend/src/components/polls/PollCard.tsx`
- `Frontend/src/components/polls/PollsFeed.tsx`

**Files Modified:**
- `Frontend/src/lib/api.ts` (added poll API functions)
- `Frontend/src/pages/FeedPage.tsx` (added polls tab)

## 🚧 In Progress / Next Steps

### 2. Verified Badge System (EPIC-3, Story 46)
**Status:** Backend schema exists (`business_location_claims` table), needs API + UI

**What needs to be done:**

1. **Backend API Update** (`Backend/api/routers/locations.py`):
   - Add LEFT JOIN with `business_location_claims` table
   - Include `claim_status` in SELECT (NULL if no claim, or 'pending'/'approved'/'rejected'/'revoked')
   - Return `has_verified_badge: bool` (true if status = 'approved')

2. **Frontend Types** (`Frontend/src/api/fetchLocations.ts`):
   - Add `has_verified_badge?: boolean` to `LocationMarker` interface

3. **Verified Badge Component** (`Frontend/src/components/VerifiedBadge.tsx`):
   - Simple badge component showing checkmark icon
   - Used in LocationCard and LocationDetail

4. **UI Integration**:
   - Add badge to `LocationCard.tsx` next to location name
   - Add badge to `LocationDetail.tsx` in header
   - Add badge to `TrendingLocationCard.tsx`

**Estimated effort:** 2-3 hours

---

### 3. Reporting System (EPIC-2.5, Story 40)
**Status:** Not started - needs full implementation

**What needs to be done:**

1. **Database Schema** (create new migration):
   - `reports` table: `id`, `reported_by_user_id`, `reported_by_client_id`, `report_type` ('location', 'note', 'reaction', 'user'), `target_id`, `reason`, `status` ('pending', 'resolved', 'dismissed'), `created_at`

2. **Backend API** (`Backend/api/routers/reports.py`):
   - `POST /api/v1/reports` - Submit report
   - `GET /api/v1/admin/reports` - List reports (admin only)
   - `PUT /api/v1/admin/reports/{id}` - Update report status

3. **Frontend UI**:
   - Report button/icon on location cards, notes, reactions
   - Report dialog with reason selection
   - Admin reports page

**Estimated effort:** 5-8 hours

---

### 4. Community Guidelines (EPIC-2.5, Story 41)
**Status:** Not started - simple but important

**What needs to be done:**

1. **Backend**:
   - Simple content table or config file
   - API endpoint: `GET /api/v1/community/guidelines`

2. **Frontend**:
   - Guidelines page component
   - Link in footer and account page
   - Modal popup on first use (optional)

**Estimated effort:** 2-3 hours

---

### 5. Business Accounts API (EPIC-3, Story 44)
**Status:** Database schema exists, needs full API implementation

**What needs to be done:**

1. **Backend API** (`Backend/api/routers/business_accounts.py`):
   - `POST /api/v1/business/accounts` - Create business account
   - `GET /api/v1/business/accounts/me` - Get own business account
   - `PUT /api/v1/business/accounts/{id}` - Update business account
   - `GET /api/v1/business/accounts/{id}/members` - List members
   - `POST /api/v1/business/accounts/{id}/members` - Add member

2. **Frontend UI**:
   - Business account creation/management page
   - Team member management

**Estimated effort:** 8-10 hours

---

### 6. Location Claiming Flow (EPIC-3, Story 45)
**Status:** Database schema exists, needs full implementation

**What needs to be done:**

1. **Backend API** (`Backend/api/routers/claims.py`):
   - `POST /api/v1/business/locations/{location_id}/claim` - Submit claim request
   - `GET /api/v1/business/claims` - List own claims
   - Admin endpoints for approval/rejection

2. **Verification Flow**:
   - Business submits claim with verification documents
   - Admin reviews and approves/rejects
   - On approval, `business_location_claims.status` = 'approved'

3. **Frontend UI**:
   - Claim button on location detail page
   - Claim submission form
   - Claim status dashboard for businesses

**Estimated effort:** 10-12 hours

---

### 7. Moderation Tools (EPIC-2.5, Story 39)
**Status:** Not started - depends on Reporting System

**What needs to be done:**

1. **Admin UI** (`Frontend/src/pages/admin/ModerationPage.tsx`):
   - Reports list with filters
   - Actions: approve, dismiss, escalate
   - User suspension/ban tools
   - Content moderation actions

2. **Backend Support**:
   - User suspension/ban endpoints
   - Content removal endpoints
   - Moderation actions logging

**Estimated effort:** 6-8 hours

---

## 📊 Implementation Priority Order

Based on value and dependencies:

1. ✅ **Polls UI** (completed)
2. **Verified Badge System** (2-3h) - Quick win, high visibility
3. **Community Guidelines** (2-3h) - Simple, legal requirement
4. **Reporting System** (5-8h) - Important for community safety
5. **Moderation Tools** (6-8h) - Depends on #4
6. **Business Accounts API** (8-10h) - Foundation for monetization
7. **Location Claiming Flow** (10-12h) - Depends on #6

## 🔗 Dependencies

- **Moderation Tools** → Requires **Reporting System**
- **Location Claiming** → Requires **Business Accounts API**
- **Verified Badge** → Works independently (schema already exists)

## 📝 Notes

- All database schemas for EPIC-3 features already exist (031_business_accounts.sql)
- Most features can be implemented incrementally
- Focus on verified badge next for quick win













