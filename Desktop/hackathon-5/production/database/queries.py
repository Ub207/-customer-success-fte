"""
Database query helpers.

All SQL lives here — no raw queries scattered across the application.
Every public function manages its own pool acquisition so callers
don't need to handle connections directly.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


# ============================================================
# Customers
# ============================================================

async def get_or_create_customer(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """
    Find an existing customer by email or phone, or create a new one.
    Returns a dict with at least: id, name, email, phone.
    """
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = None
        if email:
            row = await conn.fetchrow(
                "SELECT id, name, email, phone FROM customers WHERE email = $1",
                email.lower().strip(),
            )
        if row is None and phone:
            row = await conn.fetchrow(
                "SELECT id, name, email, phone FROM customers WHERE phone = $1",
                phone,
            )
        if row:
            return dict(row)

        customer_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO customers (id, name, email, phone)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT DO NOTHING
            """,
            customer_id,
            name or "",
            email.lower().strip() if email else None,
            phone,
        )
        logger.info("Customer created", customer_id=customer_id)
        return {"id": customer_id, "name": name or "", "email": email, "phone": phone}


async def find_customer(
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[dict]:
    """Look up a customer by email or phone. Returns None if not found."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = None
        if email:
            row = await conn.fetchrow(
                "SELECT id, name, email, phone FROM customers WHERE email = $1",
                email.lower().strip(),
            )
        if row is None and phone:
            row = await conn.fetchrow(
                "SELECT id, name, email, phone FROM customers WHERE phone = $1",
                phone,
            )
        return dict(row) if row else None


async def upsert_customer_identifier(
    customer_id: str,
    identifier_type: str,
    identifier_value: str,
) -> None:
    """Register a channel-specific identifier for cross-channel matching."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value)
            VALUES ($1::uuid, $2, $3)
            ON CONFLICT (identifier_type, identifier_value) DO NOTHING
            """,
            customer_id,
            identifier_type,
            identifier_value,
        )


async def get_customer_by_identifier(
    identifier_type: str,
    identifier_value: str,
) -> Optional[dict]:
    """Resolve any channel identifier back to a customers row."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT c.id, c.name, c.email, c.phone
            FROM customer_identifiers ci
            JOIN customers c ON c.id = ci.customer_id
            WHERE ci.identifier_type = $1 AND ci.identifier_value = $2
            """,
            identifier_type,
            identifier_value,
        )
        return dict(row) if row else None


# ============================================================
# Conversations
# ============================================================

async def get_or_create_conversation(
    customer_id: str,
    channel: str,
    conversation_id: Optional[str] = None,
    within_hours: int = 24,
) -> dict:
    """
    Return an existing active conversation for this customer+channel within
    the time window, or create a new one.
    """
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Try explicit conversation_id first
        if conversation_id:
            row = await conn.fetchrow(
                "SELECT id, customer_id, initial_channel, status FROM conversations WHERE id = $1::uuid",
                conversation_id,
            )
            if row:
                return dict(row)

        # Look for a recent active conversation
        row = await conn.fetchrow(
            """
            SELECT id, customer_id, initial_channel, status
            FROM conversations
            WHERE customer_id = $1::uuid
              AND initial_channel = $2
              AND status = 'active'
              AND started_at >= NOW() - ($3 * INTERVAL '1 hour')
            ORDER BY started_at DESC
            LIMIT 1
            """,
            customer_id,
            channel,
            within_hours,
        )
        if row:
            return dict(row)

        # Create a new one
        new_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO conversations (id, customer_id, initial_channel, status)
            VALUES ($1, $2::uuid, $3, 'active')
            """,
            new_id,
            customer_id,
            channel,
        )
        return {
            "id": new_id,
            "customer_id": customer_id,
            "initial_channel": channel,
            "status": "active",
        }


async def close_conversation(
    conversation_id: str,
    resolution_type: str = "auto_resolved",
    sentiment_score: Optional[float] = None,
    escalated_to: Optional[str] = None,
) -> None:
    """Resolve or escalate a conversation and stamp ended_at."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE conversations
            SET status          = $2,
                resolution_type = $3,
                sentiment_score = $4,
                escalated_to    = $5,
                ended_at        = NOW()
            WHERE id = $1::uuid
            """,
            conversation_id,
            "escalated" if escalated_to else "resolved",
            resolution_type,
            sentiment_score,
            escalated_to,
        )


# ============================================================
# Messages
# ============================================================

