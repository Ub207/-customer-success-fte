"""
Async database connection layer.

Provides:
  - Singleton asyncpg connection pool
  - get_db_pool()   — acquire the pool (creates it on first call)
  - close_db_pool() — graceful shutdown
  - health_check()  — liveness probe used by /health endpoint
"""

import os
from typing import Optional

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """
    Return the singleton asyncpg connection pool.
    Creates the pool on the first call using DATABASE_URL from the environment.
    """
    global _pool
    if _pool is None:
        dsn = os.environ.get(
            "DATABASE_URL",
            "postgresql://fte_user:fte_password@localhost:5433/fte_db",
        )
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("Database pool created", dsn=_redact_dsn(dsn))
    return _pool


async def close_db_pool() -> None:
    """Close the pool gracefully. Call this on application shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def health_check() -> bool:
    """
    Verify the database is reachable.
    Used by the /health endpoint and Kubernetes liveness probe.
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _redact_dsn(dsn: str) -> str:
    """Remove password from DSN before logging."""
    try:
        import re
        return re.sub(r":([^@]+)@", ":***@", dsn)
    except Exception:
        return "<dsn>"
