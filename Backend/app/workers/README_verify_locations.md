# VerifyLocationsBot

A worker that classifies and promotes CANDIDATE locations to VERIFIED state using existing AI services.

## Purpose

This worker implements the "Self-Verifying AI Loop" by:
1. Fetching CANDIDATE locations from the database
2. Classifying each using the existing `ClassifyService`
3. Validating results using existing AI validation
4. Promoting eligible locations to VERIFIED state
5. Logging all actions via `AuditService`

## Usage

### Basic Usage

```bash
cd Backend
source .venv/bin/activate

# Dry run (recommended first)
python -m app.workers.verify_locations --city rotterdam --limit 50 --dry-run 1

# Actual execution
python -m app.workers.verify_locations --city rotterdam --limit 200 --dry-run 0
```

### Command Line Options

- `--city <name>`: Filter by city (if supported by schema)
- `--source <source>`: Filter by source (e.g., OSM_OVERPASS, GOOGLE_PLACES)
- `--limit <N>`: Maximum items to process (default: 200)
- `--offset <M>`: Offset for pagination (default: 0)
- `--chunks <K>`: Total chunks for sharding (default: 1)
- `--chunk-index <i>`: Which chunk to process, 0-based (default: 0)
- `--dry-run {0|1}`: Dry run mode - don't write updates (default: 0)
- `--min-confidence <score>`: Minimum confidence for promotion (default: 0.8)
- `--model <name>`: Override AI model
- `--log-json {0|1}`: Use JSON logging (default: 0)

### Examples

```bash
# Process 100 locations from Rotterdam
python -m app.workers.verify_locations --city rotterdam --limit 100 --dry-run 0

# Process only OSM sources
python -m app.workers.verify_locations --source OSM_OVERPASS --limit 50 --dry-run 0

# Process in chunks (useful for large batches)
python -m app.workers.verify_locations --limit 1000 --chunks 4 --chunk-index 0 --dry-run 0
python -m app.workers.verify_locations --limit 1000 --chunks 4 --chunk-index 1 --dry-run 0
python -m app.workers.verify_locations --limit 1000 --chunks 4 --chunk-index 2 --dry-run 0
python -m app.workers.verify_locations --limit 1000 --chunks 4 --chunk-index 3 --dry-run 0

# Lower confidence threshold
python -m app.workers.verify_locations --min-confidence 0.7 --limit 100 --dry-run 0
```

## How It Works

1. **Fetch Candidates**: Queries `locations` table for `state = 'CANDIDATE'` and `is_retired = false`
2. **Classify**: Uses `ClassifyService.classify()` to get AI classification
3. **Validate**: Uses `validate_classification_payload()` to ensure valid results
4. **Promote**: If `action = 'keep'` and `confidence >= min_confidence`, updates:
   - `state = 'VERIFIED'`
   - `category = <classified_category>`
   - `confidence_score = <confidence>`
   - `last_verified_at = now()`
5. **Audit**: Logs all actions via `AuditService.log()`

## Output

The worker prints progress for each location:
- `[PROMOTE]`: Location was promoted to VERIFIED
- `[SKIP]`: Location was not promoted (low confidence or action=ignore)
- `[ERROR]`: Processing failed for this location

Final summary shows:
- Total processed
- Promoted to VERIFIED
- Skipped
- Errors

## Database Changes

- **No schema changes**: Uses existing `locations` table
- **State transitions**: CANDIDATE → VERIFIED (when eligible)
- **Audit trail**: All actions logged to `ai_logs` table
- **Idempotent**: Safe to re-run, won't duplicate work

## Integration

This worker integrates with:
- `ClassifyService`: For AI classification
- `ai_validation.py`: For result validation
- `AuditService`: For audit logging
- Existing database schema (no migrations needed)

## Monitoring

Check results with SQL:
```sql
-- Recently promoted locations
SELECT id, name, category, source, state, last_verified_at
FROM locations
WHERE state = 'VERIFIED'
ORDER BY last_verified_at DESC
LIMIT 50;

-- State distribution
SELECT state, COUNT(*)
FROM locations
GROUP BY state
ORDER BY 2 DESC;
```
