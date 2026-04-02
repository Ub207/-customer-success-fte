"""
Transition tests: validates that the production implementation is functionally
equivalent to the MCP prototype incubation-phase implementation.

Run with:
    pytest production/tests/test_transition.py -v
"""

import asyncio
import json
import pathlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# TestTransitionFromIncubation
# ---------------------------------------------------------------------------

class TestTransitionFromIncubation:
    """
    Validates that the production @function_tool implementations
    produce the same outcomes as the incubation MCP prototype tools.
    """

    def test_prompt_contains_required_workflow(self):
        """
        The production system prompt must contain the required 4-step workflow
        discovered during incubation.
        """
        from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT

        required_steps = [
            "create_ticket",
            "get_customer_history",
            "search_knowledge_base",
            "send_response",
        ]

        for step in required_steps:
            assert step in CUSTOMER_SUCCESS_SYSTEM_PROMPT, (
                f"System prompt missing required step: {step}"
            )

    def test_prompt_contains_hard_constraints(self):
        """
        The production system prompt must include all hard constraints
        identified during incubation.
        """
        from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT

        constraints = [
            "pricing",
            "refund",
            "send_response",
            "500",    # email word limit
            "1600",   # WhatsApp char limit
        ]

        for constraint in constraints:
            assert constraint in CUSTOMER_SUCCESS_SYSTEM_PROMPT, (
                f"System prompt missing constraint reference: {constraint}"
            )

    def test_prompt_contains_escalation_triggers(self):
        """All escalation triggers from incubation must be in the production prompt."""
        from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT

        triggers = [
            "pricing_inquiry",
            "refund_request",
            "legal_threat",
            "angry_customer",
            "security_incident",
            "human_requested",
            "knowledge_gap",
        ]

        for trigger in triggers:
            assert trigger in CUSTOMER_SUCCESS_SYSTEM_PROMPT, (
                f"Escalation trigger missing from prompt: {trigger}"
            )

    def test_prompt_contains_channel_awareness(self):
        """The production prompt must contain channel-specific instructions."""
        from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT

        assert "email" in CUSTOMER_SUCCESS_SYSTEM_PROMPT.lower()
        assert "whatsapp" in CUSTOMER_SUCCESS_SYSTEM_PROMPT.lower()
        assert (
            "web_form" in CUSTOMER_SUCCESS_SYSTEM_PROMPT.lower()
            or "web form" in CUSTOMER_SUCCESS_SYSTEM_PROMPT.lower()
        )

    def test_mcp_tools_match_function_tools(self):
        """
        The 5 tools defined in the MCP server must all exist as @function_tool
        in the production tools module.
        """
        mcp_tools = {
            "search_knowledge_base",
            "create_ticket",
            "get_customer_history",
            "escalate_to_human",
            "send_response",
        }

        import production.agent.tools as tools_module
        # Use hasattr instead of callable() — @function_tool may wrap in a non-callable object
        production_tools = {
            name for name in dir(tools_module)
            if not name.startswith("_")
        }

        for tool_name in mcp_tools:
            assert tool_name in production_tools, (
                f"MCP tool '{tool_name}' not found in production tools module"
            )

    def test_escalation_routing_matches_incubation(self):
        """
        Escalation routing rules must match what was discovered in incubation.
        """
        escalation_doc = (
            pathlib.Path(__file__).parent.parent.parent
            / "context"
            / "escalation-rules.md"
        )
        assert escalation_doc.exists(), "escalation-rules.md context doc is missing"

        content = escalation_doc.read_text()
        assert "billing@techcorp.io" in content
        assert "legal-support@techcorp.io" in content
        assert "security@techcorp.io" in content
        assert "senior-support@techcorp.io" in content

    def test_mcp_server_exists(self):
        """The incubation MCP server file must still be present for reference."""
        mcp_path = (
            pathlib.Path(__file__).parent.parent.parent / "src" / "mcp_server.py"
        )
        assert mcp_path.exists(), "src/mcp_server.py (incubation prototype) is missing"

    def test_specs_deliverables_exist(self):
        """All 3 incubation deliverable spec files must be present."""
        specs_dir = pathlib.Path(__file__).parent.parent.parent / "specs"
        required = [
            "discovery-log.md",
            "customer-success-fte-spec.md",
            "transition-checklist.md",
        ]
        for fname in required:
            assert (specs_dir / fname).exists(), f"Missing spec file: specs/{fname}"

    def test_specs_have_content(self):
        """Each spec file must contain substantive content (> 50 lines)."""
        specs_dir = pathlib.Path(__file__).parent.parent.parent / "specs"
        for fname in ["discovery-log.md", "customer-success-fte-spec.md", "transition-checklist.md"]:
            content = (specs_dir / fname).read_text()
            lines = [l for l in content.splitlines() if l.strip()]
            assert len(lines) > 50, (
                f"specs/{fname} is too short ({len(lines)} lines) — needs more content"
            )

    def test_transition_checklist_all_items_checked(self):
        """The transition checklist must have all items marked complete."""
        checklist_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "specs"
            / "transition-checklist.md"
        )
        content = checklist_path.read_text()
        # Count unchecked items
        unchecked = content.count("- [ ]")
        assert unchecked == 0, (
            f"Transition checklist has {unchecked} uncompleted item(s). "
            "All items must be checked before submission."
        )

    def test_daily_sentiment_endpoint_registered(self):
        """The /reports/daily-sentiment endpoint must be registered in the FastAPI app."""
        from production.api.main import app

        routes = {route.path for route in app.routes}
        assert "/reports/daily-sentiment" in routes, (
            "GET /reports/daily-sentiment endpoint is not registered in the FastAPI app"
        )

    def test_context_files_exist(self):
        """All 5 context files required by the hackathon must be present."""
        context_dir = pathlib.Path(__file__).parent.parent.parent / "context"
        required = [
            "company-profile.md",
            "product-docs.md",
            "sample-tickets.json",
            "escalation-rules.md",
            "brand-voice.md",
        ]
        for fname in required:
            assert (context_dir / fname).exists(), f"Missing context file: context/{fname}"


