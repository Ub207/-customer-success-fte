"""
FastAPI application — Customer Success Digital FTE

Endpoints:
  GET  /health                      — liveness probe
  POST /webhooks/gmail               — Gmail Pub/Sub push
  POST /webhooks/whatsapp            — Twilio WhatsApp webhook
  POST /web-form/submit              — web support form
  GET  /web-form/ticket/{id}         — ticket status lookup
  GET  /conversations/{id}           — full conversation history
  GET  /customers/lookup             — customer lookup by email or phone
  GET  /metrics/channels             — per-channel stats (last 24 h)
  GET  /reports/daily-sentiment      — daily sentiment + performance report
"""

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

# Load .env from production/ directory regardless of where uvicorn is run from
load_dotenv(Path(__file__).parent.parent / ".env")

from production.logging_config import configure_logging
from production.channels.gmail_handler import router as gmail_router
from production.channels.whatsapp_handler import router as whatsapp_router
from production.channels.web_form_handler import router as web_form_router

configure_logging()
logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Customer Success FTE API",
    description="CRM Digital FTE Factory — 24/7 AI customer support across Email, WhatsApp, and Web Form.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Channel routers
# ---------------------------------------------------------------------------

app.include_router(gmail_router)
app.include_router(whatsapp_router)
app.include_router(web_form_router)

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup():
    logger.info("API starting up")
    try:
        from production.database import get_db_pool
        await get_db_pool()
        logger.info("Database pool ready")
    except Exception as e:
        logger.warning("Database not available at startup — running in degraded mode", error=str(e))


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("API shutting down")
    from production.database import close_db_pool
    await close_db_pool()

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"])
async def health_check():
    """Kubernetes liveness probe. Returns 200 whether DB is up or degraded."""
    from production.database import health_check as db_health
    db_ok = await db_health()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
    }

# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

@app.get("/conversations/{conversation_id}", tags=["conversations"])
async def get_conversation(conversation_id: str):
    """Return a full conversation with all its messages."""
    try:
        from production.database import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            conv = await conn.fetchrow(
                """
                SELECT id, customer_id, initial_channel, status,
                       sentiment_score, escalated_to, started_at, ended_at
                FROM conversations
                WHERE id = $1::uuid
                """,
                conversation_id,
            )
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found")

            messages = await conn.fetch(
                """
                SELECT id, channel, direction, role, content,
                       tokens_used, latency_ms, delivery_status, created_at
                FROM messages
                WHERE conversation_id = $1::uuid
                ORDER BY created_at ASC
                """,
                conversation_id,
            )

        return {
            "conversation_id": str(conv["id"]),
            "customer_id": str(conv["customer_id"]),
            "channel": conv["initial_channel"],
            "status": conv["status"],
            "sentiment_score": float(conv["sentiment_score"]) if conv["sentiment_score"] else None,
            "escalated_to": conv["escalated_to"],
            "started_at": conv["started_at"].isoformat() if conv["started_at"] else None,
            "ended_at": conv["ended_at"].isoformat() if conv["ended_at"] else None,
            "messages": [
                {
                    "id": str(m["id"]),
                    "channel": m["channel"],
                    "direction": m["direction"],
                    "role": m["role"],
                    "content": m["content"],
                    "tokens_used": m["tokens_used"],
                    "latency_ms": m["latency_ms"],
                    "delivery_status": m["delivery_status"],
                    "created_at": m["created_at"].isoformat() if m["created_at"] else None,
                }
                for m in messages
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation failed", conversation_id=conversation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@app.get("/customers/lookup", tags=["customers"])
async def lookup_customer(email: str = None, phone: str = None):
    """Look up a customer by email or phone."""
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Provide email or phone query parameter.")
    try:
        from production.database.queries import find_customer
        customer = await find_customer(email=email, phone=phone)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {
            "id": str(customer["id"]),
            "name": customer["name"],
            "email": customer["email"],
            "phone": customer["phone"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("customer lookup failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@app.get("/metrics/channels", tags=["metrics"])
async def get_channel_metrics():
    """Per-channel message and ticket counts for the last 24 hours."""
    try:
        from production.database import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT channel,
                       COUNT(*)                                        AS total_messages,
                       COUNT(*) FILTER (WHERE direction = 'inbound')  AS inbound,
                       COUNT(*) FILTER (WHERE direction = 'outbound') AS outbound
                FROM messages
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY channel
                """
            )
        metrics = {
            r["channel"]: {
                "total_messages": r["total_messages"],
                "inbound": r["inbound"],
                "outbound": r["outbound"],
            }
            for r in rows
        }
        return {"period": "last_24h", "metrics": metrics}
    except Exception as e:
        logger.error("channel metrics failed", error=str(e))
        return {"period": "last_24h", "metrics": {}, "error": str(e)}

# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@app.get("/reports/daily-sentiment", tags=["reports"])
async def daily_sentiment_report(report_date: str = None):
    """
    Daily sentiment and performance report.
    Defaults to yesterday if report_date is not provided (YYYY-MM-DD).
    """
    from datetime import date, timedelta
    try:
        target_date = date.fromisoformat(report_date) if report_date else date.today() - timedelta(days=1)

        from production.workers.daily_report import DailySentimentReporter
        reporter = DailySentimentReporter()
        reporter.report_date = target_date
        report = await reporter.run()
        return report
    except Exception as e:
        logger.error("daily sentiment report failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
