---
title: Worker Orchestration
status: active
last_updated: 2025-01-XX
scope: operations
owners: [tda-core]
---

# Worker Orchestration — TDA-CC-S3

The worker orchestrator automatically starts workers in the background when triggered via the admin API (`POST /api/v1/admin/workers/run`). This document explains the orchestration flow, worker mapping, and how to extend the system.

## Overview

When an admin clicks "Run worker" in the Workers Dashboard, the backend:

1. Creates a `worker_runs` record with status `pending`
2. Queues a background task to start the actual worker
3. The orchestrator dispatches to the correct worker function
4. The worker updates `worker_runs` status/progress during execution
5. On completion or failure, the worker updates `worker_runs` to `finished` or `failed`

## Architecture

### Components

- **API Endpoint**: `Backend/api/routers/admin_workers.py`
  - `POST /api/v1/admin/workers/run` - Creates worker_runs record and queues background task

- **Orchestrator Service**: `Backend/services/worker_orchestrator.py`
  - `start_worker_run()` - Main orchestrator function
  - Maps bot names to worker functions
  - Constructs worker arguments from API request
  - Handles errors and status updates

- **Worker Runs Service**: `Backend/services/worker_runs_service.py`
  - Provides functions for updating `worker_runs` table
  - Used by both orchestrator and workers

### Flow Diagram

```
Admin UI
  ↓
POST /api/v1/admin/workers/run
  ↓
Create worker_runs record (status: pending)
  ↓
Queue background task: start_worker_run()
  ↓
Orchestrator: start_worker_run()
  ├─ Mark worker_runs as "running"
  ├─ Map bot name to worker function
  ├─ Construct worker arguments
  └─ Call worker function
      ↓
Worker execution
  ├─ Updates progress via worker_runs_service
  ├─ Updates status to "finished" on success
  └─ Updates status to "failed" on error
```

## Bot Name Mapping

The orchestrator maps API bot names to worker functions:

| API Bot Name | Worker Module | Function | Notes |
|-------------|---------------|----------|-------|
| `discovery` | `app.workers.discovery_bot` | `main_async()` | Uses sys.argv mocking |
| `classify` | `app.workers.classify_bot` | `main_async()` | Uses sys.argv mocking |
| `verify` | `app.workers.verify_locations` | `main_async()` | Uses sys.argv mocking |
| `monitor` | `app.workers.monitor_bot` | `main_async(limit, dry_run, worker_run_id)` | Direct function call |

### Worker Argument Construction

The orchestrator constructs appropriate arguments for each worker:

#### Discovery Bot
- `--city`: From API request (default: "rotterdam")
- `--categories`: From API `category` field (single category) or all categories if None
- `--worker-run-id`: UUID from worker_runs record
- `--max-total-inserts`: 0 (no limit)
- `--dry-run`: 0 (real execution)

#### Verify Locations
- `--city`: From API request
- `--limit`: 200 (default)
- `--min-confidence`: 0.8 (default)
- `--dry-run`: 0 (real execution)
- `--worker-run-id`: UUID from worker_runs record

#### Classify Bot
- `--city`: From API request
- `--limit`: 50 (default)
- `--min-confidence`: From `CLASSIFY_MIN_CONF` env var or 0.8
- `--dry-run`: Not set (False by default)
- `--worker-run-id`: UUID from worker_runs record

#### Monitor Bot
- Called directly with: `limit=None`, `dry_run=False`, `worker_run_id=run_id`

## Implementation Details

### sys.argv Mocking

Most workers parse CLI arguments internally using `argparse.parse_args()`, which reads from `sys.argv`. To maintain CLI compatibility while allowing programmatic invocation, the orchestrator:

1. Temporarily replaces `sys.argv` with mock arguments
2. Calls the worker's `main_async()` function
3. Restores original `sys.argv` after execution

This approach:
- ✅ Maintains full CLI compatibility
- ✅ Leverages existing worker initialization logic
- ✅ No changes required to worker code

### Error Handling

The orchestrator wraps worker execution in try/except:

- If worker raises an exception:
  - Logs error with full context
  - Updates `worker_runs` to `failed` status
  - Stores error message in `error_message` field
  - Sets `finished_at` timestamp

Workers also handle their own errors internally and update `worker_runs` accordingly.

### Status Transitions

`worker_runs.status` transitions:

