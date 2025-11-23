# Backend/services/discovery_jobs_service.py
"""
Discovery Jobs Service - Manages the Discovery Train job queue.

Provides functions to enqueue, fetch, and update discovery jobs for sequential
orchestration of discovery runs across cities, districts, and categories.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID

from services.db_service import fetch, fetchrow, execute, init_db_pool
from app.core.logging import get_logger

logger = get_logger()


class DiscoveryJob:
    """Represents a discovery job in the queue."""
    def __init__(
        self,
        id: UUID,
        city_key: str,
        district_key: Optional[str],
        category: str,
        status: str,
        attempts: int,
        last_error: Optional[str],
        created_at: datetime,
        started_at: Optional[datetime],
        finished_at: Optional[datetime],
    ):
        self.id = id
        self.city_key = city_key
        self.district_key = district_key
        self.category = category
        self.status = status
        self.attempts = attempts
        self.last_error = last_error
        self.created_at = created_at
        self.started_at = started_at
        self.finished_at = finished_at

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "DiscoveryJob":
        """Create DiscoveryJob from database row."""
        return cls(
            id=UUID(str(row["id"])),
            city_key=str(row["city_key"]),
            district_key=row.get("district_key"),
            category=str(row["category"]),
            status=str(row["status"]),
            attempts=int(row.get("attempts") or 0),
            last_error=row.get("last_error"),
            created_at=row.get("created_at") or datetime.now(timezone.utc),
            started_at=row.get("started_at"),
            finished_at=row.get("finished_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "city_key": self.city_key,
            "district_key": self.district_key,
            "category": self.category,
            "status": self.status,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


async def enqueue_jobs(
    city_key: str,
    categories: List[str],
    districts: Optional[List[str]] = None,
) -> List[UUID]:
    """
    Enqueue discovery jobs for (city, district?, category) combinations.
    
    Args:
        city_key: City key from cities.yml (e.g., "rotterdam")
        categories: List of category keys (e.g., ["restaurant", "bakery"])
        districts: Optional list of district keys. If None, creates city-level jobs.
                   If empty list, creates jobs for all districts in the city.
    
    Returns:
        List of job IDs that were created.
    """
    await init_db_pool()
    
    # If districts is None, create city-level job (district_key = NULL)
    # If districts is empty list, load all districts from cities.yml
    if districts is not None and len(districts) == 0:
        try:
            from app.workers.discovery_bot import load_cities_config
            cities_config = load_cities_config()
            city_def = (cities_config.get("cities") or {}).get(city_key)
            if city_def and isinstance(city_def, dict):
                districts_dict = city_def.get("districts", {})
                if districts_dict:
                    districts = list(districts_dict.keys())
                else:
                    districts = None  # No districts, create city-level job
            else:
                districts = None
        except Exception as e:
            logger.warning("failed_to_load_districts_for_enqueue", city_key=city_key, error=str(e))
            districts = None
    
    job_ids: List[UUID] = []
    
    # Create jobs for each (district?, category) combination
    if districts is None:
        # City-level job (no districts)
        for category in categories:
            sql = (
                """
                INSERT INTO discovery_jobs (city_key, district_key, category, status)
                VALUES ($1, NULL, $2, 'pending')
                RETURNING id
                """
            )
            rows = await fetch(sql, city_key, category)
            if rows:
                job_id = UUID(str(rows[0]["id"]))
                job_ids.append(job_id)
    else:
        # District-level jobs
        for district in districts:
            for category in categories:
                sql = (
                    """
                    INSERT INTO discovery_jobs (city_key, district_key, category, status)
                    VALUES ($1, $2, $3, 'pending')
                    RETURNING id
                    """
                )
                rows = await fetch(sql, city_key, district, category)
                if rows:
                    job_id = UUID(str(rows[0]["id"]))
                    job_ids.append(job_id)
    
    logger.info(
        "discovery_jobs_enqueued",
        city_key=city_key,
        categories=categories,
        districts=districts,
        job_count=len(job_ids),
    )
    return job_ids


async def get_next_pending_job() -> Optional[DiscoveryJob]:
    """
    Get the next pending job (FIFO: oldest first).
    
    Returns:
        DiscoveryJob or None if no pending jobs exist.
    """
    await init_db_pool()
    
    sql = (
        """
        SELECT id, city_key, district_key, category, status, attempts, last_error,
               created_at, started_at, finished_at
        FROM discovery_jobs
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
        """
    )
    row = await fetchrow(sql)
    
    if not row:
        return None
    
    return DiscoveryJob.from_row(dict(row))


async def mark_job_running(job_id: UUID) -> None:
    """Mark a job as running."""
    await init_db_pool()
    
    sql = (
        """
        UPDATE discovery_jobs
        SET status = 'running',
            started_at = NOW(),
            attempts = attempts + 1
        WHERE id = $1
        """
    )
    await execute(sql, str(job_id))
    logger.debug("discovery_job_marked_running", job_id=str(job_id))


async def mark_job_finished(job_id: UUID, counters: Optional[Dict[str, Any]] = None) -> None:
    """
    Mark a job as finished.
    
    Args:
        job_id: Job UUID
        counters: Optional counters dict (for logging/metrics)
    """
    await init_db_pool()
    
    sql = (
        """
        UPDATE discovery_jobs
        SET status = 'finished',
            finished_at = NOW(),
            last_error = NULL
        WHERE id = $1
        """
    )
    await execute(sql, str(job_id))
    logger.info(
        "discovery_job_finished",
        job_id=str(job_id),
        counters=counters,
    )


async def mark_job_failed(job_id: UUID, error: str) -> None:
    """Mark a job as failed with error message."""
    await init_db_pool()
    
    sql = (
        """
        UPDATE discovery_jobs
        SET status = 'failed',
            finished_at = NOW(),
            last_error = $2
        WHERE id = $1
        """
    )
    await execute(sql, str(job_id), error)
    logger.warning(
        "discovery_job_failed",
        job_id=str(job_id),
        error=error,
    )


async def get_job_status(job_id: UUID) -> Optional[DiscoveryJob]:
    """Get job by ID."""
    await init_db_pool()
    
    sql = (
        """
        SELECT id, city_key, district_key, category, status, attempts, last_error,
               created_at, started_at, finished_at
        FROM discovery_jobs
        WHERE id = $1
        """
    )
    row = await fetchrow(sql, str(job_id))
    
    if not row:
        return None
    
    return DiscoveryJob.from_row(dict(row))





