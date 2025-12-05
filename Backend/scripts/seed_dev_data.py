#!/usr/bin/env python3
"""
Seed Development Data Script

Creates test data for development:
- Test users (via Supabase Auth - manual creation required)
- Test cities and locations
- Random check-ins, reactions, notes, poll responses
- Sample polls with options
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
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


async def seed_cities_and_locations() -> None:
    """Seed cities and locations if they don't exist."""
    logger.info("seeding_cities_and_locations")
    
    # Get existing locations count
    count_sql = "SELECT COUNT(*) as count FROM locations WHERE state = 'VERIFIED'"
    rows = await fetch(count_sql)
    existing_count = rows[0].get("count", 0) if rows else 0
    
    if existing_count > 0:
        logger.info("locations_already_exist", count=existing_count)
        return
    
    # Get some verified locations to use
    locations_sql = """
        SELECT id, name, city_key, category_key, lat, lng
        FROM locations
        WHERE state = 'VERIFIED'
        LIMIT 50
    """
    locations = await fetch(locations_sql)
    
    if not locations:
        logger.warning("no_verified_locations_found")
        return
    
    logger.info("found_locations", count=len(locations))
    return locations


async def seed_check_ins(locations: list, num_check_ins: int = 100) -> None:
    """Seed random check-ins."""
    logger.info("seeding_check_ins", count=num_check_ins)
    
    # Generate random client_ids
    import uuid
    client_ids = [str(uuid.uuid4()) for _ in range(20)]
    
    created = 0
    for _ in range(num_check_ins):
        location = random.choice(locations)
        client_id = random.choice(client_ids)
        days_ago = random.randint(0, 30)
        created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        try:
            sql = """
                INSERT INTO check_ins (location_id, client_id, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
            """
            await execute(sql, location["id"], client_id, created_at)
            created += 1
        except Exception as e:
            logger.warning("failed_to_create_check_in", error=str(e))
    
    logger.info("check_ins_created", count=created)


async def seed_reactions(locations: list, num_reactions: int = 150) -> None:
    """Seed random reactions."""
    logger.info("seeding_reactions", count=num_reactions)
    
    import uuid
    client_ids = [str(uuid.uuid4()) for _ in range(20)]
    reaction_types = ['fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag']
    
    created = 0
    for _ in range(num_reactions):
        location = random.choice(locations)
        client_id = random.choice(client_ids)
        reaction_type = random.choice(reaction_types)
        days_ago = random.randint(0, 30)
        created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        try:
            sql = """
                INSERT INTO location_reactions (location_id, client_id, reaction_type, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT DO NOTHING
            """
            await execute(sql, location["id"], client_id, reaction_type, created_at)
            created += 1
        except Exception as e:
            logger.warning("failed_to_create_reaction", error=str(e))
    
    logger.info("reactions_created", count=created)


async def seed_notes(locations: list, num_notes: int = 50) -> None:
    """Seed random notes."""
    logger.info("seeding_notes", count=num_notes)
    
    import uuid
    client_ids = [str(uuid.uuid4()) for _ in range(15)]
    note_templates = [
        "Geweldige plek! Zeer aan te raden.",
        "Lekker eten, vriendelijke service.",
        "Mooie sfeer, kom hier regelmatig.",
        "Goede prijs-kwaliteit verhouding.",
        "Authentiek Turks eten.",
    ]
    
    created = 0
    for _ in range(num_notes):
        location = random.choice(locations)
        client_id = random.choice(client_ids)
        content = random.choice(note_templates)
        days_ago = random.randint(0, 30)
        created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        try:
            sql = """
                INSERT INTO location_notes (location_id, client_id, content, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $4)
            """
            await execute(sql, location["id"], client_id, content, created_at)
            created += 1
        except Exception as e:
            logger.warning("failed_to_create_note", error=str(e))
    
    logger.info("notes_created", count=created)


async def seed_polls() -> None:
    """Seed sample polls."""
    logger.info("seeding_polls")
    
    # Create a sample poll
    poll_sql = """
        INSERT INTO polls (title, question, poll_type, status, starts_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """
    
    poll_rows = await fetch(
        poll_sql,
        "Diaspora Poll",
        "Wat is jouw favoriete Turkse gerecht?",
        "single_choice",
        "active",
        datetime.now() - timedelta(days=1),
    )
    
    if not poll_rows:
        logger.warning("failed_to_create_poll")
        return
    
    poll_id = poll_rows[0]["id"]
    
    # Add options
    options = [
        "Baklava",
        "Döner",
        "Lahmacun",
        "Kebab",
        "Anders",
    ]
    
    for i, option_text in enumerate(options):
        option_sql = """
            INSERT INTO poll_options (poll_id, option_text, display_order)
            VALUES ($1, $2, $3)
        """
        await execute(option_sql, poll_id, option_text, i + 1)
    
    logger.info("poll_created", poll_id=poll_id, options=len(options))


async def seed_poll_responses(poll_id: int, num_responses: int = 30) -> None:
    """Seed poll responses."""
    logger.info("seeding_poll_responses", poll_id=poll_id, count=num_responses)
    
    # Get poll options
    options_sql = "SELECT id FROM poll_options WHERE poll_id = $1 ORDER BY display_order"
    option_rows = await fetch(options_sql, poll_id)
    option_ids = [row["id"] for row in option_rows]
    
    if not option_ids:
        logger.warning("no_poll_options_found")
        return
    
    import uuid
    client_ids = [str(uuid.uuid4()) for _ in range(20)]
    
    created = 0
    for _ in range(num_responses):
        client_id = random.choice(client_ids)
        option_id = random.choice(option_ids)
        days_ago = random.randint(0, 1)
        created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        try:
            # Check if response already exists (using identity_key which is auto-filled by trigger)
            # identity_key = COALESCE(user_id::text, client_id::text), so for client_id it's client_id::text
            check_sql = """
                SELECT 1 FROM poll_responses
                WHERE poll_id = $1 AND identity_key = $2
                LIMIT 1
            """
            existing = await fetch(check_sql, poll_id, client_id)
            if existing:
                continue  # Skip if already exists
            
            sql = """
                INSERT INTO poll_responses (poll_id, option_id, client_id, created_at)
                VALUES ($1, $2, $3, $4)
            """
            await execute(sql, poll_id, option_id, client_id, created_at)
            created += 1
        except Exception as e:
            logger.warning("failed_to_create_poll_response", error=str(e))
    
    logger.info("poll_responses_created", count=created)


async def main() -> None:
    """Main seed function."""
    await init_db_pool()
    logger.info("seed_script_started")
    
    # Seed cities and get locations
    locations = await seed_cities_and_locations()
    
    if not locations:
        logger.warning("no_locations_available_for_seeding")
        return
    
    # Seed activity data
    await seed_check_ins(locations, num_check_ins=100)
    await seed_reactions(locations, num_reactions=150)
    await seed_notes(locations, num_notes=50)
    
    # Seed polls
    await seed_polls()
    
    # Get poll ID for responses
    poll_sql = "SELECT id FROM polls WHERE status = 'active' LIMIT 1"
    poll_rows = await fetch(poll_sql)
    if poll_rows:
        poll_id = poll_rows[0]["id"]
        await seed_poll_responses(poll_id, num_responses=30)
    
    logger.info("seed_script_completed")


if __name__ == "__main__":
    asyncio.run(main())

