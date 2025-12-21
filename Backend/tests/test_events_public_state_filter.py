"""
Test that events_public view correctly filters by state = 'published'.

This test verifies that the SQL migration 065_fix_events_public_state_filter.sql
works correctly and only shows published events in the events_public view.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio

from services.db_service import execute, fetch, fetchrow, init_db_pool


@pytest_asyncio.fixture
async def db_pool():
    """Initialize database pool for tests."""
    await init_db_pool()
    yield
    # Cleanup handled by test isolation


@pytest.mark.asyncio
async def test_events_public_only_shows_published_events(db_pool) -> None:
    """
    Test that events_public view only includes events with state = 'published'.
    
    This test:
    1. Creates test data with different states (candidate, verified, published, rejected)
    2. Verifies that only published events appear in events_public view
    """
    # Clean up any existing test data
    await execute("DELETE FROM events_candidate WHERE source_key LIKE 'test_%'")
    await execute("DELETE FROM event_raw WHERE title LIKE 'Test Event%'")
    await execute("DELETE FROM event_sources WHERE key LIKE 'test_%'")
    
    # Create test event source
    source_id_row = await fetchrow(
        """
        INSERT INTO event_sources (key, name, base_url, status, city_key)
        VALUES ('test_source', 'Test Source', 'https://test.example.com', 'active', 'rotterdam')
        ON CONFLICT (key) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """
    )
    source_id = source_id_row["id"] if source_id_row else None
    assert source_id is not None, "Failed to create test event source"
    
    # Create test event_raw records with different processing states
    now = datetime.now(timezone.utc)
    
    # Create enriched event_raw (required for events_public)
    raw_id_row = await fetchrow(
        """
        INSERT INTO event_raw (
            event_source_id, title, description, location_text, event_url,
            start_at, processing_state, category_key, country
        )
        VALUES ($1, 'Test Event Published', 'Description', 'Rotterdam, Netherlands', 'https://test.com/1',
                $2, 'enriched', 'community', 'netherlands')
        RETURNING id
        """,
        source_id,
        now,
    )
    raw_id = raw_id_row["id"] if raw_id_row else None
    assert raw_id is not None, "Failed to create test event_raw"
    
    # Create events_candidate with different states
    candidate_id = await fetchrow(
        """
        INSERT INTO events_candidate (
            event_source_id, event_raw_id, title, start_time_utc, location_text,
            url, source_key, ingest_hash, state
        )
        VALUES ($1, $2, 'Test Event Candidate', $3, 'Rotterdam', 'https://test.com/1',
                'test_source', 'hash1', 'candidate')
        RETURNING id
        """,
        source_id,
        raw_id,
        now,
    )
    
    verified_id = await fetchrow(
        """
        INSERT INTO events_candidate (
            event_source_id, event_raw_id, title, start_time_utc, location_text,
            url, source_key, ingest_hash, state
        )
        VALUES ($1, $2, 'Test Event Verified', $3, 'Rotterdam', 'https://test.com/2',
                'test_source', 'hash2', 'verified')
        RETURNING id
        """,
        source_id,
        raw_id,
        now,
    )
    
    published_id = await fetchrow(
        """
        INSERT INTO events_candidate (
            event_source_id, event_raw_id, title, start_time_utc, location_text,
            url, source_key, ingest_hash, state
        )
        VALUES ($1, $2, 'Test Event Published', $3, 'Rotterdam', 'https://test.com/3',
                'test_source', 'hash3', 'published')
        RETURNING id
        """,
        source_id,
        raw_id,
        now,
    )
    
    rejected_id = await fetchrow(
        """
        INSERT INTO events_candidate (
            event_source_id, event_raw_id, title, start_time_utc, location_text,
            url, source_key, ingest_hash, state
        )
        VALUES ($1, $2, 'Test Event Rejected', $3, 'Rotterdam', 'https://test.com/4',
                'test_source', 'hash4', 'rejected')
        RETURNING id
        """,
        source_id,
        raw_id,
        now,
    )
    
    # Query events_public view
    public_events = await fetch(
        "SELECT id, title, state FROM events_public WHERE source_key = 'test_source'"
    )
    
    # Only published events should appear
    assert len(public_events) == 1, f"Expected 1 published event, got {len(public_events)}"
    assert public_events[0]["id"] == published_id["id"], "Published event ID mismatch"
    assert public_events[0]["title"] == "Test Event Published", "Published event title mismatch"
    assert public_events[0]["state"] == "published", "Published event state mismatch"
    
    # Verify other states are not in events_public
    public_ids = {row["id"] for row in public_events}
    assert candidate_id["id"] not in public_ids, "Candidate event should not appear in events_public"
    assert verified_id["id"] not in public_ids, "Verified event should not appear in events_public"
    assert rejected_id["id"] not in public_ids, "Rejected event should not appear in events_public"
    
    # Cleanup
    await execute("DELETE FROM events_candidate WHERE source_key = 'test_source'")
    await execute("DELETE FROM event_raw WHERE event_source_id = $1", source_id)
    await execute("DELETE FROM event_sources WHERE key = 'test_source'")


@pytest.mark.asyncio
async def test_events_public_filters_duplicates(db_pool) -> None:
    """
    Test that events_public view excludes duplicate events (duplicate_of_id IS NOT NULL).
    """
    # Clean up
    await execute("DELETE FROM events_candidate WHERE source_key = 'test_dup'")
    await execute("DELETE FROM event_raw WHERE title LIKE 'Test Dup%'")
    await execute("DELETE FROM event_sources WHERE key = 'test_dup'")
    
    # Create test source
    source_id_row = await fetchrow(
        """
        INSERT INTO event_sources (key, name, base_url, status, city_key)
        VALUES ('test_dup', 'Test Dup Source', 'https://test.example.com', 'active', 'rotterdam')
        ON CONFLICT (key) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """
    )
    source_id = source_id_row["id"] if source_id_row else None
    assert source_id is not None
    
    now = datetime.now(timezone.utc)
    
    # Create enriched event_raw
    raw_id_row = await fetchrow(
        """
        INSERT INTO event_raw (
            event_source_id, title, description, location_text, event_url,
            start_at, processing_state, category_key, country
        )
        VALUES ($1, 'Test Dup Event', 'Description', 'Rotterdam, Netherlands', 'https://test.com/dup',
                $2, 'enriched', 'community', 'netherlands')
        RETURNING id
        """,
        source_id,
        now,
    )
    raw_id = raw_id_row["id"] if raw_id_row else None
    assert raw_id is not None
    
    # Create canonical (published) event
    canonical_id = await fetchrow(
        """
        INSERT INTO events_candidate (
            event_source_id, event_raw_id, title, start_time_utc, location_text,
            url, source_key, ingest_hash, state, duplicate_of_id
        )
        VALUES ($1, $2, 'Test Dup Canonical', $3, 'Rotterdam', 'https://test.com/canonical',
                'test_dup', 'hash_canonical', 'published', NULL)
        RETURNING id
        """,
        source_id,
        raw_id,
        now,
    )
    
    # Create duplicate (published but has duplicate_of_id)
    duplicate_id = await fetchrow(
        """
        INSERT INTO events_candidate (
            event_source_id, event_raw_id, title, start_time_utc, location_text,
            url, source_key, ingest_hash, state, duplicate_of_id
        )
        VALUES ($1, $2, 'Test Dup Duplicate', $3, 'Rotterdam', 'https://test.com/duplicate',
                'test_dup', 'hash_duplicate', 'published', $4)
        RETURNING id
        """,
        source_id,
        raw_id,
        now,
        canonical_id["id"],
    )
    
    # Query events_public
    public_events = await fetch(
        "SELECT id, title, duplicate_of_id FROM events_public WHERE source_key = 'test_dup'"
    )
    
    # Only canonical (non-duplicate) published event should appear
    assert len(public_events) == 1, f"Expected 1 canonical event, got {len(public_events)}"
    assert public_events[0]["id"] == canonical_id["id"], "Canonical event ID mismatch"
    assert public_events[0]["duplicate_of_id"] is None, "Canonical should have NULL duplicate_of_id"
    
    # Duplicate should not appear
    public_ids = {row["id"] for row in public_events}
    assert duplicate_id["id"] not in public_ids, "Duplicate event should not appear in events_public"
    
    # Cleanup
    await execute("DELETE FROM events_candidate WHERE source_key = 'test_dup'")
    await execute("DELETE FROM event_raw WHERE event_source_id = $1", source_id)
    await execute("DELETE FROM event_sources WHERE key = 'test_dup'")

