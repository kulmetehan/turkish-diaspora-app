from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote


def normalize_database_url(raw: str) -> str:
    s = " ".join((raw or "").strip().strip('"').strip("'").split())
    if not s:
        raise RuntimeError("DATABASE_URL is empty")

    if s.startswith("postgres://"):
        s = s.replace("postgres://", "postgresql+asyncpg://", 1)
    if s.startswith("postgresql://"):
        s = s.replace("postgresql://", "postgresql+asyncpg://", 1)
    if s.startswith("postgresql+psycopg2://"):
        s = s.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    p = urlsplit(s)

    username = p.username or ""
    password = p.password or ""
    host = p.hostname or ""
    port = f":{p.port}" if p.port else ""

    userinfo = ""
    if username:
        userinfo = quote(username, safe="")
        if p.password is not None:
            userinfo += ":" + quote(password, safe="")
        userinfo += "@"

    netloc = f"{userinfo}{host}{port}"

    q = dict(parse_qsl(p.query, keep_blank_values=True))
    if "sslmode" in q:
        q.pop("sslmode", None)
        q["ssl"] = "true"
    if (("pooler.supabase.com" in host) or ("supabase.co" in host)) and "ssl" not in q:
        q["ssl"] = "true"

    new_query = urlencode(q, doseq=True)
    return urlunsplit(("postgresql+asyncpg", netloc, p.path, new_query, p.fragment))


def log_dsn_debug(label: str, url: str) -> None:
    if os.getenv("DB_DEBUG_URL", "0") != "1":
        return
    try:
        p = urlsplit(url)
        safe = f"driver={p.scheme} host={p.hostname} port={p.port} db={p.path.lstrip('/')} ssl={'ssl=true' in p.query}"
        print(f"[DB] {label}: {safe}")
    except Exception:
        pass


