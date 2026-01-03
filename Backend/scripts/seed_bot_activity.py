#!/usr/bin/env python3
"""
Bot Activity Seeding Script

Genereert realistische historische activiteit voor bot accounts:
- Check-ins (2-4 weken terug, sommige bots ouder)
- Location notes (verschillende lengtes per persona)
- Location reactions (emoji)
- Favorites
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import List, Dict, Any

# Path setup
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetch, execute
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="bot_seed")
logger = get_logger()


# Bot user IDs (hardcoded voor consistentie)
BOT_USERS = {
    "ea8590da-4fbf-482c-9d32-e26a4eaf4e39": "Ayşe Şahin",
    "605ea1f1-acab-4470-a0f5-3e2e45fe4c5e": "Mustafa Yılmaz",
    "15c969a2-21d2-44aa-b93b-e98f4c2c121b": "Ahmet Kaya",
    "f932471e-6560-4f87-9a71-49a8e1cb6d39": "Ali Öztürk",
    "b2e7c1a0-3125-4755-968d-aeb6b866b9d8": "Can Korkmaz",
    "c7374d23-aefe-4d57-828c-80dac01aa952": "Zeynep Demir",
    "fd34e2b4-707d-499c-9adf-1a548d47ee0e": "Emre Aslan",
    "56f035c3-3767-4b75-af30-f4dfae1f6c69": "Fatma Çelik",
}

# Bot persona definities
BOT_PERSONAS = {
    "Ahmet Kaya": {
        "type": "actieve_ondernemer",
        "note_style": "longer",  # 50-200 chars
        "note_probability": 0.6,
        "reaction_probability": 0.3,
        "check_in_probability": 0.7,
        "favorite_probability": 0.4,
        "days_back_min": 0,
        "days_back_max": 30,
    },
    "Zeynep Demir": {
        "type": "nieuwsgierige_local",
        "note_style": "short",  # 10-50 chars
        "note_probability": 0.3,
        "reaction_probability": 0.7,
        "check_in_probability": 0.8,
        "favorite_probability": 0.2,
        "days_back_min": 0,
        "days_back_max": 18,
    },
    "Mustafa Yılmaz": {
        "type": "community_figuur",
        "note_style": "medium",  # 30-100 chars
        "note_probability": 0.5,
        "reaction_probability": 0.2,
        "check_in_probability": 0.4,
        "favorite_probability": 0.3,
        "days_back_min": 0,
        "days_back_max": 40,
    },
    "Emre Aslan": {
        "type": "ontdekker",
        "note_style": "short",  # 10-60 chars
        "note_probability": 0.5,
        "reaction_probability": 0.3,
        "check_in_probability": 0.9,
        "favorite_probability": 0.1,
        "days_back_min": 0,
        "days_back_max": 12,
    },
    "Fatma Çelik": {
        "type": "enthousiaste_gebruiker",
        "note_style": "very_short",  # 5-30 chars
        "note_probability": 0.2,
        "reaction_probability": 0.8,
        "check_in_probability": 0.6,
        "favorite_probability": 0.3,
        "days_back_min": 0,
        "days_back_max": 10,
    },
    "Ali Öztürk": {
        "type": "stille_volger",
        "note_style": "short",  # 10-40 chars
        "note_probability": 0.1,
        "reaction_probability": 0.1,
        "check_in_probability": 0.2,
        "favorite_probability": 0.1,
        "days_back_min": 0,
        "days_back_max": 25,
    },
    "Ayşe Şahin": {
        "type": "historische_gebruiker",
        "note_style": "medium",  # 30-80 chars
        "note_probability": 0.3,
        "reaction_probability": 0.2,
        "check_in_probability": 0.3,
        "favorite_probability": 0.2,
        "days_back_min": 21,  # Oudere activiteit
        "days_back_max": 60,
    },
    "Can Korkmaz": {
        "type": "kritische_denker",
        "note_style": "medium",  # 30-100 chars
        "note_probability": 0.4,
        "reaction_probability": 0.3,
        "check_in_probability": 0.5,
        "favorite_probability": 0.2,
        "days_back_min": 0,
        "days_back_max": 20,
    },
}

# Note templates per persona type
NOTE_TEMPLATES = {
    "actieve_ondernemer": [
        "Vandaag langs geweest bij deze nieuwe bakker. Goede kwaliteit en vriendelijke service.",
        "Interessante plek voor de gemeenschap. Zeker een aanrader.",
        "Goede prijs-kwaliteit verhouding hier. Kom hier regelmatig.",
        "Authentiek Turks eten, precies zoals ik het verwachtte.",
        "Mooie sfeer en goede service. Zal hier vaker komen.",
        "Nieuwe plek ontdekt tijdens het winkelen. Zeer tevreden.",
        "Goede locatie voor de Turkse gemeenschap in Rotterdam.",
    ],
    "nieuwsgierige_local": [
        "Hier wil ik ook eens langs!",
        "Is dit ook open in het weekend?",
        "Thanks voor de tip 👍",
        "Ziet er goed uit!",
        "Moet ik proberen.",
        "Interessant, waar staat dit?",
    ],
    "community_figuur": [
        "Interessant, maar verschilt dit niet per wijk?",
        "Goede ontwikkeling voor de gemeenschap.",
        "Dit soort initiatieven hebben we nodig.",
        "Ben benieuwd hoe dit zich ontwikkelt.",
        "Belangrijk voor de lokale Turkse gemeenschap.",
    ],
    "ontdekker": [
        "Toevallig ontdekt tijdens het wandelen. Ziet er goed uit.",
        "Nieuwe plek gevonden!",
        "Kwam deze tegen, moet ik proberen.",
        "Leuke vondst.",
        "Onbekende plek ontdekt.",
    ],
    "enthousiaste_gebruiker": [
        "😍",
        "Leuk!",
        "🔥🔥",
        "Super!",
        "❤️",
        "Geweldig!",
    ],
    "stille_volger": [
        "Goed om te weten.",
        "Dank voor het delen.",
        "Interessant.",
        "Oké.",
    ],
    "historische_gebruiker": [
        "Al jaren vaste klant hier.",
        "Goede plek, al lang bekend.",
        "Klassieker in de buurt.",
        "Kom hier al jaren.",
    ],
    "kritische_denker": [
        "Is dit niet al langer bekend?",
        "Ben benieuwd hoe dit zich ontwikkelt.",
        "Interessant perspectief.",
        "Vraag me af of dit blijft bestaan.",
    ],
}

REACTION_TYPES = ['fire', 'heart', 'thumbs_up', 'smile', 'star', 'flag']


async def get_bot_users() -> List[Dict[str, Any]]:
    """Haal bot users op of gebruik hardcoded IDs."""
    # Probeer eerst uit database te halen
    sql = """
        SELECT 
            id,
            display_name
        FROM public.user_profiles
        WHERE is_bot = true
        ORDER BY created_at
    """
    rows = await fetch(sql)
    
    if rows:
        return [dict(r) for r in rows]
    
    # Fallback: gebruik hardcoded IDs
    logger.info("using_hardcoded_bot_ids")
    return [
        {"id": bot_id, "display_name": name}
        for bot_id, name in BOT_USERS.items()
    ]


async def get_verified_locations(limit: int = 100) -> List[Dict[str, Any]]:
    """Haal verified locations op."""
    sql = """
        SELECT id, name, lat, lng, category
        FROM locations
        WHERE state = 'VERIFIED'
          AND lat IS NOT NULL
          AND lng IS NOT NULL
          AND (is_retired = false OR is_retired IS NULL)
        ORDER BY RANDOM()
        LIMIT $1
    """
    rows = await fetch(sql, limit)
    return [dict(r) for r in rows]


def generate_note_content(persona_name: str) -> str:
    """Genereer note content gebaseerd op persona."""
    persona = BOT_PERSONAS.get(persona_name, {})
    persona_type = persona.get("type", "nieuwsgierige_local")
    style = persona.get("note_style", "short")
    
    templates = NOTE_TEMPLATES.get(persona_type, ["Goede plek."])
    base_content = random.choice(templates)
    
    # Pas lengte aan op basis van style
    if style == "very_short" and len(base_content) > 30:
        base_content = base_content[:30]
    elif style == "short" and len(base_content) > 50:
        base_content = base_content[:50]
    elif style == "medium" and len(base_content) < 30:
        base_content = base_content + " " + "Goede service en vriendelijk personeel."
    elif style == "longer" and len(base_content) < 50:
        base_content = base_content + " " + "De sfeer is goed en de prijzen zijn redelijk. Zeker een aanrader voor anderen."
    
    # Zorg dat het tussen 3 en 1000 chars is
    if len(base_content) < 3:
        base_content = "Goed."
    if len(base_content) > 1000:
        base_content = base_content[:1000]
    
    return base_content


def random_timestamp(days_back_min: int = 0, days_back_max: int = 30) -> datetime:
    """Genereer random timestamp in het verleden."""
    days_ago = random.randint(days_back_min, days_back_max)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)
    return datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)


async def seed_bot_check_ins(bot_users: List[Dict], locations: List[Dict]) -> int:
    """Seed check-ins voor bots."""
    logger.info("seeding_bot_check_ins", bot_count=len(bot_users), location_count=len(locations))
    
    created = 0
    for bot in bot_users:
        persona = BOT_PERSONAS.get(bot["display_name"], {})
        check_in_prob = persona.get("check_in_probability", 0.5)
        days_back_min = persona.get("days_back_min", 0)
        days_back_max = persona.get("days_back_max", 30)
        
        # Aantal check-ins per bot (5-15)
        num_check_ins = random.randint(5, 15) if random.random() < check_in_prob else random.randint(1, 5)
        
        selected_locations = random.sample(locations, min(num_check_ins, len(locations)))
        
        for location in selected_locations:
            created_at = random_timestamp(days_back_min, days_back_max)
            
            try:
                sql = """
                    INSERT INTO check_ins (location_id, user_id, created_at)
                    VALUES ($1, $2::uuid, $3)
                    ON CONFLICT DO NOTHING
                """
                await execute(sql, location["id"], bot["id"], created_at)
                created += 1
            except Exception as e:
                logger.warning("failed_check_in", error=str(e), bot=bot["display_name"], location_id=location["id"])
    
    logger.info("check_ins_created", count=created)
    return created


async def seed_bot_notes(bot_users: List[Dict], locations: List[Dict]) -> int:
    """Seed location notes voor bots."""
    logger.info("seeding_bot_notes")
    
    created = 0
    for bot in bot_users:
        persona = BOT_PERSONAS.get(bot["display_name"], {})
        note_prob = persona.get("note_probability", 0.3)
        days_back_min = persona.get("days_back_min", 0)
        days_back_max = persona.get("days_back_max", 30)
        
        if random.random() > note_prob:
            continue
        
        # Aantal notes per bot (2-8)
        num_notes = random.randint(2, 8)
        selected_locations = random.sample(locations, min(num_notes, len(locations)))
        
        for location in selected_locations:
            content = generate_note_content(bot["display_name"])
            created_at = random_timestamp(days_back_min, days_back_max)
            
            try:
                sql = """
                    INSERT INTO location_notes (location_id, user_id, content, created_at, updated_at)
                    VALUES ($1, $2::uuid, $3, $4, $4)
                """
                await execute(sql, location["id"], bot["id"], content, created_at)
                created += 1
            except Exception as e:
                logger.warning("failed_note", error=str(e), bot=bot["display_name"], location_id=location["id"])
    
    logger.info("notes_created", count=created)
    return created


async def seed_bot_reactions(bot_users: List[Dict], locations: List[Dict]) -> int:
    """Seed location reactions voor bots."""
    logger.info("seeding_bot_reactions")
    
    created = 0
    for bot in bot_users:
        persona = BOT_PERSONAS.get(bot["display_name"], {})
        reaction_prob = persona.get("reaction_probability", 0.3)
        days_back_min = persona.get("days_back_min", 0)
        days_back_max = persona.get("days_back_max", 30)
        
        if random.random() > reaction_prob:
            continue
        
        # Aantal reactions per bot (3-12)
        num_reactions = random.randint(3, 12)
        selected_locations = random.sample(locations, min(num_reactions, len(locations)))
        
        for location in selected_locations:
            reaction_type = random.choice(REACTION_TYPES)
            created_at = random_timestamp(days_back_min, days_back_max)
            
            try:
                sql = """
                    INSERT INTO location_reactions (location_id, user_id, reaction_type, created_at)
                    VALUES ($1, $2::uuid, $3, $4)
                    ON CONFLICT DO NOTHING
                """
                await execute(sql, location["id"], bot["id"], reaction_type, created_at)
                created += 1
            except Exception as e:
                logger.warning("failed_reaction", error=str(e), bot=bot["display_name"], location_id=location["id"])
    
    logger.info("reactions_created", count=created)
    return created


async def seed_bot_favorites(bot_users: List[Dict], locations: List[Dict]) -> int:
    """Seed favorites voor bots."""
    logger.info("seeding_bot_favorites")
    
    created = 0
    for bot in bot_users:
        persona = BOT_PERSONAS.get(bot["display_name"], {})
        favorite_prob = persona.get("favorite_probability", 0.2)
        days_back_min = persona.get("days_back_min", 0)
        days_back_max = persona.get("days_back_max", 30)
        
        if random.random() > favorite_prob:
            continue
        
        # Aantal favorites per bot (1-5)
        num_favorites = random.randint(1, 5)
        selected_locations = random.sample(locations, min(num_favorites, len(locations)))
        
        for location in selected_locations:
            created_at = random_timestamp(days_back_min, days_back_max)
            
            try:
                sql = """
                    INSERT INTO favorites (location_id, user_id, created_at)
                    VALUES ($1, $2::uuid, $3)
                    ON CONFLICT DO NOTHING
                """
                await execute(sql, location["id"], bot["id"], created_at)
                created += 1
            except Exception as e:
                logger.warning("failed_favorite", error=str(e), bot=bot["display_name"], location_id=location["id"])
    
    logger.info("favorites_created", count=created)
    return created


async def main() -> None:
    """Main seeding function."""
    await init_db_pool()
    logger.info("bot_seed_script_started")
    
    # Haal bot users op
    bot_users = await get_bot_users()
    if not bot_users:
        logger.error("no_bot_users_found")
        return
    
    logger.info("found_bot_users", count=len(bot_users), users=[b["display_name"] for b in bot_users])
    
    # Haal verified locations op
    locations = await get_verified_locations(limit=100)
    if not locations:
        logger.error("no_verified_locations_found")
        return
    
    logger.info("found_locations", count=len(locations))
    
    # Seed activity data
    check_ins = await seed_bot_check_ins(bot_users, locations)
    notes = await seed_bot_notes(bot_users, locations)
    reactions = await seed_bot_reactions(bot_users, locations)
    favorites = await seed_bot_favorites(bot_users, locations)
    
    logger.info("bot_seed_completed", 
                check_ins=check_ins,
                notes=notes,
                reactions=reactions,
                favorites=favorites)
    
    print(f"\n✅ Bot seeding voltooid!")
    print(f"   - Check-ins: {check_ins}")
    print(f"   - Notes: {notes}")
    print(f"   - Reactions: {reactions}")
    print(f"   - Favorites: {favorites}")


if __name__ == "__main__":
    asyncio.run(main())







