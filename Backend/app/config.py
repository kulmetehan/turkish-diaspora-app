# app/config.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absoluut pad naar jouw .env (staat in Backend/.env)
# Dit bestand staat in Backend/app/config.py → parent = Backend
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE, override=False)  # pre-load in procesomgeving

class Settings(BaseSettings):
    # ---- App / Infra ----
    APP_VERSION: str = "0.1.0-alpha"
    DATABASE_URL: str

    # ---- Frontend keys (optioneel; we negeren ze verder) ----
    NEXT_PUBLIC_SUPABASE_URL: Optional[str] = None
    NEXT_PUBLIC_SUPABASE_ANON_KEY: Optional[str] = None

    # ---- Google API removed to avoid costs ----
    # All discovery now uses free OSM Overpass API

    # ---- OpenAI ----
    # Niet hard-required op class-niveau om server-start niet te blokkeren;
    # valideren doen we runtime in de OpenAI service.
    OPENAI_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    OPENAI_MODEL: str = "gpt-4.1-mini"

    # ---- Admin Auth (Supabase) ----
    SUPABASE_JWT_SECRET: str
    ALLOWED_ADMIN_EMAILS: str

    # Pydantic v2 configuratie
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),          # absoluut pad
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",                  # negeer overige .env-keys
    )

settings = Settings()

def require_openai() -> None:
    """
    Runtime-check die een duidelijke foutmelding geeft als de key ontbreekt.
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY ontbreekt. Controleer Backend/.env "
            f"(geprobeerd te laden vanaf: {ENV_FILE})."
        )
