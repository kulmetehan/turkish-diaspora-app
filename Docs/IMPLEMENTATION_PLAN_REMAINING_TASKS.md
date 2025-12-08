# Implementation Plan - Remaining 5 Tasks

## Overview
This document outlines the implementation plan for the 5 remaining tasks from the roadmap backlog.

## Implementation Order (based on dependencies)

1. **Community Guidelines** (2-3h) - Independent, simple
2. **Reporting System** (5-8h) - Required for Moderation Tools
3. **Moderation Tools** (6-8h) - Depends on Reporting System
4. **Business Accounts API** (8-10h) - Required for Location Claiming
5. **Location Claiming Flow** (10-12h) - Depends on Business Accounts API

---

## Task 1: Community Guidelines (EPIC-2.5, Story 41)

### Backend Implementation

**File:** `Backend/api/routers/community.py` (new)

**Endpoint:**
- `GET /api/v1/community/guidelines` - Returns community guidelines content

**Implementation approach:**
- Simple static content (can be moved to database later if needed)
- Returns JSON with title, content (HTML), last_updated date
- Similar pattern to other content endpoints

**Files to create:**
- `Backend/api/routers/community.py`

**Files to modify:**
- `Backend/app/main.py` - Add router registration

### Frontend Implementation

**Files to create:**
- `Frontend/src/pages/CommunityGuidelinesPage.tsx` - Guidelines page component (similar to TermsOfServicePage)

**Files to modify:**
- `Frontend/src/main.tsx` - Add route for `/guidelines`
- `Frontend/src/pages/AccountPage.tsx` - Add link to guidelines in Legal section

---

## Task 2: Reporting System (EPIC-2.5, Story 40)

### Database Schema

**File:** `Infra/supabase/034_reports.sql` (new migration)

**Table:** `reports`
- `id` BIGSERIAL PRIMARY KEY
- `reported_by_user_id` UUID REFERENCES auth.users(id) ON DELETE SET NULL (optional, for authenticated users)
- `reported_by_client_id` TEXT (required, for anonymous users)
- `report_type` TEXT NOT NULL ('location', 'note', 'reaction', 'user')
- `target_id` BIGINT NOT NULL (ID of the reported item)
- `reason` TEXT NOT NULL (report reason/category)
- `details` TEXT (optional additional details)
- `status` TEXT NOT NULL DEFAULT 'pending' ('pending', 'resolved', 'dismissed')
- `resolved_by` UUID REFERENCES auth.users(id) ON DELETE SET NULL (admin who resolved)
- `resolved_at` TIMESTAMPTZ
- `created_at` TIMESTAMPTZ NOT NULL DEFAULT now()
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT now()

**Indexes:**
- `idx_reports_status` on `status`
- `idx_reports_type_target` on `(report_type, target_id)`
- `idx_reports_created` on `created_at DESC`

### Backend Implementation

**File:** `Backend/api/routers/reports.py` (new)

**Endpoints:**
- `POST /api/v1/reports` - Submit a report (public, requires client_id or user_id)
- `GET /api/v1/admin/reports` - List all reports (admin only, with filters)
- `PUT /api/v1/admin/reports/{id}` - Update report status (admin only)

**Files to create:**
- `Backend/api/routers/reports.py`

**Files to modify:**
- `Backend/app/main.py` - Add router registration

### Frontend Implementation

**Files to create:**
- `Frontend/src/components/report/ReportDialog.tsx` - Report dialog component
- `Frontend/src/components/report/ReportButton.tsx` - Report button/icon component
- `Frontend/src/pages/admin/AdminReportsPage.tsx` - Admin reports management page

**Files to modify:**
- `Frontend/src/lib/api.ts` - Add report API functions
- `Frontend/src/components/LocationCard.tsx` - Add report button
- `Frontend/src/components/LocationDetail.tsx` - Add report button
- `Frontend/src/components/feed/ActivityCard.tsx` - Add report button for notes/reactions
- `Frontend/src/main.tsx` - Add route for admin reports
- `Frontend/src/lib/admin/navigation.ts` - Add reports to admin navigation

---

## Task 3: Moderation Tools (EPIC-2.5, Story 39)

### Backend Implementation

**File:** `Backend/api/routers/moderation.py` (new)

**Endpoints:**
- `PUT /api/v1/admin/users/{user_id}/suspend` - Suspend user (admin only)
- `PUT /api/v1/admin/users/{user_id}/ban` - Ban user permanently (admin only)
- `PUT /api/v1/admin/users/{user_id}/unsuspend` - Unsuspend user (admin only)
- `DELETE /api/v1/admin/content/{type}/{id}` - Remove content (notes, reactions, etc.) (admin only)
- `POST /api/v1/admin/moderation/actions` - Log moderation action

