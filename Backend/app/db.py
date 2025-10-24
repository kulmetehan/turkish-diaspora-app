# Backend/app/db.py
import os
import ssl
from typing import Dict, Any
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from app.config import settings


def _to_str_url(url_obj: Any) -> str:
    """
    settings.DATABASE_URL kan een Pydantic AnyUrl zijn.
    SQLAlchemy verwacht str of sqlalchemy.engine.URL.
    """
    return str(url_obj)


def _strip_sslmode(url_str: str) -> str:
    """
    Haal 'sslmode' uit de querystring van de URL, zodat de driver
    (vooral asyncpg) géén onbekend kw-argument krijgt.
    """
    parts = urlsplit(url_str)
    query_items = dict(parse_qsl(parts.query, keep_blank_values=True))
    # Verwijder sslmode als die bestaat
    if "sslmode" in query_items:
        query_items.pop("sslmode", None)

    new_query = urlencode(query_items, doseq=True)
    # Herbouw URL
    cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))
    return cleaned


def _build_connect_args(db_scheme: str) -> Dict[str, Any]:
    """
    Bepaal connect_args op basis van driver.
    - Voor asyncpg: gebruik 'ssl' (bool of ssl.SSLContext).
    - Voor psycopg(3): je kunt sslmode in URL laten (maar we strippen 'm al),
      en zonodig via connect_args extra opties meegeven.
    We kiezen hier voor DEV: SSL-verificatie UIT (handig bij zelfondertekende ketens).
    In productie wil je verificatie AAN.
    """
    # DEV: certificaatverificatie uitzetten om self-signed errors te voorkomen
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE  # <-- DEV ONLY (niet in productie!)

    if "asyncpg" in db_scheme:
        # asyncpg verwacht 'ssl'
        return {"ssl": ssl_ctx}
    else:
        # Fallback voor andere drivers (bijv. psycopg), meestal niet nodig.
        # psycopg3 accepteert geen 'ssl' in connect_args op dezelfde manier;
        # doorgaans volstaat de URL, maar we geven niets extra's mee.
        return {}


# 1) URL ophalen en normaliseren
_RAW_URL = getattr(settings, "DATABASE_URL", None)
if not _RAW_URL:
    raise RuntimeError("DATABASE_URL ontbreekt in settings/config.")

_URL_STR = _to_str_url(_RAW_URL)
_URL_STR = _strip_sslmode(_URL_STR)  # Verwijder sslmode uit querystring

# 2) Connect args bepalen o.b.v. driver
_db_scheme = _URL_STR.split(":")[0]  # bijv. 'postgresql+asyncpg'
_CONNECT_ARGS = _build_connect_args(_db_scheme)

# 3) Engine aanmaken (ASYNCHRONOUS)
engine: AsyncEngine = create_async_engine(
    _URL_STR,
    echo=False,           # zet op True als je SQL wilt loggen
    future=True,
    pool_pre_ping=True,   # check verbindingen voordat ze hergebruikt worden
    connect_args=_CONNECT_ARGS,
)


async def ping_db() -> None:
    """
    Simpele gezondheidstest voor de DB-verbinding.
    Wordt bij startup aangeroepen in app.main: on_startup.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
