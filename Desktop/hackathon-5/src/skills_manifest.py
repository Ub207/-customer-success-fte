"""
Agent Skills Manifest — Customer Success FTE
=============================================
Exercise 1.5: Formalised skill definitions discovered during incubation.

Each skill is a reusable capability that the FTE agent can invoke.
Skills are implemented as @function_tool decorated functions in
production/agent/tools.py.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Skill:
    name: str
    description: str
    when_to_use: str
    inputs: List[str]
    outputs: List[str]
    production_tool: str      # maps to production/agent/tools.py function
    channel_aware: bool = False
    escalation_path: str = ""


# ---------------------------------------------------------------------------
# Skill 1 — Knowledge Retrieval
# ---------------------------------------------------------------------------
knowledge_retrieval = Skill(
    name="knowledge_retrieval",
    description=(
        "Search the product documentation (knowledge base) for articles "
        "relevant to the customer's question. Uses keyword matching during "
        "incubation; upgraded to vector-similarity search in production."
    ),
    when_to_use=(
        "Customer asks any product-related question: how-to, feature availability, "
        "bug confirmation, API usage, account settings, or pricing alternatives."
    ),
    inputs=["query (str) — customer question text", "max_results (int, default 5)"],
    outputs=[
        "ranked list of knowledge-base articles",
        "title, category, content snippet, relevance score",
    ],
    production_tool="search_knowledge_base",
    channel_aware=False,
)


# ---------------------------------------------------------------------------
# Skill 2 — Sentiment Analysis
# ---------------------------------------------------------------------------
sentiment_analysis = Skill(
    name="sentiment_analysis",
    description=(
        "Analyse the emotional tone of every incoming customer message to "
        "guide response style and detect escalation risk. "
        "Score range: 0.0 (very negative) → 1.0 (very positive)."
    ),
    when_to_use="Every inbound customer message, before generating a response.",
    inputs=["message_text (str)", "channel (str) — affects baseline expectations"],
    outputs=[
        "sentiment_score (float 0.0–1.0)",
        "label (str): 'positive' | 'neutral' | 'negative' | 'very_negative'",
        "escalation_recommended (bool) — True when score < 0.3",
    ],
    production_tool="(embedded in agent reasoning, stored in conversations.sentiment_score)",
    channel_aware=True,
    escalation_path="escalate_to_human with reason='negative_sentiment'",
)


# ---------------------------------------------------------------------------
# Skill 3 — Escalation Decision
# ---------------------------------------------------------------------------
escalation_decision = Skill(
    name="escalation_decision",
    description=(
        "Evaluate the current conversation context and decide whether the "
        "issue must be routed to a human agent. Checks trigger phrases, "
        "sentiment trend, and topic category."
    ),
    when_to_use=(
        "After generating a draft response, or immediately upon detecting "
        "escalation keywords (legal, pricing, refund, profanity)."
    ),
    inputs=[
        "conversation_context (dict) — full message history",
        "sentiment_score (float)",
        "topic_category (str)",
        "customer_message (str)",
    ],
    outputs=[
        "should_escalate (bool)",
        "reason (str): one of pricing_inquiry | refund_request | legal_threat | "
        "negative_sentiment | knowledge_gap | explicit_human_request | "
        "channel_keyword",
        "urgency (str): 'normal' | 'urgent'",
    ],
    production_tool="escalate_to_human",
    channel_aware=True,
    escalation_path="escalate_to_human",
)


# ---------------------------------------------------------------------------
# Skill 4 — Channel Adaptation
# ---------------------------------------------------------------------------
channel_adaptation = Skill(
    name="channel_adaptation",
    description=(
        "Format a raw response text to meet the style, length, and structural "
        "requirements of the target delivery channel before sending."
    ),
    when_to_use="Always — immediately before calling send_response.",
    inputs=[
        "response_text (str) — draft reply",
        "channel (str): 'email' | 'whatsapp' | 'web_form'",
        "ticket_id (str)",
        "customer_name (str, optional)",
    ],
    outputs=[
        "formatted_response (str) respecting channel limits:",
        "  email     -- formal greeting + sign-off + ticket ref, max 500 words",
        "  whatsapp  -- concise, conversational, max 1600 chars, human-opt footer",
        "  web_form  -- semi-formal, bullet-friendly, max 300 words, help footer",
    ],
    production_tool="send_response (formatting done inside tool via formatters.py)",
    channel_aware=True,
)


# ---------------------------------------------------------------------------
# Skill 5 — Customer Identification
# ---------------------------------------------------------------------------
customer_identification = Skill(
    name="customer_identification",
    description=(
        "Resolve the inbound message to a unified customer record. "
        "Merges email-based and phone-based identities so the agent has "
        "a single customer_id regardless of which channel was used."
    ),
    when_to_use="On every incoming message, before creating a ticket.",
    inputs=[
        "customer_email (str, optional) — from email/web-form",
        "customer_phone (str, optional) — from WhatsApp (E.164 format)",
        "customer_name  (str, optional)",
    ],
    outputs=[
        "customer_id (UUID) — unified identifier",
        "is_new_customer (bool)",
        "merged_channels (list[str]) — channels this customer has used before",
    ],
    production_tool="(executed by MessageProcessor.resolve_customer in workers/message_processor.py)",
    channel_aware=True,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
SKILLS: List[Skill] = [
    knowledge_retrieval,
    sentiment_analysis,
    escalation_decision,
    channel_adaptation,
    customer_identification,
]


def get_skill(name: str) -> Skill:
    """Retrieve a skill definition by name."""
    for skill in SKILLS:
        if skill.name == name:
            return skill
    raise KeyError(f"Skill '{name}' not found. Available: {[s.name for s in SKILLS]}")


def print_manifest() -> None:
    """Print a human-readable summary of all skills."""
    print("=" * 60)
    print("CUSTOMER SUCCESS FTE — AGENT SKILLS MANIFEST")
    print("=" * 60)
    for i, skill in enumerate(SKILLS, 1):
        print(f"\n{i}. {skill.name.upper()}")
        print(f"   Description : {skill.description[:80]}...")
        print(f"   When to use : {skill.when_to_use[:80]}...")
        print(f"   Inputs      : {', '.join(skill.inputs[:2])}")
        print(f"   Outputs     : {', '.join(skill.outputs[:2])}")
        print(f"   Tool        : {skill.production_tool}")
        print(f"   Channel-aware: {skill.channel_aware}")
    print()


if __name__ == "__main__":
    print_manifest()
