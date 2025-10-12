# Backend/app/core/config.py
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    APP_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str

    # Frontend keys (optioneel, om .env ruis te negeren)
    NEXT_PUBLIC_SUPABASE_URL: Optional[str] = None
    NEXT_PUBLIC_SUPABASE_ANON_KEY: Optional[str] = None

    # Google Places
    GOOGLE_API_KEY: str
    GOOGLE_PLACES_LANGUAGE: str = "nl"
    GOOGLE_PLACES_REGION: str = "NL"

    # Pydantic v2 settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # toleranter voor env-namen
        extra="ignore",         # negeer alle overige .env-keys
    )

settings = Settings()