1. **pending** → Created by API endpoint
2. **running** → Set by orchestrator or worker when execution starts
3. **finished** → Set by worker on successful completion (progress = 100)
4. **failed** → Set by orchestrator or worker on error

Progress updates (0-100) happen during worker execution via `update_worker_run_progress()`.

### Overlap Protection

The API endpoint includes a lenient overlap check:

- Before creating a new run, checks for existing runs with same `bot` and `status IN ('pending', 'running')`
- If found: Logs a warning but allows the new run to proceed
- Future enhancement: Could reject with HTTP 409 Conflict if strict mode is desired

## Adding New Workers

To add a new worker to the orchestrator:

1. **Add bot name to API**:
   - Update `BOT_CHOICES` in `Backend/api/routers/admin_workers.py`

2. **Add mapping in orchestrator**:
   - Add elif branch in `start_worker_run()` in `Backend/services/worker_orchestrator.py`
   - Create helper function `_run_<bot_name>()` that:
     - Imports the worker module
     - Constructs appropriate arguments
     - Calls worker function (with sys.argv mocking if needed)

3. **Ensure worker supports worker_run_id**:
   - Worker should accept `--worker-run-id` CLI argument
   - Worker should call `mark_worker_run_running()`, `update_worker_run_progress()`, and `finish_worker_run()` from `worker_runs_service`

4. **Update documentation**:
   - Add entry to bot name mapping table above
   - Document worker-specific argument construction

### Example: Adding a New Worker

```python
# In worker_orchestrator.py

async def start_worker_run(...):
    # ... existing code ...
    elif bot == "new_bot":
        await _run_new_bot(run_id, city, category)

async def _run_new_bot(
    run_id: UUID,
    city: Optional[str],
    category: Optional[str],
) -> None:
    """Run new_bot with constructed arguments."""
    from app.workers.new_bot import main_async
    
    argv = ["new_bot"]
    if city:
        argv.extend(["--city", city])
    argv.extend(["--worker-run-id", str(run_id)])
    # ... other args ...
    
    with mock_sys_argv(argv):
        await main_async()
```

## CLI Compatibility

**CLI usage remains fully supported and unchanged.**

Workers can still be invoked directly from the command line:

```bash
# Discovery bot
python -m app.workers.discovery_bot --city rotterdam --worker-run-id <UUID>

# Verify locations
python -m app.workers.verify_locations --limit 200 --worker-run-id <UUID>

# Classify bot
python -m app.workers.classify_bot --limit 50 --worker-run-id <UUID>

# Monitor bot
python -m app.workers.monitor_bot --worker-run-id <UUID>
```

The orchestrator's sys.argv mocking does not interfere with CLI usage because:
- Mocking only happens during programmatic invocation
- CLI calls bypass the orchestrator entirely
- Workers parse `sys.argv` normally when called from CLI

## Testing

### Manual API Test

```bash
# Start backend
cd Backend
uvicorn app.main:app --reload

# Trigger worker via API
curl -X POST http://127.0.0.1:8000/api/v1/admin/workers/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -d '{
    "bot": "discovery",
    "city": "rotterdam",
    "category": "bakery"
  }'

# Check worker_runs status
curl http://127.0.0.1:8000/api/v1/admin/workers/runs \
  -H "Authorization: Bearer <ADMIN_JWT>"
```

### Verify Status Transitions

1. Create worker run via API → status should be `pending`
2. Within seconds → status should transition to `running`
3. During execution → progress should update (0-99)
4. On completion → status should be `finished`, progress = 100
5. On error → status should be `failed`, error_message populated

### CLI Compatibility Test

```bash
# Verify CLI still works
python -m app.workers.discovery_bot --city rotterdam --worker-run-id <UUID> --dry-run
```

## Future Enhancements

- **Params dict in API**: Add `params` field to `WorkerRunRequest` for more control over worker parameters
- **Strict overlap protection**: Option to reject overlapping runs with HTTP 409
- **Worker cancellation**: Ability to cancel running workers
- **Retry logic**: Automatic retry for failed workers
- **Priority queue**: Support for prioritizing certain worker runs

## Related Documentation

- `Docs/worker-runs.md` - Worker runs table schema and usage
- `Backend/services/worker_runs_service.py` - Worker runs service functions
- `Backend/api/routers/admin_workers.py` - Admin workers API endpoints

