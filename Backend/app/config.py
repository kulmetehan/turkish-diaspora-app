# app/config.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import EmailStr, Field
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
    SUPABASE_JWT_SECRET: Optional[str] = Field(
        default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET")
    )
    ALLOWED_ADMIN_EMAILS: List[EmailStr] = Field(default_factory=list)

    # ---- Category Health Metrics ----
    CATEGORY_HEALTH_OVERPASS_WINDOW_HOURS: int = 168  # Default: 7 days

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


def require_supabase_jwt() -> str:
    """
    Verifieer dat SUPABASE_JWT_SECRET aanwezig is wanneer auth dit nodig heeft.
    """
    secret = settings.SUPABASE_JWT_SECRET
    if not secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET ontbreekt. Zet deze in Backend/.env "
            f"(geprobeerd te laden vanaf: {ENV_FILE})."
        )
    return secret


def get_allowed_admin_emails() -> list[str]:
    """
    Geef de geparste admin allowlist terug (lowercase, zonder lege waarden).
    """
    return [
        str(email).strip().lower()
        for email in settings.ALLOWED_ADMIN_EMAILS
        if str(email).strip()
    ]


def require_allowed_admin_emails() -> list[str]:
    """
    Zorg dat admin flows enkel doorgaan als er minstens één e-mailadres is geconfigureerd.
    """
    allowed = get_allowed_admin_emails()
    if not allowed:
        raise RuntimeError(
            "ALLOWED_ADMIN_EMAILS ontbreekt of is leeg. Voeg minstens één admin e-mail toe "
            f"in Backend/.env (bron: {ENV_FILE})."
        )
    return allowed
