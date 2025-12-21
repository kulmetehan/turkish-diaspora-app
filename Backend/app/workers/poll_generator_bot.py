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
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List
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


class PollOptionModel(BaseModel):
    """Single poll option."""
    option_text: str = Field(..., description="The text of the poll option")
    display_order: int = Field(..., description="Display order (1-based)")


class PollGenerationResult(BaseModel):
    """AI-generated poll structure."""
    title: str = Field(..., description="Short title for the poll")
    question: str = Field(..., description="The poll question")
    options: List[PollOptionModel] = Field(..., min_length=2, max_length=5, description="Poll options (2-5 options)")


async def generate_daily_poll(model: Optional[str] = None, dry_run: bool = False) -> dict:
    """
    Generate a daily poll using AI and save it to the database.
    
    Returns dict with poll_id if successful, error info if failed.
    """
    logger.info("poll_generation_start")
    
    try:
        # Initialize OpenAI service
        ai_service = OpenAIService(model=model)
        
        # Generate poll using AI
        system_prompt = """Je bent een expert in het creëren van relevante polls voor de Turkse diaspora gemeenschap in Nederland.
        
Je moet een interessante poll vraag maken die:
- Relevant is voor de Turkse diaspora in Nederland
- Meerdere antwoordopties heeft (2-5 opties)
- Een korte, duidelijke titel heeft
- De vraag is duidelijk en begrijpelijk

Geef een poll terug met een titel, vraag en 2-5 antwoordopties."""

        user_prompt = """Genereer een nieuwe poll voor de Turkse diaspora gemeenschap in Nederland.
Kies een relevant onderwerp zoals:
- Cultuur en tradities
- Integratie en dagelijks leven
- Voedsel en restaurants
- Evenementen en activiteiten
- Gemeenschapskwesties
- Of een ander relevant onderwerp

Zorg dat de poll:
- Betekenisvol is voor de gemeenschap
- Meerdere interessante antwoordopties heeft
- Een duidelijke titel en vraag heeft"""

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
                       options_count=len(poll_result.options))
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
        
        logger.info("poll_generation_complete", 
                   poll_id=poll_id,
                   title=poll_result.title,
                   options_count=len(poll_result.options))
        
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


@with_run_id
async def main():
    """CLI entry point for poll generator."""
    parser = argparse.ArgumentParser(description="Generate a daily poll using AI")
    parser.add_argument("--dry-run", type=int, default=0, help="If 1, don't write to database")
    parser.add_argument("--model", type=str, default=None, help="OpenAI model to use (default: from config)")
    
    args = parser.parse_args()
    dry_run = bool(args.dry_run)
    
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
