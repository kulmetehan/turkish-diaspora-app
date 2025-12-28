# Backend/services/email/brevo_provider.py
"""
Brevo (formerly Sendinblue) email provider implementation.

Full implementation for sending emails via Brevo REST API.
"""

from __future__ import annotations

from typing import Optional
import os
import asyncio

try:
    from sib_api_v3_sdk import TransactionalEmailsApi, SendSmtpEmail, ApiClient, Configuration
    from sib_api_v3_sdk.rest import ApiException
    BREVO_AVAILABLE = True
except ImportError:
    BREVO_AVAILABLE = False
    TransactionalEmailsApi = None  # type: ignore
    SendSmtpEmail = None  # type: ignore
    ApiException = Exception  # type: ignore

from app.core.logging import get_logger
from .base import EmailProvider

logger = get_logger()


class BrevoEmailProvider(EmailProvider):
    """
    Email provider using Brevo (formerly Sendinblue).
    
    Supports sending HTML and plain text emails via Brevo Transactional Email API.
    Handles rate limiting, bounces, and other Brevo-specific errors.
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
            from_email: Sender email address (from EMAIL_FROM env var if not provided, must be verified in Brevo)
            from_name: Sender display name (from EMAIL_FROM_NAME env var if not provided)
        """
        # Get from_email from env if not provided
        final_from_email = from_email or os.getenv("EMAIL_FROM")
        final_from_name = from_name if from_name != "Turkspot" else os.getenv("EMAIL_FROM_NAME", "Turkspot")
        
        super().__init__(final_from_email, final_from_name)
        self.api_key = api_key or os.getenv("BREVO_API_KEY")
        
        # Initialize Brevo client (lazy initialization in _get_client)
        self._brevo_client: Optional[TransactionalEmailsApi] = None
    
    def _get_client(self) -> TransactionalEmailsApi:
        """
        Get or create the Brevo client instance.
        
        Returns:
            Brevo TransactionalEmailsApi client instance
            
        Raises:
            ImportError: If brevo SDK is not installed
        """
        if not BREVO_AVAILABLE:
            raise ImportError(
                "sib-api-v3-sdk is required for Brevo email provider. Install it with: pip install sib-api-v3-sdk"
            )
        
        if self._brevo_client is None:
            # Configure API client
            config = Configuration()
            config.api_key['api-key'] = self.api_key
            
            api_client = ApiClient(config)
            self._brevo_client = TransactionalEmailsApi(api_client)
        
        return self._brevo_client
    
    def is_configured(self) -> bool:
        """
        Check if Brevo is properly configured.
        
        Returns:
            True if brevo SDK is available, API key is set, and from_email is set.
        """
        # brevo SDK must be available
        if not BREVO_AVAILABLE:
            return False
        
        # API key must be set
        if not self.api_key:
            return False
        
        # From email must be set
        if not self.from_email:
            return False
        
        return True
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> str:
        """
        Send an email via Brevo Transactional Email API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text fallback
            
        Returns:
            Message ID from Brevo response
            
        Raises:
            ValueError: If provider is not configured
            ApiException: If Brevo API call fails (rate limit, invalid email, etc.)
            Exception: For other errors (network, etc.)
        """
        if not self.is_configured():
            logger.warning(
                "brevo_email_not_configured",
                to_email=to,
                subject=subject,
            )
            raise ValueError("Brevo email provider is not configured")
        
        try:
            brevo_client = self._get_client()
            
            # Build email message
            send_smtp_email = SendSmtpEmail(
                to=[{"email": to}],
                subject=subject,
                html_content=html_body,
                sender={"email": self.from_email, "name": self.from_name},
            )
            
            # Add text body if provided
            if text_body:
                send_smtp_email.text_content = text_body
            
            # Add email headers for better deliverability and spam prevention
            frontend_url = os.getenv("FRONTEND_URL", "https://turkspot.app")
            unsubscribe_url = f"{frontend_url}/#/account?tab=notificaties"
            
            # Email headers for better deliverability and spam prevention
            # These headers help email clients identify legitimate emails
            headers = {
                # Unsubscribe headers (required for bulk emails, helps with deliverability)
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                
                # Reply-To header (helps with reputation)
                "Reply-To": self.from_email,
                
                # REMOVED: "Precedence: bulk" - This header can trigger spam filters
                # Email clients can detect bulk emails automatically without this header
                
                # Mailer identification (helps with reputation tracking)
                "X-Mailer": "Turkspot Email Service",
                
                # Suppress auto-responses (prevents out-of-office loops)
                "X-Auto-Response-Suppress": "All",
                
                # Message-ID format (helps with tracking and reputation)
                # Brevo will generate this automatically, but we can hint at format
                
                # Content-Type hints (helps email clients parse correctly)
                # Note: Brevo handles Content-Type automatically based on html_content/text_content
            }
            send_smtp_email.headers = headers
            
            # Send email via Brevo
            # Run in executor to avoid blocking (brevo SDK is synchronous)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: brevo_client.send_transac_email(send_smtp_email),
            )
            
            # Extract message ID from response
            message_id = response.message_id
            
            # Log full response for debugging - check all available attributes
            response_info = {
                "message_id": message_id,
                "response_type": type(response).__name__,
            }
            
            # Try to get all response attributes
            if hasattr(response, 'to_dict'):
                try:
                    response_dict = response.to_dict()
                    response_info["response_dict"] = response_dict
                except:
                    pass
            
            # Log all response attributes for debugging
            for attr in ['message_id', 'code', 'message', 'data']:
                if hasattr(response, attr):
                    try:
                        value = getattr(response, attr)
                        response_info[attr] = str(value) if value is not None else None
                    except:
                        pass
            
            logger.info(
                "brevo_email_sent",
                to_email=to,
                subject=subject,
                **response_info,
            )
            
            return message_id
            
        except ApiException as e:
            error_code = e.status if hasattr(e, 'status') else None
            error_body = e.body if hasattr(e, 'body') else str(e)
            
            # Handle specific Brevo error codes
            if error_code == 429:
                # Rate limit exceeded
                logger.error(
                    "brevo_email_rate_limited",
                    to_email=to,
                    subject=subject,
                    error_code=error_code,
                    error_body=error_body,
                )
                raise RuntimeError(f"Brevo rate limit exceeded: {error_body}") from e
            
            elif error_code == 400:
                # Invalid email address, missing required fields, etc.
                logger.error(
                    "brevo_email_rejected",
                    to_email=to,
                    subject=subject,
                    error_code=error_code,
                    error_body=error_body,
                )
                raise ValueError(f"Brevo message rejected: {error_body}") from e
            
            elif error_code == 401:
                # Invalid API key or unauthorized IP
                error_str = str(error_body)
                if "unrecognised IP address" in error_str or "unauthorized" in error_str.lower():
                    # Unauthorized IP address - more specific error
                    logger.error(
                        "brevo_unauthorized_ip",
                        to_email=to,
                        subject=subject,
                        error_code=error_code,
                        error_body=error_body,
                    )
                    raise ValueError(
                        f"Brevo unauthorized IP address: {error_body}. "
                        f"Please add your server IP address to Brevo's authorized IPs list at "
                        f"https://app.brevo.com/security/authorised_ips"
                    ) from e
                else:
                    # Invalid API key
                    logger.error(
                        "brevo_invalid_api_key",
                        to_email=to,
                        subject=subject,
                        error_code=error_code,
                        error_body=error_body,
                    )
                    raise ValueError(
                        f"Brevo API key invalid: {error_body}. "
                        f"Please check your BREVO_API_KEY environment variable."
                    ) from e
            
            else:
                # Other Brevo errors
                logger.error(
                    "brevo_email_send_failed",
                    to_email=to,
                    subject=subject,
                    error_code=error_code,
                    error_body=error_body,
                    exc_info=True,
                )
                raise RuntimeError(f"Brevo error ({error_code}): {error_body}") from e
            
        except Exception as e:
            logger.error(
                "brevo_email_send_failed",
                to_email=to,
                subject=subject,
                error=str(e),
                exc_info=True,
            )
            raise

