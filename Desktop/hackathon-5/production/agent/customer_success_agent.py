"""
Customer Success FTE — OpenAI Agents SDK agent definition.

Provider priority (first key found wins):
  OPENAI_API_KEY  → GPT-4o  (paid)
  GROQ_API_KEY    → llama-3.3-70b-versatile via Groq (free tier)
  GEMINI_API_KEY  → gemini-1.5-flash via Google AI Studio (free tier)

The agent is initialized lazily on the first call to run_agent() so that
environment variables are guaranteed to be loaded before model selection.
"""

import os
import time
import structlog

logger = structlog.get_logger(__name__)

try:
    from agents import Agent, Runner, OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    AGENTS_SDK_AVAILABLE = True
except ImportError:
    AGENTS_SDK_AVAILABLE = False
    Agent = Runner = OpenAIChatCompletionsModel = AsyncOpenAI = None

from production.agent.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response,
)
from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------

_agent = None


def _build_model():
    """
    Select the LLM provider based on available API keys.
    Returns a model name string (OpenAI) or an OpenAIChatCompletionsModel
    (Groq / Gemini via OpenAI-compatible endpoint).
    """
    openai_key = os.getenv("OPENAI_API_KEY", "")
    groq_key   = os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    if openai_key and not openai_key.startswith("sk-placeholder"):
        logger.info("Agent provider: OpenAI (gpt-4o)")
        return "gpt-4o"

    if groq_key:
        logger.info("Agent provider: Groq (llama-3.3-70b-versatile) — free tier")
        client = AsyncOpenAI(
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1",
        )
        return OpenAIChatCompletionsModel(
            model="llama-3.3-70b-versatile",
            openai_client=client,
        )

    if gemini_key:
        logger.info("Agent provider: Google Gemini (gemini-1.5-flash) — free tier")
        client = AsyncOpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        return OpenAIChatCompletionsModel(
            model="gemini-1.5-flash",
            openai_client=client,
        )

    logger.warning("No valid API key found. Set OPENAI_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY.")
    return "gpt-4o"  # will fail at runtime without a key


def _get_agent() -> "Agent":
    """Return the singleton agent, building it on first call."""
    global _agent
    if _agent is None:
        if not AGENTS_SDK_AVAILABLE:
            raise RuntimeError("openai-agents SDK not installed. Run: pip install openai-agents")
        _agent = Agent(
            name="Customer Success FTE",
            model=_build_model(),
            instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
            tools=[
                search_knowledge_base,
                create_ticket,
                get_customer_history,
                escalate_to_human,
                send_response,
            ],
        )
        logger.info("Customer Success agent initialized")
    return _agent


# ---------------------------------------------------------------------------
# Public entry point — called by the Kafka worker
# ---------------------------------------------------------------------------

async def run_agent(message: str, context: dict) -> dict:
    """
    Run the Customer Success agent for a single inbound message.

    Args:
        message : Raw customer message text.
        context : Dict with keys:
                    customer_id    (str)  — email or phone number
                    channel        (str)  — 'email' | 'whatsapp' | 'web_form'
                    customer_name  (str, optional)
                    subject        (str, optional)
                    conversation_id (str, optional)

    Returns:
        Dict with keys:
            response        (str)   — final agent output
            ticket_id       (str)   — created ticket UUID
            conversation_id (str)   — conversation UUID
            escalated       (bool)
            tool_calls      (list)  — names of tools called
            latency_ms      (int)
    """
    if not AGENTS_SDK_AVAILABLE:
        return _error_response("openai-agents SDK not installed")

    channel         = context.get("channel", "web_form")
    customer_id     = context.get("customer_id", "unknown")
    customer_name   = context.get("customer_name", "")
    subject         = context.get("subject", "")
    conversation_id = context.get("conversation_id", "")

    # Build the context-prefixed message the agent will see
    full_message = (
        f"[Channel: {channel}] "
        f"[Customer: {customer_id}] "
        f"[Name: {customer_name}] "
    )
    if subject:
        full_message += f"[Subject: {subject}] "
    if conversation_id:
        full_message += f"[Conversation: {conversation_id}] "
    full_message += f"\n\nCustomer message: {message}"

    start = time.monotonic()
    try:
        agent  = _get_agent()
        result = await Runner.run(agent, full_message)

        latency_ms = int((time.monotonic() - start) * 1000)

        # Extract tool calls and detect escalation
        tool_calls = []
        escalated  = False
        ticket_id  = None

        if hasattr(result, "messages"):
            for msg in result.messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        name = tc.function.name if hasattr(tc, "function") else str(tc)
                        tool_calls.append(name)
                        if name == "escalate_to_human":
                            escalated = True

        final_response = (
            result.final_output if hasattr(result, "final_output") else str(result)
        )

        logger.info(
            "Agent run complete",
            channel=channel,
            customer_id=customer_id,
            latency_ms=latency_ms,
            escalated=escalated,
            tools_called=tool_calls,
        )

        return {
            "response":        final_response,
            "ticket_id":       ticket_id,
            "conversation_id": conversation_id,
            "escalated":       escalated,
            "tool_calls":      tool_calls,
            "latency_ms":      latency_ms,
        }

    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.error("Agent run failed", error=str(e), customer_id=customer_id)
        return _error_response(str(e), latency_ms=latency_ms)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _error_response(error: str, latency_ms: int = 0) -> dict:
    return {
        "response": (
            "I apologize, but I'm experiencing a technical issue right now. "
            "Your request has been logged and our team will follow up shortly."
        ),
        "ticket_id":       None,
        "conversation_id": None,
        "escalated":       True,
        "tool_calls":      [],
        "latency_ms":      latency_ms,
        "error":           error,
    }
