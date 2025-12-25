# Backend/services/email_service.py
"""
Email service for sending transactional and digest emails.

Uses provider pattern to support multiple email providers (SMTP, SES, etc.).
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from pathlib import Path
import os
from jinja2 import Template

from app.core.logging import get_logger
from services.email import EmailProvider, SMTPEmailProvider, SESEmailProvider, BrevoEmailProvider
from services.email_template_service import get_email_template_service

logger = get_logger()


class EmailService:
    """
    Email sending service facade.
    
    Uses provider pattern to support multiple email providers.
    Currently supports SMTP (default) and SES (skeleton).
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "Turkspot",
    ):
        """
        Initialize email service.
        
        Args:
            provider: Email provider to use ('smtp' or 'ses'). Defaults to EMAIL_PROVIDER env var or 'smtp'.
            from_email: Sender email address
            from_name: Sender display name
        """
        self.from_email = from_email
        self.from_name = from_name
        self._provider: Optional[EmailProvider] = None
        self._provider_name = provider or os.getenv("EMAIL_PROVIDER", "smtp").lower()
    
    def _get_provider(self) -> EmailProvider:
        """
        Get or create the email provider instance.
        
        Returns:
            EmailProvider instance based on configuration
        """
        if self._provider is None:
            if self._provider_name == "ses":
                self._provider = SESEmailProvider(
                    from_email=self.from_email,
                    from_name=self.from_name,
                )
            elif self._provider_name == "brevo":
                self._provider = BrevoEmailProvider(
                    from_email=self.from_email,
                    from_name=self.from_name,
                )
            else:
                # Default to SMTP
                self._provider = SMTPEmailProvider(
                    from_email=self.from_email,
                    from_name=self.from_name,
                )
        
        return self._provider
    
    @property
    def is_configured(self) -> bool:
        """
        Check if email service is properly configured.
        
        Returns:
            True if configured and ready to send emails, False otherwise
        """
        return self._get_provider().is_configured()
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text fallback
            
        Returns:
            True if sent successfully, False otherwise
        """
        provider = self._get_provider()
        
        if not provider.is_configured():
            logger.warning(
                "email_not_configured",
                to_email=to_email,
                subject=subject,
                provider=self._provider_name,
            )
            return False
        
        try:
            # Provider returns message_id (str), but we maintain backward compatibility with bool
            message_id = await provider.send_email(
                to=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "email_sent",
                to_email=to_email,
                subject=subject,
                message_id=message_id,
                provider=self._provider_name,
            )
            return True
            
        except Exception as e:
            logger.error(
                "email_send_failed",
                to_email=to_email,
                subject=subject,
                error=str(e),
                provider=self._provider_name,
                exc_info=True,
            )
            return False
    
    async def send_email_with_message_id(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send an email and return the message ID.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text fallback
            
        Returns:
            Message ID from provider (e.g., SES MessageId) if sent successfully, None otherwise
        """
        provider = self._get_provider()
        
        if not provider.is_configured():
            logger.warning(
                "email_not_configured",
                to_email=to_email,
                subject=subject,
                provider=self._provider_name,
            )
            return None
        
        try:
            # Provider returns message_id (str)
            message_id = await provider.send_email(
                to=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "email_sent_with_message_id",
                to_email=to_email,
                subject=subject,
                message_id=message_id,
                provider=self._provider_name,
            )
            return message_id
            
        except Exception as e:
            logger.error(
                "email_send_failed",
                to_email=to_email,
                subject=subject,
                error=str(e),
                provider=self._provider_name,
                exc_info=True,
            )
            return None
    
    def render_template(
        self,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        language: str = "nl",
    ) -> tuple[str, str]:
        """
        Render an email template using the EmailTemplateService.
        
        Args:
            template_name: Name of template file (without extension)
            context: Template variables (merged with defaults)
            language: Language code (nl, tr, en)
            
        Returns:
            Tuple of (html_body, text_body)
        """
        template_service = get_email_template_service()
        return template_service.render_template(
            template_name=template_name,
            context=context,
            language=language,
        )


# Global instance (lazy initialization)
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