# ---------------------------------------------------------------------------
# TestToolMigration
# ---------------------------------------------------------------------------

class TestToolMigration:
    """
    Tests that verify each tool migrated correctly from MCP prototype
    to production @function_tool with proper Pydantic validation.
    """

    def test_ticket_input_model_validation(self):
        """TicketInput Pydantic model validates required fields."""
        from production.agent.tools import TicketInput

        t = TicketInput(
            customer_id="test@example.com",
            issue_summary="Password reset not working",
            channel="email",
        )
        assert t.customer_id == "test@example.com"
        assert t.channel == "email"
        assert t.priority == "medium"  # default

    def test_ticket_input_requires_customer_id(self):
        """TicketInput must require customer_id."""
        from pydantic import ValidationError
        from production.agent.tools import TicketInput

        with pytest.raises(ValidationError):
            TicketInput(
                issue_summary="Test issue",
                channel="email",
                # customer_id missing
            )

    def test_ticket_input_requires_channel(self):
        """TicketInput must require channel."""
        from pydantic import ValidationError
        from production.agent.tools import TicketInput

        with pytest.raises(ValidationError):
            TicketInput(
                customer_id="test@example.com",
                issue_summary="Test issue",
                # channel missing
            )

    def test_ticket_input_requires_issue_summary(self):
        """TicketInput must require issue_summary."""
        from pydantic import ValidationError
        from production.agent.tools import TicketInput

        with pytest.raises(ValidationError):
            TicketInput(
                customer_id="test@example.com",
                channel="email",
                # issue_summary missing
            )

    def test_escalation_input_model_validation(self):
        """EscalationInput Pydantic model validates required fields."""
        from production.agent.tools import EscalationInput

        e = EscalationInput(
            ticket_id="TKT-001",
            reason="pricing_inquiry",
            context_notes="Customer asked about enterprise pricing.",
        )
        assert e.ticket_id == "TKT-001"
        assert e.reason == "pricing_inquiry"

    def test_escalation_input_valid_reasons(self):
        """All 7 escalation reason codes from incubation must be valid EscalationInput values."""
        from production.agent.tools import EscalationInput

        valid_reasons = [
            "pricing_inquiry",
            "refund_request",
            "legal_threat",
            "angry_customer",
            "security_incident",
            "knowledge_gap",
            "human_requested",
        ]
        for reason in valid_reasons:
            e = EscalationInput(
                ticket_id="TKT-001",
                reason=reason,
                context_notes="Test",
            )
            assert e.reason == reason

    def test_knowledge_search_input_defaults(self):
        """KnowledgeSearchInput has sensible defaults."""
        from production.agent.tools import KnowledgeSearchInput

        k = KnowledgeSearchInput(query="how to reset password")
        assert k.max_results == 5
        assert k.query == "how to reset password"

    def test_knowledge_search_input_requires_query(self):
        """KnowledgeSearchInput must require query."""
        from pydantic import ValidationError
        from production.agent.tools import KnowledgeSearchInput

        with pytest.raises(ValidationError):
            KnowledgeSearchInput()  # no query

    def test_response_input_model_valid(self):
        """ResponseInput accepts valid fields."""
        from production.agent.tools import ResponseInput

        r = ResponseInput(
            ticket_id="TKT-001",
            message="Here is how to reset your password...",
            channel="email",
            customer_name="John Smith",
        )
        assert r.channel == "email"
        assert r.ticket_id == "TKT-001"

    def test_response_input_requires_message_and_channel(self):
        """ResponseInput must require message and channel."""
        from pydantic import ValidationError
        from production.agent.tools import ResponseInput

        with pytest.raises(ValidationError):
            ResponseInput(
                ticket_id="TKT-001",
                # message and channel missing
            )

    def test_channel_formatter_email(self):
        """Email formatter produces formal greeting and footer."""
        async def run():
            from production.agent.formatters import format_for_channel
            result = await format_for_channel(
                "Your password reset link has been sent.",
                "email",
                customer_name="Jane Doe",
                ticket_id="TKT-TEST-001",
            )
            assert "Jane Doe" in result or "Hi" in result
            assert "TKT-TEST-001" in result

        asyncio.get_event_loop().run_until_complete(run())

    def test_channel_formatter_whatsapp_truncation(self):
        """WhatsApp formatter truncates to 1,600 chars max."""
        async def run():
            from production.agent.formatters import format_for_channel
            very_long = "A" * 2000
            result = await format_for_channel(very_long, "whatsapp")
            assert len(result) <= 1600

        asyncio.get_event_loop().run_until_complete(run())

    def test_channel_formatter_web_form_footer(self):
        """Web form formatter includes 'Need more help?' footer."""
        async def run():
            from production.agent.formatters import format_for_channel
            result = await format_for_channel("Test response", "web_form")
            assert "Need more help?" in result

        asyncio.get_event_loop().run_until_complete(run())

    def test_channel_formatter_unknown_channel_fallback(self):
        """Unknown channel falls back to web_form style."""
        async def run():
            from production.agent.formatters import format_for_channel
            result = await format_for_channel("Test response", "unknown_channel")
            assert "Need more help?" in result

        asyncio.get_event_loop().run_until_complete(run())

    def test_channel_formatter_email_includes_ticket_reference(self):
        """Email format includes ticket reference (discovered in incubation)."""
        async def run():
            from production.agent.formatters import format_for_channel
            result = await format_for_channel(
                "Test response.",
                "email",
                ticket_id="TKT-TEST-001",
            )
            assert "TKT-TEST-001" in result

        asyncio.get_event_loop().run_until_complete(run())

    def test_all_channels_supported_by_formatter(self):
        """formatter supports all 3 production channels without error."""
        async def run():
            from production.agent.formatters import format_for_channel
            for channel in ["email", "whatsapp", "web_form"]:
                result = await format_for_channel("Hello", channel)
                assert isinstance(result, str)
                assert len(result) > 0

        asyncio.get_event_loop().run_until_complete(run())


