# -*- coding: utf-8 -*-
"""
Contact Discovery Bot — Automatische contact discovery voor verified locaties
- Selecteert verified locaties zonder contact informatie
- Gebruikt contact_discovery_service om contactgegevens te ontdekken
- Slaat gevonden contacts op in outreach_contacts tabel
- Rate limiting voor externe API calls (website scraping)

Pad: Backend/app/workers/contact_discovery_bot.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import UUID

# --- Uniform logging ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="contact_discovery_bot")

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' en 'services.*' werken
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend

# ---------------------------------------------------------------------------
# DB (asyncpg helpers)
# ---------------------------------------------------------------------------
from services.db_service import init_db_pool, fetch, execute, fetchrow

# ---------------------------------------------------------------------------
# Contact Discovery Service
# ---------------------------------------------------------------------------
from services.contact_discovery_service import get_contact_discovery_service

# ---------------------------------------------------------------------------
# Worker run tracking
# ---------------------------------------------------------------------------
from services.worker_runs_service import (
    start_worker_run,
    mark_worker_run_running,
    update_worker_run_progress,
    finish_worker_run,
)

# Configuration
DEFAULT_BATCH_SIZE = int(os.getenv("CONTACT_DISCOVERY_BATCH_SIZE", "100"))
DEFAULT_MAX_LOCATIONS = int(os.getenv("CONTACT_DISCOVERY_MAX_LOCATIONS", "1000"))


async def fetch_locations_for_discovery(
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_locations: int = DEFAULT_MAX_LOCATIONS,
) -> List[Dict[str, Any]]:
    """
    Fetch locations that need contact discovery.
    
    Selects verified locations that:
    - status = 'VERIFIED'
    - is_claimable = true (or NULL, if column doesn't exist yet)
    - claimed_status = 'unclaimed' (or NULL, if column doesn't exist yet)
    - No entry in outreach_contacts for this location_id
    
    Args:
        batch_size: Maximum number of locations to fetch per batch
        max_locations: Maximum total locations to process
        
    Returns:
        List of location dicts with id, name, status, etc.
    """
    sql = """
        SELECT 
            l.id,
            l.name,
            l.address,
            l.state,
            l.lat,
            l.lng,
            l.place_id,
            l.source
        FROM locations l
        WHERE l.state = 'VERIFIED'
          AND (l.is_claimable IS NULL OR l.is_claimable = true)
          AND (l.claimed_status IS NULL OR l.claimed_status = 'unclaimed')
          AND NOT EXISTS (
              SELECT 1 
              FROM outreach_contacts oc 
              WHERE oc.location_id = l.id
          )
        ORDER BY l.last_verified_at DESC NULLS LAST, l.id DESC
        LIMIT $1
    """
    
    rows = await fetch(sql, min(batch_size, max_locations))
    return [dict(r) for r in rows]


async def save_contact(
    *,
    location_id: int,
    contact_info: Any,  # ContactInfo from contact_discovery_service
) -> bool:
    """
    Save discovered contact to outreach_contacts table.
    
    Args:
        location_id: Location ID
        contact_info: ContactInfo object from discovery service
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        await execute(
            """
            INSERT INTO outreach_contacts (
                location_id,
                email,
                source,
                confidence_score,
                discovered_at
            )
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (location_id, email) DO NOTHING
            """,
            location_id,
            contact_info.email,
            contact_info.source,
            contact_info.confidence_score,
            contact_info.discovered_at,
        )
        return True
    except Exception as e:
        logger.error(
            "save_contact_error",
            location_id=location_id,
            email=contact_info.email[:3] + "***" if contact_info.email else "N/A",
            error=str(e),
            exc_info=True
        )
        return False


async def process_location(
    *,
    location: Dict[str, Any],
    discovery_service: Any,
) -> Dict[str, Any]:
    """
    Process a single location through contact discovery.
    
    Args:
        location: Location dict with id, name, etc.
        discovery_service: ContactDiscoveryService instance
        
    Returns:
        Result dict with success status, contact info, etc.
    """
    location_id = location["id"]
    location_name = location.get("name", "Unknown")
    
    result = {
        "location_id": location_id,
        "location_name": location_name,
        "success": False,
        "contact_found": False,
        "contact_saved": False,
        "error": None,
        "contact_email": None,
        "contact_source": None,
        "confidence_score": None,
    }
    
    try:
        # Run contact discovery
        contact_info = await discovery_service.discover_contact(location_id)
        
        if contact_info:
            result.update({
                "contact_found": True,
                "contact_email": contact_info.email[:3] + "***",  # Partially masked for logging
                "contact_source": contact_info.source,
                "confidence_score": contact_info.confidence_score,
            })
            
            # Save to database
            saved = await save_contact(
                location_id=location_id,
                contact_info=contact_info,
            )
            
            if saved:
                result.update({
                    "success": True,
                    "contact_saved": True,
                })
                logger.info(
                    "contact_discovered_and_saved",
                    location_id=location_id,
                    location_name=location_name,
                    source=contact_info.source,
                    confidence=contact_info.confidence_score,
                    email=contact_info.email[:3] + "***"
                )
            else:
                result["error"] = "Failed to save contact to database"
                logger.warning(
                    "contact_discovered_but_not_saved",
                    location_id=location_id,
                    location_name=location_name,
                    source=contact_info.source,
                    confidence=contact_info.confidence_score,
                )
        else:
            # No contact found - this is not an error, just no result
            result.update({
                "success": True,  # Successfully processed, just no contact found
                "contact_found": False,
            })
            logger.debug(
                "no_contact_found",
                location_id=location_id,
                location_name=location_name,
            )
    
    except Exception as e:
        result["error"] = str(e)
        logger.error(
            "process_location_error",
            location_id=location_id,
            location_name=location_name,
            error=str(e),
            exc_info=True
        )
    
    return result


async def run_contact_discovery(
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_locations: int = DEFAULT_MAX_LOCATIONS,
    worker_run_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """
    Main contact discovery logic.
    
    Args:
        batch_size: Maximum number of locations to process per batch
        max_locations: Maximum total locations to process
        worker_run_id: Optional worker run ID for tracking
        
    Returns:
        Dictionary with counters and results
    """
    discovery_service = get_contact_discovery_service()
    last_progress = -1
    
    # Fetch locations that need contact discovery
    locations = await fetch_locations_for_discovery(
        batch_size=batch_size,
        max_locations=max_locations,
    )
    
    if not locations:
        counters: Dict[str, Any] = {
            "total_processed": 0,
            "contacts_found": 0,
            "contacts_saved": 0,
            "no_contact": 0,
            "errors": 0,
            "results": [],
        }
        if worker_run_id:
            storage_counters = {k: v for k, v in counters.items() if k != "results"}
            await finish_worker_run(worker_run_id, "finished", 100, storage_counters, None)
        logger.info("contact_discovery_no_locations_to_process")
        return counters
    
    logger.info(
        "contact_discovery_starting",
        total_locations=len(locations),
        batch_size=batch_size,
        max_locations=max_locations,
    )
    print(f"[ContactDiscoveryBot] Processing {len(locations)} locations for contact discovery...")
    
    results = []
    contacts_found = 0
    contacts_saved = 0
    no_contact = 0
    errors = 0
    
    # Process locations with rate limiting
    # Website scraping has built-in rate limiting (1 request per 2 seconds)
    # OSM queries are fast, but we add a small delay to be safe
    for idx, location in enumerate(locations):
        try:
            # Update progress
            if worker_run_id and idx > 0 and idx % 10 == 0:
                progress = int((idx / len(locations)) * 100)
                if progress != last_progress:
                    await update_worker_run_progress(
                        worker_run_id,
                        progress,
                        {
                            "processed": idx,
                            "total": len(locations),
                            "contacts_found": contacts_found,
                            "contacts_saved": contacts_saved,
                        }
                    )
                    last_progress = progress
            
            # Process location
            result = await process_location(
                location=location,
                discovery_service=discovery_service,
            )
            
            results.append(result)
            
            if result["error"]:
                errors += 1
            elif result["contact_found"]:
                contacts_found += 1
                if result["contact_saved"]:
                    contacts_saved += 1
            else:
                no_contact += 1
            
            # Small delay between locations to avoid hammering external APIs
            # Website scraper has its own rate limiting, but we add a small delay here too
            if idx < len(locations) - 1:  # Don't delay after last location
                await asyncio.sleep(0.5)  # 500ms delay between locations
        
        except Exception as e:
            errors += 1
            logger.error(
                "contact_discovery_unexpected_error",
                location_id=location.get("id"),
                error=str(e),
                exc_info=True
            )
            results.append({
                "location_id": location.get("id"),
                "location_name": location.get("name", "Unknown"),
                "success": False,
                "error": str(e),
            })
    
    counters: Dict[str, Any] = {
        "total_processed": len(locations),
        "contacts_found": contacts_found,
        "contacts_saved": contacts_saved,
        "no_contact": no_contact,
        "errors": errors,
        "results": results[:10],  # Only include first 10 results in response
    }
    
    logger.info(
        "contact_discovery_completed",
        total_processed=len(locations),
        contacts_found=contacts_found,
        contacts_saved=contacts_saved,
        no_contact=no_contact,
        errors=errors,
    )
    print(f"[ContactDiscoveryBot] Completed: {len(locations)} processed, {contacts_found} contacts found, {contacts_saved} saved, {no_contact} no contact, {errors} errors")
    
    if worker_run_id:
        storage_counters = {k: v for k, v in counters.items() if k != "results"}
        await finish_worker_run(worker_run_id, "finished", 100, storage_counters, None)
    
    return counters


def _parse_worker_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("worker-run-id must be a valid UUID") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Contact Discovery Bot - Discover contact information for verified locations"
    )
    parser.add_argument(
        "--worker-run-id",
        type=_parse_worker_run_id,
        help="Worker run ID for tracking (optional)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size for processing (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--max-locations",
        type=int,
        default=DEFAULT_MAX_LOCATIONS,
        help=f"Maximum locations to process (default: {DEFAULT_MAX_LOCATIONS})",
    )
    return parser.parse_args()


@with_run_id
async def main_async():
    """Main entry point for contact discovery bot."""
    args = parse_args()
    
    worker_run_id = args.worker_run_id
    
    # Initialize database pool
    await init_db_pool()
    
    try:
        # Mark as running if worker_run_id provided
        if worker_run_id:
            await mark_worker_run_running(worker_run_id)
        
        # Run contact discovery
        counters = await run_contact_discovery(
            batch_size=args.batch_size,
            max_locations=args.max_locations,
            worker_run_id=worker_run_id,
        )
        
        print(f"[ContactDiscoveryBot] Summary: {counters}")
        return counters
    
    except Exception as e:
        logger.error(
            "contact_discovery_bot_failed",
            error=str(e),
            exc_info=True
        )
        if worker_run_id:
            await finish_worker_run(worker_run_id, "failed", 0, {}, str(e))
        raise


def main():
    """CLI entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

