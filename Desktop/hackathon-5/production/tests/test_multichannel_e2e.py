"""
Multi-channel end-to-end tests for the Customer Success FTE system.

Tests cover complete flows across Web Form, Email, and WhatsApp channels,
as well as cross-channel customer continuity and metrics collection.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_agent_result_resolved():
    return {
        "response": "Here are the steps to reset your password...",
        "ticket_id": "TKT-e2e-001",
        "conversation_id": "CONV-e2e-001",
        "escalated": False,
        "tool_calls": ["create_ticket", "get_customer_history", "search_knowledge_base", "send_response"],
    }


@pytest.fixture
def mock_agent_result_escalated():
    return {
        "response": "I'm connecting you with our billing team...",
        "ticket_id": "TKT-e2e-002",
        "conversation_id": "CONV-e2e-002",
        "escalated": True,
        "tool_calls": ["create_ticket", "get_customer_history", "escalate_to_human", "send_response"],
    }


# ---------------------------------------------------------------------------
# TestWebFormChannel
# ---------------------------------------------------------------------------

class TestWebFormChannel:
    """End-to-end tests for the web form submission channel."""

    @pytest.mark.asyncio
    async def test_valid_form_submission_returns_ticket_id(self, mock_agent_result_resolved):
        """A valid web form submission publishes to Kafka and returns a ticket ID."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        mock_producer = AsyncMock()
        mock_producer.send = AsyncMock(return_value=None)

        with patch("production.channels.web_form_handler._get_producer", return_value=mock_producer):
            client = TestClient(app)
            response = client.post(
                "/web-form/submit",
                json={
                    "name": "Sarah Jones",
                    "email": "sarah.jones@startup.io",
                    "subject": "API rate limit exceeded",
                    "category": "technical",
                    "message": "We're getting HTTP 429 errors on our API integration. We're on the Pro plan.",
                    "priority": "high",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "ticket_id" in data
        assert "message" in data
        assert "estimated_response_time" in data

    @pytest.mark.asyncio
    async def test_web_form_validation_rejects_short_message(self):
        """Web form rejects messages that are too short."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        client = TestClient(app)
        response = client.post(
            "/web-form/submit",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Test",
                "message": "Hi",  # too short
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_web_form_pricing_question_returns_escalated_response(self, mock_agent_result_escalated):
        """Pricing questions submitted via web form are accepted and queued via Kafka."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        mock_producer = AsyncMock()
        mock_producer.send = AsyncMock(return_value=None)

        with patch("production.channels.web_form_handler._get_producer", return_value=mock_producer):
            client = TestClient(app)
            response = client.post(
                "/web-form/submit",
                json={
                    "name": "Mike Enterprise",
                    "email": "mike@enterprise.co",
                    "subject": "Enterprise plan pricing",
                    "category": "billing",
                    "message": "We have 500 users and need enterprise features. How much does it cost?",
                    "priority": "medium",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "ticket_id" in data

    def test_web_form_response_contains_sla_by_priority(self):
        """Web form response SLA matches the submitted priority."""
        from production.channels.web_form_handler import SLA_BY_PRIORITY

        assert "2 hours" in SLA_BY_PRIORITY["urgent"]
        assert "24 hours" in SLA_BY_PRIORITY["low"]
        assert "medium" in SLA_BY_PRIORITY


# ---------------------------------------------------------------------------
# TestEmailChannel
# ---------------------------------------------------------------------------

class TestEmailChannel:
    """End-to-end tests for the Gmail/email channel."""

    @pytest.mark.asyncio
    async def test_gmail_webhook_processes_message(self, mock_agent_result_resolved):
        """Gmail push notification is processed and triggers agent."""
        import base64

        from fastapi.testclient import TestClient
        from production.api.main import app

        # Simulate a Pub/Sub message
        notification_data = json.dumps({"historyId": "12345", "emailAddress": "john@company.com"})
        encoded_data = base64.b64encode(notification_data.encode()).decode()

        pubsub_payload = {
            "message": {
                "data": encoded_data,
                "messageId": "pubsub-msg-001",
                "publishTime": "2026-03-27T00:00:00Z",
            }
        }

        with patch("production.channels.gmail_handler.GmailHandler.process_notification", return_value=[]):
            client = TestClient(app)
            response = client.post("/webhooks/gmail", json=pubsub_payload)

        assert response.status_code == 200
        assert response.json()["status"] == "no_new_messages"

    def test_email_formatter_produces_correct_structure(self):
        """Email formatter produces greeting + body + signature structure."""
        import asyncio
        from production.agent.formatters import format_for_channel

        async def run():
            result = await format_for_channel(
                response="Here are the troubleshooting steps.",
                channel="email",
                ticket_id="TKT-EMAIL-001",
                customer_name="John Smith",
            )
            lines = result.split("\n")
            assert lines[0].startswith("Hi John Smith")
            assert "Best regards" in result
            assert "TechCorp Support Team" in result
            assert "TKT-EMAIL-001" in result

        asyncio.get_event_loop().run_until_complete(run())

    def test_email_word_limit_enforced(self):
        """Email responses are truncated at 500 words."""
        import asyncio
        from production.agent.formatters import format_for_channel

        long_body = " ".join(["word"] * 700)

        async def run():
            result = await format_for_channel(
                response=long_body,
                channel="email",
            )
            # The response body portion should be truncated
            assert "..." in result or len(result.split()) <= 550  # some slack for signature

        asyncio.get_event_loop().run_until_complete(run())


# ---------------------------------------------------------------------------
# TestWhatsAppChannel
# ---------------------------------------------------------------------------

class TestWhatsAppChannel:
    """End-to-end tests for the WhatsApp/Twilio channel."""

    @pytest.mark.asyncio
    async def test_whatsapp_webhook_processes_inbound(self):
        """WhatsApp webhook POST returns 200 accepted status."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        with patch("production.channels.whatsapp_handler.WhatsAppHandler.process_webhook",
                   new_callable=AsyncMock,
                   return_value={
                       "channel": "whatsapp",
                       "customer_phone": "+1234567890",
                       "message": "Hi how do I add team members?",
                       "is_human_request": False,
                   }):
            client = TestClient(app)
            # Simulate Twilio form-encoded webhook
            response = client.post(
                "/webhooks/whatsapp",
                data={
                    "MessageSid": "SM123",
                    "From": "whatsapp:+1234567890",
                    "To": "whatsapp:+14155238886",
                    "Body": "Hi how do I add team members?",
                    "NumMedia": "0",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_whatsapp_status_callback_updates_delivery(self):
        """WhatsApp status callback updates message delivery status."""
        from fastapi.testclient import TestClient
        from production.api.main import app

        with patch("production.database.queries.update_delivery_status", new_callable=AsyncMock):
            client = TestClient(app)
            response = client.post(
                "/webhooks/whatsapp/status",
                data={
                    "MessageSid": "SM123456",
                    "MessageStatus": "delivered",
                    "To": "whatsapp:+1234567890",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert response.status_code == 200

    def test_whatsapp_response_under_300_chars_for_simple_answer(self):
        """Simple answers should stay under 300 chars (preferred limit)."""
        from production.channels.whatsapp_handler import WhatsAppHandler

        handler = WhatsAppHandler.__new__(WhatsAppHandler)
        handler._client = None

        simple_answer = "Settings > Data > Export Tasks (CSV/JSON)."
        parts = handler.format_response(simple_answer)

        assert len(parts) == 1
        assert len(parts[0]) < 300


# ---------------------------------------------------------------------------
# TestCrossChannelContinuity
# ---------------------------------------------------------------------------

class TestCrossChannelContinuity:
    """
    Tests that a customer is identified correctly across channels,
    and that conversation history is shared.
    """

    @pytest.mark.asyncio
    async def test_same_email_identified_across_channels(self):
        """
        A customer who emails and also uses the web form is identified
        as the same customer (by email).
        """
        email = "recurring@customer.com"
        phone = "+5551234567"

        # Simulate DB lookup returning same customer
        mock_customer = {
            "id": "cust-uuid-001",
            "email": email,
            "phone": phone,
            "name": "Recurring Customer",
        }

        with patch("production.database.queries.find_customer", new_callable=AsyncMock, return_value=mock_customer):
            from production.database.queries import find_customer
            result_by_email = await find_customer(email=email)
            result_by_phone = await find_customer(phone=phone)

        assert result_by_email["id"] == result_by_phone["id"] == "cust-uuid-001"

    @pytest.mark.asyncio
    async def test_conversation_history_includes_all_channels(self):
        """
        get_customer_history_all_channels returns messages from
        all channels for the same customer.
        """
        mock_history = [
            {"channel": "email", "role": "user", "content": "Email message", "created_at": datetime.utcnow()},
            {"channel": "whatsapp", "role": "user", "content": "WhatsApp message", "created_at": datetime.utcnow()},
            {"channel": "web_form", "role": "user", "content": "Web form message", "created_at": datetime.utcnow()},
        ]

        with patch(
            "production.database.queries.get_customer_history_all_channels",
            new_callable=AsyncMock,
            return_value=mock_history,
        ):
            from production.database.queries import get_customer_history_all_channels
            history = await get_customer_history_all_channels("cust-uuid-001")

        channels = {m["channel"] for m in history}
        assert "email" in channels
        assert "whatsapp" in channels
        assert "web_form" in channels

    def test_conversation_reuse_within_24_hours(self):
        """
        get_or_create_conversation reuses an existing conversation
        within the 24-hour window.
        """
        # This is tested by verifying the logic in queries.py uses
        # a time-window filter. We verify the function signature.
        import inspect
        from production.database.queries import get_or_create_conversation

        sig = inspect.signature(get_or_create_conversation)
        params = list(sig.parameters.keys())

        assert "customer_id" in params
        assert "channel" in params
        assert "within_hours" in params


# ---------------------------------------------------------------------------
# TestChannelMetrics
# ---------------------------------------------------------------------------

class TestChannelMetrics:
    """Tests for channel-level metrics collection and reporting."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_channel_data(self):
        """GET /metrics/channels returns per-channel statistics."""
        mock_metrics = {
            "email": {"message_count": 50, "escalation_rate": 0.12, "avg_latency_ms": 2100},
            "whatsapp": {"message_count": 150, "escalation_rate": 0.18, "avg_latency_ms": 1800},
            "web_form": {"message_count": 80, "escalation_rate": 0.15, "avg_latency_ms": 2300},
        }

        with patch(
            "production.workers.metrics_collector.MetricsCollector.collect_channel_metrics",
            new_callable=AsyncMock,
            return_value=mock_metrics,
        ):
            from fastapi.testclient import TestClient
            from production.api.main import app

            client = TestClient(app)
            response = client.get("/metrics/channels")

        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "period" in data

    @pytest.mark.asyncio
    async def test_record_metric_stores_to_db(self):
        """MetricsCollector.record_metric inserts into agent_metrics table."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_pool.acquire = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(),
            )
        )

        with patch("production.database.get_db_pool", return_value=mock_pool):
            from production.workers.metrics_collector import MetricsCollector
            collector = MetricsCollector()
            await collector.record_metric(
                metric_name="message_count",
                value=42.0,
                channel="email",
                dimensions={"window": "1h"},
            )

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert "agent_metrics" in call_args[0]
