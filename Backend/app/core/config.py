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

    # Google API removed to avoid costs
    # All discovery now uses free OSM Overpass API

    # Pydantic v2 settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # toleranter voor env-namen
        extra="ignore",         # negeer alle overige .env-keys
    )

# Backend/app/core/config.py (aanvulling)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ...
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-mini"  # of "gpt-4o-mini"
    # ...

settings = Settings()
