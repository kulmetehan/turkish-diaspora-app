from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncpg

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.core.logging import get_logger
from services.outreach_metrics_service import get_outreach_metrics_service

logger = get_logger()

router = APIRouter(
    prefix="/outreach",
    tags=["outreach-metrics"],
)


class OutreachMetricsResponse(BaseModel):
    """Response model for outreach metrics."""
    mails_sent: int
    bounce_rate: float
    claim_rate: float
    removal_rate: float
    no_action_rate: float
    click_rate: float


@router.get("/metrics", response_model=OutreachMetricsResponse)
async def get_outreach_metrics(
    admin: AdminUser = Depends(verify_admin_user)
) -> OutreachMetricsResponse:
    """
    Get all outreach metrics.
    
    Returns metrics for monitoring outreach effectiveness:
    - mails_sent: Total number of emails sent
    - bounce_rate: Percentage of emails that bounced
    - claim_rate: Percentage of emails that resulted in claims
    - removal_rate: Percentage of emails that resulted in removals
    - no_action_rate: Percentage of emails with no action
    - click_rate: Percentage of emails with clicks
    
    Requires admin authentication.
    """
    try:
        metrics_service = get_outreach_metrics_service()
        metrics = await metrics_service.get_all_metrics()
        
        return OutreachMetricsResponse(
            mails_sent=metrics["mails_sent"],
            bounce_rate=metrics["bounce_rate"],
            claim_rate=metrics["claim_rate"],
            removal_rate=metrics["removal_rate"],
            no_action_rate=metrics["no_action_rate"],
            click_rate=metrics["click_rate"],
        )
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        logger.exception("outreach_metrics_error", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Outreach metrics unavailable"
        ) from exc
    except Exception as exc:
        logger.exception("outreach_metrics_unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve outreach metrics"
        ) from exc

