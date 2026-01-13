# Backend/services/admin_notification_service.py
"""
Service for sending admin notification emails for user-generated actions.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import os

from services.email_service import get_email_service
from services.email_template_service import get_email_template_service
from app.config import get_admin_notification_emails
from app.core.logging import get_logger

logger = get_logger()


async def send_admin_notification(
    action_type: str,
    context: Dict[str, Any],
    language: str = "nl",
) -> bool:
    """
    Send notification email to all admin email addresses.
    
    Args:
        action_type: Type of user action ('account_created', 'location_submitted', 
                    'claim_submitted', 'event_submitted', 'report_submitted')
        context: Template context variables
        language: Email language (nl, tr, en). Defaults to 'nl' for admin notifications.
    
    Returns:
        True if at least one email was sent successfully, False otherwise
    """
    admin_emails = get_admin_notification_emails()
    
    if not admin_emails:
        logger.warning(
            "admin_notification_no_emails_configured",
            action_type=action_type,
        )
        return False
    
    email_service = get_email_service()
    template_service = get_email_template_service()
    
    # Map action types to template names
    template_map = {
        "account_created": "admin_notification_account_created",
        "location_submitted": "admin_notification_location_submitted",
        "claim_submitted": "admin_notification_claim_submitted",
        "event_submitted": "admin_notification_event_submitted",
        "report_submitted": "admin_notification_report_submitted",
    }
    
    template_name = template_map.get(action_type)
    if not template_name:
        logger.error(
            "admin_notification_unknown_action_type",
            action_type=action_type,
            available_types=list(template_map.keys()),
        )
        return False
    
    # Subject mapping per language
    subjects = {
        "account_created": {
            "nl": "Nieuw account aangemaakt",
            "tr": "Yeni hesap oluşturuldu",
            "en": "New account created",
        },
        "location_submitted": {
            "nl": "Nieuwe locatie ingediend",
            "tr": "Yeni konum gönderildi",
            "en": "New location submitted",
        },
        "claim_submitted": {
            "nl": "Nieuwe locatie claim ingediend",
            "tr": "Yeni konum talebi gönderildi",
            "en": "New location claim submitted",
        },
        "event_submitted": {
            "nl": "Nieuw event ingediend",
            "tr": "Yeni etkinlik gönderildi",
            "en": "New event submitted",
        },
        "report_submitted": {
            "nl": "Nieuw report ingediend",
            "tr": "Yeni rapor gönderildi",
            "en": "New report submitted",
        },
    }
    
    subject_map = subjects.get(action_type, {})
    subject = subject_map.get(language, subject_map.get("nl", "Admin Notification"))
    
    # Add base URL and admin dashboard URL to context
    frontend_url = os.getenv("FRONTEND_URL", "https://turkspot.app")
    context_with_base = {
        **context,
        "base_url": frontend_url,
        "admin_dashboard_url": f"{frontend_url}/#/admin",
    }
    
    # Render template
    try:
        html_body, text_body = template_service.render_template(
            template_name=template_name,
            context=context_with_base,
            language=language,
        )
    except Exception as e:
        logger.error(
            "admin_notification_template_render_failed",
            action_type=action_type,
            template_name=template_name,
            error=str(e),
            exc_info=True,
        )
        return False
    
    # Send to all admin emails
    success_count = 0
    for admin_email in admin_emails:
        try:
            email_sent = await email_service.send_email(
                to_email=admin_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            if email_sent:
                success_count += 1
                logger.info(
                    "admin_notification_sent",
                    action_type=action_type,
                    admin_email=admin_email,
                )
            else:
                logger.warning(
                    "admin_notification_failed",
                    action_type=action_type,
                    admin_email=admin_email,
                    reason="email_service_returned_false",
                )
        except Exception as e:
            logger.error(
                "admin_notification_send_error",
                action_type=action_type,
                admin_email=admin_email,
                error=str(e),
                exc_info=True,
            )
    
    return success_count > 0
