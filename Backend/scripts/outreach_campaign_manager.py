#!/usr/bin/env python3
"""
Outreach campaign manager for structured phased rollout.

Manages campaign days with increasing batch sizes and monitoring.
Provides KPI tracking and PostHog analytics integration.

Usage:
    python Backend/scripts/outreach_campaign_manager.py --day 1 --batch-size 10
"""

import asyncio
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import configure_logging, get_logger
from services.outreach_mailer_service import send_queued_emails
from services.outreach_metrics_service import get_outreach_metrics_service
from services.outreach_analytics_service import get_outreach_analytics_service
from services.db_service import execute

# Configure logging
configure_logging(service_name="campaign_manager")
logger = get_logger()

# Campaign configuration
CAMPAIGN_PHASES = [
    {"day": 1, "batch_size": 10, "description": "Initial test batch"},
    {"day": 2, "batch_size": 100, "description": "Small scale rollout"},
    {"day": 3, "batch_size": 250, "description": "Medium scale"},
    {"day": 4, "batch_size": 500, "description": "Large scale"},
    {"day": 5, "batch_size": 1000, "description": "Full scale"},
]

# KPI thresholds for progression
KPI_THRESHOLDS = {
    "max_bounce_rate": 5.0,  # Stop if bounce rate > 5%
    "min_delivery_rate": 90.0,  # Stop if delivery rate < 90%
    "min_click_rate": 10.0,  # Warning if click rate < 10%
}


async def queue_emails_for_campaign_day(day: int, batch_size: int) -> int:
    """
    Queue emails for a specific campaign day.
    
    Args:
        day: Campaign day number
        batch_size: Number of emails to queue
        
    Returns:
        Number of emails queued
    """
    sql = """
        UPDATE outreach_emails
        SET campaign_day = $1,
            updated_at = NOW()
        WHERE id IN (
            SELECT oe.id
            FROM outreach_emails oe
            WHERE oe.status = 'queued'
            AND oe.campaign_day IS NULL
            ORDER BY oe.created_at ASC
            LIMIT $2
        )
        RETURNING id
    """
    rows = await execute(sql, day, batch_size)
    queued_count = len(rows) if rows else 0
    
    logger.info(
        "campaign_emails_queued",
        campaign_day=day,
        batch_size=batch_size,
        queued_count=queued_count,
    )
    
    return queued_count


