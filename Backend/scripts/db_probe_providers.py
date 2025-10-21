import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text
from app.db import engine

async def main():
    since = datetime.utcnow() - timedelta(days=14)
    async with engine.begin() as conn:
        # First, let's see what tables exist
        q_tables = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = q_tables.all()
        print("=== AVAILABLE TABLES ===")
        for table in tables:
            print(f"  {table[0]}")
        
        # Check if locations table has the expected columns
        q_columns = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'locations'
            ORDER BY ordinal_position;
        """))
        columns = q_columns.all()
        print("\n=== LOCATIONS TABLE COLUMNS ===")
        for col_name, col_type in columns:
            print(f"  {col_name}: {col_type}")
        
        # Count per source/state (using 'source' instead of 'provider')
        q = await conn.execute(text("""
            SELECT source, state, COUNT(*) 
            FROM locations
            WHERE first_seen_at >= :since
            GROUP BY source, state
            ORDER BY source, state;
        """), {"since": since})
        rows = q.all()
        print("\n=== COUNTS LAST 14d BY SOURCE/STATE ===")
        for source, state, cnt in rows:
            print(f"{source:7} {state:10} {cnt}")

        # Show 10 newest OSM rows with coordinates
        q2 = await conn.execute(text("""
            SELECT id, source, state, lat, lng, name, first_seen_at
            FROM locations
            WHERE source='OSM_OVERPASS'
              AND lat IS NOT NULL
              AND lng IS NOT NULL
            ORDER BY first_seen_at DESC
            LIMIT 10;
        """))
        latest = q2.mappings().all()
        print("\n=== LATEST OSM ROWS (top 10) ===")
        for r in latest:
            print(f"{r['first_seen_at']}  {r['id']}  {r['name']}  ({r['lat']:.6f},{r['lng']:.6f})")

        if latest:
            # derive bbox around newest OSM points (simple min/max)
            lats = [float(r["lat"]) for r in latest if r["lat"] is not None]
            lngs = [float(r["lng"]) for r in latest if r["lng"] is not None]
            if lats and lngs:
                lat_min, lat_max = min(lats), max(lats)
                lng_min, lng_max = min(lngs), max(lngs)
                # pad a little
                pad_lat, pad_lng = 0.01, 0.015
                print(f"\nSuggested bbox from latest OSM points:")
                print(f"lat_min={lat_min - pad_lat:.6f} lat_max={lat_max + pad_lat:.6f}  lng_min={lng_min - pad_lng:.6f} lng_max={lng_max + pad_lng:.6f}")
        else:
            print("\nNo OSM rows found in the last 14 days with coordinates.")

if __name__ == "__main__":
    asyncio.run(main())
