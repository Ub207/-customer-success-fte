"""
Response Delivery Worker.

Consumes messages from the fte.agent.responses Kafka topic and routes
each response to the appropriate outbound channel:
  - email   → send_gmail_reply()
  - whatsapp → send_whatsapp_reply()
  - web_form → send_web_form_reply()

This worker is the final step in the processing pipeline:
  Customer → Channel → Kafka → Worker → Agent → Kafka (agent_responses) → HERE → Customer
"""

import asyncio
import signal

import structlog

from production.kafka_client import FTEKafkaConsumer, TOPICS

logger = structlog.get_logger(__name__)


class ResponseDeliveryWorker:
    """
    Consumes agent_responses topic and delivers replies to customers
    via the correct channel.
    """

    def __init__(self):
        self.consumer = FTEKafkaConsumer(
            topics=[TOPICS["agent_responses"]],
            group_id="fte-response-delivery",
        )
        self._running = False
        self._delivered = 0
        self._errors = 0

    async def start(self) -> None:
        await self.consumer.start()
        self._running = True
        logger.info("ResponseDeliveryWorker started")

    async def stop(self) -> None:
        self._running = False
        await self.consumer.stop()
        logger.info(
            "ResponseDeliveryWorker stopped",
            delivered=self._delivered,
            errors=self._errors,
        )

    async def deliver(self, event: dict) -> None:
        """
        Route a single agent response to the correct channel handler.

        Expected event keys:
          channel          — 'email', 'whatsapp', or 'web_form'
          response         — the formatted reply text
          customer_id      — email or phone (used as delivery address)
          ticket_id        — for reference in email footer
          thread_id        — Gmail thread ID (email only)
          conversation_id  — conversation reference
          escalated        — bool; if True, delivery still proceeds
        """
        channel = event.get("channel", "")
        response = event.get("response", "")
        customer_id = event.get("customer_id", "")
        ticket_id = event.get("ticket_id")
        thread_id = event.get("thread_id")

        if not response or not customer_id:
            logger.warning(
                "Skipping delivery — missing response or customer_id",
                channel=channel,
                customer_id=customer_id,
            )
            return

        logger.info(
            "Delivering response",
            channel=channel,
            customer_id=customer_id,
            ticket_id=ticket_id,
            escalated=event.get("escalated", False),
        )

        try:
            if channel == "email":
                from production.channels.gmail_handler import send_gmail_reply
                subject = event.get("subject", "Re: Your support request")
                result = await send_gmail_reply(
                    to_email=customer_id,
                    subject=subject,
                    body=response,
                    thread_id=thread_id,
                    ticket_id=ticket_id,
                )

            elif channel == "whatsapp":
                from production.channels.whatsapp_handler import send_whatsapp_reply
                result = await send_whatsapp_reply(
                    to_phone=customer_id,
                    message=response,
                    ticket_id=ticket_id,
                )

            elif channel == "web_form":
                from production.channels.web_form_handler import send_web_form_reply
                customer_name = event.get("customer_name")
                result = await send_web_form_reply(
                    customer_email=customer_id,
                    message=response,
                    ticket_id=ticket_id,
                    customer_name=customer_name,
                )

            else:
                logger.warning("Unknown channel for delivery", channel=channel)
                return

            self._delivered += 1
            logger.info(
                "Response delivered",
                channel=channel,
                customer_id=customer_id,
                result_status=result.get("status") if isinstance(result, dict) else "ok",
            )

        except Exception as e:
            self._errors += 1
            logger.error(
                "Response delivery failed",
                channel=channel,
                customer_id=customer_id,
                error=str(e),
            )

    async def run_forever(self) -> None:
        """Main loop — deliver responses until stopped."""
        logger.info("Starting response delivery loop")
        try:
            async for kafka_message in self.consumer.consume():
                if not self._running:
                    break
                payload = kafka_message.get("value", {})
                await self.deliver(payload)
        except asyncio.CancelledError:
            logger.info("Response delivery loop cancelled")
        except Exception as e:
            logger.error("Fatal error in delivery loop", error=str(e))
            raise
        finally:
            await self.stop()


async def main():
    worker = ResponseDeliveryWorker()
    loop = asyncio.get_event_loop()

    def _shutdown():
        logger.info("Shutdown signal received")
        asyncio.ensure_future(worker.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass  # Windows

    await worker.start()
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
