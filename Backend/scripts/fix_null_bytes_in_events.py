#!/usr/bin/env python3
"""
Script om null bytes te verwijderen uit bestaande event data in de database.

Dit script repareert:
- event_raw: title, description, location_text, venue, event_url, image_url, summary_ai
- events_candidate: title, description, location_text, url
- JSONB kolommen: raw_payload, processing_errors (via UPDATE met REPLACE)

Gebruik:
  cd Backend
  source .venv/bin/activate
  python scripts/fix_null_bytes_in_events.py
"""

import asyncio
import sys
from pathlib import Path

# Path setup
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger
from services.db_service import init_db_pool, execute, fetch, fetchrow
import json

configure_logging(service_name="script")
logger = get_logger()


def has_null_bytes(text: str) -> bool:
    """Check if a string contains null bytes."""
    if not isinstance(text, str):
        return False
    return '\x00' in text or '\u0000' in text


def sanitize_string(text: str) -> str:
    """Remove null bytes from a string."""
    if not isinstance(text, str):
        return text
    return text.replace('\x00', '').replace('\u0000', '')


def sanitize_jsonb(obj: any) -> any:
    """Recursively sanitize JSONB object."""
    if obj is None:
        return None
    if isinstance(obj, str):
        return sanitize_string(obj)
    if isinstance(obj, dict):
        return {k: sanitize_jsonb(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_jsonb(item) for item in obj]
    return obj


async def fix_null_bytes_in_event_raw() -> int:
    """
    Fix null bytes in event_raw table.
    Returns number of rows updated.
    """
    logger.info("fixing_null_bytes_in_event_raw")
    
    # Fetch all rows - we can't use LIKE with null bytes
    from services.db_service import fetch as db_fetch
    rows = await db_fetch(
        """
        SELECT 
            id,
            title,
            description,
            location_text,
            venue,
            event_url,
            image_url,
            summary_ai,
            raw_payload,
            processing_errors
        FROM event_raw
        """
    )
    
    if not rows:
        logger.info("no_rows_found_in_event_raw")
        return 0
    
    updated_count = 0
    
    for row in rows:
        row_dict = dict(row)
        event_id = row_dict["id"]
        needs_update = False
        updates = []
        params = [event_id]
        param_num = 2
        
        # Check and sanitize text fields
        for field in ["title", "description", "location_text", "venue", "event_url", "image_url", "summary_ai"]:
            value = row_dict.get(field)
            if value and has_null_bytes(value):
                sanitized = sanitize_string(value)
                updates.append(f"{field} = ${param_num}")
                params.append(sanitized)
                param_num += 1
                needs_update = True
        
        # Check and sanitize JSONB fields
        for field in ["raw_payload", "processing_errors"]:
            value = row_dict.get(field)
            if value:
                # Check if JSONB contains null bytes by converting to string
                try:
                    json_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
                    if has_null_bytes(json_str):
                        sanitized = sanitize_jsonb(value)
                        updates.append(f"{field} = CAST(${param_num}::text AS JSONB)")
                        params.append(json.dumps(sanitized, ensure_ascii=False))
                        param_num += 1
                        needs_update = True
                except Exception:
                    # Skip if we can't serialize
                    pass
        
        if needs_update:
            sql = f"""
                UPDATE event_raw
                SET {', '.join(updates)}
                WHERE id = $1
            """
            await execute(sql, *params)
            updated_count += 1
    
    logger.info(
        "fixed_null_bytes_in_event_raw",
        rows_updated=updated_count,
        total_rows_checked=len(rows),
    )
    
    return updated_count


async def fix_null_bytes_in_events_candidate() -> int:
    """
    Fix null bytes in events_candidate table.
    Returns number of rows updated.
    """
    logger.info("fixing_null_bytes_in_events_candidate")
    
    # Fetch all rows - we can't use LIKE with null bytes
    from services.db_service import fetch as db_fetch
    rows = await db_fetch(
        """
        SELECT 
            id,
            title,
            description,
            location_text,
            url
        FROM events_candidate
        """
    )
    
    if not rows:
        logger.info("no_rows_found_in_events_candidate")
        return 0
    
    updated_count = 0
    
    for row in rows:
        row_dict = dict(row)
        candidate_id = row_dict["id"]
        needs_update = False
        updates = []
        params = [candidate_id]
        param_num = 2
        
        # Check and sanitize text fields
        for field in ["title", "description", "location_text", "url"]:
            value = row_dict.get(field)
            if value and has_null_bytes(value):
                sanitized = sanitize_string(value)
                updates.append(f"{field} = ${param_num}")
                params.append(sanitized)
                param_num += 1
                needs_update = True
        
        if needs_update:
            sql = f"""
                UPDATE events_candidate
                SET {', '.join(updates)}
                WHERE id = $1
            """
            await execute(sql, *params)
            updated_count += 1
    
    logger.info(
        "fixed_null_bytes_in_events_candidate",
        rows_updated=updated_count,
        total_rows_checked=len(rows),
    )
    
    return updated_count


async def main() -> None:
    """Main entry point."""
    await init_db_pool()
    
    logger.info("starting_null_byte_fix")
    
    try:
        event_raw_count = await fix_null_bytes_in_event_raw()
        events_candidate_count = await fix_null_bytes_in_events_candidate()
        
        total_fixed = event_raw_count + events_candidate_count
        
        logger.info(
            "null_byte_fix_complete",
            event_raw_fixed=event_raw_count,
            events_candidate_fixed=events_candidate_count,
            total_fixed=total_fixed,
        )
        
        print(f"\n✅ Null byte fix complete!")
        print(f"   - event_raw: {event_raw_count} rows fixed")
        print(f"   - events_candidate: {events_candidate_count} rows fixed")
        print(f"   - Total: {total_fixed} rows fixed")
        
    except Exception as e:
        logger.error("null_byte_fix_failed", error=str(e), exc_info=e)
        raise


if __name__ == "__main__":
    asyncio.run(main())










