# Backend/services/outreach_audit_service.py
"""
Outreach Audit Logging Service

Service for logging all outreach and claim actions for AVG compliance.
Logs to outreach_audit_log table.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from services.db_service import execute, init_db_pool

logger = get_logger()


def _json_sanitize(obj: Any) -> Any:
    """
    Make objects JSON-safe for storage in JSONB.
    Converts datetime to ISO format, Decimal to float, etc.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_sanitize(v) for v in obj]
    # Fallback: string representation
    return str(obj)


class OutreachAuditService:
    """
    Service for logging outreach and claim actions.
    
    All logs are append-only (no UPDATE/DELETE operations).
    Retention policy: 2 years.
    """
    
    async def log_outreach_action(
        self,
        action_type: str,
        location_id: Optional[int] = None,
        email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an outreach action.
        
        Args:
            action_type: Type of action (email_sent, claim, remove, opt_out, etc.)
            location_id: Location ID related to the action (optional)
            email: Email address related to the action (optional)
            details: Additional details about the action (optional)
        """
        await init_db_pool()
        
        # Sanitize details for JSONB storage
        details_json = None
        if details:
            sanitized_details = _json_sanitize(details)
            details_json = json.dumps(sanitized_details, ensure_ascii=False)
        
        sql = """
            INSERT INTO outreach_audit_log (
                action_type,
                location_id,
                email,
                details,
                created_at
            ) VALUES (
                $1,
                $2,
                $3,
                CAST($4 AS JSONB),
                NOW()
            )
        """
        
        try:
            await execute(
                sql,
                action_type,
                location_id,
                email,
                details_json,
            )
            
            logger.debug(
                "outreach_audit_logged",
                action_type=action_type,
                location_id=location_id,
                email=email,
            )
        except Exception as e:
            # Log error but don't raise - audit logging should not break the main flow
            logger.error(
                "outreach_audit_log_failed",
                action_type=action_type,
                location_id=location_id,
                email=email,
                error=str(e),
                exc_info=True,
            )


# Global instance (lazy initialization)
_outreach_audit_service: Optional[OutreachAuditService] = None


def get_outreach_audit_service() -> OutreachAuditService:
    """Get or create the global outreach audit service instance."""
    global _outreach_audit_service
    if _outreach_audit_service is None:
        _outreach_audit_service = OutreachAuditService()
    return _outreach_audit_service


async def log_outreach_action(
    action_type: str,
    location_id: Optional[int] = None,
    email: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Convenience function to log an outreach action.
    
    Args:
        action_type: Type of action (email_sent, claim, remove, opt_out, etc.)
        location_id: Location ID related to the action (optional)
        email: Email address related to the action (optional)
        details: Additional details about the action (optional)
    """
    service = get_outreach_audit_service()
    await service.log_outreach_action(
        action_type=action_type,
        location_id=location_id,
        email=email,
        details=details,
    )

