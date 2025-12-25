# Backend/services/email/brevo_provider.py
"""
Brevo (formerly Sendinblue) email provider implementation.

This is a skeleton implementation for future marketing email support.
Currently throws NotImplementedError - full implementation to be added when needed.

Use Cases:
- Marketing emails (newsletters, promotions, etc.)
- Service emails (outreach, confirmations) → Use SES provider

Configuration:
- BREVO_API_KEY: Brevo API key (required when implemented)
- EMAIL_PROVIDER=brevo to use this provider
"""

from __future__ import annotations

from typing import Optional
import os

from app.core.logging import get_logger
from .base import EmailProvider

logger = get_logger()


class BrevoEmailProvider(EmailProvider):
    """
    Email provider using Brevo (formerly Sendinblue).
    
    Skeleton implementation - full implementation to be added when marketing emails are needed.
    
    For now, this provider is not implemented and will raise NotImplementedError.
    Use SES provider for service emails (outreach, confirmations).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "Turkspot",
    ):
        """
        Initialize Brevo email provider.
        
        Args:
            api_key: Brevo API key (from BREVO_API_KEY env var if not provided)
            from_email: Sender email address
            from_name: Sender display name
        """
        super().__init__(from_email, from_name)
        self.api_key = api_key or os.getenv("BREVO_API_KEY")
        
        # TODO: Initialize Brevo client when implementing
        # Example: self.client = TransactionalEmailsApi()
        # self.client.api_key = {'api-key': self.api_key}

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> str:
        """
        Send an email via Brevo.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text fallback
            
        Returns:
            Message ID (string) for tracking purposes
            
        Raises:
            NotImplementedError: This provider is not yet implemented
        """
        # TODO: Implement Brevo email sending
        # Example implementation:
        # try:
        #     send_smtp_email = SendSmtpEmail(
        #         to=[{"email": to}],
        #         subject=subject,
        #         html_content=html_body,
        #         text_content=text_body,
        #         sender={"email": self.from_email, "name": self.from_name},
        #     )
        #     result = self.client.send_transac_email(send_smtp_email)
        #     return result.message_id
        # except Exception as e:
        #     logger.error("brevo_email_send_failed", to=to, error=str(e), exc_info=True)
        #     raise
        
        raise NotImplementedError(
            "Brevo email provider is not yet implemented. "
            "Use SES provider for service emails (EMAIL_PROVIDER=ses)."
        )

    def is_configured(self) -> bool:
        """
        Check if Brevo provider is properly configured.
        
        Returns:
            True if configured, False otherwise
        """
        # TODO: Check if Brevo API key is set when implementing
        # return bool(self.api_key)
        return False  # Not implemented yet

