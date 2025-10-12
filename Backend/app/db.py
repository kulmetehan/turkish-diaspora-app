"""
Database bootstrap met SQLAlchemy 2.x (async) + asyncpg.

Belangrijkste punten:
- Supabase vereist TLS. We maken een expliciete SSL-context.
- In sommige (lokale) netwerken zit TLS-inspectie (self-signed CA). Daarvoor
  is er een *ontwikkel* toggel via env: SUPABASE_SSL_NO_VERIFY=1.
  Gebruik dit alléén voor lokaal debuggen. In productie/cloud: niet zetten.

Gebruik:
- set SUPABASE_SSL_NO_VERIFY=1 (alleen lokaal) om tijdelijk certificate checks uit te zetten.
- laat variabele weg in cloud (Render/Railway/etc.) zodat verificatie aan staat.
"""

import os
import ssl
import certifi
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.config import settings


def build_ssl_context() -> ssl.SSLContext:
    """
    Bouw een SSL-context voor asyncpg.

    - Default (aanbevolen): strikte verificatie met de certifi CA-store.
    - Als SUPABASE_SSL_NO_VERIFY=1 is gezet (alleen voor development!):
      hostname-check & certificaatverificatie uit.
    """
    if os.getenv("SUPABASE_SSL_NO_VERIFY", "0") == "1":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    # Strikte, veilige context met certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


# Maak één gedeelde engine voor de app
_engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    connect_args={"ssl": build_ssl_context()},  # expliciete SSL context voor Supabase
    pool_pre_ping=True,                         # check connecties voor hergebruik
    pool_size=5,
    max_overflow=5,
)

# Session factory (per request/usage een AsyncSession via dependency)
AsyncSessionLocal = sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)


async def get_engine() -> AsyncEngine:
    """Geef de gedeelde engine terug (handig voor advanced use)."""
    return _engine


async def get_db():
    """
    FastAPI dependency voor database-sessies.
    Gebruik in endpoints als: `async def endpoint(db: AsyncSession = Depends(get_db))`
    """
    async with AsyncSessionLocal() as session:
        yield session


async def ping_db() -> None:
    """
    Voer een simpele query uit om de verbinding te verifiëren.
    SQLAlchemy 2.x vereist `text()` voor raw SQL.
    """
    async with _engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        _ = result.scalar()  # 1 verwacht
