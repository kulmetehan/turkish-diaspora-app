# Backend/services/email_service.py
"""
Email service for sending transactional and digest emails.

Currently supports SMTP providers (SendGrid, Mailgun, Gmail, etc.).
Future: Can be extended with Supabase Edge Functions or other services.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from pathlib import Path
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template

from app.core.logging import get_logger

logger = get_logger()


class EmailService:
    """
    Email sending service using SMTP.
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
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = smtp_use_tls
        self.from_email = from_email or os.getenv("SMTP_FROM_EMAIL", "noreply@turkspot.nl")
        self.from_name = from_name
        
        # Check if email is configured
        self.is_configured = bool(self.smtp_host and self.smtp_user and self.smtp_password)
    
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
        if not self.is_configured:
            logger.warning(
                "email_not_configured",
                to_email=to_email,
                subject=subject,
            )
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            
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
            
            logger.info(
                "email_sent",
                to_email=to_email,
                subject=subject,
            )
            return True
            
        except Exception as e:
            logger.error(
                "email_send_failed",
                to_email=to_email,
                subject=subject,
                error=str(e),
                exc_info=True,
            )
            return False
    
    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
    ) -> tuple[str, str]:
        """
        Render an email template.
        
        Args:
            template_name: Name of template file (without extension)
            context: Template variables
            
        Returns:
            Tuple of (html_body, text_body)
        """
        templates_dir = Path(__file__).parent.parent / "templates" / "emails"
        html_template_path = templates_dir / f"{template_name}.html.j2"
        text_template_path = templates_dir / f"{template_name}.txt.j2"
        
        html_body = ""
        text_body = ""
        
        # Load and render HTML template
        if html_template_path.exists():
            with open(html_template_path, "r", encoding="utf-8") as f:
                html_template = Template(f.read())
                html_body = html_template.render(**context)
        
        # Load and render text template (fallback)
        if text_template_path.exists():
            with open(text_template_path, "r", encoding="utf-8") as f:
                text_template = Template(f.read())
                text_body = text_template.render(**context)
        else:
            # Generate simple text from HTML if no text template
            text_body = html_body  # Simple fallback
        
        return (html_body, text_body)


# Global instance (lazy initialization)
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

