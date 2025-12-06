---
title: User Groups Feature
status: active
last_updated: 2025-01-XX
scope: community
owners: [tda-core]
---

# User Groups Feature

## Overview

User Groups enable community members to create and join groups around shared interests, locations, or activities. Groups have their own activity feeds and member management.

## Use Cases

1. **Location-Based Groups**
   - Groups for specific neighborhoods or cities
   - Turkish community groups by region

2. **Interest-Based Groups**
   - Food enthusiasts
   - Business owners network
   - Cultural events

3. **Activity Groups**
   - Check-in challenges
   - Location discovery teams

## Database Schema

### user_groups Table
```sql
CREATE TABLE user_groups (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    is_public BOOLEAN DEFAULT true,
    member_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### user_group_members Table
```sql
CREATE TABLE user_group_members (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member', -- 'owner', 'admin', 'member'
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(group_id, user_id)
);
```

### Activity Stream Integration

Groups don't have a separate activity table. Instead, we filter `activity_stream` by group membership:
- Users in the same group see each other's activity
- Group activity feed shows activity from all members
- Filter by `actor_id` in group members list

## API Endpoints

### `POST /groups`
Create a new group:
```json
{
  "name": "Rotterdam Turkish Foodies",
  "description": "Discovering Turkish restaurants in Rotterdam",
  "is_public": true
}
```

### `GET /groups`
List groups with filters:
- Query params: `search`, `city`, `category`, `is_public`
- Returns paginated list

### `GET /groups/{group_id}`
Get group details:
```json
{
  "id": 1,
  "name": "Rotterdam Turkish Foodies",
  "description": "...",
  "member_count": 25,
  "created_by": "user-uuid",
  "is_public": true,
  "created_at": "2025-01-01T00:00:00Z"
}
```

### `POST /groups/{group_id}/join`
Join a group:
- Public groups: Auto-join
- Private groups: Requires approval (future)

### `DELETE /groups/{group_id}/leave`
Leave a group:
- Cannot leave if you're the owner (transfer ownership first)

### `GET /groups/{group_id}/members`
List group members:
- Paginated
- Shows role and join date

### `GET /groups/{group_id}/activity`
Get group activity feed:
- Filters activity_stream by group members
- Returns recent activity from all members
- Paginated

## Frontend Components

### GroupsPage
- Groups list/grid view
- Search and filter
- Create group button
- Group cards with preview

### GroupDetailPage
- Group information
- Member list
- Activity feed
- Join/leave actions
- Settings (for owners/admins)

### GroupCard
- Group name and description
- Member count
- Join button
- Preview of recent activity

## Activity Feed Logic

### Group Activity Query
```sql
SELECT * FROM activity_stream
WHERE actor_id IN (
    SELECT user_id FROM user_group_members
    WHERE group_id = $1
)
ORDER BY created_at DESC
LIMIT 50;
```

### Performance Considerations
- Index on `activity_stream(actor_id, created_at)`
- Consider materialized view for large groups
- Pagination for activity feeds
- Cache member lists for frequently accessed groups

## Permissions

### Group Owner
- Edit group details
- Delete group
- Manage members (add/remove)
- Assign admin roles

### Group Admin
- Edit group details
- Manage members (add/remove)
- Cannot delete group

### Group Member
- View group
- Post activity (normal user activity)
- Leave group

## Privacy

- Public groups: Visible to all, anyone can join
- Private groups: Invite-only (future feature)
- Group activity: Only visible to members
- Member list: Visible to all (or members only - configurable)

## Moderation

- Group owners can remove members
- Report group functionality (uses existing reporting system)
- Admin tools for group moderation (future)

## Future Enhancements

- Private groups with invitations
- Group events
- Group discussions/chat
- Group achievements/badges
- Group analytics
- Group recommendations



