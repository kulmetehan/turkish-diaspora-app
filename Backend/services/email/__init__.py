"""
Email provider package for Turkspot.

Provides abstraction layer for different email providers (SMTP, SES, etc.).
"""

from .base import EmailProvider
from .smtp_provider import SMTPEmailProvider
from .ses_provider import SESEmailProvider

__all__ = [
    "EmailProvider",
    "SMTPEmailProvider",
    "SESEmailProvider",
]

