"""
Centrale configuratie met Pydantic Settings (v2).

- Leest variabelen uit `.env` in de Backend-map.
- Negeert extra variabelen die je voor andere delen van je project gebruikt
  (handig als je dezelfde .env bijvoorbeeld ook frontend keys laat bevatten).

Benodigde env:
- APP_VERSION (optioneel; default hieronder)
- DATABASE_URL  (vereist)  -> postgresql+asyncpg://...

Voorbeeld DATABASE_URL voor Supabase Session Pooler (IPv4):
postgresql+asyncpg://postgres.<PROJECT_REF>:<URL_ENCODED_PASS>@aws-1-eu-central-1.pooler.supabase.com:5432/postgres
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl

class Settings(BaseSettings):
    # Versie van je app (mag uit .env komen, maar heeft een veilige default)
    APP_VERSION: str = "0.1.0-alpha"

    # Verplichte database-URL (SQLAlchemy async + asyncpg)
    DATABASE_URL: AnyUrl

    # Pydantic v2 configuratie
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",   # voorkom errors als .env extra keys heeft
    )

# Eager load settings bij import, zodat fouten meteen zichtbaar zijn
settings = Settings()
