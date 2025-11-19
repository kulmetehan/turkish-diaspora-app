---
title: Discovery Train
status: active
last_updated: 2025-01-XX
scope: backend, automation
owners: [tda-core]
---

# Discovery Train

The Discovery Train is a sequential discovery orchestration system that processes discovery jobs one by one from a database-backed job queue, ensuring orderly execution and avoiding overload on the OSM Overpass API.

## Overview

Instead of running many discovery jobs in parallel (which can hammer OSM), the Discovery Train:

1. **Enqueues jobs** for (city, district?, category) combinations
2. **Processes jobs sequentially** via `discovery_train_bot` worker
3. **Tracks job status** in `discovery_jobs` table
4. **Respects rate limits** with delays between jobs

## Architecture

### Database: `discovery_jobs` Table

**Location**: `Infra/supabase/010_discovery_jobs.sql`

**Schema**:
- `id` (UUID) - Primary key
- `city_key` (text) - City from cities.yml
- `district_key` (text, nullable) - District from cities.yml (NULL for city-level jobs)
- `category` (text) - Category from categories.yml
- `status` (enum) - pending, running, finished, failed
- `attempts` (int) - Number of execution attempts
- `last_error` (text, nullable) - Error message if failed
- `created_at`, `started_at`, `finished_at` (timestamps)

**Indexes**:
- `idx_discovery_jobs_pending_fifo` - Efficient FIFO selection of pending jobs

### Service Layer: `discovery_jobs_service.py`

**Location**: `Backend/services/discovery_jobs_service.py`

**Functions**:
- `enqueue_jobs(city_key, categories, districts=None)` - Create jobs for combinations
- `get_next_pending_job()` - FIFO selection (oldest pending job first)
- `mark_job_running(job_id)` - Mark job as running
- `mark_job_finished(job_id, counters)` - Mark job as finished
- `mark_job_failed(job_id, error)` - Mark job as failed

### Worker: `discovery_train_bot.py`

**Location**: `Backend/app/workers/discovery_train_bot.py`

**Behavior**:
- Fetches `get_next_pending_job()` on each invocation
- If no pending jobs → exits gracefully
- Marks job as running
- Calls `run_discovery_job()` from `discovery_bot.py`
- Marks job as finished/failed
- Logs structured events (`train_job_started`, `train_job_finished`, `train_job_failed`)

**CLI**:
```bash
python -m app.workers.discovery_train_bot [--max-jobs N]
```

- Default: Process 1 job and exit (cron-friendly)
- `--max-jobs N`: Process up to N jobs sequentially

### Integration: `discovery_bot.py`

**Location**: `Backend/app/workers/discovery_bot.py`

**New Function**: `run_discovery_job(city_key, district_key, category, worker_run_id)`

- Pure function that runs discovery for a single job
- Resolves bbox/center from `cities.yml`
- Uses `categories.yml` for discovery parameters
- Returns counters dict
- Still uses `discovery_runs` and `worker_runs` for tracking

**New CLI Parameter**: `--job-id <UUID>`

- If provided, loads job from `discovery_jobs` and runs it
- Otherwise, uses existing parameterized mode (backward compatible)

## Usage

### Enqueue Jobs

**For a city (all districts, all categories)**:
```bash
python -m scripts.enqueue_discovery_jobs --city rotterdam
```

**For specific categories**:
```bash
python -m scripts.enqueue_discovery_jobs --city rotterdam --categories restaurant,bakery
```

**For specific districts**:
```bash
python -m scripts.enqueue_discovery_jobs --city rotterdam --districts centrum,noord
```

**For city-level job (no districts)**:
```bash
python -m scripts.enqueue_discovery_jobs --city vlaardingen
# (If vlaardingen has no districts, creates city-level job)
```

### Run Discovery Train

**Process 1 job (cron-friendly)**:
```bash
python -m app.workers.discovery_train_bot
```

**Process multiple jobs**:
```bash
python -m app.workers.discovery_train_bot --max-jobs 5
```

### Manual Job Execution

**Run a specific job directly**:
```bash
python -m app.workers.discovery_bot --job-id <uuid>
```

## Scheduling