async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    channel: str = "web_form",
    direction: str = "inbound",
    tokens_used: Optional[int] = None,
    latency_ms: Optional[int] = None,
    channel_message_id: Optional[str] = None,
    tool_calls: Optional[list] = None,
    delivery_status: str = "pending",
) -> str:
    """Insert one message row and return its UUID."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    message_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO messages (
                id, conversation_id, channel, direction, role, content,
                tokens_used, latency_ms, tool_calls, channel_message_id, delivery_status
            ) VALUES ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11)
            """,
            message_id,
            conversation_id,
            channel,
            direction,
            role,
            content,
            tokens_used,
            latency_ms,
            json.dumps(tool_calls or []),
            channel_message_id,
            delivery_status,
        )
    return message_id


async def update_delivery_status(channel_message_id: str, status: str) -> None:
    """Update delivery_status for a message by its channel-native ID (Twilio SID, etc.)."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE messages SET delivery_status = $1 WHERE channel_message_id = $2",
            status,
            channel_message_id,
        )


async def get_customer_history_all_channels(customer_id: str, limit: int = 20) -> list:
    """Return the most recent messages for a customer across ALL channels."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.id, m.channel, m.direction, m.role, m.content, m.created_at
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.customer_id = $1::uuid
            ORDER BY m.created_at DESC
            LIMIT $2
            """,
            customer_id,
            limit,
        )
        return [dict(r) for r in rows]


# ============================================================
# Tickets
# ============================================================

async def create_ticket(
    customer_id: str,
    source_channel: str,
    category: str = "general",
    priority: str = "medium",
    conversation_id: Optional[str] = None,
    resolution_notes: Optional[str] = None,
) -> str:
    """Create a new support ticket and return its UUID."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    ticket_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tickets (
                id, customer_id, conversation_id, source_channel,
                category, priority, status, resolution_notes
            ) VALUES ($1, $2::uuid, $3::uuid, $4, $5, $6, 'open', $7)
            """,
            ticket_id,
            customer_id,
            conversation_id,
            source_channel,
            category,
            priority,
            resolution_notes,
        )
    return ticket_id


async def update_ticket_status(
    ticket_id: str,
    status: str,
    resolution_notes: Optional[str] = None,
) -> None:
    """Update ticket status. Sets resolved_at when status becomes 'resolved'."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    resolved_at = datetime.now(timezone.utc) if status == "resolved" else None
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE tickets
            SET status           = $2,
                resolution_notes = COALESCE($3, resolution_notes),
                resolved_at      = $4,
                updated_at       = NOW()
            WHERE id = $1::uuid
            """,
            ticket_id,
            status,
            resolution_notes,
            resolved_at,
        )


async def get_customer_tickets(customer_id: str, limit: int = 10) -> list:
    """Return recent tickets for a customer."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, source_channel, category, priority, status,
                   resolution_notes, created_at, resolved_at
            FROM tickets
            WHERE customer_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT $2
            """,
            customer_id,
            limit,
        )
        return [dict(r) for r in rows]


# ============================================================
# Knowledge Base
# ============================================================

async def search_knowledge_base(query: str, max_results: int = 5) -> list:
    """Keyword (ILIKE) search — used when no embedding is available."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, content, category
            FROM knowledge_base
            WHERE title ILIKE $1 OR content ILIKE $1
            LIMIT $2
            """,
            f"%{query}%",
            max_results,
        )
        return [dict(r) for r in rows]


async def search_knowledge_base_vector(embedding: list, max_results: int = 5) -> list:
    """Semantic search using pgvector cosine similarity."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, content, category,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM knowledge_base
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            embedding,
            max_results,
        )
        return [dict(r) for r in rows]


async def insert_knowledge_article(
    title: str,
    content: str,
    category: str,
    embedding: Optional[list] = None,
) -> str:
    """Insert a new knowledge base article and return its UUID."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    article_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO knowledge_base (id, title, content, category, embedding)
            VALUES ($1, $2, $3, $4, $5)
            """,
            article_id,
            title,
            content,
            category,
            embedding,
        )
    return article_id


# ============================================================
# Agent Metrics
# ============================================================

async def record_agent_metric(
    metric_name: str,
    metric_value: float,
    channel: Optional[str] = None,
    dimensions: Optional[dict] = None,
) -> None:
    """Record a single named metric data point."""
    from production.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO agent_metrics (metric_name, metric_value, channel, dimensions)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            metric_name,
            metric_value,
            channel,
            json.dumps(dimensions or {}),
        )
