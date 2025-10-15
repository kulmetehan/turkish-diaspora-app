# scripts/classify_batch.py
#
# Doel:
# 1) Zoek CANDIDATE/PENDING_VERIFICATION locaties zonder AI-score
# 2) Roep jouw bestaande endpoint /dev/ai/classify-apply?id=... aan (per id)
# 3) Promoot daarna naar VERIFIED als AI-evidence sterk genoeg is
# 4) Print een samenvatting (counts, en API-resultaat met only_turkish=true)
#
# Gebruik:
#   source .venv/bin/activate
#   python scripts/classify_batch.py --limit 1000 --sleep 0.25 --min-promote 0.80 --promote
#
# Benodigd: asyncpg, httpx
#   pip install asyncpg httpx

import os
import re
import asyncio
import argparse
from typing import List, Optional

import asyncpg
import httpx


def normalize_db_url(url: str) -> str:
    """
    asyncpg accepteert geen 'postgresql+asyncpg://'
    We strippen het +asyncpg deel.
    """
    if not url:
        raise RuntimeError("DATABASE_URL is empty")
    return re.sub(r"\+asyncpg", "", url)


async def fetch_pending_ids(conn: asyncpg.Connection, limit: int) -> List[int]:
    sql = """
    SELECT id
    FROM locations
    WHERE state IN ('CANDIDATE', 'PENDING_VERIFICATION')
      AND (confidence_score IS NULL OR TRIM((confidence_score)::text) = '')
    ORDER BY id
    LIMIT $1;
    """
    rows = await conn.fetch(sql, limit)
    return [r["id"] for r in rows]


async def classify_ids(ids: List[int], base_url: str, sleep_sec: float) -> None:
    if not ids:
        print("⚠️  Geen records gevonden om te classificeren.")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, lid in enumerate(ids, 1):
            url = f"{base_url.rstrip('/')}/dev/ai/classify-apply"
            try:
                r = await client.post(url, params={"id": lid}, headers={"accept": "application/json"})
                if r.status_code != 200:
                    print(f"❌ [{i}/{len(ids)}] id={lid} → HTTP {r.status_code} {r.text[:200]}")
                else:
                    print(f"✅ [{i}/{len(ids)}] id={lid} → {r.text[:200]}")
            except Exception as e:
                print(f"❌ [{i}/{len(ids)}] id={lid} → error: {e}")
            await asyncio.sleep(sleep_sec)


async def promote_verified(conn: asyncpg.Connection, min_promote: float) -> int:
    """
    Promoot naar VERIFIED als:
    - confidence_score >= min_promote  (0.80 default)
      OF
    - notes bevat Turk* varianten
    """
    sql = """
    UPDATE locations
    SET state = 'VERIFIED'
    WHERE state IN ('PENDING_VERIFICATION', 'CANDIDATE')
      AND (
        (
          TRIM((confidence_score)::text) ~ '^-?[0-9]+(\\.[0-9]+)?$'
          AND (confidence_score)::float >= $1
        )
        OR (notes ILIKE '%Turk%' OR notes ILIKE '%Türk%')
      );
    """
    res = await conn.execute(sql, min_promote)
    # res = 'UPDATE <count>'
    try:
        count = int(res.split()[-1])
    except Exception:
        count = 0
    return count


async def count_by_state(conn: asyncpg.Connection) -> None:
    sql = """
    SELECT state, COUNT(*)
    FROM locations
    GROUP BY state
    ORDER BY 1;
    """
    rows = await conn.fetch(sql)
    print("\n📊 Aantallen per state:")
    for r in rows:
        print(f" - {r['state']}: {r['count']}")


async def check_public_api(base_url: str) -> None:
    api = f"{base_url.rstrip('/')}/api/v1/locations/?only_turkish=true&limit=200"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(api)
        if r.status_code != 200:
            print(f"\n❌ Public API check → HTTP {r.status_code}: {r.text[:200]}")
            return
        try:
            data = r.json()
            print(f"\n🌐 Public API (only_turkish=true) → {len(data)} resultaten")
            if len(data) > 0:
                sample = data[:3]
                print("Voorbeeld records:", [s.get("name") for s in sample])
        except Exception as e:
            print(f"\n❌ Public API JSON parse error: {e}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000, help="Max aantal records op te halen voor classificatie")
    parser.add_argument("--sleep", type=float, default=0.25, help="Pauze tussen requests (seconden)")
    parser.add_argument("--min-promote", type=float, default=0.80, help="Drempel voor promotie naar VERIFIED")
    parser.add_argument("--promote", action="store_true", help="Voer promotie-query uit na classificeren")
    parser.add_argument("--api-base", type=str, default="http://127.0.0.1:8000", help="Backend base URL")
    args = parser.parse_args()

    db_url_raw = os.getenv("DATABASE_URL", "")
    if not db_url_raw:
        raise RuntimeError("DATABASE_URL ontbreekt in je omgeving (Backend .env)")

    db_url = normalize_db_url(db_url_raw)

    print(f"🔌 Verbinden met DB …")
    conn = await asyncpg.connect(dsn=db_url)
    try:
        await count_by_state(conn)

        print(f"\n🔎 IDs ophalen (limit={args.limit}) …")
        ids = await fetch_pending_ids(conn, args.limit)
        print(f"Gevonden: {len(ids)} record(s) zonder AI-score.")

        print(f"\n🤖 Classificeren via /dev/ai/classify-apply?id=… (sleep={args.sleep}s) …")
        await classify_ids(ids, args.api_base, args.sleep)

        if args.promote:
            print(f"\n🚀 Promoveren naar VERIFIED (min_promote={args.min_promote:.2f}) …")
            touched = await promote_verified(conn, args.min_promote)
            print(f"Promoted rows: {touched}")

        await count_by_state(conn)

    finally:
        await conn.close()

    await check_public_api(args.api_base)


if __name__ == "__main__":
    asyncio.run(main())
