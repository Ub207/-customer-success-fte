"""
Daily Sentiment Report Worker.

Runs as a scheduled job (cron: daily at 06:00 UTC).
Generates a full sentiment + performance report for the previous day
and publishes the result to the Kafka metrics topic.

Run manually:
  python -m production.workers.daily_report
"""

import asyncio
import os
from datetime import date, timedelta
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class DailySentimentReporter:
    """
    Builds and publishes the daily customer sentiment + agent performance report.
    Queries are aligned to the V1 schema (agent_metrics.recorded_at, etc.)
    """

    def __init__(self):
        self.report_date: date = date.today() - timedelta(days=1)

    # ------------------------------------------------------------------
    # Data fetchers
    # ------------------------------------------------------------------

    async def fetch_ticket_stats(self) -> dict:
        """
        Count tickets created on report_date, broken down by channel and status.
        Uses the tickets table (source_channel, status, created_at).
        """
        try:
            from production.database import get_db_pool
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*)                                                AS total,
                        COUNT(*) FILTER (WHERE source_channel = 'email')        AS email_count,
                        COUNT(*) FILTER (WHERE source_channel = 'whatsapp')     AS whatsapp_count,
                        COUNT(*) FILTER (WHERE source_channel = 'web_form')     AS webform_count,
                        COUNT(*) FILTER (WHERE status = 'escalated')            AS escalated_count,
                        COUNT(*) FILTER (WHERE status = 'resolved')             AS resolved_count
                    FROM tickets
                    WHERE DATE(created_at AT TIME ZONE 'UTC') = $1
                    """,
                    self.report_date,
                )
                if row:
                    return dict(row)
        except Exception as e:
            logger.warning("fetch_ticket_stats failed", error=str(e))

        return {
            "total": 0,
            "email_count": 0,
            "whatsapp_count": 0,
            "webform_count": 0,
            "escalated_count": 0,
            "resolved_count": 0,
        }

    async def fetch_performance_stats(self) -> dict:
        """
        Aggregate agent_metrics rows for report_date.
        Uses recorded_at (the correct V1 column), metric_name, and metric_value.
        """
        try:
            from production.database import get_db_pool
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        AVG(metric_value) FILTER (WHERE metric_name = 'response_latency_ms')
                            AS avg_latency_ms,
                        SUM(metric_value) FILTER (WHERE metric_name = 'escalation')
                            AS escalation_signals,
                        AVG(metric_value) FILTER (WHERE metric_name = 'tool_calls_per_message')
                            AS avg_tool_calls
                    FROM agent_metrics
                    WHERE DATE(recorded_at AT TIME ZONE 'UTC') = $1
                    """,
                    self.report_date,
                )
                if row:
                    return {
                        "avg_latency_ms":       round(float(row["avg_latency_ms"] or 0), 0),
                        "escalation_signals":   int(row["escalation_signals"] or 0),
                        "avg_tool_calls":       round(float(row["avg_tool_calls"] or 0), 2),
                    }
        except Exception as e:
            logger.warning("fetch_performance_stats failed", error=str(e))

        return {
            "avg_latency_ms":     0.0,
            "escalation_signals": 0,
            "avg_tool_calls":     0.0,
        }

    async def fetch_sentiment_scores(self) -> dict:
        """
        Aggregate sentiment_score from the conversations table for report_date.
        sentiment_score lives on conversations (0.00 = negative, 1.00 = positive).
        """
        try:
            from production.database import get_db_pool
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT sentiment_score, initial_channel
                    FROM conversations
                    WHERE DATE(started_at AT TIME ZONE 'UTC') = $1
                      AND sentiment_score IS NOT NULL
                    """,
                    self.report_date,
                )
                if rows:
                    scores = [float(r["sentiment_score"]) for r in rows]
                    avg    = sum(scores) / len(scores)
                    # 0.00-0.39 = negative, 0.40-0.59 = neutral, 0.60-1.00 = positive
                    positive = sum(1 for s in scores if s >= 0.6)
                    negative = sum(1 for s in scores if s < 0.4)
                    neutral  = len(scores) - positive - negative
                    return {
                        "average_sentiment": round(avg, 3),
                        "positive_count":   positive,
                        "neutral_count":    neutral,
                        "negative_count":   negative,
                        "total_scored":     len(scores),
                    }
        except Exception as e:
            logger.warning("fetch_sentiment_scores failed", error=str(e))

        return {
            "average_sentiment": 0.0,
            "positive_count":   0,
            "neutral_count":    0,
            "negative_count":   0,
            "total_scored":     0,
        }

    async def fetch_hourly_volume(self) -> list:
        """
        Return per-hour message counts for report_date (for trend charts).
        Uses the messages table.
        """
        try:
            from production.database import get_db_pool
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')::int AS hour,
                        channel,
                        COUNT(*) AS count
                    FROM messages
                    WHERE DATE(created_at AT TIME ZONE 'UTC') = $1
                      AND direction = 'inbound'
                    GROUP BY 1, 2
                    ORDER BY 1, 2
                    """,
                    self.report_date,
                )
                return [{"hour": r["hour"], "channel": r["channel"], "count": r["count"]} for r in rows]
        except Exception as e:
            logger.warning("fetch_hourly_volume failed", error=str(e))
            return []

    # ------------------------------------------------------------------
    # Report builder
    # ------------------------------------------------------------------

    def build_report(
        self,
        ticket_stats: dict,
        perf_stats: dict,
        sentiment: dict,
        hourly: list,
    ) -> dict:
        total = ticket_stats.get("total", 0) or 1
        escalation_rate = round(ticket_stats.get("escalated_count", 0) / total * 100, 1)
        resolution_rate = round(ticket_stats.get("resolved_count", 0) / total * 100, 1)

        return {
            "report_date": str(self.report_date),
            "total_tickets": ticket_stats.get("total", 0),
            "channel_breakdown": {
                "email":    ticket_stats.get("email_count", 0),
                "whatsapp": ticket_stats.get("whatsapp_count", 0),
                "web_form": ticket_stats.get("webform_count", 0),
            },
            "escalations": {
                "total":        ticket_stats.get("escalated_count", 0),
                "rate_percent": escalation_rate,
            },
            "resolutions": {
                "total":        ticket_stats.get("resolved_count", 0),
                "rate_percent": resolution_rate,
            },
            "agent_performance": {
                "avg_response_latency_ms": perf_stats.get("avg_latency_ms", 0),
                "avg_tool_calls":          perf_stats.get("avg_tool_calls", 0),
            },
            "sentiment": sentiment,
            "hourly_volume": hourly,
        }

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish_report(self, report: dict) -> None:
        """Publish report payload to the Kafka metrics topic."""
        try:
            from production.kafka_client import FTEKafkaProducer, TOPICS
            producer = FTEKafkaProducer()
            await producer.start()
            await producer.send(TOPICS["metrics"], {"metric": "daily_report", **report})
            await producer.stop()
            logger.info("Daily report published to Kafka", report_date=report["report_date"])
        except Exception as e:
            logger.warning("Failed to publish report to Kafka", error=str(e))

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run(self) -> dict:
        """Run the full daily report pipeline and return the report dict."""
        logger.info("Building daily report", report_date=str(self.report_date))

        ticket_stats, perf_stats, sentiment, hourly = await asyncio.gather(
            self.fetch_ticket_stats(),
            self.fetch_performance_stats(),
            self.fetch_sentiment_scores(),
            self.fetch_hourly_volume(),
        )

        report = self.build_report(ticket_stats, perf_stats, sentiment, hourly)
        await self.publish_report(report)

        logger.info(
            "Daily report complete",
            total_tickets=report["total_tickets"],
            escalation_rate=report["escalations"]["rate_percent"],
            avg_sentiment=report["sentiment"]["average_sentiment"],
        )
        return report


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    reporter = DailySentimentReporter()
    import json
    print(json.dumps(await reporter.run(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
