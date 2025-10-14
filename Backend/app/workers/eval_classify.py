# app/workers/eval_classify.py
from __future__ import annotations

import argparse
import asyncio
from collections import Counter

from sqlalchemy import text

# LET OP: services staat op top-level, dus zo importeren:
from services.db_service import async_engine
from services.classify_service import ClassifyService


async def load_gold(limit: int):
    q = text("""
        SELECT
          td.location_id,
          td.label_action,
          td.label_category,
          l.name,
          l.address,
          l.category AS type
        FROM training_data td
        JOIN locations l ON l.id = td.location_id
        WHERE td.is_gold_standard = TRUE
        ORDER BY td.id ASC
        LIMIT :limit
    """)
    async with async_engine.begin() as conn:
        rows = (await conn.execute(q, {"limit": limit})).mappings().all()
    return rows


async def run(limit: int, model: str | None = None):
    gold = await load_gold(limit)
    if not gold:
        print("No gold data found in training_data. Add labeled rows first.")
        return

    svc = ClassifyService(model=model) if model else ClassifyService()

    tp = fp = tn = fn = 0
    keep_pred_categories = []
    total = 0

    for row in gold:
        total += 1
        location_id = row["location_id"]
        name = row["name"]
        address = row["address"]
        typ = row["type"]
        gold_action = (row["label_action"] or "").strip().lower()
        gold_category = (row["label_category"] or "").strip().lower() or None

        parsed, meta = svc.classify(name=name, address=address, typ=typ, location_id=location_id)
        pred_action = parsed.action
        pred_category = parsed.category

        # Confusion-matrix voor "keep" als positieve klasse
        if gold_action == "keep" and pred_action == "keep":
            tp += 1
            # voor category-accuracy: alleen bij predicted keep vergelijken
            keep_pred_categories.append((gold_category, pred_category))
        elif gold_action != "keep" and pred_action == "keep":
            fp += 1
            keep_pred_categories.append((gold_category, pred_category))
        elif gold_action != "keep" and pred_action != "keep":
            tn += 1
        elif gold_action == "keep" and pred_action != "keep":
            fn += 1

    # Precision op "keep"
    precision_keep = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    # Category accuracy alleen op predicted keep (waar we net keep_pred_categories gevuld hebben)
    cat_correct = sum(1 for gold_cat, pred_cat in keep_pred_categories if (gold_cat or "") == (pred_cat or ""))
    cat_acc = cat_correct / len(keep_pred_categories) if keep_pred_categories else 0.0

    print(f"Records evaluated: {total}")
    print(f"Confusion (pos=KEEP): TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"KEEP precision: {precision_keep:.3f}")
    print(f"Category accuracy (on predicted KEEP): {cat_acc:.3f}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate classify quality on gold set")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--model", type=str, default=None, help="override model name")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.model))


if __name__ == "__main__":
    main()
