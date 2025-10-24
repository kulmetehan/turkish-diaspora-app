# Backend/app/db.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.utils.db_url import normalize_database_url, log_dsn_debug


# 1) URL ophalen en normaliseren
_RAW_URL = getattr(settings, "DATABASE_URL", None)
if not _RAW_URL:
    raise RuntimeError("DATABASE_URL ontbreekt in settings/config.")

_URL_STR = normalize_database_url(str(_RAW_URL))
log_dsn_debug("app_db", _URL_STR)

engine: AsyncEngine = create_async_engine(
    _URL_STR,
    echo=False,
    future=True,
    pool_pre_ping=True,
    poolclass=NullPool,
)


async def ping_db() -> None:
    """
    Simpele gezondheidstest voor de DB-verbinding.
    Wordt bij startup aangeroepen in app.main: on_startup.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
