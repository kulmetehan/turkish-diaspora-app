# Backend/app/db.py
import os
from typing import Dict, Any
from sqlalchemy.engine.url import make_url

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from app.core.logging import logger
from services.db_service import normalize_db_url  # shared helper
import asyncpg

from app.config import settings


def _to_str_url(url_obj: Any) -> str:
    """
    settings.DATABASE_URL kan een Pydantic AnyUrl zijn.
    SQLAlchemy verwacht str of sqlalchemy.engine.URL.
    """
    return str(url_obj)


def _normalize_url(url_str: str) -> str:
    return normalize_db_url(url_str)


def _build_connect_args(db_scheme: str) -> Dict[str, Any]:
    return {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "timeout": 60,
    }


# 1) URL ophalen en normaliseren
_RAW_URL = getattr(settings, "DATABASE_URL", None)
if not _RAW_URL:
    raise RuntimeError("DATABASE_URL ontbreekt in settings/config.")

_URL_STR = _to_str_url(_RAW_URL)
_URL_STR = _normalize_url(_URL_STR)

# 2) Connect args bepalen o.b.v. driver
_db_scheme = _URL_STR.split(":")[0]  # bijv. 'postgresql+asyncpg'
_CONNECT_ARGS = _build_connect_args(_db_scheme)

# 3) Engine aanmaken (ASYNCHRONOUS)
async def _asyncpg_creator():
    return await asyncpg.connect(_URL_STR)

async_engine: AsyncEngine = create_async_engine(
    "postgresql+asyncpg://",
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "creator": _asyncpg_creator,
    },
)

# Log de genormaliseerde URL met gemaskeerd wachtwoord
try:
    masked = str(make_url(_URL_STR).set(password="***"))
    logger.info("db_engine_initialized", url=masked)
except Exception:
    pass

# Backwards-compat alias
engine: AsyncEngine = async_engine


async def ping_db() -> None:
    """
    Simpele gezondheidstest voor de DB-verbinding.
    Wordt bij startup aangeroepen in app.main: on_startup.
    """
    async with async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
