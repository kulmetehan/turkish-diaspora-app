# -*- coding: utf-8 -*-
"""
PollGeneratorBot — AI-powered daily poll generation

Generates a new poll each day using OpenAI to create relevant questions
for the Turkish diaspora community in the Netherlands.

Pad: Backend/app/workers/poll_generator_bot.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

# --- Uniform logging ---
from app.core.logging import configure_logging, get_logger
from app.core.request_id import with_run_id

configure_logging(service_name="worker")
logger = get_logger()
logger = logger.bind(worker="poll_generator_bot")

# ---------------------------------------------------------------------------
# Pathing zodat 'app.*' werkt (CI, GH Actions, lokale run)
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend

# ---------------------------------------------------------------------------
# DB (asyncpg helpers)
# ---------------------------------------------------------------------------
from services.db_service import init_db_pool, fetch, execute

# ---------------------------------------------------------------------------
# OpenAI Service
# ---------------------------------------------------------------------------
from services.openai_service import OpenAIService

# ---------------------------------------------------------------------------
# Push Notifications Service
# ---------------------------------------------------------------------------
from services.push_service import get_push_service

# System UUID for business actor_type (admin/system-generated content)
SYSTEM_UUID = UUID("00000000-0000-0000-0000-000000000000")


class PollOptionModel(BaseModel):
    """Single poll option."""
    option_text: str = Field(..., description="The text of the poll option")
    display_order: int = Field(..., description="Display order (1-based)")


class PollGenerationResult(BaseModel):
    """AI-generated poll structure."""
    title: str = Field(..., description="Short title for the poll")
    question: str = Field(..., description="The poll question")
    options: List[PollOptionModel] = Field(..., min_length=2, max_length=5, description="Poll options (2-5 options)")


async def get_recent_polls(days: int = 30, limit: int = 15) -> List[Dict[str, Any]]:
    """Get recent polls to avoid duplicates."""
    sql = """
        SELECT title, question, created_at
        FROM polls
        WHERE created_at >= now() - INTERVAL '%s days'
        ORDER BY created_at DESC
        LIMIT $1
    """ % days
    
    rows = await fetch(sql, limit)
    return rows if rows else []


def get_topic_rotation_index() -> int:
    """Get rotation index based on day of year to ensure variety."""
    day_of_year = datetime.now().timetuple().tm_yday
    return day_of_year % 10  # Rotate through 10 different topic groups


def get_topic_group_by_index(index: int) -> Dict[str, str]:
    """Get topic group details by rotation index."""
    topic_groups = [
        {
            "name": "Media & Entertainment",
            "topics": """MEDIA & ENTERTAINMENT:
- Welke streamingdienst gebruiken ze het meest? (Netflix, Disney+, BluTV, PuhuTV, etc.)
- Welke muziek luisteren ze? (Turkse pop, Nederlandse pop, Arabesque, Klasik, etc.)
- Welke social media gebruiken ze het meest? (Instagram, TikTok, Facebook, Twitter/X, etc.)
- Hoe volgen ze nieuws? (Turkse nieuwsapps, Nederlandse media, sociale media, websites)
- Welke Turkse zender kijken ze het meest? (TRT, Show TV, ATV, Star TV, etc.)
- Welke Nederlandse zender kijken ze het meest? (RTL, NPO, SBS6, etc.)
- Wat is hun favoriete Turkse serie?
- Wat is hun favoriete Nederlandse serie/programma?"""
        },
        {
            "name": "Religie & Spiritualiteit",
            "topics": """RELIGIE & SPIRITUALITEIT:
- Hoe vaak bezoeken ze de moskee? (Dagelijks, wekelijks, alleen feesten, nooit)
- Welke religieuze feesten vieren ze het meest? (Ramadan, Kurban Bayramı, Mevlid, etc.)
- Hoe belangrijk is religie in hun dagelijks leven? (Zeer belangrijk, Belangrijk, Neutraal, etc.)
- Welke religieuze organisaties kennen ze? (Diyanet, Milli Görüş, etc.)
- Hoe vieren ze religieuze feesten? (Thuis, moskee, familie bijeenkomsten)
- Wat is hun houding ten opzichte van religieuze praktijken?"""
        },
        {
            "name": "Cultuur & Traditie",
            "topics": """CULTUUR & TRADITIE:
- Welke Turkse feesten vieren ze? (Bayram, Hıdrellez, Nevruz, etc.)
- Hoe behouden ze Turkse tradities? (Keuken, muziek, dans, taal)
- Welke culturele evenementen bezoeken ze? (Festivals, concerten, culturele avonden)
- Hoe belangrijk is de Turkse keuken voor ze? (Zeer belangrijk, soms, niet belangrijk)
- Welke culturele activiteiten doen ze met familie?
- Hoe vieren ze belangrijke levensgebeurtenissen? (Trouwen, geboorte, etc.)"""
        },
        {
            "name": "Integratie & Sociale Netwerken",
            "topics": """INTEGRATIE & SOCIALE NETWERKEN:
- Met wie brengen ze het meeste tijd door? (Turkse vrienden, Nederlandse vrienden, familie, gemengd)
- In welke taal denken ze? (Turks, Nederlands, beide, Engels)
- Hoe voelen ze zich over hun identiteit? (Meer Turks, meer Nederlands, beide, anders)
- Waar voelen ze zich het meest thuis? (Nederland, Turkije, beide, nergens)
- In welke taal communiceren ze thuis? (Turks, Nederlands, beide)
- Hoe belangrijk zijn Nederlandse vriendschappen voor ze?
- Hoe belangrijk zijn Turkse vriendschappen voor ze?"""
        },
        {
            "name": "Consumptie & Winkelen",
            "topics": """CONSUMPTIE & WINKELEN:
- Waar kopen ze kleding? (Turkse winkels, Nederlandse ketens, online, markten)
- Welke merken prefereren ze? (Turkse merken, Nederlandse merken, internationale merken)
- Hoe belangrijk is prijs vs kwaliteit? (Prijs belangrijkst, kwaliteit belangrijkst, balans)
- Waar kopen ze specifieke producten? (Turkse producten: Turkse winkels, Nederlandse supermarkten, online)
- Waar kopen ze het meest? (Turkse winkels, Nederlandse supermarkten, online, markten)
- Hoe vaak shoppen ze online?
- Welke betaalmethoden gebruiken ze het meest?"""
        },
        {
            "name": "Onderwijs & Opleiding",
            "topics": """ONDERWIJS & OPLEIDING:
- Welke taal spreken ze thuis met kinderen? (Turks, Nederlands, beide)
- Welke schoolkeuze maken ze voor kinderen? (Nederlandse school, Turkse school, beide)
- Hoe belangrijk is Turks taalonderwijs? (Zeer belangrijk, belangrijk, niet belangrijk)
- Welke opleiding hebben ze gevolgd? (VMBO, HAVO, VWO, MBO, HBO, Universiteit)
- Hoe belangrijk is onderwijs voor hun kinderen?
- Welke vakken vinden ze belangrijk voor hun kinderen?
- Hoe betrokken zijn ze bij schoolactiviteiten?"""
        },
        {
            "name": "Werk & Ondernemerschap",
            "topics": """WERK & ONDERNEMERSCHAP:
- In welke sectoren werken ze? (Horeca, detailhandel, zorg, onderwijs, techniek, etc.)
- Hoe belangrijk is ondernemerschap? (Zeer belangrijk, belangrijk, niet belangrijk)
- Wat zijn hun werkwaarden? (Geld, voldoening, balans, status)
- Hoe combineren ze werk en privé? (Goed, moeilijk, werk eerst, privé eerst)
- Werken ze liever voor een baas of voor zichzelf?
- Hoe belangrijk is werkzekerheid?
- Welke vaardigheden vinden ze belangrijk voor werk?"""
        },
        {
            "name": "Gezondheid & Welzijn",
            "topics": """GEZONDHEID & WELZIJN:
- Waar zoeken ze gezondheidszorg? (Huisarts Nederland, ziekenhuis Nederland, Turkije, alternatief)
- Hoe belangrijk is preventieve zorg? (Zeer belangrijk, belangrijk, niet belangrijk)
- Welke gezondheidsproblemen maken ze zich zorgen over? (Fysiek, mentaal, beide, geen)
- Gebruiken ze alternatieve geneeskunde? (Ja vaak, soms, nee)
- Hoe belangrijk is gezonde voeding?
- Hoe belangrijk is beweging en sport?
- Waar krijgen ze gezondheidsinformatie vandaan?"""
        },
        {
            "name": "Vrije Tijd & Sport",
            "topics": """VRIJE TIJD & SPORT:
