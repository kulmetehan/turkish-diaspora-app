# app/workers/import_training_labels.py
from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path
from typing import Optional, Dict, Any

from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

from services.db_service import async_engine


def _norm(s: Optional[str]) -> Optional[str]:
    """Trim, maak lege strings -> None."""
    if s is None:
        return None
    s2 = s.strip()
    return s2 if s2 != "" else None


def _make_input_data(name: str, address: str, typ: Optional[str]) -> Dict[str, Any]:
    return {"name": name, "address": address, "type": (typ or "other")}


def _make_expected_output(action: str, category: Optional[str]) -> Dict[str, Any]:
    # gold standaard: confidence = 1.0 en korte reason
    out: Dict[str, Any] = {
        "action": action,
        "confidence_score": 1.0,
        "reason": "gold: imported from CSV",
    }
    # Alleen een category meesturen als die is ingevuld
    if _norm(category):
        out["category"] = category
    else:
        out["category"] = None
    return out


async def upsert_row(conn, row: dict) -> bool:
    """
    Verwacht CSV-kolommen:
      location_id,name,address,type,label_action,label_category,notes
    Alleen rows met label_action gevuld (keep/ignore) worden geïmporteerd.
    """
    loc_id = int(row["location_id"])
    name = row["name"].strip()
    address = row["address"].strip()
    typ = _norm(row.get("type"))
    action = _norm(row.get("label_action"))
    category = _norm(row.get("label_category"))
    notes = _norm(row.get("notes"))

    if action is None:
        # niks gelabeld -> skippen
        return False

    # Validatie: als action=keep maar geen category -> we forceren wel een category veld in expected_output,
    # maar het mag ook None zijn als je dat wil. Wil je strict? Dan hier error gooien.
    input_data = _make_input_data(name, address, typ)
    expected = _make_expected_output(action, category)

    q = text(
        """
        INSERT INTO training_data
            (location_id, input_data, expected_output, is_gold_standard, label_action, label_category, notes)
        VALUES
            (:location_id, :input_data, :expected_output, TRUE, :label_action, :label_category, :notes)
        ON CONFLICT (location_id) DO UPDATE
        SET
            input_data       = EXCLUDED.input_data,
            expected_output  = EXCLUDED.expected_output,
            is_gold_standard = TRUE,
            label_action     = EXCLUDED.label_action,
            label_category   = EXCLUDED.label_category,
            notes            = EXCLUDED.notes
        """
    ).bindparams(
        bindparam("input_data", type_=JSONB),
        bindparam("expected_output", type_=JSONB),
    )

    await conn.execute(
        q,
        {
            "location_id": loc_id,
            "input_data": input_data,              # python dict -> JSONB door bindparam
            "expected_output": expected,           # python dict -> JSONB door bindparam
            "label_action": action,
            "label_category": category,
            "notes": notes,
        },
    )
    return True


async def run(infile: Path, only_labeled: bool) -> None:
    if not infile.exists():
        raise FileNotFoundError(f"CSV niet gevonden: {infile}")

    with infile.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = ["location_id", "name", "address", "type", "label_action", "label_category", "notes"]
        missing = [c for c in required if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV mist kolommen: {missing}. Gevonden: {reader.fieldnames}")

        rows = list(reader)

    imported = 0
    skipped = 0

    async with async_engine.begin() as conn:
        for r in rows:
            # --only-labeled = True -> sla rijen zonder label_action over
            if only_labeled and _norm(r.get("label_action")) is None:
                skipped += 1
                continue

            ok = await upsert_row(conn, r)
            imported += int(ok)
            skipped += int(not ok)

    print(f"✅ Import klaar. Imported={imported}, Skipped={skipped}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--infile", type=Path, required=True, help="CSV met labels")
    p.add_argument("--only-labeled", action="store_true", help="Sla rijen zonder label_action over")
    args = p.parse_args()
    asyncio.run(run(args.infile, args.only_labeled))


if __name__ == "__main__":
    main()
