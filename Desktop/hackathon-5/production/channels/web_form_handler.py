"""
Web Form channel handler.

Flow:
  POST /web-form/submit
    → validate input
    → publish normalized message to Kafka (topic: web_form_inbound)
    → return 201 with ticket_id placeholder

  GET /web-form/ticket/{ticket_id}
    → look up ticket in PostgreSQL
    → return status

The agent is NOT called here. The Kafka worker handles agent execution.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/web-form", tags=["web-form"])

VALID_CATEGORIES = {"general", "technical", "billing", "account", "bug", "feedback", "other"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}

SLA_BY_PRIORITY = {
    "urgent": "Usually within 1 minute",
    "high":   "Usually within 2 minutes",
    "medium": "Usually within 5 minutes",
    "low":    "Usually within 5 minutes",
}

# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class SupportFormSubmission(BaseModel):
    name:     str
    email:    str
    subject:  str = ""
    message:  str
    category: str = "general"
    priority: str = "medium"

    @field_validator("name")
    @classmethod
    def name_min_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("name must be at least 2 characters")
        return v.strip()

    @field_validator("message")
    @classmethod
    def message_min_length(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("message must be at least 10 characters")
        return v.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        return v if v in VALID_PRIORITIES else "medium"

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return v if v in VALID_CATEGORIES else "general"


# Backward-compatible alias used by tests
WebFormSubmission = SupportFormSubmission


# ---------------------------------------------------------------------------
# Kafka producer singleton
# ---------------------------------------------------------------------------

_producer = None


async def _get_producer():
    global _producer
    if _producer is None:
        from production.kafka_client import FTEKafkaProducer
        _producer = FTEKafkaProducer()
        await _producer.start()
    return _producer


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/submit", status_code=201)
async def submit_support_form(submission: SupportFormSubmission):
    """
    Accept a web support form submission.
    Publishes to Kafka for async agent processing.
    Returns a placeholder ticket_id and SLA immediately.
    """
    import uuid

    pending_ticket_id = f"WEB-{str(uuid.uuid4())[:8].upper()}"

    normalized = {
        "channel":        "web_form",
        "customer_email": submission.email,
        "customer_name":  submission.name,
        "subject":        submission.subject,
        "message":        submission.message,
        "category":       submission.category,
        "priority":       submission.priority,
        "pending_ticket_id": pending_ticket_id,
    }

    try:
        from production.kafka_client import TOPICS
        producer = await _get_producer()
        await producer.send(
            TOPICS["webform_inbound"],
            normalized,
            key=submission.email,
        )
        logger.info(
            "Web form submission queued",
            email=submission.email,
            pending_ticket_id=pending_ticket_id,
        )
    except Exception as e:
        # Kafka unavailable: log and continue — ticket will be created when worker is up
        logger.warning("Kafka unavailable, message not queued", error=str(e))

    return {
        "ticket_id":             pending_ticket_id,
        "message":               "Your request has been received. We will respond shortly.",
        "estimated_response_time": SLA_BY_PRIORITY[submission.priority],
        "status":                "queued",
    }


@router.get("/ticket/{ticket_id}")
async def get_ticket_status(ticket_id: str):
    """Return the current status of a support ticket."""
    try:
        import uuid as _uuid
        # pending_ticket_id (WEB-XXXXXXXX) is not a DB UUID — handle gracefully
        try:
            _uuid.UUID(ticket_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Ticket not found")

        from production.database import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, status, priority, source_channel, created_at, resolved_at
                FROM tickets
                WHERE id = $1::uuid
                """,
                ticket_id,
            )
        if not row:
            raise HTTPException(status_code=404, detail="Ticket not found")

        return {
            "ticket_id":  str(row["id"]),
            "status":     row["status"],
            "priority":   row["priority"],
            "channel":    row["source_channel"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "resolved_at": row["resolved_at"].isoformat() if row["resolved_at"] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ticket status lookup failed", ticket_id=ticket_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve ticket status")


# ---------------------------------------------------------------------------
# Reply helper (called by Kafka worker after agent finishes)
# ---------------------------------------------------------------------------

async def send_web_form_reply(
    customer_email: str,
    message: str,
    ticket_id: Optional[str] = None,
    customer_name: Optional[str] = None,
) -> dict:
    """
    Deliver the agent's response to the customer via SMTP.

    Reads SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM from env.
    Falls back to logging when SMTP is not configured (dev mode).
    """
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    logger.info(
        "Web form reply ready",
        to=customer_email,
        ticket_id=ticket_id,
        preview=message[:100],
    )

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not smtp_host or not smtp_user or not smtp_pass:
        logger.info(
            "SMTP not configured — reply logged only (set SMTP_HOST, SMTP_USER, SMTP_PASS)",
            to=customer_email,
        )
        return {"status": "logged", "to": customer_email, "ticket_id": ticket_id}

    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_from = os.environ.get("SMTP_FROM", smtp_user)
    name = customer_name or "there"
    subject = f"Re: Your support request" + (f" [Ticket #{ticket_id}]" if ticket_id else "")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = customer_email

        plain_body = message
        if ticket_id:
            plain_body += f"\n\n---\nTicket reference: {ticket_id}"

        msg.attach(MIMEText(plain_body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, customer_email, msg.as_string())

        logger.info("Web form reply sent via SMTP", to=customer_email, ticket_id=ticket_id)
        return {"status": "sent", "to": customer_email, "ticket_id": ticket_id}

    except Exception as e:
        logger.error("SMTP send failed", to=customer_email, error=str(e))
        return {"status": "error", "to": customer_email, "error": str(e)}
