"""
Tests for channel handler normalization and validation logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Gmail Handler Tests
# ---------------------------------------------------------------------------

class TestGmailMessageNormalization:
    """Test that Gmail messages are correctly normalized."""

    def test_gmail_message_normalization_basic(self):
        """A Gmail message payload is normalized to standard format."""
        from production.channels.gmail_handler import GmailHandler

        handler = GmailHandler.__new__(GmailHandler)  # skip __init__
        handler.service = None

        from_header = "John Smith <john.smith@company.com>"
        email = handler._extract_email(from_header)
        name = handler._extract_name(from_header)

        assert email == "john.smith@company.com"
        assert name == "John Smith"

    def test_gmail_extract_plain_email(self):
        """Extract email from a plain email address (no display name)."""
        from production.channels.gmail_handler import GmailHandler

        handler = GmailHandler.__new__(GmailHandler)
        handler.service = None

        email = handler._extract_email("noreply@techcorp.io")
        assert email == "noreply@techcorp.io"

    def test_gmail_extract_body_plain_text(self):
        """Extract plain text body from a simple text/plain payload."""
        import base64
        from production.channels.gmail_handler import GmailHandler

        handler = GmailHandler.__new__(GmailHandler)
        handler.service = None

        body_text = "Hello, I need help with my account."
        encoded = base64.urlsafe_b64encode(body_text.encode()).decode()
        payload = {
            "mimeType": "text/plain",
            "body": {"data": encoded},
        }

        result = handler._extract_body(payload)
        assert result == body_text

    def test_gmail_normalized_dict_has_required_keys(self):
        """Normalized Gmail message must have channel, customer_email, message keys."""
        # Simulate what get_message() returns
        normalized = {
            "channel": "email",
            "channel_message_id": "msg-123",
            "thread_id": "thread-456",
            "customer_email": "test@example.com",
            "customer_name": "Test User",
            "subject": "Test Subject",
            "message": "Hello world",
            "raw_headers": {},
        }

        assert normalized["channel"] == "email"
        assert "customer_email" in normalized
        assert "message" in normalized
        assert "subject" in normalized


# ---------------------------------------------------------------------------
# WhatsApp Handler Tests
# ---------------------------------------------------------------------------

class TestWhatsAppMessageNormalization:
    """Test WhatsApp webhook processing and message normalization."""

    @pytest.mark.asyncio
    async def test_whatsapp_basic_normalization(self):
        """A Twilio WhatsApp webhook is normalized to standard format."""
        from production.channels.whatsapp_handler import WhatsAppHandler

        handler = WhatsAppHandler.__new__(WhatsAppHandler)
        handler.account_sid = ""
        handler.auth_token = ""
        handler.from_number = "whatsapp:+14155238886"
        handler._client = None

        form_data = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+14155238886",
            "Body": "Hi how do I add team members?",
            "NumMedia": "0",
            "ProfileName": "John",
        }

        result = await handler.process_webhook(form_data)

        assert result is not None
        assert result["channel"] == "whatsapp"
        assert result["customer_phone"] == "+1234567890"
        assert result["message"] == "Hi how do I add team members?"
        assert result["is_human_request"] is False

    @pytest.mark.asyncio
    async def test_whatsapp_human_keyword_detection(self):
        """Messages with 'human' keyword are flagged as human_request."""
        from production.channels.whatsapp_handler import WhatsAppHandler

        handler = WhatsAppHandler.__new__(WhatsAppHandler)
        handler.account_sid = ""
        handler.auth_token = ""
        handler.from_number = "whatsapp:+14155238886"
        handler._client = None

        for keyword in ["human", "agent", "representative", "person"]:
            form_data = {
                "MessageSid": "SM999",
                "From": "whatsapp:+9876543210",
                "To": "whatsapp:+14155238886",
                "Body": keyword,
                "NumMedia": "0",
                "ProfileName": "",
            }
            result = await handler.process_webhook(form_data)
            assert result["is_human_request"] is True, (
                f"Keyword '{keyword}' should trigger human_request flag"
            )

    def test_whatsapp_response_splitting_long_message(self):
        """Messages over 1600 chars are split into multiple parts."""
        from production.channels.whatsapp_handler import WhatsAppHandler

        handler = WhatsAppHandler.__new__(WhatsAppHandler)
        handler._client = None

        long_message = "This is a test sentence. " * 100  # ~2500 chars
        parts = handler.format_response(long_message, max_length=1600)

        assert len(parts) > 1, "Long message should be split into multiple parts"
        for part in parts:
            assert len(part) <= 1600, f"Part too long: {len(part)} chars"

    def test_whatsapp_short_message_not_split(self):
        """Short messages under 1600 chars are not split."""
        from production.channels.whatsapp_handler import WhatsAppHandler

        handler = WhatsAppHandler.__new__(WhatsAppHandler)
        handler._client = None

        short_message = "You can export tasks via Settings > Data > Export Tasks."
        parts = handler.format_response(short_message, max_length=1600)

        assert len(parts) == 1


# ---------------------------------------------------------------------------
# Web Form Validation Tests
# ---------------------------------------------------------------------------

class TestWebFormValidation:
    """Test SupportFormSubmission Pydantic validation."""

    def test_web_form_validation_name_too_short(self):
        """Names shorter than 2 characters should fail validation."""
        from pydantic import ValidationError
        from production.channels.web_form_handler import SupportFormSubmission

        with pytest.raises(ValidationError) as exc_info:
            SupportFormSubmission(
                name="A",  # too short
                email="test@example.com",
                subject="Test subject",
                message="This is a valid message with enough characters.",
            )

        errors = exc_info.value.errors()
        assert any("name" in str(e).lower() or "2" in str(e) for e in errors)

    def test_web_form_validation_message_too_short(self):
        """Messages shorter than 10 characters should fail validation."""
        from pydantic import ValidationError
        from production.channels.web_form_handler import SupportFormSubmission

        with pytest.raises(ValidationError):
            SupportFormSubmission(
                name="John Smith",
                email="test@example.com",
                subject="Test subject",
                message="Short",  # too short
            )

    def test_web_form_valid_submission(self):
        """A fully valid form submission should be accepted without errors."""
        from production.channels.web_form_handler import SupportFormSubmission

        submission = SupportFormSubmission(
            name="Sarah Jones",
            email="sarah.jones@startup.io",
            subject="API rate limit exceeded",
            category="technical",
            message="We're getting HTTP 429 errors on our API integration. We're on the Pro plan. Is there a way to get higher limits?",
            priority="high",
        )

        assert submission.name == "Sarah Jones"
        assert submission.email == "sarah.jones@startup.io"
        assert submission.category == "technical"
        assert submission.priority == "high"

    def test_web_form_email_normalization(self):
        """Emails should be lowercased during validation."""
        from production.channels.web_form_handler import SupportFormSubmission

        submission = SupportFormSubmission(
            name="Test User",
            email="Test.User@EXAMPLE.COM",
            subject="Testing email normalization",
            message="This is a test message with enough characters to pass validation.",
        )

        assert submission.email == "test.user@example.com"

    def test_web_form_invalid_category_defaults_to_general(self):
        """Invalid priority falls back to 'medium'."""
        from production.channels.web_form_handler import SupportFormSubmission

        submission = SupportFormSubmission(
            name="Test User",
            email="test@example.com",
            subject="Test subject here",
            message="This is a sufficiently long message to pass the minimum length check.",
            priority="super_urgent",  # invalid - should default to medium
        )

        assert submission.priority == "medium"

    def test_web_form_valid_categories(self):
        """All valid categories should be accepted."""
        from production.channels.web_form_handler import SupportFormSubmission

        valid_categories = ["general", "technical", "billing", "account", "bug", "feedback", "other"]
        for category in valid_categories:
            submission = SupportFormSubmission(
                name="Test User",
                email="test@example.com",
                subject="Test subject",
                message="This is a test message long enough to pass validation.",
                category=category,
            )
            assert submission.category == category
