"""
AWS SES email provider implementation.

Full implementation for sending emails via AWS Simple Email Service (SES).
"""

from __future__ import annotations

from typing import Optional, Any
import os
import asyncio

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None  # type: ignore
    ClientError = Exception  # type: ignore
    BotoCoreError = Exception  # type: ignore

from app.core.logging import get_logger
from .base import EmailProvider

logger = get_logger()


class SESEmailProvider(EmailProvider):
    """
    Email provider using AWS SES.
    
    Supports sending HTML and plain text emails via AWS Simple Email Service.
    Handles throttling, bounces, and other SES-specific errors.
    """
    
    def __init__(
        self,
        aws_region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "Turkspot",
    ):
        """
        Initialize SES email provider.
        
        Args:
            aws_region: AWS region for SES (e.g., 'eu-west-1')
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            from_email: Sender email address (must be verified in SES)
            from_name: Sender display name
        """
        super().__init__(from_email, from_name)
        
        self.aws_region = aws_region or os.getenv("AWS_SES_REGION")
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Initialize SES client (lazy initialization in _get_client)
        self._ses_client: Optional[Any] = None
    
    def _get_client(self):
        """
        Get or create the SES client instance.
        
        Returns:
            boto3 SES client instance
            
        Raises:
            ImportError: If boto3 is not installed
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for SES email provider. Install it with: pip install boto3"
            )
        
        if self._ses_client is None:
            client_kwargs = {
                "service_name": "ses",
                "region_name": self.aws_region,
            }
            
            # Only include credentials if explicitly provided (boto3 will use default credentials otherwise)
            if self.aws_access_key_id and self.aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = self.aws_access_key_id
                client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key
            
            self._ses_client = boto3.client(**client_kwargs)
        
        return self._ses_client
    
    def is_configured(self) -> bool:
        """
        Check if SES is properly configured.
        
        Returns:
            True if boto3 is available, region is set, and from_email is set.
            Credentials can come from explicit params, env vars, or default AWS credentials chain.
        """
        # boto3 must be available
        if not BOTO3_AVAILABLE:
            return False
        
        # Region must be set
        if not self.aws_region:
            return False
        
        # From email must be set
        if not self.from_email:
            return False
        
        # Credentials can come from:
        # 1. Explicit parameters (both must be provided)
        # 2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        # 3. Default AWS credentials chain (IAM role, ~/.aws/credentials, etc.)
        # So we don't require explicit credentials here - boto3 will handle credential resolution
        
        return True
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> str:
        """
        Send an email via AWS SES.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Optional plain text fallback
            
        Returns:
            Message ID from SES response
            
        Raises:
            ValueError: If provider is not configured
            ClientError: If SES API call fails (throttling, invalid email, etc.)
            Exception: For other errors (network, etc.)
        """
        if not self.is_configured():
            logger.warning(
                "ses_email_not_configured",
                to_email=to,
                subject=subject,
            )
            raise ValueError("SES email provider is not configured")
        
        try:
            ses_client = self._get_client()
            
            # Build email message
            message: dict[str, Any] = {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            }
            
            # Add text body if provided
            if text_body:
                message["Body"]["Text"] = {"Data": text_body, "Charset": "UTF-8"}
            
            # Send email via SES
            # Run in executor to avoid blocking (boto3 is synchronous)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ses_client.send_email(
                    Source=f"{self.from_name} <{self.from_email}>",
                    Destination={"ToAddresses": [to]},
                    Message=message,
                ),
            )
            
            # Extract message ID from response
            message_id = response.get("MessageId", "")
            
            logger.info(
                "ses_email_sent",
                to_email=to,
                subject=subject,
                message_id=message_id,
            )
            
            return message_id
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            # Handle specific SES error codes
            if error_code == "Throttling":
                logger.error(
                    "ses_email_throttled",
                    to_email=to,
                    subject=subject,
                    error_code=error_code,
                    error_message=error_message,
                )
                raise RuntimeError(f"SES throttling error: {error_message}") from e
            
            elif error_code == "MessageRejected":
                # Invalid email address, bounce, complaint, etc.
                logger.error(
                    "ses_email_rejected",
                    to_email=to,
                    subject=subject,
                    error_code=error_code,
                    error_message=error_message,
                )
                raise ValueError(f"SES message rejected: {error_message}") from e
            
            elif error_code == "MailFromDomainNotVerified":
                logger.error(
                    "ses_mail_from_domain_not_verified",
                    to_email=to,
                    subject=subject,
                    from_email=self.from_email,
                    error_code=error_code,
                    error_message=error_message,
                )
                raise ValueError(
                    f"SES sender domain not verified: {error_message}. "
                    f"Please verify {self.from_email} in SES console."
                ) from e
            
            else:
                # Other SES errors
                logger.error(
                    "ses_email_send_failed",
                    to_email=to,
                    subject=subject,
                    error_code=error_code,
                    error_message=error_message,
                    exc_info=True,
                )
                raise RuntimeError(f"SES error ({error_code}): {error_message}") from e
            
        except BotoCoreError as e:
            # Network errors, configuration errors, etc.
            logger.error(
                "ses_email_boto_error",
                to_email=to,
                subject=subject,
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"SES boto error: {str(e)}") from e
            
        except Exception as e:
            logger.error(
                "ses_email_send_failed",
                to_email=to,
                subject=subject,
                error=str(e),
                exc_info=True,
            )
            raise

