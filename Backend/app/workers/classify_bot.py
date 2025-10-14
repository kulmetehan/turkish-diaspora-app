# app/workers/classify_bot.py
from __future__ import annotations

import argparse
import asyncio
import os

from typing import Optional

from services.db_service import fetch_candidates_for_classification, update_location_classification
from services.classify_service import ClassifyService

async def run(limit: int, min_conf: float, dry_run: bool, model: Optional[str]) -> None:
    svc = ClassifyService(model=model)
    rows = await fetch_candidates_for_classification(limit=limit)

    if not rows:
        print("No candidates found (state=CANDIDATE & confidence_score IS NULL).")
        return

    keep_cnt = ignore_cnt = skipped_low_conf = 0
    total = 0
    keep_conf_sum = 0.0

    for r in rows:
        total += 1
        parsed, _meta = svc.classify(
            name=r["name"],
            address=r.get("address"),
            typ=r.get("type"),
            location_id=r["id"],
        )

        conf = float(parsed.confidence_score or 0.0)
        if conf < min_conf:
            skipped_low_conf += 1
            print(f"[skip <{min_conf:.2f}] id={r['id']} name={r['name']!r} -> {parsed.action}/{parsed.category} conf={conf:.2f}")
            continue

        if parsed.action == "keep":
            keep_cnt += 1
            keep_conf_sum += conf
        elif parsed.action == "ignore":
            ignore_cnt += 1

        print(f"[apply] id={r['id']} -> action={parsed.action} category={parsed.category} conf={conf:.2f}")

        if not dry_run:
            await update_location_classification(
                id=r["id"],
                action=parsed.action,
                category=parsed.category,
                confidence_score=conf,
                reason=parsed.reason,
            )

    avg_keep_conf = (keep_conf_sum / keep_cnt) if keep_cnt else 0.0
    print(
        f"\nSummary: classified={total}  keep={keep_cnt}  ignore={ignore_cnt}  skipped_low_conf={skipped_low_conf} "
        f"avg_conf(keep)={avg_keep_conf:.2f}  dry_run={dry_run}"
    )

def main():
    p = argparse.ArgumentParser(description="Batch classify candidates")
    p.add_argument("--limit", type=int, default=50)
    
    default_conf = float(os.getenv("CLASSIFY_MIN_CONF", "0.80"))
    p.add_argument("--min-confidence", type=float, default=default_conf, help="Minimale confidence score")
    
    p.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    p.add_argument("--model", type=str, default=None, help="Override model name")
    args = p.parse_args()

    asyncio.run(run(args.limit, args.min_confidence, args.dry_run, args.model))

if __name__ == "__main__":
    main()