# Discovery Workflow Documentation

## Overview

The TDA Discovery workflow runs weekly discovery jobs to discover Turkish diaspora locations using OSM (OpenStreetMap) data. The workflow is designed to handle long-running discovery tasks across multiple categories and chunks.

## Runtime Expectations

The discovery workflow processes **48 chunks total**:
- **8 categories**: bakery, restaurant, supermarket, barber, mosque, travel_agency, butcher, fast_food
- **6 chunks per category**: numbered 0-5 (chunk_index)
- **Per-chunk timeout**: 45 minutes
- **Total expected runtime**: ~36 hours (48 chunks × 45 minutes each)

The workflow runs sequentially (max-parallel: 1) to respect rate limits and avoid overwhelming the OSM Overpass API.

## Schedule

- **Frequency**: Runs every 2 hours (cron: `0 */2 * * *`)
- **Manual trigger**: Available via `workflow_dispatch`

## Concurrency & Queueing

The workflow uses a concurrency group `tda-discovery` with `cancel-in-progress: false` to prevent self-cancellation:

- **Concurrency group**: `tda-discovery`
- **Cancel behavior**: `cancel-in-progress: false` - new runs will **queue** instead of canceling active runs
- **Guard job**: A `check-active` job runs before the discovery matrix to check for active runs:
  - If another run is `in_progress`, the current run exits successfully (exit code 0) without starting matrix jobs
  - If no active run is found, the discovery job proceeds

This ensures that:
1. Long-running discovery jobs complete successfully
2. New runs wait for active runs to finish (queued behavior)
3. No duplicate runs execute simultaneously

## Workflow Structure

### Jobs

1. **check-active** (Guard job)
   - Checks for active runs in the same concurrency group
   - Exits early if another run is in progress
   - Runs before the discovery matrix

2. **discovery** (Matrix job)
   - Executes discovery bot for each category/chunk combination
   - 48 total jobs (8 categories × 6 chunks)
   - Sequential execution (max-parallel: 1)
   - Each job has a 45-minute timeout

### Discovery Bot Configuration

Each discovery job runs with these parameters:
- City: Rotterdam
- Grid span: 6 km
- Nearby radius: 1200 m
- Max per cell per category: 25
- Max cells per category: 50
- Max total inserts: 500
- Chunks: 6
- Chunk index: 0-5 (from matrix)

## Monitoring Progress

### Run Summary

Each discovery job prints a summary at the end:
```
=== Discovery Run Summary ===
Category: [category]
Chunk: [chunk_index] / 5 (0-indexed)
Total chunks: 48 (8 categories × 6 chunks)
Job status: [status]
Elapsed time: [duration] seconds
============================
```

### GitHub Actions UI

Monitor progress in the GitHub Actions UI:
1. Navigate to the "Actions" tab
2. Select the "TDA Discovery (weekly, chunked)" workflow
3. View individual job status and logs

### Manual Trigger

To manually trigger a discovery run:
1. Go to the workflow page in GitHub Actions
2. Click "Run workflow"
3. Select the branch and click "Run workflow"

## Troubleshooting

### Workflow Stuck

If a workflow appears stuck:
- Check if jobs are actually running (look at individual job logs)
- Verify the discovery bot is making progress (check logs for OSM API calls)
- Check for rate limit errors (429) in logs

### Jobs Timing Out

If jobs consistently timeout:
- Consider reducing `--max-total-inserts` or `--max-cells-per-category`
- Check OSM Overpass API response times
- Verify network connectivity

### Multiple Runs Queued

If multiple runs are queued:
- This is expected behavior when runs are scheduled every 2 hours
- The guard job will skip runs if another is active
- Only one run will execute at a time

## Related Documentation

- Discovery bot: `Backend/app/workers/discovery_bot.py`
- OSM service: `Backend/services/osm_service.py`
- Category mappings: `Infra/config/categories.yml`
- City configurations: `Infra/config/cities.yml`