**Optional: Moderation actions log table:**
- `moderation_actions` table for audit trail

**Files to create:**
- `Backend/api/routers/moderation.py`

**Files to modify:**
- `Backend/app/main.py` - Add router registration

### Frontend Implementation

**Files to create:**
- `Frontend/src/pages/admin/ModerationPage.tsx` - Main moderation dashboard
- `Frontend/src/components/moderation/ReportsList.tsx` - Reports list component with filters
- `Frontend/src/components/moderation/UserActions.tsx` - User suspension/ban tools

**Files to modify:**
- `Frontend/src/lib/api.ts` - Add moderation API functions
- `Frontend/src/main.tsx` - Add route for moderation page
- `Frontend/src/lib/admin/navigation.ts` - Add moderation to admin navigation

---

## Task 4: Business Accounts API (EPIC-3, Story 44)

### Database Schema

**Status:** Already exists in `Infra/supabase/031_business_accounts.sql`

### Backend Implementation

**File:** `Backend/api/routers/business_accounts.py` (new)

**Endpoints:**
- `POST /api/v1/business/accounts` - Create business account (requires authenticated user)
- `GET /api/v1/business/accounts/me` - Get own business account(s) (authenticated user)
- `GET /api/v1/business/accounts/{id}` - Get business account by ID (public, limited fields)
- `PUT /api/v1/business/accounts/{id}` - Update business account (owner/admin only)
- `GET /api/v1/business/accounts/{id}/members` - List members (owner/admin only)
- `POST /api/v1/business/accounts/{id}/members` - Add member (owner/admin only)
- `DELETE /api/v1/business/accounts/{id}/members/{user_id}` - Remove member (owner/admin only)

**Files to create:**
- `Backend/api/routers/business_accounts.py`

**Files to modify:**
- `Backend/app/main.py` - Add router registration

### Frontend Implementation

**Files to create:**
- `Frontend/src/pages/business/BusinessAccountPage.tsx` - Business account management
- `Frontend/src/components/business/BusinessAccountForm.tsx` - Create/edit form
- `Frontend/src/components/business/TeamMembersList.tsx` - Member management

**Files to modify:**
- `Frontend/src/lib/api.ts` - Add business accounts API functions
- `Frontend/src/main.tsx` - Add route for business account page
- `Frontend/src/pages/AccountPage.tsx` - Add link/button to create/view business account

---

## Task 5: Location Claiming Flow (EPIC-3, Story 45)

### Database Schema

**Status:** Already exists in `Infra/supabase/031_business_accounts.sql` (business_location_claims table)

### Backend Implementation

**File:** `Backend/api/routers/claims.py` (new)

**Endpoints:**
- `POST /api/v1/business/locations/{location_id}/claim` - Submit claim request (requires business account)
- `GET /api/v1/business/claims` - List own claims (authenticated business user)
- `GET /api/v1/business/claims/{id}` - Get claim details (owner/admin only)
- `PUT /api/v1/admin/claims/{id}/approve` - Approve claim (admin only)
- `PUT /api/v1/admin/claims/{id}/reject` - Reject claim (admin only)
- `PUT /api/v1/admin/claims/{id}/revoke` - Revoke approved claim (admin only)

**Files to create:**
- `Backend/api/routers/claims.py`

**Files to modify:**
- `Backend/app/main.py` - Add router registration

### Frontend Implementation

**Files to create:**
- `Frontend/src/components/claims/ClaimLocationDialog.tsx` - Claim submission form
- `Frontend/src/components/claims/ClaimStatusBadge.tsx` - Claim status indicator
- `Frontend/src/pages/business/BusinessClaimsPage.tsx` - Claims dashboard for businesses

**Files to modify:**
- `Frontend/src/lib/api.ts` - Add claims API functions
- `Frontend/src/components/LocationDetail.tsx` - Add claim button (if user has business account)
- `Frontend/src/main.tsx` - Add route for claims page
- `Frontend/src/pages/business/BusinessAccountPage.tsx` - Add link to claims dashboard

---

## Estimated Total Time

- Community Guidelines: 2-3 hours
- Reporting System: 5-8 hours
- Moderation Tools: 6-8 hours
- Business Accounts API: 8-10 hours
- Location Claiming Flow: 10-12 hours

**Total: 31-41 hours**