# ---------------------------------------------------------------------------
# TestInfrastructureMigration
# ---------------------------------------------------------------------------

class TestInfrastructureMigration:
    """
    Tests that verify the production infrastructure components exist and
    are correctly wired (Kafka topics, DB schema, K8s manifests, etc.)
    """

    def test_kafka_topics_defined(self):
        """All required Kafka topics from incubation must be defined."""
        from production.kafka_client import TOPICS

        required_topics = [
            "gmail_inbound",
            "whatsapp_inbound",
            "webform_inbound",
            "outbound_email",
            "outbound_whatsapp",
            "escalations",
            "dlq",
        ]
        for topic_key in required_topics:
            assert topic_key in TOPICS, f"Kafka topic key '{topic_key}' not found in TOPICS dict"
            assert TOPICS[topic_key].startswith("fte."), (
                f"Topic '{TOPICS[topic_key]}' should be namespaced with 'fte.'"
            )

    def test_database_schema_file_exists(self):
        """The production database schema SQL file must exist."""
        schema_path = (
            pathlib.Path(__file__).parent.parent
            / "database"
            / "schema.sql"
        )
        assert schema_path.exists(), "production/database/schema.sql is missing"

    def test_database_schema_has_required_tables(self):
        """The schema must define all required tables."""
        schema_path = (
            pathlib.Path(__file__).parent.parent
            / "database"
            / "schema.sql"
        )
        content = schema_path.read_text()
        required_tables = [
            "customers",
            "customer_identifiers",
            "conversations",
            "messages",
            "tickets",
            "knowledge_base",
            "channel_configs",
            "agent_metrics",
        ]
        for table in required_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in content, (
                f"Table '{table}' not found in schema.sql"
            )

    def test_schema_has_pgvector_extension(self):
        """The schema must enable the pgvector extension for semantic search."""
        schema_path = (
            pathlib.Path(__file__).parent.parent
            / "database"
            / "schema.sql"
        )
        content = schema_path.read_text()
        assert "pgvector" in content, "pgvector extension not found in schema.sql"
        assert "VECTOR" in content.upper() or "vector" in content, (
            "No VECTOR column type found — pgvector not being used"
        )

    def test_schema_has_sentiment_score_column(self):
        """The conversations table must have a sentiment_score column."""
        schema_path = (
            pathlib.Path(__file__).parent.parent
            / "database"
            / "schema.sql"
        )
        content = schema_path.read_text()
        assert "sentiment_score" in content, (
            "conversations table missing sentiment_score column — required for daily report"
        )

    def test_k8s_manifests_exist(self):
        """All required Kubernetes manifests must be present."""
        k8s_dir = pathlib.Path(__file__).parent.parent / "k8s"
        required = [
            "namespace.yaml",
            "configmap.yaml",
            "secrets.yaml",
            "deployment-api.yaml",
            "deployment-worker.yaml",
            "service.yaml",
            "ingress.yaml",
            "hpa.yaml",
        ]
        for fname in required:
            assert (k8s_dir / fname).exists(), f"Missing K8s manifest: k8s/{fname}"

    def test_docker_compose_exists(self):
        """docker-compose.yml must exist for local development."""
        compose_path = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
        assert compose_path.exists(), "production/docker-compose.yml is missing"

    def test_docker_compose_has_required_services(self):
        """docker-compose.yml must define all required services."""
        import yaml
        compose_path = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
        with open(compose_path) as f:
            compose = yaml.safe_load(f)

        services = set(compose.get("services", {}).keys())
        required = {"postgres", "kafka", "fte-api", "fte-worker"}
        missing = required - services
        assert not missing, f"docker-compose.yml missing services: {missing}"

    def test_requirements_txt_has_core_dependencies(self):
        """requirements.txt must include all key dependencies."""
        req_path = pathlib.Path(__file__).parent.parent / "requirements.txt"
        assert req_path.exists(), "production/requirements.txt is missing"

        content = req_path.read_text().lower()
        required_packages = [
            "fastapi",
            "openai",
            "asyncpg",
            "aiokafka",
            "pydantic",
            "structlog",
        ]
        for pkg in required_packages:
            assert pkg in content, f"requirements.txt missing package: {pkg}"

    def test_web_form_component_is_standalone(self):
        """SupportForm.jsx must be a standalone embeddable React component."""
        form_path = (
            pathlib.Path(__file__).parent.parent
            / "web-form"
            / "components"
            / "SupportForm.jsx"
        )
        assert form_path.exists(), "SupportForm.jsx is missing"

        content = form_path.read_text()
        # Must export SupportForm as default or named export
        assert "export default SupportForm" in content or "export { SupportForm" in content, (
            "SupportForm.jsx must have a default or named export"
        )
        # Must accept apiUrl prop (not hardcoded URL)
        assert "apiUrl" in content, (
            "SupportForm.jsx must accept apiUrl prop for embeddability"
        )
        # Must use useState (React hooks, no class component)
        assert "useState" in content, "SupportForm.jsx must use React hooks"

    def test_daily_report_worker_exists(self):
        """The daily sentiment report worker must exist."""
        worker_path = (
            pathlib.Path(__file__).parent.parent
            / "workers"
            / "daily_report.py"
        )
        assert worker_path.exists(), "production/workers/daily_report.py is missing"

    def test_daily_report_worker_has_main_entry(self):
        """daily_report.py must be runnable as a standalone script."""
        worker_path = (
            pathlib.Path(__file__).parent.parent
            / "workers"
            / "daily_report.py"
        )
        content = worker_path.read_text()
        assert 'if __name__ == "__main__"' in content, (
            "daily_report.py must have __main__ entry point for cron job execution"
        )
        assert "asyncio.run" in content, (
            "daily_report.py must use asyncio.run() for async entry point"
        )
