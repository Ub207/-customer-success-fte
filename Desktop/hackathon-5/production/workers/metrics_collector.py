"""
Metrics Collector worker.

Runs as a background process, sampling agent performance data every
COLLECTION_INTERVAL_SECONDS (default 300 = 5 min) and writing
aggregated snapshots back to agent_metrics for dashboard consumption.

Also exposes collect_channel_metrics() used by GET /metrics/channels.

Run standalone:
  python -m production.workers.metrics_collector
"""

import asyncio
import signal
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

COLLECTION_INTERVAL_SECONDS = 300  # 5 minutes


class MetricsCollector:
    """
    Periodically aggregates raw agent_metrics rows into summary snapshots
    and writes them back to the database.
    """

    def __init__(self):
        self._running = False
        self._cycles  = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._running = True
        logger.info("MetricsCollector started", interval_seconds=COLLECTION_INTERVAL_SECONDS)

    async def stop(self) -> None:
        self._running = False
        logger.info("MetricsCollector stopped", cycles_completed=self._cycles)

    async def run_forever(self) -> None:
        logger.info("Starting metrics collection loop")
        try:
            while self._running:
                await self.collect_cycle()
                self._cycles += 1
                await asyncio.sleep(COLLECTION_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Metrics collection loop cancelled")
        finally:
            await self.stop()

    # ------------------------------------------------------------------
    # Single collection cycle
    # ------------------------------------------------------------------

    async def collect_cycle(self) -> dict:
        """
        Aggregate the last 5-minute window and write summary rows.
        Returns the snapshot dict (also used in tests).
        """
        now          = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=5)

        snapshot = {
            "collected_at":   now.isoformat(),
            "window_start":   window_start.isoformat(),
            "total_messages": 0,
            "escalated":      0,
            "avg_latency_ms": 0.0,
            "avg_tool_calls": 0.0,
            "by_channel":     {},
        }

        try:
            from production.database import get_db_pool
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Overall window aggregates
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*)    FILTER (WHERE metric_name = 'response_latency_ms') AS messages,
                        SUM(metric_value) FILTER (WHERE metric_name = 'escalation')    AS escalated,
                        AVG(metric_value) FILTER (WHERE metric_name = 'response_latency_ms')
                                                                                       AS avg_latency,
                        AVG(metric_value) FILTER (WHERE metric_name = 'tool_calls_per_message')
                                                                                       AS avg_tools
                    FROM agent_metrics
                    WHERE recorded_at >= $1
                    """,
                    window_start,
                )
                if row:
                    snapshot["total_messages"] = int(row["messages"] or 0)
                    snapshot["escalated"]      = int(row["escalated"] or 0)
                    snapshot["avg_latency_ms"] = round(float(row["avg_latency"] or 0), 0)
                    snapshot["avg_tool_calls"] = round(float(row["avg_tools"] or 0), 2)

                # Per-channel message counts
                channel_rows = await conn.fetch(
                    """
                    SELECT channel, COUNT(*) AS cnt
                    FROM agent_metrics
                    WHERE recorded_at >= $1
                      AND metric_name = 'response_latency_ms'
                      AND channel IS NOT NULL
                    GROUP BY channel
                    """,
                    window_start,
                )
                snapshot["by_channel"] = {
                    r["channel"]: int(r["cnt"]) for r in channel_rows
                }

                # Write snapshot back as a summary metric row
                await conn.execute(
                    """
                    INSERT INTO agent_metrics (metric_name, metric_value, dimensions)
                    VALUES ('snapshot_total_messages', $1, $2::jsonb)
                    """,
                    float(snapshot["total_messages"]),
                    __import__("json").dumps({
                        "window_start": snapshot["window_start"],
                        "escalated":    snapshot["escalated"],
                        "avg_latency":  snapshot["avg_latency_ms"],
                    }),
                )

        except Exception as e:
            logger.warning("collect_cycle DB query failed", error=str(e))

        logger.info(
            "Metrics snapshot",
            total=snapshot["total_messages"],
            escalated=snapshot["escalated"],
            avg_latency_ms=snapshot["avg_latency_ms"],
        )
        return snapshot

    # ------------------------------------------------------------------
    # API helper — used by GET /metrics/channels
    # ------------------------------------------------------------------

    async def collect_channel_metrics(self, window_hours: int = 24) -> dict:
        """
        Aggregate per-channel metrics for the last window_hours.
        Returns dict keyed by channel with message_count, escalation_rate,
        avg_latency_ms.
        """
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        result: dict = {}

        try:
            from production.database import get_db_pool
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        channel,
                        COUNT(*) FILTER (WHERE metric_name = 'response_latency_ms')
                            AS message_count,
                        SUM(metric_value) FILTER (WHERE metric_name = 'escalation')
                            AS escalated_count,
                        AVG(metric_value) FILTER (WHERE metric_name = 'response_latency_ms')
                            AS avg_latency_ms
                    FROM agent_metrics
                    WHERE recorded_at >= $1
                      AND channel IS NOT NULL
                    GROUP BY channel
                    """,
                    window_start,
                )
                for row in rows:
                    msg_count = int(row["message_count"] or 0)
                    esc_count = float(row["escalated_count"] or 0)
                    result[row["channel"]] = {
                        "message_count":    msg_count,
                        "escalation_rate":  round(esc_count / msg_count, 4) if msg_count else 0.0,
                        "avg_latency_ms":   round(float(row["avg_latency_ms"] or 0), 0),
                    }
        except Exception as e:
            logger.warning("collect_channel_metrics failed", error=str(e))

        return result

    # ------------------------------------------------------------------
    # Single-metric write helper (used by message_processor directly)
    # ------------------------------------------------------------------

    async def record_metric(
        self,
        metric_name: str,
        value: float,
        channel: Optional[str] = None,
        dimensions: Optional[dict] = None,
    ) -> None:
        """Write a single metric row to agent_metrics."""
        from production.database.queries import record_agent_metric
        await record_agent_metric(
            metric_name=metric_name,
            metric_value=value,
            channel=channel,
            dimensions=dimensions,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    collector = MetricsCollector()
    loop = asyncio.get_event_loop()

    def _shutdown():
        logger.info("Shutdown signal received")
        asyncio.ensure_future(collector.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass  # Windows

    await collector.start()
    await collector.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
