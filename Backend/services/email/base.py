"""
Abstract base class for email providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class EmailProvider(ABC):
    """
    Abstract base class for email providers.
    
    All email providers must implement this interface to ensure
    consistent behavior across different email services.
    """
    
    def __init__(
        self,
        from_email: Optional[str] = None,
        from_name: str = "Turkspot",
    ):
        """
        Initialize email provider.
        
        Args:
            from_email: Sender email address
            from_name: Sender display name
        """
        self.from_email = from_email
        self.from_name = from_name
    
    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> str:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text fallback
            
        Returns:
            Message ID (string) for tracking purposes
            
        Raises:
            Exception: If email sending fails
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the email provider is properly configured.
        
        Returns:
            True if configured and ready to send emails, False otherwise
        """
        pass

