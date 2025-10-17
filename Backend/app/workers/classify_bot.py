# app/workers/classify_bot.py
from __future__ import annotations

import argparse
import asyncio
import os
from typing import Optional, Any, Dict

# jouw bestaande services (toplevel 'services' package)
from services.db_service import (
    fetch_candidates_for_classification,
    update_location_classification,
)
from services.classify_service import ClassifyService

# Unified AI schema entrypoints via services (met structlog)
from services.ai_validation import validate_classification_payload
from app.models.ai import AIClassification


async def run(limit: int, min_conf: float, dry_run: bool, model: Optional[str]) -> None:
    """
    Batch-classifier:
      - haalt CANDIDATE records op
      - laat LLM classificeren via ClassifyService
      - valideert payload met unified schema (AIClassification)
      - past min_conf toe
      - schrijft resultaat naar DB (tenzij --dry-run)
    """
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

        # 1) Vraag classificatie op bij de service
        raw_payload, _meta = svc.classify(
            name=r["name"],
            address=r.get("address"),
            typ=r.get("type"),
            location_id=r["id"],
        )

        # 2) Valideer via unified schema (accepteert dict of model)
        if isinstance(raw_payload, AIClassification):
            parsed = raw_payload
        else:
            # best-effort dict
            if hasattr(raw_payload, "model_dump"):
                raw_dict: Dict[str, Any] = raw_payload.model_dump()  # type: ignore[attr-defined]
            else:
                raw_dict = dict(raw_payload) if isinstance(raw_payload, dict) else {"__raw__": raw_payload}
            parsed = validate_classification_payload(raw_dict)

        # 3) Gebruik enums veilig (.value) en min_conf-drempel
        action = parsed.action.value
        category = parsed.category.value
        conf = float(parsed.confidence_score or 0.0)

        if conf < min_conf:
            skipped_low_conf += 1
            print(
                f"[skip <{min_conf:.2f}] id={r['id']} name={r['name']!r} "
                f"-> {action}/{category} conf={conf:.2f}"
            )
            continue

        if action == "keep":
            keep_cnt += 1
            keep_conf_sum += conf
        elif action == "ignore":
            ignore_cnt += 1

        print(f"[apply] id={r['id']} -> action={action} category={category} conf={conf:.2f}")

        # 4) Persist (tenzij dry-run)
        if not dry_run:
            await update_location_classification(
                id=r["id"],
                action=action,
                category=category,
                confidence_score=conf,
                reason=parsed.reason,
            )

    avg_keep_conf = (keep_conf_sum / keep_cnt) if keep_cnt else 0.0
    print(
        f"\nSummary: classified={total}  keep={keep_cnt}  ignore={ignore_cnt}  "
        f"skipped_low_conf={skipped_low_conf} avg_conf(keep)={avg_keep_conf:.2f}  dry_run={dry_run}"
    )


def main():
    p = argparse.ArgumentParser(description="Batch classify candidates")
    p.add_argument("--limit", type=int, default=50)

    default_conf = float(os.getenv("CLASSIFY_MIN_CONF", "0.80"))
    p.add_argument(
        "--min-confidence",
        type=float,
        default=default_conf,
        help="Minimale confidence score (0..1)"
    )

    p.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    p.add_argument("--model", type=str, default=None, help="Override model name")
    args = p.parse_args()

    asyncio.run(run(args.limit, args.min_confidence, args.dry_run, args.model))


if __name__ == "__main__":
    main()
