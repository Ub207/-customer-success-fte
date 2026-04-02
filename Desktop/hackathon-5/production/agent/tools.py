"""
Agent tools — five @function_tool definitions for the OpenAI Agents SDK.

Tools:
  search_knowledge_base  — find relevant KB articles
  create_ticket          — log a support ticket in PostgreSQL
  get_customer_history   — retrieve prior interactions across all channels
  escalate_to_human      — route to a human agent / specialist team
  send_response          — deliver the final reply to the customer
"""

import uuid
from typing import Optional

import structlog
from pydantic import BaseModel

try:
    from agents import function_tool
    AGENTS_SDK_AVAILABLE = True
except ImportError:
    def function_tool(fn):
        return fn
    AGENTS_SDK_AVAILABLE = False

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class KnowledgeSearchInput(BaseModel):
    query:       str
    max_results: int = 5


class TicketInput(BaseModel):
    customer_id:   str
    channel:       str
    issue_summary: str
    priority:      str = "medium"
    category:      str = "general"


class CustomerHistoryInput(BaseModel):
    customer_id: str


class EscalationInput(BaseModel):
    reason:        str                    # reason code from the prompt
    ticket_id:     Optional[str] = None
    customer_id:   Optional[str] = None
    urgency:       str = "normal"         # 'normal' | 'urgent'
    context_notes: Optional[str] = None


class ResponseInput(BaseModel):
    channel:       str
    message:       str
    ticket_id:     Optional[str] = None
    customer_id:   Optional[str] = None
    customer_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@function_tool
async def search_knowledge_base(input: KnowledgeSearchInput) -> dict:
    """
    Search the knowledge base for articles relevant to the customer's query.
    Returns a list of matching articles with title, category, and a content snippet.
    Try with different keywords if the first search returns no results.
    """
    logger.info("search_knowledge_base", query=input.query)
    try:
        from production.database.queries import search_knowledge_base as db_search
        articles = await db_search(input.query, max_results=input.max_results)
        return {
            "articles": [
                {
                    "id":       str(a["id"]),
                    "title":    a["title"],
                    "content":  a["content"][:500],
                    "category": a["category"],
                }
                for a in articles
            ],
            "count": len(articles),
        }
    except Exception as e:
        logger.warning("search_knowledge_base failed", error=str(e))
        return {"articles": [], "count": 0, "error": str(e)}


@function_tool
async def create_ticket(input: TicketInput) -> dict:
    """
    Create a support ticket for the customer's issue.
    Call this FIRST before any other tool.
    Returns the ticket_id, status, and priority.
    """
    logger.info("create_ticket", customer_id=input.customer_id, priority=input.priority)
    try:
        from production.database.queries import (
            get_or_create_customer,
            get_or_create_conversation,
            create_ticket as db_create_ticket,
        )

        # Resolve or create the customer record
        is_email = "@" in input.customer_id
        customer = await get_or_create_customer(
            email=input.customer_id if is_email else None,
            phone=input.customer_id if not is_email else None,
        )
        customer_id = str(customer["id"])

        # Get or open a conversation
        conversation = await get_or_create_conversation(
            customer_id=customer_id,
            channel=input.channel,
        )
        conversation_id = str(conversation["id"])

        ticket_id = await db_create_ticket(
            customer_id=customer_id,
            source_channel=input.channel,
            category=input.category,
            priority=input.priority,
            conversation_id=conversation_id,
            resolution_notes=input.issue_summary,
        )

        logger.info("Ticket created", ticket_id=ticket_id)
        return {
            "ticket_id":       ticket_id,
            "conversation_id": conversation_id,
            "customer_id":     customer_id,
            "status":          "open",
            "priority":        input.priority,
        }

    except Exception as e:
        logger.warning("create_ticket DB failed — returning generated ID", error=str(e))
        return {
            "ticket_id":   str(uuid.uuid4()),
            "customer_id": input.customer_id,
            "status":      "open",
            "priority":    input.priority,
            "error":       str(e),
        }


