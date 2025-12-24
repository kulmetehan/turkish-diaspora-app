---
title: Database Schema Reconciliation
status: active
last_updated: 2025-01-15
scope: database, migrations
owners: [tda-core]
---

# Database Schema Reconciliation

This document explains the database schema conflicts in the migration files and clarifies which migrations are authoritative for production use.

## Critical Schema Conflict

### The Problem

Two conflicting schema definitions exist in `Infra/supabase/`:

1. **`0001_init.sql`** (Authoritative)
   - Defines `locations.id` as `bigserial` (BIGINT)
   - Defines `ai_logs.location_id` as `bigint`
   - Defines `tasks.location_id` as `bigint`
   - Defines `training_data.location_id` as `bigint`

2. **`001_tables.sql`** (Legacy/Conflict)
   - Defines `locations.id` as `uuid` (using `gen_random_uuid()`)
   - Defines `ai_logs.location_id` as `uuid`
   - Defines `tasks.id` as `uuid` (vs `bigserial` in `0001_init.sql`)
   - Different schema structure overall

### Evidence of Authoritative Schema

All later migrations consistently reference `BIGINT` for `location_id`:

- `027_trending_tables.sql`: `location_id BIGINT NOT NULL REFERENCES public.locations(id)`
- `025_activity_canonical_tables.sql`: Multiple `location_id BIGINT` references
- `031_business_accounts.sql`: `location_id BIGINT NOT NULL REFERENCES public.locations(id)`
- `035_business_analytics.sql`: `location_id BIGINT REFERENCES public.locations(id)`
- `037_google_business_sync.sql`: `location_id BIGINT NOT NULL REFERENCES public.locations(id)`
- `039_promoted_locations.sql`: `location_id BIGINT NOT NULL REFERENCES public.locations(id)`
- `042_bulletin_board.sql`: `linked_location_id BIGINT REFERENCES public.locations(id)`

Additionally, the API code in `Backend/api/routers/locations.py` and `Backend/services/db_service.py` expects `location_id: int`, confirming the BIGINT schema.

## Authoritative Migration Set

### Production Schema (BIGINT-based)

**Base Migration**: `0001_init.sql`
- `locations.id`: `bigserial` (BIGINT auto-increment)
- `ai_logs.location_id`: `bigint`
- `tasks.location_id`: `bigint`
- `training_data.location_id`: `bigint`

**Subsequent Migrations** (all compatible with BIGINT schema):
- `002_constraints.sql` through `074_remove_location_reactions_constraint.sql`
- All later migrations assume `locations.id` is BIGINT

### Legacy/Conflict Migration

**`001_tables.sql`** should be considered **legacy/conflict**:
- Uses UUID-based schema
- Incompatible with production schema
- Not referenced by any later migrations
- Likely an early prototype or alternative schema that was never used in production

## Migration Order

The correct migration order for production is:

1. `0001_init.sql` - Base schema with BIGINT IDs
2. `002_constraints.sql` - Constraints
3. `003_indexes.sql` - Indexes
4. `004_fk_indexes.sql` - Foreign key indexes
5. All subsequent numbered migrations (005-074)

**Do NOT apply `001_tables.sql` in production** - it conflicts with the authoritative schema.

## Verification

To verify which schema is in use in your database:

```sql
-- Check locations table ID type
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'locations' 
  AND column_name = 'id';

-- Should return: data_type = 'bigint', column_default like 'nextval(...)'
```

If you see `uuid` as the data type, the wrong schema was applied.

## Recommendations

1. **For New Setups**: Only apply `0001_init.sql` and subsequent migrations (002-074). Skip `001_tables.sql`.

2. **For Existing Databases**: Verify the schema matches `0001_init.sql`. If `locations.id` is UUID, a migration script is needed to convert to BIGINT (this is a breaking change and requires careful planning).

3. **For Documentation**: Always reference `0001_init.sql` as the authoritative base schema. Document `001_tables.sql` as legacy/conflict.

## Related Documentation

- [`Docs/runbook.md`](../runbook.md) - Database setup procedures
- [`Infra/supabase/0001_init.sql`](../../Infra/supabase/0001_init.sql) - Authoritative base schema
- [`Backend/services/db_service.py`](../../Backend/services/db_service.py) - Database service layer (expects BIGINT)

