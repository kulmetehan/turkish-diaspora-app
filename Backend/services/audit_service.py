# Backend/services/audit_service.py
from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from services.db_service import execute, init_db_pool


def _json_sanitize(obj: Any) -> Any:
    """
    Maak dicts/lists JSON-safe: Decimal -> float, datetime/date/time -> isoformat, sets -> list, etc.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Decimal):
        # Behoud zoveel mogelijk precisie, maar JSON kan geen Decimal aan.
        return float(obj)
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_sanitize(v) for v in obj]
    # Fallback: string representatie (laat nooit de insert klappen)
    return str(obj)


class AuditService:
    """
    Table-based audit logging (zelfde stijl als ai_logs).
    Schrijft:
      - action_type: 'admin.create' | 'admin.update'
      - validated_output: JSONB (actor, action, before, after, meta, at)
      - model_used='admin'
    """

    def __init__(self) -> None:
        pass

    async def log(
        self,
        *,
        action_type: str,
        actor: str,
        location_id: Optional[int],
        before: Optional[Dict[str, Any]],
        after: Optional[Dict[str, Any]],
        is_success: bool,
        error_message: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "actor": actor,
            "action": action_type,
            "before": _json_sanitize(before),
            "after": _json_sanitize(after),
            "meta": _json_sanitize(meta) or {},
            "at": datetime.now(timezone.utc).isoformat(),
        }
        validated_output_json = json.dumps(payload, ensure_ascii=False)

        await init_db_pool()
        sql = (
            """
            INSERT INTO ai_logs (
                location_id,
                action_type,
                prompt,
                raw_response,
                validated_output,
                model_used,
                is_success,
                error_message,
                created_at
            ) VALUES (
                $1,
                $2,
                $3,
                CAST($4 AS JSONB),
                CAST($5 AS JSONB),
                $6,
                $7,
                $8,
                NOW()
            )
            """
        )
        await execute(
            sql,
            location_id,
            action_type,
            "",
            None,
            validated_output_json,
            "admin",
            bool(is_success),
            error_message,
        )


audit_service = AuditService()
