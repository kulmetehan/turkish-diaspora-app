# ingest/supabase_ingest.py
from __future__ import annotations

import os
import logging
from typing import Any, Dict, Iterable, List, Optional
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv, find_dotenv

# -----------------------------------------------------------------------------
# .env inladen (vind hem automatisch in projectroot)
# -----------------------------------------------------------------------------
# find_dotenv() zoekt omhoog in mappen en pakt de eerste .env die hij vindt.
# Dit werkt ook als je het script vanuit een submap runt.
load_dotenv(find_dotenv(usecwd=True))

# Lees beide varianten van de key; SERVICE_KEY heeft de voorkeur.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logger = logging.getLogger("ingest")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    logger.addHandler(_ch)

def _env_error() -> str:
    # Maak zichtbaar wat er wel/niet staat (zonder je keys te lekken)
    parts = [
        f"SUPABASE_URL set: {bool(SUPABASE_URL)}",
        f"SUPABASE_SERVICE_KEY set: {bool(os.getenv('SUPABASE_SERVICE_KEY'))}",
        f"SUPABASE_KEY set (fallback): {bool(os.getenv('SUPABASE_KEY'))}",
    ]
    return " | ".join(parts)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "Supabase env mist. Verwacht SUPABASE_URL en SUPABASE_SERVICE_KEY (of SUPABASE_KEY). "
        f"Status -> {_env_error()}\n"
        "Zet ze in je .env of in Render/GitHub Actions secrets."
    )

POSTGREST_ITEMS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/items"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _to_iso8601(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    if isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                dt = datetime.fromisoformat(s.split(".")[0])
            except Exception:
                logger.warning(f"published_at niet parsebaar: {value!r}; fallback naar now()")
                dt = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    return datetime.now(timezone.utc).isoformat()

def _clamp_quality(score: Any) -> float:
    try:
        val = float(score)
    except Exception:
        val = 0.5
    val = max(0.0, min(val, 9.99))
    return float(f"{val:.2f}")

def _batch(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    buf: List[Dict[str, Any]] = []
    for it in items:
        buf.append(it)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def _map_to_items_row(
    agg: Dict[str, Any],
    default_kind: str = "news",
    default_source_id: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "kind": agg.get("kind") or default_kind,
        "source_id": agg.get("source_id", default_source_id),
        "title": agg["title"],
        "url": agg["url"],
        "published_at": _to_iso8601(agg["published_at"]),
        "lang": agg.get("lang") or "nl",
        "quality_score": _clamp_quality(agg.get("score", 0.5)),
        "summary_tr": agg.get("summary_tr"),
        "summary_nl": agg.get("summary_nl"),
        "tags": agg.get("tags") or [],
        "regions": agg.get("regions") or [],
    }

# -----------------------------------------------------------------------------
# Ingest
# -----------------------------------------------------------------------------
def insert_items_ignore_duplicates(
    rows: List[Dict[str, Any]],
    batch_size: int = 200,
    timeout_s: float = 20.0,
) -> Dict[str, int]:
    if not rows:
        return {"attempted": 0, "inserted_estimate": 0}

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }
    params = {"on_conflict": "url"}

    attempted = 0

    with httpx.Client(timeout=timeout_s) as client:
        for chunk in _batch(rows, batch_size):
            attempted += len(chunk)
            resp = client.post(
                POSTGREST_ITEMS_ENDPOINT,
                params=params,
                headers=headers,
                json=chunk,
            )
            if resp.status_code not in (201, 204):
                logger.error("Insert error %s: %s", resp.status_code, resp.text)

    return {"attempted": attempted, "inserted_estimate": 0}

def ingest_aggregated_items(
    aggregated: Iterable[Dict[str, Any]],
    default_kind: str = "news",
    default_source_id: Optional[int] = None,
) -> Dict[str, int]:
    rows: List[Dict[str, Any]] = []
    for a in aggregated:
        try:
            rows.append(_map_to_items_row(a, default_kind, default_source_id))
        except KeyError as e:
            logger.warning("Item overgeslagen (ontbreekt sleutel %s): %r", e, a)
    return insert_items_ignore_duplicates(rows)
