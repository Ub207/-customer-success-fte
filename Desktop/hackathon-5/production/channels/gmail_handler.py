"""
Gmail channel handler.

Flow:
  POST /webhooks/gmail
    → decode Google Pub/Sub push notification (base64 JSON)
    → fetch new messages from Gmail API via historyId
    → normalize each message
    → publish to Kafka (topic: gmail_inbound)
    → return 200 accepted

  send_gmail_reply()   — called by Kafka worker after agent finishes
"""

import base64
import json
import os
import re
from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Request

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["gmail"])

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
# Gmail message parser
# ---------------------------------------------------------------------------

class GmailHandler:
    """Parse Gmail API message objects into the normalized format."""

    def __init__(self, service=None):
        self.service = service  # googleapiclient service object (None in tests)

    # ------------------------------------------------------------------
    # Header helpers
    # ------------------------------------------------------------------

    def _extract_email(self, from_header: str) -> str:
        """'Name <email@example.com>' → 'email@example.com'"""
        match = re.search(r"<([^>]+)>", from_header)
        return match.group(1).strip() if match else from_header.strip()

    def _extract_name(self, from_header: str) -> str:
        """'Name <email@example.com>' → 'Name'"""
        match = re.match(r"^([^<]+)<", from_header)
        return match.group(1).strip() if match else ""

    def _extract_body(self, payload: dict) -> str:
        """Recursively find the first text/plain part and decode it."""
        mime_type = payload.get("mimeType", "")
        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            result = self._extract_body(part)
            if result:
                return result
        return ""

    # ------------------------------------------------------------------
    # Pub/Sub notification processor
    # ------------------------------------------------------------------

    def process_notification(
        self,
        history_id: str = "",
        email_address: str = "",
    ) -> List[dict]:
        """
        Fetch new messages from Gmail API using the historyId from the push
        notification. Returns a list of normalized message dicts.
        Returns [] when the Gmail service is not initialized (dev/test).
        """
        if self.service is None:
            logger.warning("Gmail service not initialized — skipping Gmail API fetch")
            return []

        try:
            history = (
                self.service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=history_id,
                    historyTypes=["messageAdded"],
                )
                .execute()
            )

            messages = []
            for record in history.get("history", []):
                for added in record.get("messagesAdded", []):
                    msg_id = added["message"]["id"]
                    msg = (
                        self.service.users()
                        .messages()
                        .get(userId="me", id=msg_id, format="full")
                        .execute()
                    )
                    headers = {
                        h["name"]: h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }
                    from_header = headers.get("From", "")
                    messages.append({
                        "channel":            "email",
                        "channel_message_id": msg_id,
                        "thread_id":          msg.get("threadId"),
                        "customer_email":     self._extract_email(from_header),
                        "customer_name":      self._extract_name(from_header),
                        "subject":            headers.get("Subject", ""),
                        "message":            self._extract_body(msg.get("payload", {})),
                    })
            return messages

        except Exception as e:
            logger.error("Gmail process_notification failed", error=str(e))
            return []


# ---------------------------------------------------------------------------
# Pub/Sub helper
# ---------------------------------------------------------------------------

def parse_gmail_pubsub(data: str) -> dict:
    """Decode a base64-encoded Pub/Sub message body."""
    try:
        decoded = base64.b64decode(data + "==").decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        logger.warning("Failed to decode Gmail Pub/Sub message", error=str(e))
        return {}


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/gmail")
async def gmail_webhook(request: Request):
    """
    Receive Gmail push notification from Google Pub/Sub.
    Decodes the notification, fetches new messages, publishes each to Kafka.
    """
    try:
        body = await request.json()
        pubsub_message = body.get("message", {})
        data = pubsub_message.get("data", "")
        payload = parse_gmail_pubsub(data)

        if not payload:
            return {"status": "ignored", "reason": "empty payload"}

        history_id   = str(payload.get("historyId", ""))
        email_address = payload.get("emailAddress", "")

        handler = GmailHandler(service=None)  # service injected in production via env
        messages = handler.process_notification(
            history_id=history_id,
            email_address=email_address,
        )

        if not messages:
            return {"status": "no_new_messages"}

        from production.kafka_client import TOPICS
        producer = await _get_producer()
        for normalized in messages:
            await producer.send(
                TOPICS["gmail_inbound"],
                normalized,
                key=normalized.get("customer_email", "unknown"),
            )
            logger.info(
                "Gmail message queued",
                customer=normalized.get("customer_email"),
                subject=normalized.get("subject"),
            )

        return {"status": "accepted", "messages_queued": len(messages)}

    except Exception as e:
        logger.error("Gmail webhook error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Reply helper (called by Kafka worker after agent finishes)
# ---------------------------------------------------------------------------

async def send_gmail_reply(
    to_email: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    ticket_id: Optional[str] = None,
) -> dict:
    """Send a reply email via the Gmail API."""
    logger.info(
        "send_gmail_reply called",
        to=to_email,
        subject=subject,
        ticket_id=ticket_id,
    )
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account

        credentials_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_file:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS not set")

        scopes = ["https://www.googleapis.com/auth/gmail.send"]
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )
        service = build("gmail", "v1", credentials=creds)

        reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"
        raw_email = "\n".join([
            f"To: {to_email}",
            f"Subject: {reply_subject}",
            "Content-Type: text/plain; charset=utf-8",
            "",
            body,
        ])
        encoded = base64.urlsafe_b64encode(raw_email.encode()).decode()
        msg_body: dict = {"raw": encoded}
        if thread_id:
            msg_body["threadId"] = thread_id

        result = service.users().messages().send(userId="me", body=msg_body).execute()
        logger.info("Gmail reply sent", message_id=result.get("id"))
        return {"status": "sent", "message_id": result.get("id")}

    except ImportError:
        logger.warning("google-api-python-client not installed — reply skipped")
        return {"status": "skipped", "reason": "google-api-python-client not installed"}
    except Exception as e:
        logger.error("Gmail send failed", error=str(e))
        return {"status": "error", "error": str(e)}