- Welke sporten beoefenen ze? (Voetbal, fitness, zwemmen, vechtsporten, etc.)
- Hoe besteden ze hun vrije tijd? (Sport, hobby's, familie, vrienden, rusten)
- Welke hobby's hebben ze? (Muziek, lezen, gamen, koken, etc.)
- Waar gaan ze op vakantie? (Turkije, Nederland, andere landen, geen vakantie)
- Hoe vaak gaan ze uit? (Dagelijks, wekelijks, maandelijks, zelden)
- Welke activiteiten doen ze in het weekend?
- Hoe belangrijk is vrije tijd voor ze?"""
        },
        {
            "name": "Wonen & Buurt",
            "topics": """WONEN & BUURT:
- Wat zoeken ze in een wijk? (Turkse gemeenschap, Nederlandse buurt, gemengd, rust)
- Hoe belangrijk is de buurtgemeenschap? (Zeer belangrijk, belangrijk, niet belangrijk)
- Welke voorzieningen zijn belangrijk? (Scholen, winkels, moskee, parken, openbaar vervoer)
- Waar willen ze wonen? (Stad, buitenwijk, dorp, platteland)
- Hoe belangrijk is de buurt voor hun kinderen?
- Hoe betrokken zijn ze bij buurtactiviteiten?
- Wat vinden ze belangrijk aan hun woning?"""
        }
    ]
    
    return topic_groups[index % len(topic_groups)]


async def generate_daily_poll(model: Optional[str] = None, dry_run: bool = False) -> dict:
    """
    Generate a daily poll using AI and save it to the database.
    
    Returns dict with poll_id if successful, error info if failed.
    """
    logger.info("poll_generation_start")
    
    try:
        # Get recent polls to avoid duplicates
        recent_polls = await get_recent_polls(days=30, limit=15)
        recent_polls_count = len(recent_polls)
        logger.info("recent_polls_fetched", count=recent_polls_count)
        
        # Build context string with recent polls
        recent_polls_context = ""
        if recent_polls:
            recent_polls_context = "\n\nRECENTE POLLS (vermijd vergelijkbare onderwerpen):\n"
            for poll in recent_polls[:10]:  # Show last 10
                recent_polls_context += f"- {poll['title']}: {poll['question']}\n"
            recent_polls_context += "\nBELANGRIJK: Zorg dat je nieuwe poll NIET hetzelfde onderwerp heeft als deze recente polls.\n"
        
        # Get topic rotation index and select topic group
        rotation_index = get_topic_rotation_index()
        topic_group = get_topic_group_by_index(rotation_index)
        logger.info("topic_rotation_selected", 
                   rotation_index=rotation_index,
                   topic_group=topic_group["name"])
        
        # Initialize OpenAI service
        ai_service = OpenAIService(model=model)
        
        # Generate poll using AI with improved prompts
        system_prompt = """Je bent een expert in het creëren van relevante polls voor marktonderzoek 
onder de Turkse diaspora gemeenschap in Nederland.

Je moet polls maken die:
- In het TURKS zijn geschreven (niet Nederlands)
- Marktonderzoek data verzamelen over:
  * Media consumptie (Turkse/Nederlandse zenders, series, streaming diensten)
  * Religieuze betrokkenheid (gebedsruimtes, religieuze feesten, religieuze organisaties)
  * Culturele voorkeuren (tradities, feesten, culturele evenementen)
  * Integratie patronen (taalgebruik, sociale netwerken, werk)
  * Consumptie gewoonten (winkels, restaurants, online shopping)
  * Onderwijs (Nederlandse vs Turkse scholen, taalonderwijs)
  * Werk (sectoren, ondernemerschap, werk-privé balans)
  * Gezondheid (gezondheidszorg voorkeuren, alternatieve geneeskunde)
  * Vrije tijd (sport, hobby's, sociale activiteiten)
  * Wonen (wijk voorkeuren, woningtype, buurtkenmerken)
- Relevant zijn voor de Turkse diaspora in Nederland
- Meerdere antwoordopties hebben (2-5 opties)
- Een korte, duidelijke titel hebben
- De vraag is duidelijk en begrijpelijk in het Turks
- VARIATIE: Kies elke dag een ANDER onderwerp dan recente polls
- UNIEKHEID: Zorg dat de poll niet te veel lijkt op recente polls

Geef een poll terug met een titel, vraag en 2-5 antwoordopties - ALLES IN HET TURKS."""

        user_prompt = f"""Genereer een NIEUWE, UNIEKE poll voor marktonderzoek onder de Turkse diaspora 
gemeenschap in Nederland.

{recent_polls_context}

Kies een onderwerp uit de volgende categorie die NOG NIET recent is gevraagd:

{topic_group["topics"]}

Zorg dat:
- De poll IN HET TURKS is geschreven
- Betekenisvol is voor marktonderzoek
- Meerdere interessante antwoordopties heeft (2-5 opties)
- Een duidelijke titel en vraag heeft
- NIET hetzelfde is als recente polls hierboven
- Een specifiek aspect van de categorie behandelt (niet te algemeen)"""

        logger.info("poll_ai_call_start")
        poll_result, meta = ai_service.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=PollGenerationResult,
            action_type="poll_generation",
        )
        logger.info("poll_ai_call_complete", model=meta.get("model"), duration_ms=meta.get("duration_ms"))
        
        # Validate options
        if len(poll_result.options) < 2:
            raise ValueError("Poll must have at least 2 options")
        if len(poll_result.options) > 5:
            raise ValueError("Poll can have at most 5 options")
        
        if dry_run:
            logger.info("poll_generation_dry_run", 
                       title=poll_result.title,
                       question=poll_result.question,
                       options_count=len(poll_result.options),
                       topic_group=topic_group["name"],
                       rotation_index=rotation_index,
                       recent_polls_checked=recent_polls_count)
            return {
                "ok": True,
                "dry_run": True,
                "title": poll_result.title,
                "question": poll_result.question,
                "options_count": len(poll_result.options),
            }
        
        # Insert poll into database
        starts_at = datetime.now(timezone.utc)
        ends_at = starts_at + timedelta(days=7)  # Poll expires in 7 days
        
        poll_insert_sql = """
            INSERT INTO polls (title, question, poll_type, is_sponsored, starts_at, ends_at, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """
        poll_rows = await fetch(
            poll_insert_sql,
            poll_result.title,
            poll_result.question,
            "single_choice",  # Default to single choice
            False,  # Not sponsored
            starts_at,
            ends_at,
            "active",
            datetime.now(timezone.utc),
        )
        
        if not poll_rows:
            raise RuntimeError("Failed to insert poll into database")
        
        poll_id = poll_rows[0]["id"]
        logger.info("poll_inserted", poll_id=poll_id, title=poll_result.title)
        
        # Insert poll options
        for idx, option in enumerate(poll_result.options, start=1):
            option_sql = """
                INSERT INTO poll_options (poll_id, option_text, display_order, created_at)
                VALUES ($1, $2, $3, $4)
            """
            await execute(
                option_sql,
                poll_id,
                option.option_text,
                idx,  # display_order (1-based)
                datetime.now(timezone.utc),
            )
        
        # Create activity_stream entry for poll
        # This makes the poll visible in the timeline feed
        try:
            activity_stream_payload = json.dumps({
                "poll_id": poll_id,
                "title": poll_result.title,
                "question": poll_result.question
            })
            
            activity_stream_sql = """
                INSERT INTO activity_stream 
                (actor_type, actor_id, client_id, activity_type, location_id, city_key, category_key, payload, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """
            
            await execute(
                activity_stream_sql,
                'business',  # actor_type
                SYSTEM_UUID,  # actor_id (system UUID for generated polls)
                SYSTEM_UUID,  # client_id (system UUID for generated polls)
                'poll',  # activity_type
                None,  # location_id (polls don't have locations)
                None,  # city_key (polls don't have city targeting yet)
                None,  # category_key
                activity_stream_payload,
                datetime.now(timezone.utc),
            )
            logger.info("poll_activity_stream_entry_created", poll_id=poll_id)
        except Exception as e:
            # Log error but don't fail poll creation if activity_stream entry fails
            logger.error(
                "failed_to_create_poll_activity_stream",
                poll_id=poll_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
        
        # Send push notifications to users with poll notifications enabled
        # Only send if not dry_run
        notification_count = 0
        notification_failed = 0
        
        if not dry_run:
            try:
                push_service = get_push_service()
                
                # Get users with poll notifications enabled
                users_sql = """
                    SELECT DISTINCT user_id
                    FROM push_notification_preferences
                    WHERE enabled = true AND poll_notifications = true
                """
                users = await fetch(users_sql)
                
                if users:
                    logger.info("sending_poll_notifications", poll_id=poll_id, user_count=len(users))
                    
                    # Prepare notification content
                    notification_title = "Nieuwe Poll"
                    
                    notification_body = poll_result.title[:100]  # Max 100 chars
                    if len(poll_result.title) > 100:
                        notification_body = f"{poll_result.title[:97]}..."
                    
                    # Deep link URL to feed with timeline filter and pollId
                    deep_link_url = f"/feed?filter=timeline&pollId={poll_id}"
                    
                    # Send notification to each user
                    for user_row in users:
                        user_id = user_row["user_id"]
                        try:
                            result = await push_service.send_notification(
                                user_id=str(user_id),
                                notification_type="poll",
                                title=notification_title,
                                body=notification_body,
                                data={
                                    "type": "poll",
                                    "poll_id": poll_id,
                                    "url": deep_link_url,  # Deep link naar feed met timeline filter en pollId
                                },
                            )
                            notification_count += result.get("sent", 0)
                            notification_failed += result.get("failed", 0)
                        except Exception as e:
                            logger.error(
                                "failed_to_send_poll_notification",
                                user_id=str(user_id),
                                poll_id=poll_id,
                                error=str(e),
                                error_type=type(e).__name__,
                                exc_info=True,
                            )
                            notification_failed += 1
                    
                    logger.info(
                        "poll_notifications_sent",
                        poll_id=poll_id,
                        sent=notification_count,
                        failed=notification_failed,
                        total_users=len(users),
                    )
                else:
                    logger.info("no_users_with_poll_notifications_enabled", poll_id=poll_id)
                    
            except Exception as e:
                # Log error but don't fail poll creation if notifications fail
                logger.error(
                    "failed_to_send_poll_notifications",
                    poll_id=poll_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
        
        logger.info("poll_generation_complete", 
                   poll_id=poll_id,
                   title=poll_result.title,
                   options_count=len(poll_result.options),
                   topic_group=topic_group["name"],
                   rotation_index=rotation_index,
                   recent_polls_checked=recent_polls_count,
                   notifications_sent=notification_count,
                   notifications_failed=notification_failed)
        
        return {
            "ok": True,
            "poll_id": poll_id,
            "title": poll_result.title,
            "question": poll_result.question,
            "options_count": len(poll_result.options),
        }
        
    except Exception as e:
        logger.error("poll_generation_failed", error=str(e), error_type=type(e).__name__)
        return {
            "ok": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


async def main():
    """CLI entry point for poll generator."""
    parser = argparse.ArgumentParser(description="Generate a daily poll using AI")
    parser.add_argument("--dry-run", type=int, default=0, help="If 1, don't write to database")
    parser.add_argument("--model", type=str, default=None, help="OpenAI model to use (default: from config)")
    
    args = parser.parse_args()
    dry_run = bool(args.dry_run)
    
    with with_run_id():
        logger.info("poll_generator_start", dry_run=dry_run, model=args.model)
        
        # Initialize database pool
        await init_db_pool()
        
        try:
            result = await generate_daily_poll(model=args.model, dry_run=dry_run)
            
            if result.get("ok"):
                if dry_run:
                    print(f"[PollGeneratorBot] DRY RUN: Would create poll:")
                    print(f"  Title: {result.get('title')}")
                    print(f"  Question: {result.get('question')}")
                    print(f"  Options: {result.get('options_count')}")
                else:
                    print(f"[PollGeneratorBot] Successfully created poll ID: {result.get('poll_id')}")
                    print(f"  Title: {result.get('title')}")
            else:
                print(f"[PollGeneratorBot] Failed: {result.get('error')}")
                sys.exit(1)
                
        except Exception as e:
            logger.error("poll_generator_fatal", error=str(e))
            print(f"[PollGeneratorBot] Fatal error: {e}")
            sys.exit(1)
        finally:
            # DB pool cleanup handled by context manager
            pass


if __name__ == "__main__":
    asyncio.run(main())



