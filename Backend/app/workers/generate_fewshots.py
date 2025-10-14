# app/workers/generate_fewshots.py
from __future__ import annotations
import argparse, json, asyncio
from pathlib import Path
from sqlalchemy import text
from services.db_service import async_engine

OUTFILE = Path("app/services/prompts/classify_fewshot_nltr.md")

SQL = """
SELECT
  td.location_id,
  td.label_action,
  COALESCE(td.label_category, NULL) AS label_category,
  l.name, l.address, l.category AS type
FROM training_data td
JOIN locations l ON l.id = td.location_id
WHERE td.is_gold_standard = TRUE
ORDER BY td.location_id ASC
LIMIT :limit
"""

TEMPLATE = """### EXAMPLE
INPUT:
{input_json}
OUTPUT:
{output_json}

"""

def make_output(action: str, category: str|None, reason_hint: str):
    # Construeer een strakke, consistente output JSON
    out = {
        "action": action,
        "category": category if action == "keep" else None,
        "confidence_score": 0.95 if action == "keep" else 0.99,  # high precision bias
        "reason": reason_hint,
    }
    return json.dumps(out, ensure_ascii=False)

async def run(limit: int):
    async with async_engine.begin() as conn:
        rows = (await conn.execute(text(SQL), {"limit": limit})).mappings().all()

    blocks = []
    for r in rows:
        inp = {"name": r["name"], "address": r["address"], "type": r["type"] or "other"}
        if r["label_action"] == "keep":
            # if type=bakery & keep => category=bakery (regel verankeren)
            cat = r["label_category"] or ("bakery" if (inp["type"] == "bakery") else None)
            reason = "gold: Turkse cues en type sluiten aan."
        else:
            cat = None
            reason = "gold: geen Turkse indicaties."

        block = TEMPLATE.format(
            input_json=json.dumps(inp, ensure_ascii=False),
            output_json=make_output(r["label_action"], cat, reason),
        )
        blocks.append(block)

    text_out = (
        "# FEW-SHOT NL/TR\n\n"
        "De voorbeelden hieronder zijn automatisch gegenereerd uit gold labels.\n\n"
        + "".join(blocks)
    )
    OUTFILE.write_text(text_out, encoding="utf-8")
    print(f"✅ Few-shots geschreven naar: {OUTFILE} (n={len(blocks)})")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=40, help="aantal voorbeelden")
    args = parser.parse_args()
    asyncio.run(run(args.limit))

if __name__ == "__main__":
    main()
