#!/usr/bin/env python3
"""
Seed Leaderboard Data Script

Creates realistic leaderboard entries with proper context_data:
- soz_hafta: Links to actual notes with content
- mahalle_gururu: Links to locations with names
- diaspora_nabzı: Links to polls with questions
- sessiz_guç: No specific context needed
"""
from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Path setup
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch, execute
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="seed")
logger = get_logger()


async def seed_leaderboard_entries() -> None:
    """Seed leaderboard entries with realistic context data."""
    logger.info("seeding_leaderboard_entries")
    
    # Get current week bounds
    now = datetime.now(timezone.utc)
    days_since_monday = now.weekday()
    period_start = (now - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    period_end = now
    
    # Get existing users (with display_name set, not UUIDs)
    users_sql = """
        SELECT id, display_name
        FROM user_profiles
        WHERE display_name IS NOT NULL
          AND display_name != ''
          AND display_name !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        LIMIT 20
    """
    users = await fetch(users_sql)
    
    if not users:
        logger.warning("no_users_found_for_leaderboard")
        return
    
    logger.info("found_users", count=len(users))
    
    # Get locations for mahalle_gururu
    locations_sql = """
        SELECT id, name
        FROM locations
        WHERE state = 'VERIFIED'
        LIMIT 10
    """
    locations = await fetch(locations_sql)
    
    if not locations:
        logger.warning("no_locations_found")
    else:
        logger.info("found_locations", count=len(locations))
    
    # Get notes for soz_hafta - only notes from our users at VERIFIED locations
    # First try current period, if no results, use last 30 days
    user_ids = [u["id"] for u in users]
    
    notes_sql = """
        SELECT ln.id, ln.content, ln.location_id, ln.user_id, l.name as location_name
        FROM location_notes ln
        INNER JOIN locations l ON ln.location_id = l.id
        WHERE ln.user_id = ANY($1::uuid[])
          AND l.state = 'VERIFIED'
          AND ln.created_at >= $2
          AND ln.created_at <= $3
        ORDER BY ln.created_at DESC
        LIMIT 20
    """
    notes = await fetch(notes_sql, user_ids, period_start, period_end)
    
    # If no notes in current period, try last 30 days
    if not notes:
        fallback_start = period_end - timedelta(days=30)
        notes_sql_fallback = """
            SELECT ln.id, ln.content, ln.location_id, ln.user_id, l.name as location_name
            FROM location_notes ln
            INNER JOIN locations l ON ln.location_id = l.id
            WHERE ln.user_id = ANY($1::uuid[])
              AND l.state = 'VERIFIED'
              AND ln.created_at >= $2
              AND ln.created_at <= $3
            ORDER BY ln.created_at DESC
            LIMIT 20
        """
        notes = await fetch(notes_sql_fallback, user_ids, fallback_start, period_end)
    
    if not notes:
        logger.warning("no_notes_found")
    else:
        logger.info("found_notes", count=len(notes))
    
    # Get check-ins for mahalle_gururu - only VERIFIED locations
    # First try current period, if not enough results, use last 30 days
    check_ins_sql = """
        SELECT DISTINCT ci.location_id, l.name as location_name, ci.user_id, ci.created_at
        FROM check_ins ci
        INNER JOIN locations l ON ci.location_id = l.id
        WHERE ci.user_id = ANY($1::uuid[])
          AND l.state = 'VERIFIED'
          AND ci.created_at >= $2
          AND ci.created_at <= $3
        ORDER BY ci.created_at DESC
        LIMIT 20
    """
    check_ins = await fetch(check_ins_sql, user_ids, period_start, period_end)
    
    # If not enough check-ins in current period, try last 30 days
    if len(check_ins) < 5:
        fallback_start = period_end - timedelta(days=30)
        check_ins_sql_fallback = """
            SELECT DISTINCT ci.location_id, l.name as location_name, ci.user_id, ci.created_at
            FROM check_ins ci
            INNER JOIN locations l ON ci.location_id = l.id
            WHERE ci.user_id = ANY($1::uuid[])
              AND l.state = 'VERIFIED'
              AND ci.created_at >= $2
              AND ci.created_at <= $3
            ORDER BY ci.created_at DESC
            LIMIT 20
        """
        check_ins_fallback = await fetch(check_ins_sql_fallback, user_ids, fallback_start, period_end)
        if check_ins_fallback:
            check_ins = check_ins_fallback
    
    if not check_ins:
        logger.warning("no_check_ins_found")
    else:
        logger.info("found_check_ins", count=len(check_ins))
    
    # Get poll responses for diaspora_nabzı - only polls where users actually responded
    # First try current period, if not enough results, use last 30 days
    poll_responses_sql = """
        SELECT DISTINCT pr.poll_id, p.question, pr.user_id, pr.created_at
        FROM poll_responses pr
        INNER JOIN polls p ON pr.poll_id = p.id
        WHERE pr.user_id = ANY($1::uuid[])
          AND p.status = 'active'
          AND pr.created_at >= $2
          AND pr.created_at <= $3
        ORDER BY pr.created_at DESC
        LIMIT 20
    """
    poll_responses = await fetch(poll_responses_sql, user_ids, period_start, period_end)
    
    # If not enough poll responses in current period, try last 30 days
    if len(poll_responses) < 5:
        fallback_start = period_end - timedelta(days=30)
        poll_responses_sql_fallback = """
            SELECT DISTINCT pr.poll_id, p.question, pr.user_id, pr.created_at
            FROM poll_responses pr
            INNER JOIN polls p ON pr.poll_id = p.id
            WHERE pr.user_id = ANY($1::uuid[])
              AND p.status = 'active'
              AND pr.created_at >= $2
              AND pr.created_at <= $3
            ORDER BY pr.created_at DESC
            LIMIT 20
        """
        poll_responses_fallback = await fetch(poll_responses_sql_fallback, user_ids, fallback_start, period_end)
        if poll_responses_fallback:
            poll_responses = poll_responses_fallback
    
    if not poll_responses:
        logger.warning("no_poll_responses_found")
    else:
        logger.info("found_poll_responses", count=len(poll_responses))
    
    # Clear existing entries for this period to avoid duplicates
    clear_sql = """
        DELETE FROM leaderboard_entries
        WHERE period_start = $1 AND period_end = $2
    """
    await execute(clear_sql, period_start, period_end)
    logger.info("cleared_existing_entries_for_period")
    
    created = 0
    
    # Seed soz_hafta (best notes this week) - only use notes that belong to users
    if notes:
        # Group notes by user_id
        notes_by_user: dict = {}
        for note in notes:
            user_id = str(note["user_id"])
            if user_id not in notes_by_user:
                notes_by_user[user_id] = []
            notes_by_user[user_id].append(note)
        
        # Select top 5 users with most notes, then pick their best note
        user_note_counts = [(user_id, len(user_notes)) for user_id, user_notes in notes_by_user.items()]
        user_note_counts.sort(key=lambda x: x[1], reverse=True)
        top_users = user_note_counts[:5]
        
        for rank, (user_id, _) in enumerate(top_users, 1):
            user_notes = notes_by_user[user_id]
            # Pick the most recent note for this user
            note = user_notes[0]
            context_data = {
                "note_id": note["id"],
                "location_id": note.get("location_id")
            }
            
            insert_sql = """
                INSERT INTO leaderboard_entries 
                (user_id, category, city_key, period_start, period_end, score, rank, context_data)
                VALUES ($1, 'soz_hafta', NULL, $2, $3, $4, $5, $6::jsonb)
            """
            await execute(
                insert_sql,
                user_id,
                period_start,
                period_end,
                100 - rank * 10,  # Score decreases with rank
                rank,
                json.dumps(context_data, ensure_ascii=False)
            )
            created += 1
        
        logger.info("soz_hafta_entries_created", count=len(top_users))
    
    # Seed mahalle_gururu (local active) - only VERIFIED locations where users checked in
    if check_ins:
        # Group check-ins by user_id
        check_ins_by_user: dict = {}
        for ci in check_ins:
            user_id = str(ci["user_id"])
            if user_id not in check_ins_by_user:
                check_ins_by_user[user_id] = []
            check_ins_by_user[user_id].append(ci)
        
        # Select top 5 users with most check-ins
        user_check_in_counts = [(user_id, len(user_check_ins)) for user_id, user_check_ins in check_ins_by_user.items()]
        user_check_in_counts.sort(key=lambda x: x[1], reverse=True)
        top_users = user_check_in_counts[:5]
        
        for rank, (user_id, _) in enumerate(top_users, 1):
            user_check_ins = check_ins_by_user[user_id]
            # Pick the most recent check-in location for this user
            check_in = user_check_ins[0]
            context_data = {
                "location_id": check_in["location_id"]
            }
            
            insert_sql = """
                INSERT INTO leaderboard_entries 
                (user_id, category, city_key, period_start, period_end, score, rank, context_data)
                VALUES ($1, 'mahalle_gururu', NULL, $2, $3, $4, $5, $6::jsonb)
            """
            await execute(
                insert_sql,
                user_id,
                period_start,
                period_end,
                100 - rank * 10,
                rank,
                json.dumps(context_data, ensure_ascii=False)
            )
            created += 1
        
        logger.info("mahalle_gururu_entries_created", count=len(top_users))
    
    # Seed diaspora_nabzı (poll contribution) - only polls where users actually responded
    if poll_responses:
        # Group poll responses by user_id
        polls_by_user: dict = {}
        for pr in poll_responses:
            user_id = str(pr["user_id"])
            if user_id not in polls_by_user:
                polls_by_user[user_id] = []
            polls_by_user[user_id].append(pr)
        
        logger.info("polls_by_user_debug", 
                   total_responses=len(poll_responses),
                   unique_users=len(polls_by_user),
                   user_counts={user_id: len(polls) for user_id, polls in polls_by_user.items()})
        
        # Select top 5 users with most poll responses
        user_poll_counts = [(user_id, len(user_polls)) for user_id, user_polls in polls_by_user.items()]
        user_poll_counts.sort(key=lambda x: x[1], reverse=True)
        top_users = user_poll_counts[:5]
        
        logger.info("top_users_for_diaspora_nabzı", users=top_users)
        
        for rank, (user_id, _) in enumerate(top_users, 1):
            user_polls = polls_by_user[user_id]
            # Pick the most recent poll response for this user
            poll_response = user_polls[0]
            context_data = {
                "poll_id": poll_response["poll_id"]
            }
            
            insert_sql = """
                INSERT INTO leaderboard_entries 
                (user_id, category, city_key, period_start, period_end, score, rank, context_data)
                VALUES ($1, 'diaspora_nabzı', NULL, $2, $3, $4, $5, $6::jsonb)
            """
            await execute(
                insert_sql,
                user_id,
                period_start,
                period_end,
                100 - rank * 10,
                rank,
                json.dumps(context_data, ensure_ascii=False)
            )
            created += 1
        
        logger.info("diaspora_nabzı_entries_created", count=len(top_users))
    
    # Seed sessiz_guç (silent power - no specific context needed)
    # Use users that are NOT already in other categories to avoid duplicates
    if len(users) >= 5:
        # Get users already in other categories
        existing_users_sql = """
            SELECT DISTINCT user_id
            FROM leaderboard_entries
            WHERE period_start = $1 AND period_end = $2
              AND category IN ('soz_hafta', 'mahalle_gururu', 'diaspora_nabzı')
        """
        existing_users_rows = await fetch(existing_users_sql, period_start, period_end)
        existing_user_ids = {str(row["user_id"]) for row in existing_users_rows}
        
        # Filter out users already in other categories
        available_users = [u for u in users if str(u["id"]) not in existing_user_ids]
        
        # If not enough users, use all users
        if len(available_users) < 5:
            available_users = users
        
        selected_users = random.sample(available_users, min(5, len(available_users)))
        for rank, user in enumerate(selected_users, 1):
            insert_sql = """
                INSERT INTO leaderboard_entries 
                (user_id, category, city_key, period_start, period_end, score, rank, context_data)
                VALUES ($1, 'sessiz_guç', NULL, $2, $3, $4, $5, NULL)
            """
            await execute(
                insert_sql,
                user["id"],
                period_start,
                period_end,
                100 - rank * 10,
                rank
            )
            created += 1
        
        logger.info("sessiz_guç_entries_created", count=len(selected_users))
    
    logger.info("leaderboard_entries_created", total=created)


async def main() -> None:
    """Main seed function."""
    await init_db_pool()
    logger.info("seed_leaderboard_script_started")
    
    await seed_leaderboard_entries()
    
    logger.info("seed_leaderboard_script_completed")


if __name__ == "__main__":
    asyncio.run(main())

