from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, Field
from typing import Set

# This allows Pydantic to validate our custom database URL scheme
class CustomPostgresDsn(PostgresDsn):
    allowed_schemes: Set[str] = Field(default_factory=lambda: {"postgres", "postgresql", "postgresql+asyncpg"})

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    PROJECT_NAME: str = "Turkish Diaspora Location App API"
    APP_VERSION: str = "0.1.0"

    # Use our custom type for the DATABASE_URL
    DATABASE_URL: CustomPostgresDsn

settings = Settings()