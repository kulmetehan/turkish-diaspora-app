# app/workers/export_candidates.py
from __future__ import annotations
import argparse, asyncio, csv
from pathlib import Path
from sqlalchemy import text
from services.db_service import async_engine

DEFAULT_OUT = Path("data/candidates_to_label.csv")

async def run(limit: int, outfile: Path):
    outfile.parent.mkdir(parents=True, exist_ok=True)

    # Alleen echte kandidaten exporteren. Géén 'PENDING_CLASSIFICATION' (bestaat niet in je ENUM).
    # Eventueel wil je ook 'PENDING_VERIFICATION' meenemen; dan voeg je die toe aan de IN-lijst.
    q = text("""
        SELECT id AS location_id, name, address, category AS type
        FROM locations
        WHERE state IN ('CANDIDATE') OR state IS NULL
        ORDER BY id ASC
        LIMIT :limit
    """)

    async with async_engine.begin() as conn:
        rows = (await conn.execute(q, {"limit": limit})).mappings().all()

    with outfile.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["location_id","name","address","type","label_action","label_category","notes"])
        for r in rows:
            w.writerow([r["location_id"], r["name"], r["address"], r["type"] or "", "", "", ""])

    print(f"✅ Export klaar: {outfile}  (open in Excel/Numbers)")
    print("Vul voor elke rij:")
    print("- label_action: keep of ignore")
    print("- label_category: alleen bij keep (bv. kebab, bakery, restaurant, bakkal/supermarket, butcher, barber, mosque, association)")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=150, help="Aantal kandidaten om te labelen")
    p.add_argument("--outfile", type=Path, default=DEFAULT_OUT, help="Bestand om te schrijven")
    args = p.parse_args()
    asyncio.run(run(args.limit, args.outfile))

if __name__ == "__main__":
    main()
