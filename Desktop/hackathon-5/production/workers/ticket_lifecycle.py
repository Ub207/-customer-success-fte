"""
Ticket lifecycle and escalation management.

Defines:
  - Valid ticket states and legal transitions
  - Escalation routing table (reason → team + SLA)
  - resolve_ticket()   — auto-close a ticket after successful agent response
  - escalate_ticket()  — transition ticket to 'escalated' and notify the team
  - close_conversation_after_reply()  — stamp ended_at + resolution_type
"""

from datetime import datetime, timezone
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Ticket state machine
# ---------------------------------------------------------------------------

VALID_STATES = {"open", "in_progress", "resolved", "escalated", "closed"}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "open":        {"in_progress", "resolved", "escalated"},
    "in_progress": {"resolved", "escalated"},
    "resolved":    {"open"},          # re-open if customer replies again
    "escalated":   {"resolved", "closed"},
    "closed":      set(),             # terminal
}


def is_valid_transition(current: str, next_state: str) -> bool:
    return next_state in ALLOWED_TRANSITIONS.get(current, set())


# ---------------------------------------------------------------------------
# Escalation routing
# ---------------------------------------------------------------------------

ESCALATION_ROUTES: dict[str, dict] = {
    "pricing_inquiry": {
        "team":       "Billing",
        "email":      "billing@techcorp.io",
        "sla_hours":  4,
    },
    "refund_request": {
        "team":       "Billing",
        "email":      "billing@techcorp.io",
        "sla_hours":  4,
    },
    "billing_inquiry": {
        "team":       "Billing",
        "email":      "billing@techcorp.io",
        "sla_hours":  4,
    },
    "legal_threat": {
        "team":       "Legal",
        "email":      "legal-support@techcorp.io",
        "sla_hours":  1,
    },
    "security_incident": {
        "team":       "Security",
        "email":      "security@techcorp.io",
        "sla_hours":  1,
    },
    "angry_customer": {
        "team":       "Senior Support",
        "email":      "senior-support@techcorp.io",
        "sla_hours":  2,
    },
    "human_requested": {
        "team":       "Support",
        "email":      "support@techcorp.io",
        "sla_hours":  4,
    },
    "knowledge_gap": {
        "team":       "Support",
        "email":      "support@techcorp.io",
        "sla_hours":  8,
    },
}

DEFAULT_ROUTE = {
    "team":      "Support",
    "email":     "support@techcorp.io",
    "sla_hours": 4,
}


def get_escalation_route(reason: str) -> dict:
    """Return the routing info for an escalation reason code."""
    return ESCALATION_ROUTES.get(reason, DEFAULT_ROUTE)


def format_sla(sla_hours: int) -> str:
    if sla_hours == 1:
        return "1 hour"
    return f"{sla_hours} hours"


# ---------------------------------------------------------------------------
# Lifecycle operations
# ---------------------------------------------------------------------------

async def resolve_ticket(
    ticket_id: str,
    resolution_notes: Optional[str] = None,
) -> bool:
    """
    Transition a ticket to 'resolved'.
    Called by the message processor after a successful agent response.
    Returns True if updated, False if not found or already in terminal state.
    """
    try:
        from production.database import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM tickets WHERE id = $1::uuid",
                ticket_id,
            )
            if not row:
                logger.warning("resolve_ticket: ticket not found", ticket_id=ticket_id)
                return False

            current = row["status"]
            if not is_valid_transition(current, "resolved"):
                logger.warning(
                    "resolve_ticket: invalid transition",
                    ticket_id=ticket_id,
                    current=current,
                )
                return False

            await conn.execute(
                """
                UPDATE tickets
                SET status           = 'resolved',
                    resolved_at      = $2,
                    updated_at       = NOW(),
                    resolution_notes = COALESCE($3, resolution_notes)
                WHERE id = $1::uuid
                """,
                ticket_id,
                datetime.now(timezone.utc),
                resolution_notes,
            )
        logger.info("Ticket resolved", ticket_id=ticket_id)
        return True

    except Exception as e:
        logger.error("resolve_ticket failed", ticket_id=ticket_id, error=str(e))
        return False


async def escalate_ticket(
    ticket_id: str,
    reason: str,
    context_notes: Optional[str] = None,
) -> dict:
    """
    Transition a ticket to 'escalated' and return routing info.
    Called when escalate_to_human is triggered by the agent.
    """
    route = get_escalation_route(reason)
    sla   = format_sla(route["sla_hours"])

    try:
        from production.database import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM tickets WHERE id = $1::uuid",
                ticket_id,
            )
            if row and is_valid_transition(row["status"], "escalated"):
                notes = f"Escalated [{reason}]: {context_notes or ''}".strip()
                await conn.execute(
                    """
                    UPDATE tickets
                    SET status           = 'escalated',
                        updated_at       = NOW(),
                        resolution_notes = COALESCE($2, resolution_notes)
                    WHERE id = $1::uuid
                    """,
                    ticket_id,
                    notes,
                )
                logger.info(
                    "Ticket escalated",
                    ticket_id=ticket_id,
                    reason=reason,
                    routed_to=route["email"],
                )

    except Exception as e:
        logger.error("escalate_ticket DB update failed", ticket_id=ticket_id, error=str(e))

    return {
        "ticket_id":  ticket_id,
        "reason":     reason,
        "routed_to":  route["email"],
        "team":       route["team"],
        "sla":        sla,
        "sla_hours":  route["sla_hours"],
    }


async def reopen_ticket(ticket_id: str) -> bool:
    """
    Reopen a resolved ticket (e.g. customer replies again).
    Returns True if updated.
    """
    try:
        from production.database import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM tickets WHERE id = $1::uuid",
                ticket_id,
            )
            if not row or not is_valid_transition(row["status"], "open"):
                return False

            await conn.execute(
                """
                UPDATE tickets
                SET status     = 'open',
                    updated_at = NOW(),
                    resolved_at = NULL
                WHERE id = $1::uuid
                """,
                ticket_id,
            )
        logger.info("Ticket reopened", ticket_id=ticket_id)
        return True

    except Exception as e:
        logger.error("reopen_ticket failed", ticket_id=ticket_id, error=str(e))
        return False


async def close_conversation_after_reply(
    conversation_id: str,
    escalated: bool = False,
    escalated_to: Optional[str] = None,
    sentiment_score: Optional[float] = None,
) -> None:
    """
    Mark a conversation resolved or escalated after the agent delivers a reply.
    Stamps ended_at and sets resolution_type.
    """
    try:
        from production.database.queries import close_conversation
        await close_conversation(
            conversation_id=conversation_id,
            resolution_type="escalated" if escalated else "auto_resolved",
            sentiment_score=sentiment_score,
            escalated_to=escalated_to,
        )
        logger.info(
            "Conversation closed",
            conversation_id=conversation_id,
            escalated=escalated,
        )
    except Exception as e:
        logger.error("close_conversation_after_reply failed", conversation_id=conversation_id, error=str(e))
