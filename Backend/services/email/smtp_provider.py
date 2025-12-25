"""
SMTP email provider implementation.

Supports SendGrid, Mailgun, Gmail, and other SMTP providers.
"""

from __future__ import annotations

from typing import Optional
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.logging import get_logger
from .base import EmailProvider

logger = get_logger()


class SMTPEmailProvider(EmailProvider):
    """
    Email provider using SMTP.
    
    Supports SendGrid, Mailgun, Gmail, and other SMTP providers.
    """
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_use_tls: bool = True,
        from_email: Optional[str] = None,
        from_name: str = "Turkspot",
    ):
        """
        Initialize SMTP email provider.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (default: 587)
            smtp_user: SMTP username
            smtp_password: SMTP password
            smtp_use_tls: Whether to use TLS (default: True)
            from_email: Sender email address
            from_name: Sender display name
        """
        super().__init__(from_email, from_name)
        
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = smtp_use_tls
        
        if not self.from_email:
            self.from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@turkspot.nl")
    
    def is_configured(self) -> bool:
        """
        Check if SMTP is properly configured.
        
        Returns:
            True if all required SMTP settings are present, False otherwise
        """
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> str:
        """
        Send an email via SMTP.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text fallback
            
        Returns:
            Message ID (format: "smtp-{timestamp}")
            
        Raises:
            Exception: If email sending fails
        """
        if not self.is_configured():
            logger.warning(
                "email_not_configured",
                to_email=to,
                subject=subject,
            )
            raise ValueError("SMTP email provider is not configured")
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to
            
            # Add text part if provided
            if text_body:
                text_part = MIMEText(text_body, "plain", "utf-8")
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            # Generate message ID for tracking
            message_id = f"smtp-{datetime.now().timestamp()}"
            
            logger.info(
                "email_sent",
                to_email=to,
                subject=subject,
                message_id=message_id,
            )
            
            return message_id
            
        except Exception as e:
            logger.error(
                "email_send_failed",
                to_email=to,
                subject=subject,
                error=str(e),
                exc_info=True,
            )
            raise

