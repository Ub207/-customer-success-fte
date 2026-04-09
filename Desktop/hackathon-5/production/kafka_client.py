"""
Kafka client for the Customer Success FTE system.

Provides producer and consumer classes for all FTE message topics.
Uses aiokafka for async Kafka operations.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

# Load .env if not already loaded
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

logger = structlog.get_logger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_SASL_USERNAME     = os.environ.get("KAFKA_SASL_USERNAME", "")
KAFKA_SASL_PASSWORD     = os.environ.get("KAFKA_SASL_PASSWORD", "")
KAFKA_SECURITY_PROTOCOL = os.environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
KAFKA_SASL_MECHANISM    = os.environ.get("KAFKA_SASL_MECHANISM", "PLAIN")

def _sasl_kwargs() -> dict:
    """Return SASL kwargs if credentials are configured."""
    if KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD:
        import ssl
        ssl_ctx = ssl.create_default_context()
        return {
            "security_protocol":   KAFKA_SECURITY_PROTOCOL,
            "sasl_mechanism":      KAFKA_SASL_MECHANISM,
            "sasl_plain_username": KAFKA_SASL_USERNAME,
            "sasl_plain_password": KAFKA_SASL_PASSWORD,
            "ssl_context":         ssl_ctx,
        }
    return {}

TOPICS: Dict[str, str] = {
    "gmail_inbound": "fte.gmail.inbound",
    "whatsapp_inbound": "fte.whatsapp.inbound",
    "webform_inbound": "fte.webform.inbound",
    "outbound_email": "fte.channels.email.outbound",
    "outbound_whatsapp": "fte.channels.whatsapp.outbound",
    "escalations": "fte.escalations",
    "agent_responses": "fte.agent.responses",
    "metrics": "fte.metrics",
    "dlq": "fte.dlq",
}


class FTEKafkaProducer:
    """Async Kafka producer for publishing FTE messages."""

    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers or KAFKA_BOOTSTRAP_SERVERS
        self._producer = None

    async def start(self) -> None:
        try:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                **_sasl_kwargs(),
            )
            await self._producer.start()
            logger.info("Kafka producer started", servers=self.bootstrap_servers)
        except Exception as e:
            logger.warning("Kafka producer start failed (offline mode)", error=str(e))
            self._producer = None

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")

    async def send(self, topic: str, value: dict, key: Optional[str] = None) -> None:
        if self._producer is None:
            logger.warning("Kafka producer offline, message dropped", topic=topic)
            return
        await self._producer.send_and_wait(topic, value=value, key=key)
        logger.debug("Message sent", topic=topic, key=key)

    async def send_to_dlq(self, original_topic: str, value: dict, error: str) -> None:
        dlq_message = {
            "original_topic": original_topic,
            "error": error,
            "original_message": value,
        }
        await self.send(TOPICS["dlq"], dlq_message, key=original_topic)


class FTEKafkaConsumer:
    """Async Kafka consumer for reading FTE messages."""

    def __init__(self, topics: List[str], group_id: str, bootstrap_servers: Optional[str] = None):
        self.topics = topics
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers or KAFKA_BOOTSTRAP_SERVERS
        self._consumer = None

    async def start(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer
            self._consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                **_sasl_kwargs(),
            )
            await self._consumer.start()
            logger.info(
                "Kafka consumer started",
                topics=self.topics,
                group_id=self.group_id,
            )
        except Exception as e:
            logger.warning("Kafka consumer start failed (offline mode)", error=str(e))
            self._consumer = None

    async def stop(self) -> None:
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
            logger.info("Kafka consumer stopped")

    async def consume(self):
        """
        Async generator that yields normalized message dicts.
        Each yielded dict has at minimum a 'value' key.
        """
        if self._consumer is None:
            logger.warning("Kafka consumer offline, no messages to consume")
            return

        async for msg in self._consumer:
            yield {
                "topic": msg.topic,
                "partition": msg.partition,
                "offset": msg.offset,
                "key": msg.key.decode("utf-8") if msg.key else None,
                "value": msg.value,
            }
