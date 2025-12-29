from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List
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


class DailyOutreachMetrics(BaseModel):
    """Response model for daily outreach metrics."""
    campaign_day: int
    emails_sent: int
    emails_delivered: int
    emails_clicked: int
    emails_bounced: int
    emails_opted_out: int
    claims: int
    delivery_rate: float
    click_rate: float
    bounce_rate: float
    claim_rate: float


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


@router.get("/metrics/daily", response_model=DailyOutreachMetrics)
async def get_daily_outreach_metrics(
    campaign_day: int = Query(..., description="Campaign day number"),
    admin: AdminUser = Depends(verify_admin_user)
) -> DailyOutreachMetrics:
    """
    Get daily outreach metrics for a specific campaign day.
    
    Returns metrics for a specific campaign day:
    - campaign_day: Campaign day number
    - emails_sent: Number of emails sent
    - emails_delivered: Number of emails delivered
    - emails_clicked: Number of emails clicked
    - emails_bounced: Number of emails bounced
    - emails_opted_out: Number of emails opted out
    - claims: Number of claims
    - delivery_rate: Delivery rate as percentage
    - click_rate: Click rate as percentage
    - bounce_rate: Bounce rate as percentage
    - claim_rate: Claim rate as percentage
    
    Requires admin authentication.
    """
    try:
        metrics_service = get_outreach_metrics_service()
        metrics = await metrics_service.get_daily_metrics(campaign_day)
        
        return DailyOutreachMetrics(
            campaign_day=metrics["campaign_day"],
            emails_sent=metrics["emails_sent"],
            emails_delivered=metrics["emails_delivered"],
            emails_clicked=metrics["emails_clicked"],
            emails_bounced=metrics["emails_bounced"],
            emails_opted_out=metrics["emails_opted_out"],
            claims=metrics["claims"],
            delivery_rate=metrics["delivery_rate"],
            click_rate=metrics["click_rate"],
            bounce_rate=metrics["bounce_rate"],
            claim_rate=metrics["claim_rate"],
        )
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        logger.exception("outreach_daily_metrics_error", campaign_day=campaign_day, error=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Outreach daily metrics unavailable"
        ) from exc
    except Exception as exc:
        logger.exception("outreach_daily_metrics_unexpected_error", campaign_day=campaign_day, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve daily outreach metrics"
        ) from exc


@router.get("/metrics/campaign-days", response_model=List[int])
async def get_campaign_days(
    admin: AdminUser = Depends(verify_admin_user)
) -> List[int]:
    """
    Get list of all campaign days that exist in the database.
    
    Returns a sorted list of campaign day numbers.
    
    Requires admin authentication.
    """
    try:
        metrics_service = get_outreach_metrics_service()
        campaign_days = await metrics_service.get_all_campaign_days()
        
        return campaign_days
    except (asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
        logger.exception("outreach_campaign_days_error", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail="Outreach campaign days unavailable"
        ) from exc
    except Exception as exc:
        logger.exception("outreach_campaign_days_unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve campaign days"
        ) from exc

