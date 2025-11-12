# Database Maintenance

This document describes the automated database maintenance workflows for the Turkish Diaspora App.

## Overview

The `public.ai_logs` table stores audit logs for all AI operations. To manage table size and performance, we run two complementary maintenance workflows:

1. **Daily Cleanup** (`tda_cleanup.yml`) - Row deletion and light optimization
2. **Weekly Compaction** (`tda_weekly_compact.yml`) - Physical table compaction

## Daily Cleanup

**Workflow**: `.github/workflows/tda_cleanup.yml`  
**Schedule**: Daily at 03:00 UTC  
**Duration**: ~20 minutes max

### What it does:
- Deletes oldest rows in batches of ~50k until `ai_logs` contains ≤100k rows
- Runs `VACUUM ANALYZE` to reclaim space and update statistics

### Characteristics:
- **Non-blocking**: `VACUUM ANALYZE` does not require an exclusive lock
- **Fast**: Typically completes in minutes
- **Safe**: Can run during business hours with minimal impact

## Weekly Compaction

**Workflow**: `.github/workflows/tda_weekly_compact.yml`  
**Schedule**: Weekly on Sunday at 03:30 UTC  
**Duration**: Up to 90 minutes

### What it does:
- Runs `VACUUM FULL` to physically compact the table and reclaim all unused space
- Runs `REINDEX TABLE` to rebuild all indexes
- Shows table sizes before and after compaction

### Characteristics:
- **Exclusive lock**: `VACUUM FULL` requires an exclusive table lock
- **Longer duration**: Can take 30-90 minutes depending on table size
- **Scheduled off-peak**: Runs Sunday 03:30 UTC to minimize impact
- **Significant space reduction**: Can reduce table size from ~695 MB to ~payload size + small overhead

### Important Notes:

1. **Locking Behavior**: `VACUUM FULL` acquires an exclusive lock on the table, blocking all reads and writes during the operation. This is why it's scheduled for Sunday 03:30 UTC (off-peak hours).

2. **Supabase UI Lag**: The Supabase dashboard may show stale size information. The actual table size is what's reported by the `pg_size_pretty()` queries in the workflow logs.

3. **Manual Trigger**: Both workflows can be manually triggered via `workflow_dispatch` for testing or emergency maintenance.

4. **Verification**: After the weekly compaction runs, check the "Show sizes after" step in the workflow logs to verify the actual space reduction achieved.

## Workflow Comparison

| Feature | Daily Cleanup | Weekly Compaction |
|---------|--------------|-------------------|
| **Purpose** | Row deletion + stats update | Physical table compaction |
| **Lock Type** | Shared lock | Exclusive lock |
| **Impact** | Minimal | Blocks all access |
| **Duration** | ~5-20 minutes | ~30-90 minutes |
| **Schedule** | Daily 03:00 UTC | Weekly Sunday 03:30 UTC |
| **Space Reduction** | Moderate (reclaims deleted rows) | Maximum (full compaction) |

## Related Files

- `.github/workflows/tda_cleanup.yml` - Daily cleanup workflow
- `.github/workflows/tda_weekly_compact.yml` - Weekly compaction workflow
- `Infra/supabase/0001_init.sql` - Table schema definition

## Session Timeout Safeguards

To prevent lingering backend sessions from blocking autovacuum or accumulating table bloat, apply a session-level timeout on the application role. This complements the application-side statement timeout configured in code.

```sql
-- Replace <app_role> with the Supabase role the backend uses (see DATABASE_URL user)
ALTER ROLE <app_role> SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE <app_role> SET lock_timeout = '5s';
```

If multiple environments share the same database, you can apply these settings at the database level instead:

```sql
ALTER DATABASE <database_name> SET idle_in_transaction_session_timeout = '60s';
ALTER DATABASE <database_name> SET lock_timeout = '5s';
```

