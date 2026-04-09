"""
Kafka Worker — Unified Message Processor.

Consumes inbound messages from all three channel topics:
  fte.gmail.inbound
  fte.whatsapp.inbound
  fte.webform.inbound

For each message:
  1. Identify / upsert customer in PostgreSQL
  2. Open or reuse a conversation
  3. Save the inbound message to the messages table
  4. Run the Customer Success agent
  5. Save the agent response to the messages table
  6. Deliver the reply via the correct channel sender
  7. Record latency + escalation metrics to agent_metrics
  8. On failure: publish to the dead-letter queue (fte.dlq)

Run as a standalone process:
  python -m production.workers.message_processor
"""

import asyncio
import os
import signal
import time
from pathlib import Path

# Load .env before anything else
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import structlog

from production.logging_config import configure_logging
from production.kafka_client import FTEKafkaConsumer, FTEKafkaProducer, TOPICS

configure_logging()

logger = structlog.get_logger(__name__)

INBOUND_TOPICS = [
    TOPICS["gmail_inbound"],
    TOPICS["whatsapp_inbound"],
    TOPICS["webform_inbound"],
]


class MessageProcessor:
    """
    Consumes Kafka messages, runs the agent, delivers replies,
    and persists everything to PostgreSQL.
    """

    def __init__(self):
        self.consumer = FTEKafkaConsumer(
            topics=INBOUND_TOPICS,
            group_id="fte-message-processor",
        )
        self.producer = FTEKafkaProducer()
        self._running   = False
        self._processed = 0
        self._errors    = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        await self.consumer.start()
        await self.producer.start()
        self._running = True
        logger.info("MessageProcessor started", topics=INBOUND_TOPICS)

    async def stop(self) -> None:
        self._running = False
        await self.consumer.stop()
        await self.producer.stop()
        from production.database import close_db_pool
        await close_db_pool()
        logger.info(
            "MessageProcessor stopped",
            processed=self._processed,
            errors=self._errors,
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run_forever(self) -> None:
        logger.info("Entering message processing loop")
        try:
            async for kafka_msg in self.consumer.consume():
                if not self._running:
                    break
                await self.process_message(kafka_msg.get("value", {}))
        except asyncio.CancelledError:
            logger.info("Processing loop cancelled")
        except Exception as e:
            logger.error("Fatal error in processing loop", error=str(e))
            raise
        finally:
            await self.stop()

    # ------------------------------------------------------------------
    # Single-message handler
    # ------------------------------------------------------------------

    async def process_message(self, message: dict) -> None:
        """
        End-to-end processing for one inbound support message.

        Expected keys in `message` (all optional except channel + message):
          channel            — 'email' | 'whatsapp' | 'web_form'
          message            — raw customer text
          customer_email     — used for email + web_form
          customer_phone     — used for whatsapp
          customer_name
          subject
          conversation_id
          channel_message_id — Gmail message ID, Twilio SID, etc.
          thread_id          — Gmail thread ID (for reply threading)
          category, priority — web form only
        """
        channel = message.get("channel", "unknown")
        customer_id_raw = (
            message.get("customer_email")
            or message.get("customer_phone")
            or "unknown"
        )

        logger.info(
            "Processing message",
            channel=channel,
            customer=customer_id_raw,
        )

        start = time.monotonic()
        try:
            # ── 1. Upsert customer ────────────────────────────────────
            from production.database.queries import (
                get_or_create_customer,
                upsert_customer_identifier,
                get_or_create_conversation,
                save_message,
                record_agent_metric,
            )

            is_email_id = "@" in customer_id_raw
            customer = await get_or_create_customer(
                email=customer_id_raw if is_email_id else None,
                phone=customer_id_raw if not is_email_id else None,
                name=message.get("customer_name"),
            )
            customer_uuid = str(customer["id"])

            # Register identifier for cross-channel matching
            id_type = "email" if is_email_id else "whatsapp"
            await upsert_customer_identifier(customer_uuid, id_type, customer_id_raw)

            # ── 2. Open / reuse conversation ──────────────────────────
            conversation = await get_or_create_conversation(
                customer_id=customer_uuid,
                channel=channel,
                conversation_id=message.get("conversation_id"),
            )
            conversation_id = str(conversation["id"])

            # ── 3. Persist inbound message ────────────────────────────
            await save_message(
                conversation_id=conversation_id,
                role="customer",
                content=message.get("message", ""),
                channel=channel,
                direction="inbound",
                channel_message_id=message.get("channel_message_id"),
            )

            # ── 4. Run agent ──────────────────────────────────────────
            from production.agent.customer_success_agent import run_agent

            context = {
                "customer_id":     customer_id_raw,
                "channel":         channel,
                "customer_name":   customer.get("name") or message.get("customer_name", ""),
                "subject":         message.get("subject", ""),
                "conversation_id": conversation_id,
                "category":        message.get("category", "general"),
                "priority":        message.get("priority", "medium"),
            }

            result = await run_agent(
                message=message.get("message", ""),
                context=context,
            )

            latency_ms   = result.get("latency_ms", 0)
            escalated    = result.get("escalated", False)
            response_text = result.get("response", "")

            # ── 5. Persist agent response ─────────────────────────────
            await save_message(
                conversation_id=conversation_id,
                role="agent",
                content=response_text,
                channel=channel,
                direction="outbound",
                tokens_used=None,
                latency_ms=latency_ms,
                tool_calls=result.get("tool_calls", []),
                delivery_status="pending",
            )

            # ── 6. Ticket lifecycle ───────────────────────────────────
            ticket_id = result.get("ticket_id")
            if ticket_id:
                from production.workers.ticket_lifecycle import (
                    resolve_ticket,
                    escalate_ticket,
                    close_conversation_after_reply,
                )
                if escalated:
                    await escalate_ticket(ticket_id, reason="agent_escalation")
                else:
                    await resolve_ticket(
                        ticket_id,
                        resolution_notes="Auto-resolved by agent.",
                    )
                await close_conversation_after_reply(
                    conversation_id=conversation_id,
                    escalated=escalated,
                )

            # ── 7. Deliver reply via correct channel sender ───────────
            await self._deliver_reply(
                channel=channel,
                response=response_text,
                message=message,
                ticket_id=ticket_id,
                customer_name=context["customer_name"],
            )

            # ── 8. Record metrics ─────────────────────────────────────
            elapsed = time.monotonic() - start
            await record_agent_metric(
                "response_latency_ms",
                latency_ms,
                channel=channel,
                dimensions={"escalated": escalated},
            )
            await record_agent_metric(
                "tool_calls_per_message",
                float(len(result.get("tool_calls", []))),
                channel=channel,
            )
            if escalated:
                await record_agent_metric("escalation", 1.0, channel=channel)

            self._processed += 1
            logger.info(
                "Message processed",
                channel=channel,
                ticket_id=result.get("ticket_id"),
                escalated=escalated,
                latency_ms=latency_ms,
                total_elapsed_ms=int(elapsed * 1000),
            )

        except Exception as e:
            self._errors += 1
            logger.error(
                "Message processing failed",
                channel=channel,
                customer=customer_id_raw,
                error=str(e),
            )
            await self.producer.send_to_dlq(
                original_topic=f"fte.{channel}.inbound",
                value=message,
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Channel reply routing
    # ------------------------------------------------------------------

    async def _deliver_reply(
        self,
        channel: str,
        response: str,
        message: dict,
        ticket_id: str | None,
        customer_name: str,
    ) -> None:
        """Route the agent response to the correct channel sender."""
        try:
            if channel == "email":
                from production.channels.gmail_handler import send_gmail_reply
                await send_gmail_reply(
                    to_email=message.get("customer_email", ""),
                    subject=message.get("subject", "Support Request"),
                    body=response,
                    thread_id=message.get("thread_id"),
                    ticket_id=ticket_id,
                )

            elif channel == "whatsapp":
                from production.channels.whatsapp_handler import send_whatsapp_reply
                await send_whatsapp_reply(
                    to_phone=message.get("customer_phone", ""),
                    message=response,
                    ticket_id=ticket_id,
                )

            elif channel == "web_form":
                from production.channels.web_form_handler import send_web_form_reply
                await send_web_form_reply(
                    customer_email=message.get("customer_email", ""),
                    message=response,
                    ticket_id=ticket_id,
                    customer_name=customer_name,
                )

            else:
                logger.warning("Unknown channel — reply not delivered", channel=channel)

        except Exception as e:
            logger.error("Reply delivery failed", channel=channel, error=str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    processor = MessageProcessor()

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.get_event_loop()

    def _shutdown():
        logger.info("Shutdown signal received")
        asyncio.ensure_future(processor.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass  # Windows: signal handlers not supported in event loop

    await processor.start()
    await processor.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