async def run_campaign_day(day: int, batch_size: int) -> Dict[str, Any]:
    """
    Run a single campaign day.
    
    Args:
        day: Campaign day number
        batch_size: Number of emails to send
        
    Returns:
        Campaign day results dictionary
    """
    logger.info(
        "campaign_day_started",
        campaign_day=day,
        batch_size=batch_size,
    )
    
    # 1. Queue emails for this campaign day
    queued_count = await queue_emails_for_campaign_day(day, batch_size)
    
    if queued_count == 0:
        logger.warning(
            "campaign_no_emails_to_queue",
            campaign_day=day,
        )
        return {
            "campaign_day": day,
            "batch_size": batch_size,
            "queued": 0,
            "sent": 0,
            "error": "No emails available to queue",
        }
    
    # 2. Send queued emails
    send_results = await send_queued_emails(limit=batch_size)
    sent_count = send_results.get("sent", 0)
    failed_count = send_results.get("failed", 0)
    
    logger.info(
        "campaign_emails_sent",
        campaign_day=day,
        sent=sent_count,
        failed=failed_count,
    )
    
    # 3. Wait for delivery events (give Brevo webhooks time to process)
    logger.info(
        "campaign_day_waiting_for_events",
        campaign_day=day,
        wait_seconds=300,
    )
    await asyncio.sleep(300)  # Wait 5 minutes for webhooks
    
    # 4. Calculate metrics
    metrics_service = get_outreach_metrics_service()
    daily_metrics = await metrics_service.get_daily_metrics(day)
    
    # 5. Track in PostHog
    analytics = get_outreach_analytics_service()
    await analytics.track_campaign_day_summary(
        campaign_day=day,
        emails_sent=daily_metrics["emails_sent"],
        emails_delivered=daily_metrics["emails_delivered"],
        emails_clicked=daily_metrics["emails_clicked"],
        emails_bounced=daily_metrics["emails_bounced"],
        claims=daily_metrics.get("claims", 0),
        removals=0,  # TODO: track removals if needed
    )
    
    # 6. Check KPIs
    kpi_status = check_kpis(daily_metrics)
    
    # 7. Generate report
    report = {
        "campaign_day": day,
        "batch_size": batch_size,
        "queued": queued_count,
        "sent": sent_count,
        "failed": failed_count,
        "metrics": daily_metrics,
        "kpi_status": kpi_status,
        "timestamp": datetime.now().isoformat(),
    }
    
    logger.info(
        "campaign_day_completed",
        **report,
    )
    
    # Print summary to console
    print("\n" + "="*60)
    print(f"Campaign Day {day} Summary")
    print("="*60)
    print(f"Batch Size: {batch_size}")
    print(f"Queued: {queued_count}")
    print(f"Sent: {sent_count}")
    print(f"Failed: {failed_count}")
    print(f"\nMetrics:")
    print(f"  Emails Sent: {daily_metrics['emails_sent']}")
    print(f"  Emails Delivered: {daily_metrics['emails_delivered']}")
    print(f"  Emails Clicked: {daily_metrics['emails_clicked']}")
    print(f"  Emails Bounced: {daily_metrics['emails_bounced']}")
    print(f"  Claims: {daily_metrics.get('claims', 0)}")
    print(f"\nRates:")
    print(f"  Delivery Rate: {daily_metrics['delivery_rate']:.1f}%")
    print(f"  Click Rate: {daily_metrics['click_rate']:.1f}%")
    print(f"  Bounce Rate: {daily_metrics['bounce_rate']:.1f}%")
    print(f"  Claim Rate: {daily_metrics['claim_rate']:.1f}%")
    print(f"\nKPI Status: {kpi_status['status'].upper()}")
    if kpi_status['warnings']:
        print(f"Warnings:")
        for warning in kpi_status['warnings']:
            print(f"  - {warning}")
    print("="*60 + "\n")
    
    return report


def check_kpis(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check KPIs against thresholds.
    
    Args:
        metrics: Daily metrics dictionary
        
    Returns:
        Dictionary with status and warnings
    """
    bounce_rate = metrics.get("bounce_rate", 0)
    delivery_rate = metrics.get("delivery_rate", 0)
    click_rate = metrics.get("click_rate", 0)
    
    status = "ok"
    warnings = []
    
    if bounce_rate > KPI_THRESHOLDS["max_bounce_rate"]:
        status = "critical"
        warnings.append(
            f"Bounce rate {bounce_rate:.1f}% exceeds threshold {KPI_THRESHOLDS['max_bounce_rate']}%"
        )
    
    if delivery_rate < KPI_THRESHOLDS["min_delivery_rate"]:
        status = "critical"
        warnings.append(
            f"Delivery rate {delivery_rate:.1f}% below threshold {KPI_THRESHOLDS['min_delivery_rate']}%"
        )
    
    if click_rate < KPI_THRESHOLDS["min_click_rate"]:
        warnings.append(
            f"Click rate {click_rate:.1f}% below expected {KPI_THRESHOLDS['min_click_rate']}%"
        )
        if status == "ok":
            status = "warning"
    
    return {
        "status": status,
        "warnings": warnings,
        "bounce_rate": bounce_rate,
        "delivery_rate": delivery_rate,
        "click_rate": click_rate,
    }


async def main():
    """Main entry point for campaign manager."""
    parser = argparse.ArgumentParser(
        description="Run outreach campaign day with monitoring"
    )
    parser.add_argument(
        "--day",
        type=int,
        required=True,
        help="Campaign day number (1, 2, 3, etc.)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        required=True,
        help="Number of emails to send in this batch"
    )
    
    args = parser.parse_args()
    
    try:
        result = await run_campaign_day(args.day, args.batch_size)
        
        # Exit with error code if critical KPI issues
        if result.get("kpi_status", {}).get("status") == "critical":
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.exception(
            "campaign_manager_error",
            error=str(e),
            exc_info=True,
        )
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