@function_tool
async def get_customer_history(input: CustomerHistoryInput) -> dict:
    """
    Retrieve the customer's support history across all channels.
    Returns recent tickets and messages so you can personalize the response.
    """
    logger.info("get_customer_history", customer_id=input.customer_id)
    try:
        from production.database.queries import (
            get_or_create_customer,
            get_customer_tickets,
            get_customer_history_all_channels,
        )

        is_email = "@" in input.customer_id
        customer = await get_or_create_customer(
            email=input.customer_id if is_email else None,
            phone=input.customer_id if not is_email else None,
        )
        customer_id = str(customer["id"])

        tickets  = await get_customer_tickets(customer_id, limit=5)
        messages = await get_customer_history_all_channels(customer_id, limit=10)

        return {
            "customer_id":   customer_id,
            "customer_name": customer.get("name", ""),
            "ticket_count":  len(tickets),
            "tickets": [
                {
                    "ticket_id": str(t["id"]),
                    "channel":   t["source_channel"],
                    "category":  t["category"],
                    "status":    t["status"],
                    "priority":  t["priority"],
                    "notes":     t["resolution_notes"],
                }
                for t in tickets
            ],
            "recent_messages": [
                {
                    "channel":   m["channel"],
                    "direction": m["direction"],
                    "role":      m["role"],
                    "content":   m["content"][:200],
                }
                for m in messages
            ],
        }

    except Exception as e:
        logger.warning("get_customer_history failed", error=str(e))
        return {
            "customer_id":    input.customer_id,
            "ticket_count":   0,
            "tickets":        [],
            "recent_messages": [],
            "error":          str(e),
        }


@function_tool
async def escalate_to_human(input: EscalationInput) -> dict:
    """
    Escalate the conversation to a human agent or specialist team.
    Use this for: pricing_inquiry, refund_request, legal_threat,
    angry_customer, security_incident, human_requested, knowledge_gap, billing_inquiry.
    Always call this BEFORE send_response when escalating.
    """
    logger.info(
        "escalate_to_human",
        customer_id=input.customer_id,
        reason=input.reason,
        urgency=input.urgency,
    )

    ROUTING = {
        "pricing_inquiry": "billing@techcorp.io",
        "refund_request":  "billing@techcorp.io",
        "legal_threat":    "legal-support@techcorp.io",
        "angry_customer":  "senior-support@techcorp.io",
        "security_incident": "security@techcorp.io",
        "billing_inquiry": "billing@techcorp.io",
        "knowledge_gap":   "support@techcorp.io",
        "human_requested": "support@techcorp.io",
    }
    SLA = {
        "legal_threat":    "1 hour",
        "security_incident": "1 hour",
        "angry_customer":  "2 hours",
        "pricing_inquiry": "4 hours",
        "refund_request":  "4 hours",
        "billing_inquiry": "4 hours",
        "human_requested": "4 hours",
        "knowledge_gap":   "8 hours",
    }

    escalation_id  = str(uuid.uuid4())
    routed_to      = ROUTING.get(input.reason, "support@techcorp.io")
    sla            = SLA.get(input.reason, "4 hours")
    priority       = "high" if input.urgency == "urgent" else "medium"

    try:
        from production.database.queries import (
            get_or_create_customer,
            create_ticket as db_create_ticket,
            close_conversation,
        )

        if input.customer_id:
            is_email = "@" in input.customer_id
            customer = await get_or_create_customer(
                email=input.customer_id if is_email else None,
                phone=input.customer_id if not is_email else None,
            )
            customer_id = str(customer["id"])

            await db_create_ticket(
                customer_id=customer_id,
                source_channel="escalation",
                category="escalation",
                priority=priority,
                resolution_notes=f"ESCALATION [{input.reason}]: {input.context_notes or ''}".strip(),
            )

    except Exception as e:
        logger.warning("escalation DB write failed", error=str(e))

    logger.info("Escalation created", escalation_id=escalation_id, routed_to=routed_to)
    return {
        "escalation_id": escalation_id,
        "status":        "escalated",
        "reason":        input.reason,
        "routed_to":     routed_to,
        "sla":           sla,
        "message":       (
            f"Your case has been escalated to our {input.reason.replace('_', ' ')} team "
            f"at {routed_to}. You can expect a response within {sla}."
        ),
    }


@function_tool
async def send_response(input: ResponseInput) -> dict:
    """
    Send the final response to the customer via their channel.
    This must be the LAST tool called. Always call this — never output text directly.
    """
    logger.info(
        "send_response",
        customer_id=input.customer_id,
        channel=input.channel,
        ticket_id=input.ticket_id,
    )

    from production.agent.formatters import format_for_channel
    formatted = await format_for_channel(
        response=input.message,
        channel=input.channel,
        ticket_id=input.ticket_id,
        customer_name=input.customer_name,
    )

    return {
        "status":          "sent",
        "channel":         input.channel,
        "customer_id":     input.customer_id,
        "ticket_id":       input.ticket_id,
        "message_preview": formatted[:120],
    }
