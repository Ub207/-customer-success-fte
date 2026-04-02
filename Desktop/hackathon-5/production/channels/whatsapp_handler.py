"""
WhatsApp channel handler (Twilio).

Flow:
  POST /webhooks/whatsapp
    → parse Twilio form-encoded payload
    → normalize message
    → publish to Kafka (topic: whatsapp_inbound)
    → return 200 accepted

  POST /webhooks/whatsapp/status
    → update delivery_status in messages table

  send_whatsapp_reply()  — called by Kafka worker after agent finishes
"""

import os
from typing import List, Optional
from urllib.parse import parse_qs

import structlog
from fastapi import APIRouter, HTTPException, Request

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["whatsapp"])

HUMAN_KEYWORDS = {"human", "agent", "representative", "person", "talk to someone"}

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
# WhatsApp message handler
# ---------------------------------------------------------------------------

def detect_human_request(message: str) -> bool:
    """Return True if the customer is explicitly asking for a human agent."""
    lower = message.lower().strip()
    return any(kw in lower for kw in HUMAN_KEYWORDS)


class WhatsAppHandler:
    """Parse Twilio webhook payloads and format outbound messages."""

    def normalize(self, form_data: dict) -> dict:
        """
        Convert a Twilio webhook form_data dict into the canonical
        normalized message format shared across all channels.
        """
        from_raw     = form_data.get("From", "")
        customer_phone = from_raw.replace("whatsapp:", "").strip()
        body         = form_data.get("Body", "").strip()

        return {
            "channel":           "whatsapp",
            "channel_message_id": form_data.get("MessageSid", ""),
            "customer_phone":    customer_phone,
            "customer_name":     form_data.get("ProfileName", ""),
            "message":           body,
            "is_human_request":  detect_human_request(body),
        }

    def split_message(self, message: str, max_length: int = 1600) -> List[str]:
        """
        Split long messages into chunks ≤ max_length characters.
        Prefers splitting at sentence boundaries.
        """
        if len(message) <= max_length:
            return [message]

        parts = []
        while len(message) > max_length:
            chunk = message[:max_length]
            split_at = max(
                chunk.rfind(". "),
                chunk.rfind("! "),
                chunk.rfind("? "),
            )
            if split_at > max_length // 2:
                split_at += 1
            else:
                split_at = max_length
            parts.append(message[:split_at].strip())
            message = message[split_at:].strip()

        if message:
            parts.append(message)
        return parts

    def format_response(self, message: str, max_length: int = 1600) -> List[str]:
        """
        Format an outbound WhatsApp message into delivery-ready parts.
        Splits at sentence boundaries if the message exceeds max_length.
        Alias for split_message — used by response delivery worker.
        """
        return self.split_message(message, max_length=max_length)

    async def process_webhook(self, form_data: dict) -> dict:
        """
        Async entry point used by tests and the webhook handler.
        Normalizes Twilio form_data into the canonical message format.
        """
        return self.normalize(form_data)


# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receive inbound WhatsApp message from Twilio.
    Twilio sends application/x-www-form-urlencoded data.
    """
    try:
        raw_body = await request.body()
        params   = parse_qs(raw_body.decode("utf-8"))

        def get(key: str) -> str:
            return params.get(key, [""])[0]

        form_data = {
            "MessageSid":  get("MessageSid"),
            "From":        get("From"),
            "To":          get("To"),
            "Body":        get("Body"),
            "ProfileName": get("ProfileName"),
            "NumMedia":    get("NumMedia"),
        }

        handler    = WhatsAppHandler()
        normalized = handler.normalize(form_data)

        if not normalized["customer_phone"] or not normalized["message"]:
            return {"status": "ignored", "reason": "missing From or Body"}

        from production.kafka_client import TOPICS
        producer = await _get_producer()
        await producer.send(
            TOPICS["whatsapp_inbound"],
            normalized,
            key=normalized["customer_phone"],
        )

        logger.info(
            "WhatsApp message queued",
            from_number=normalized["customer_phone"],
            is_human_request=normalized["is_human_request"],
        )
        return {"status": "accepted"}

    except Exception as e:
        logger.error("WhatsApp webhook error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whatsapp/status")
async def whatsapp_status_callback(request: Request):
    """
    Receive Twilio delivery status callback.
    Updates the delivery_status column in the messages table.
    """
    try:
        raw_body = await request.body()
        params   = parse_qs(raw_body.decode("utf-8"))

        def get(key: str) -> str:
            return params.get(key, [""])[0]

        message_sid    = get("MessageSid")
        message_status = get("MessageStatus")

        if message_sid and message_status:
            try:
                from production.database.queries import update_delivery_status
                await update_delivery_status(message_sid, message_status)
            except Exception as db_err:
                logger.warning("Delivery status DB update failed", error=str(db_err))

        logger.info("WhatsApp status callback", sid=message_sid, status=message_status)
        return {"status": "ok"}

    except Exception as e:
        logger.error("WhatsApp status callback error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Reply helper (called by Kafka worker after agent finishes)
# ---------------------------------------------------------------------------

async def send_whatsapp_reply(
    to_phone: str,
    message: str,
    ticket_id: Optional[str] = None,
) -> dict:
    """Send a WhatsApp reply via the Twilio REST API."""
    # Hard cap at 1600 chars (Twilio limit)
    if len(message) > 1600:
        message = message[:1597] + "..."

    logger.info("send_whatsapp_reply called", to=to_phone, ticket_id=ticket_id)

    try:
        from twilio.rest import Client

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token  = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

        if not account_sid or not auth_token:
            raise RuntimeError("TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not configured")

        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            from_=from_number,
            to=f"whatsapp:{to_phone}",
            body=message,
        )
        logger.info("WhatsApp reply sent", sid=msg.sid)
        return {"status": "sent", "sid": msg.sid}

    except ImportError:
        logger.warning("twilio not installed — reply skipped")
        return {"status": "skipped", "reason": "twilio not installed"}
    except Exception as e:
        logger.error("WhatsApp send failed", error=str(e))
        return {"status": "error", "error": str(e)}
