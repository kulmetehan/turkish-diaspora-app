# Backend/tests/test_outreach_infrastructure.py
"""
Tests for outreach infrastructure: database schema, rate limiting, and metrics.

Tests the foundation components for the outreach system without sending actual emails.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, date, timedelta

from services.db_service import fetch, execute, fetchrow
from services.outreach_rate_limiting_service import OutreachRateLimitingService
from services.outreach_metrics_service import OutreachMetricsService


pytestmark = pytest.mark.asyncio


async def test_outreach_contacts_table_exists():
    """Test that outreach_contacts table exists with correct structure."""
    # Check table exists
    sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'outreach_contacts'
        )
    """
    rows = await fetch(sql)
    assert rows and len(rows) > 0
    assert rows[0].get("exists", False) is True
    
    # Check columns exist
    sql_columns = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND table_name = 'outreach_contacts'
        ORDER BY column_name
    """
    columns = await fetch(sql_columns)
    column_names = [row["column_name"] for row in columns]
    
    assert "id" in column_names
    assert "location_id" in column_names
    assert "email" in column_names
    assert "source" in column_names
    assert "confidence_score" in column_names
    assert "discovered_at" in column_names
    assert "created_at" in column_names


async def test_outreach_emails_table_exists():
    """Test that outreach_emails table exists with correct structure."""
    # Check table exists
    sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'outreach_emails'
        )
    """
    rows = await fetch(sql)
    assert rows and len(rows) > 0
    assert rows[0].get("exists", False) is True
    
    # Check columns exist
    sql_columns = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND table_name = 'outreach_emails'
        ORDER BY column_name
    """
    columns = await fetch(sql_columns)
    column_names = [row["column_name"] for row in columns]
    
    assert "id" in column_names
    assert "location_id" in column_names
    assert "contact_id" in column_names
    assert "email" in column_names
    assert "status" in column_names
    assert "message_id" in column_names  # Generic message_id column
    assert "ses_message_id" in column_names  # Kept for backward compatibility
    assert "sent_at" in column_names
    assert "delivered_at" in column_names
    assert "clicked_at" in column_names
    assert "bounced_at" in column_names
    assert "bounce_reason" in column_names


async def test_outreach_email_status_enum_exists():
    """Test that outreach_email_status ENUM type exists."""
    sql = """
        SELECT EXISTS (
            SELECT FROM pg_type 
            WHERE typname = 'outreach_email_status'
        )
    """
    rows = await fetch(sql)
    assert rows and len(rows) > 0
    assert rows[0].get("exists", False) is True
    
    # Check enum values
    sql_values = """
        SELECT enumlabel
        FROM pg_enum
        WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'outreach_email_status')
        ORDER BY enumsortorder
    """
    enum_rows = await fetch(sql_values)
    enum_values = [row["enumlabel"] for row in enum_rows]
    
    assert "queued" in enum_values
    assert "sent" in enum_values
    assert "delivered" in enum_values
    assert "bounced" in enum_values
    assert "clicked" in enum_values
    assert "opted_out" in enum_values


async def test_outreach_contacts_unique_constraint():
    """Test that UNIQUE constraint on (location_id, email) works."""
    # Create a test location first
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        "Test Location for Outreach",
        "Test Address 123",
        "restaurant",
        "VERIFIED",
        0.95,
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    try:
        # Insert first contact
        await execute(
            """
            INSERT INTO outreach_contacts (location_id, email, source, confidence_score)
            VALUES ($1, $2, $3, $4)
            """,
            location_id,
            "test@example.com",
            "osm",
            90,
        )
        
        # Try to insert duplicate (should fail)
        with pytest.raises(Exception):  # Should raise unique constraint violation
            await execute(
                """
                INSERT INTO outreach_contacts (location_id, email, source, confidence_score)
                VALUES ($1, $2, $3, $4)
                """,
                location_id,
                "test@example.com",
                "website",
                85,
            )
    finally:
        # Cleanup
        await execute("DELETE FROM outreach_contacts WHERE location_id = $1", location_id)
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_rate_limiting_service_can_send_email():
    """Test that rate limiting service correctly checks if email can be sent."""
    service = OutreachRateLimitingService(daily_limit=50)
    
    # Initially should be able to send (no emails sent today)
    can_send = await service.can_send_email()
    assert can_send is True
    
    # Get today's count
    count = await service.get_today_count()
    assert count >= 0  # Should be 0 or more
    
    # Get remaining quota
    remaining = await service.get_remaining_quota()
    assert remaining >= 0
    assert remaining <= 50


async def test_rate_limiting_service_tracks_emails():
    """Test that rate limiting service correctly tracks sent emails."""
    # Create test location and contact
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        "Test Location for Rate Limiting",
        "Test Address 456",
        "restaurant",
        "VERIFIED",
        0.95,
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    contact_row = await fetchrow(
        """
        INSERT INTO outreach_contacts (location_id, email, source, confidence_score)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        location_id,
        "ratelimit@example.com",
        "osm",
        90,
    )
    assert contact_row is not None
    contact_id = contact_row["id"]
    
    try:
        service = OutreachRateLimitingService(daily_limit=50)
        
        # Get initial count
        initial_count = await service.get_today_count()
        
        # Create a sent email (simulate sending)
        await execute(
            """
            INSERT INTO outreach_emails (location_id, contact_id, email, status, sent_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            location_id,
            contact_id,
            "ratelimit@example.com",
            "sent",
            datetime.now(timezone.utc),
        )
        
        # Count should increase
        new_count = await service.get_today_count()
        assert new_count == initial_count + 1
        
        # Remaining quota should decrease
        remaining = await service.get_remaining_quota()
        assert remaining == 50 - new_count
        
    finally:
        # Cleanup
        await execute("DELETE FROM outreach_emails WHERE location_id = $1", location_id)
        await execute("DELETE FROM outreach_contacts WHERE location_id = $1", location_id)
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_metrics_service_get_mails_sent_count():
    """Test that metrics service correctly counts sent emails."""
    service = OutreachMetricsService()
    
    # Get initial count
    initial_count = await service.get_mails_sent_count()
    assert initial_count >= 0
    
    # Create test location and contact
    location_row = await fetchrow(
        """
        INSERT INTO locations (name, address, category, state, confidence_score)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        "Test Location for Metrics",
        "Test Address 789",
        "restaurant",
        "VERIFIED",
        0.95,
    )
    assert location_row is not None
    location_id = location_row["id"]
    
    contact_row = await fetchrow(
        """
        INSERT INTO outreach_contacts (location_id, email, source, confidence_score)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        location_id,
        "metrics@example.com",
        "osm",
        90,
    )
    assert contact_row is not None
    contact_id = contact_row["id"]
    
    try:
        # Create sent email
        await execute(
            """
            INSERT INTO outreach_emails (location_id, contact_id, email, status, sent_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            location_id,
            contact_id,
            "metrics@example.com",
            "sent",
            datetime.now(timezone.utc),
        )
        
        # Count should increase
        new_count = await service.get_mails_sent_count()
        assert new_count == initial_count + 1
        
    finally:
        # Cleanup
        await execute("DELETE FROM outreach_emails WHERE location_id = $1", location_id)
        await execute("DELETE FROM outreach_contacts WHERE location_id = $1", location_id)
        await execute("DELETE FROM locations WHERE id = $1", location_id)


async def test_metrics_service_get_bounce_rate():
    """Test that metrics service correctly calculates bounce rate."""
    service = OutreachMetricsService()
    
    # Get initial bounce rate (should be 0.0 if no emails)
    bounce_rate = await service.get_bounce_rate()
    assert bounce_rate >= 0.0
    assert bounce_rate <= 100.0


async def test_metrics_service_get_click_rate():
    """Test that metrics service correctly calculates click rate."""
    service = OutreachMetricsService()
    
    # Get initial click rate (should be 0.0 if no emails)
    click_rate = await service.get_click_rate()
    assert click_rate >= 0.0
    assert click_rate <= 100.0


async def test_metrics_service_get_all_metrics():
    """Test that metrics service returns all metrics in a single call."""
    service = OutreachMetricsService()
    
    metrics = await service.get_all_metrics()
    
    assert "mails_sent" in metrics
    assert "bounce_rate" in metrics
    assert "click_rate" in metrics
    assert "claim_rate" in metrics
    assert "removal_rate" in metrics
    assert "no_action_rate" in metrics
    
    assert isinstance(metrics["mails_sent"], int)
    assert isinstance(metrics["bounce_rate"], float)
    assert isinstance(metrics["click_rate"], float)
    assert isinstance(metrics["claim_rate"], float)
    assert metrics["bounce_rate"] >= 0.0
    assert metrics["bounce_rate"] <= 100.0
    assert metrics["click_rate"] >= 0.0
    assert metrics["click_rate"] <= 100.0