### GitHub Actions (Active)

The Discovery Train is automated via `.github/workflows/discovery-train.yml`:

- **Trigger**: Cron every 30 minutes (`*/30 * * * *`) + manual dispatch
- **Command**: `python -m app.workers.discovery_train_bot --max-jobs 1`
- **Concurrency**: Single instance (prevents parallel runs)
- **Timeout**: 30 minutes

**To adjust frequency**: Edit the cron schedule in `discovery-train.yml`:
```yaml
schedule:
  - cron: "*/30 * * * *"    # Change to desired frequency
```

**To process multiple jobs per run**: Change `--max-jobs` parameter:
```yaml
run: |
  python -m app.workers.discovery_train_bot --max-jobs 3  # Process 3 jobs per run
```

### Render Cron (Alternative)

If using Render instead of GitHub Actions, add to Render cron job:
```
*/30 * * * * python -m app.workers.discovery_train_bot
```
(Runs every 30 minutes, processes 1 job per run)

### Manual Orchestration

For large backfills, run with higher `--max-jobs`:
```bash
python -m app.workers.discovery_train_bot --max-jobs 20
```

## Job Lifecycle

```
pending → running → finished
              ↓
           failed
```

1. **pending**: Job created, waiting to be processed
2. **running**: Job is currently being executed
3. **finished**: Job completed successfully
4. **failed**: Job failed with error (stored in `last_error`)

**FIFO Selection**: Jobs are processed in order of `created_at` (oldest first).

**Locking**: `get_next_pending_job()` uses `FOR UPDATE SKIP LOCKED` to prevent concurrent processing of the same job.

## Adding New Cities

To add a new city (e.g., Den Haag) to the Discovery Train:

1. **Add to `cities.yml`** with districts (see `Docs/metrics-multi-city.md`)
2. **Enqueue jobs**:
   ```bash
   python -m scripts.enqueue_discovery_jobs --city den_haag
   ```
3. **Train will automatically process** jobs for the new city when they reach the front of the queue

## Monitoring

### Job Status Queries

```sql
-- Pending jobs count
SELECT COUNT(*) FROM discovery_jobs WHERE status = 'pending';

-- Jobs by city
SELECT city_key, COUNT(*) as count, status
FROM discovery_jobs
GROUP BY city_key, status
ORDER BY city_key, status;

-- Failed jobs
SELECT id, city_key, district_key, category, last_error, attempts
FROM discovery_jobs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;
```

### Worker Run Tracking

Discovery Train worker runs are tracked in `worker_runs` table:
- `bot = 'discovery_train_bot'`
- `counters` includes: `jobs_processed`, `jobs_succeeded`, `jobs_failed`

## Error Handling

**Job Failures**:
- Job is marked as `failed` with error message
- `attempts` counter is incremented
- Failed jobs remain in queue (can be retried manually or via cleanup script)

**Circuit Breaker**:
- Discovery bot has built-in circuit breaker for Overpass errors
- If triggered, job completes in "degraded" mode (counters include `degraded: true`)
- Job is still marked as `finished` (not `failed`)

## Best Practices

1. **Enqueue jobs in batches**: Don't enqueue thousands of jobs at once
2. **Monitor queue size**: Keep pending jobs < 1000 to avoid long wait times
3. **Use appropriate --max-jobs**: For cron, use 1. For manual runs, use 5-10
4. **Respect rate limits**: Discovery Train includes 2-second delay between jobs
5. **Clean up failed jobs**: Periodically review and retry or remove failed jobs

## Troubleshooting

**No jobs being processed**:
- Check if jobs exist: `SELECT COUNT(*) FROM discovery_jobs WHERE status = 'pending'`
- Verify `discovery_train_bot` is running (check worker_runs table)
- Check for errors in worker logs

**Jobs stuck in "running"**:
- May indicate worker crashed mid-execution
- Manually reset: `UPDATE discovery_jobs SET status = 'pending' WHERE status = 'running' AND started_at < NOW() - INTERVAL '1 hour'`

**High failure rate**:
- Check `last_error` column for common error patterns
- Verify OSM Overpass API is accessible
- Check circuit breaker thresholds (may need adjustment)

