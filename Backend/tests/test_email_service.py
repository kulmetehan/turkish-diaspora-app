"""
Tests for email service and email providers (SMTP, SES).
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.email.ses_provider import SESEmailProvider
from services.email.smtp_provider import SMTPEmailProvider
from services.email_service import EmailService


# ============================================================================
# SES Provider Tests
# ============================================================================


@pytest.mark.asyncio
async def test_ses_provider_send_email_success():
    """Test successful email sending via SES."""
    # Mock boto3 SES client
    mock_ses_client = MagicMock()
    mock_response = {"MessageId": "000001378603177f-7a5433e7-8edb-42ae-af10-f0181f34d6ee-000000"}
    mock_ses_client.send_email.return_value = mock_response

    with patch("services.email.ses_provider.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_ses_client

        provider = SESEmailProvider(
            aws_region="eu-west-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            from_email="test@turkspot.nl",
            from_name="Turkspot Test",
        )

        # Mock asyncio.run_in_executor to execute synchronously
        async def mock_run_in_executor(executor, fn, *args):
            return fn(*args)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = mock_run_in_executor
            mock_loop.return_value = mock_loop_instance

            message_id = await provider.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<h1>Test HTML</h1>",
                text_body="Test Text",
            )

            assert message_id == "000001378603177f-7a5433e7-8edb-42ae-af10-f0181f34d6ee-000000"
            mock_ses_client.send_email.assert_called_once()
            call_args = mock_ses_client.send_email.call_args
            assert call_args[1]["Source"] == "Turkspot Test <test@turkspot.nl>"
            assert call_args[1]["Destination"]["ToAddresses"] == ["recipient@example.com"]
            assert call_args[1]["Message"]["Subject"]["Data"] == "Test Subject"
            assert call_args[1]["Message"]["Body"]["Html"]["Data"] == "<h1>Test HTML</h1>"
            assert call_args[1]["Message"]["Body"]["Text"]["Data"] == "Test Text"


@pytest.mark.asyncio
async def test_ses_provider_send_email_html_only():
    """Test SES email sending with HTML only (no text body)."""
    mock_ses_client = MagicMock()
    mock_response = {"MessageId": "test-message-id"}
    mock_ses_client.send_email.return_value = mock_response

    with patch("services.email.ses_provider.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_ses_client

        provider = SESEmailProvider(
            aws_region="eu-west-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            from_email="test@turkspot.nl",
        )

        async def mock_run_in_executor(executor, fn, *args):
            return fn(*args)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = mock_run_in_executor
            mock_loop.return_value = mock_loop_instance

            await provider.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<h1>Test HTML</h1>",
                text_body=None,
            )

            call_args = mock_ses_client.send_email.call_args
            # Should only have Html in Body, no Text
            assert "Html" in call_args[1]["Message"]["Body"]
            assert "Text" not in call_args[1]["Message"]["Body"]


@pytest.mark.asyncio
async def test_ses_provider_send_email_throttling_error():
    """Test SES provider handling of throttling errors."""
    from botocore.exceptions import ClientError

    mock_ses_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "Throttling",
            "Message": "Maximum sending rate exceeded",
        }
    }
    mock_ses_client.send_email.side_effect = ClientError(error_response, "SendEmail")

    with patch("services.email.ses_provider.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_ses_client

        provider = SESEmailProvider(
            aws_region="eu-west-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            from_email="test@turkspot.nl",
        )

        async def mock_run_in_executor(executor, fn, *args):
            return fn(*args)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = mock_run_in_executor
            mock_loop.return_value = mock_loop_instance

            with pytest.raises(RuntimeError) as exc_info:
                await provider.send_email(
                    to="recipient@example.com",
                    subject="Test Subject",
                    html_body="<h1>Test</h1>",
                )

            assert "SES throttling error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ses_provider_send_email_message_rejected():
    """Test SES provider handling of message rejection errors."""
    from botocore.exceptions import ClientError

    mock_ses_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "MessageRejected",
            "Message": "Email address is not verified",
        }
    }
    mock_ses_client.send_email.side_effect = ClientError(error_response, "SendEmail")

    with patch("services.email.ses_provider.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_ses_client

        provider = SESEmailProvider(
            aws_region="eu-west-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            from_email="test@turkspot.nl",
        )

        async def mock_run_in_executor(executor, fn, *args):
            return fn(*args)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = mock_run_in_executor
            mock_loop.return_value = mock_loop_instance

            with pytest.raises(ValueError) as exc_info:
                await provider.send_email(
                    to="recipient@example.com",
                    subject="Test Subject",
                    html_body="<h1>Test</h1>",
                )

            assert "SES message rejected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ses_provider_send_email_mail_from_domain_not_verified():
    """Test SES provider handling of unverified domain errors."""
    from botocore.exceptions import ClientError

    mock_ses_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "MailFromDomainNotVerified",
            "Message": "Domain not verified",
        }
    }
    mock_ses_client.send_email.side_effect = ClientError(error_response, "SendEmail")

    with patch("services.email.ses_provider.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_ses_client

        provider = SESEmailProvider(
            aws_region="eu-west-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            from_email="test@turkspot.nl",
        )

        async def mock_run_in_executor(executor, fn, *args):
            return fn(*args)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = mock_run_in_executor
            mock_loop.return_value = mock_loop_instance

            with pytest.raises(ValueError) as exc_info:
                await provider.send_email(
                    to="recipient@example.com",
                    subject="Test Subject",
                    html_body="<h1>Test</h1>",
                )

            assert "SES sender domain not verified" in str(exc_info.value)
            assert "test@turkspot.nl" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ses_provider_send_email_network_error():
    """Test SES provider handling of network/boto errors."""
    from botocore.exceptions import BotoCoreError

    mock_ses_client = MagicMock()
    mock_ses_client.send_email.side_effect = BotoCoreError()

    with patch("services.email.ses_provider.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_ses_client

        provider = SESEmailProvider(
            aws_region="eu-west-1",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            from_email="test@turkspot.nl",
        )

        async def mock_run_in_executor(executor, fn, *args):
            return fn(*args)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_in_executor = mock_run_in_executor
            mock_loop.return_value = mock_loop_instance

            with pytest.raises(RuntimeError) as exc_info:
                await provider.send_email(
                    to="recipient@example.com",
                    subject="Test Subject",
                    html_body="<h1>Test</h1>",
                )

            assert "SES boto error" in str(exc_info.value)


def test_ses_provider_is_configured():
    """Test SES provider configuration check."""
    # Fully configured
    provider1 = SESEmailProvider(
        aws_region="eu-west-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        from_email="test@turkspot.nl",
    )
    assert provider1.is_configured() is True

    # Missing region
    provider2 = SESEmailProvider(
        aws_region=None,
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        from_email="test@turkspot.nl",
    )
    assert provider2.is_configured() is False

    # Missing from_email
    provider3 = SESEmailProvider(
        aws_region="eu-west-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        from_email=None,
    )
    assert provider3.is_configured() is False


def test_ses_provider_is_configured_from_env():
    """Test SES provider configuration from environment variables."""
    with patch.dict(
        os.environ,
        {
            "AWS_SES_REGION": "eu-west-1",
            "AWS_ACCESS_KEY_ID": "env-key",
            "AWS_SECRET_ACCESS_KEY": "env-secret",
        },
    ):
        provider = SESEmailProvider(from_email="test@turkspot.nl")
        assert provider.aws_region == "eu-west-1"
        assert provider.aws_access_key_id == "env-key"
        assert provider.aws_secret_access_key == "env-secret"
        assert provider.is_configured() is True


@pytest.mark.asyncio
async def test_ses_provider_not_configured_error():
    """Test SES provider raises error when not configured."""
    provider = SESEmailProvider(
        aws_region=None,  # Not configured
        from_email="test@turkspot.nl",
    )

    with pytest.raises(ValueError) as exc_info:
        await provider.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<h1>Test</h1>",
        )

    assert "not configured" in str(exc_info.value).lower()


# ============================================================================
# SMTP Provider Tests
# ============================================================================


def test_smtp_provider_is_configured():
    """Test SMTP provider configuration check."""
    # Fully configured
    provider1 = SMTPEmailProvider(
        smtp_host="smtp.example.com",
        smtp_user="user",
        smtp_password="password",
        from_email="test@turkspot.nl",
    )
    assert provider1.is_configured() is True

    # Missing host
    provider2 = SMTPEmailProvider(
        smtp_host=None,
        smtp_user="user",
        smtp_password="password",
    )
    assert provider2.is_configured() is False

    # Missing user
    provider3 = SMTPEmailProvider(
        smtp_host="smtp.example.com",
        smtp_user=None,
        smtp_password="password",
    )
    assert provider3.is_configured() is False


# ============================================================================
# Email Service Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_email_service_with_smtp_provider():
    """Test EmailService using SMTP provider."""
    with patch.dict(os.environ, {"EMAIL_PROVIDER": "smtp"}):
        service = EmailService()

        # Mock SMTP provider
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send_email.return_value = "smtp-message-id-123"

        service._provider = mock_provider

        result = await service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<h1>Test</h1>",
            text_body="Test",
        )

        assert result is True
        mock_provider.send_email.assert_called_once_with(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<h1>Test</h1>",
            text_body="Test",
        )


@pytest.mark.asyncio
async def test_email_service_with_ses_provider():
    """Test EmailService using SES provider."""
    with patch.dict(os.environ, {"EMAIL_PROVIDER": "ses"}):
        service = EmailService()

        # Mock SES provider
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send_email.return_value = "000001378603177f-7a5433e7-8edb-42ae-af10-f0181f34d6ee-000000"

        service._provider = mock_provider

        result = await service.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<h1>Test</h1>",
        )

        assert result is True
        mock_provider.send_email.assert_called_once()


@pytest.mark.asyncio
async def test_email_service_provider_not_configured():
    """Test EmailService when provider is not configured."""
    service = EmailService()

    mock_provider = AsyncMock()
    mock_provider.is_configured.return_value = False

    service._provider = mock_provider

    result = await service.send_email(
        to_email="recipient@example.com",
        subject="Test Subject",
        html_body="<h1>Test</h1>",
    )

    assert result is False
    mock_provider.send_email.assert_not_called()


@pytest.mark.asyncio
async def test_email_service_provider_send_error():
    """Test EmailService error handling when provider send fails."""
    service = EmailService()

    mock_provider = AsyncMock()
    mock_provider.is_configured.return_value = True
    mock_provider.send_email.side_effect = Exception("Send failed")

    service._provider = mock_provider

    result = await service.send_email(
        to_email="recipient@example.com",
        subject="Test Subject",
        html_body="<h1>Test</h1>",
    )

    assert result is False  # Should return False on error, not raise


def test_email_service_default_provider():
    """Test EmailService defaults to SMTP provider."""
    with patch.dict(os.environ, {}, clear=True):
        service = EmailService()
        # Should default to SMTP when EMAIL_PROVIDER is not set
        provider = service._get_provider()
        assert isinstance(provider, SMTPEmailProvider)


def test_email_service_ses_provider_selection():
    """Test EmailService selects SES provider when configured."""
    with patch.dict(os.environ, {"EMAIL_PROVIDER": "ses"}):
        service = EmailService()
        provider = service._get_provider()
        assert isinstance(provider, SESEmailProvider)


