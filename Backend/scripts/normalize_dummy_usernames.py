#!/usr/bin/env python3
"""
Normalize Dummy User Display Names

Converts "Voornaam Achternaam" format to username format like "voornaam" or "voornaam123"
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
import sys

# Path setup
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch, execute
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="normalize")
logger = get_logger()


def normalize_to_username(display_name: str) -> str:
    """
    Convert "Voornaam Achternaam" to username format.
    Examples:
    - "Ahmet Yılmaz" -> "ahmet"
    - "Mehmet Ali Demir" -> "mehmetali"
    - "Ayşe" -> "ayse"
    """
    if not display_name:
        return ""
    
    # Split by spaces
    parts = display_name.strip().split()
    
    if len(parts) == 0:
        return ""
    
    # Take first part (voornaam) and lowercase
    username = parts[0].lower()
    
    # Remove Turkish characters and convert to ASCII-friendly
    # This is a simple approach - you might want more sophisticated transliteration
    replacements = {
        'ı': 'i', 'İ': 'i', 'ş': 's', 'Ş': 's',
        'ğ': 'g', 'Ğ': 'g', 'ü': 'u', 'Ü': 'u',
        'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'
    }
    
    for old, new in replacements.items():
        username = username.replace(old, new)
    
    # Remove any non-alphanumeric characters
    username = re.sub(r'[^a-z0-9]', '', username)
    
    # If username is too short, add a number
    if len(username) < 3:
        username = username + "123"
    
    return username


async def normalize_all_dummy_users() -> None:
    """Normalize all user display_names that look like full names."""
    logger.info("normalizing_dummy_usernames")
    
    # Get all users with display_name that contains a space (likely "Voornaam Achternaam")
    users_sql = """
        SELECT id, display_name
        FROM user_profiles
        WHERE display_name IS NOT NULL
          AND display_name != ''
          AND display_name LIKE '% %'
          AND display_name !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    """
    users = await fetch(users_sql)
    
    if not users:
        logger.info("no_users_to_normalize")
        return
    
    logger.info("found_users_to_normalize", count=len(users))
    
    updated = 0
    skipped = 0
    
    for user in users:
        old_name = user["display_name"]
        new_name = normalize_to_username(old_name)
        
        # Skip if normalization resulted in empty string
        if not new_name:
            logger.warning("normalization_resulted_in_empty", user_id=str(user["id"]), old=old_name)
            skipped += 1
            continue
        
        # Check if username already exists
        check_sql = """
            SELECT id FROM user_profiles
            WHERE LOWER(TRIM(display_name)) = LOWER(TRIM($1))
              AND id != $2::uuid
        """
        existing = await fetch(check_sql, new_name, user["id"])
        
        if existing:
            # Add number suffix if username exists
            counter = 1
            candidate_name = f"{new_name}{counter}"
            existing = await fetch(check_sql, candidate_name, user["id"])
            
            while existing:
                counter += 1
                candidate_name = f"{new_name}{counter}"
                existing = await fetch(check_sql, candidate_name, user["id"])
            
            new_name = candidate_name
        
        # Update display_name
        update_sql = """
            UPDATE user_profiles
            SET display_name = $1, updated_at = NOW()
            WHERE id = $2::uuid
        """
        await execute(update_sql, new_name, user["id"])
        
        logger.info("normalized_username", 
                   user_id=str(user["id"]), 
                   old=old_name, 
                   new=new_name)
        updated += 1
    
    logger.info("normalization_completed", updated=updated, skipped=skipped)


async def main() -> None:
    """Main function."""
    await init_db_pool()
    logger.info("normalize_script_started")
    
    await normalize_all_dummy_users()
    
    logger.info("normalize_script_completed")


if __name__ == "__main__":
    asyncio.run(main())

