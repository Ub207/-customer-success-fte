"""
Structured logging configuration using structlog.

Call configure_logging() once at process startup (in main() or app startup).
All modules use structlog.get_logger(__name__) — no further config needed.

Output:
  - Development (LOG_FORMAT=text or unset in non-JSON env): colored key=value
  - Production  (LOG_FORMAT=json):  newline-delimited JSON (ideal for log aggregators)

Log level is controlled by LOG_LEVEL env var (default: INFO).
"""

import logging
import os
import sys

import structlog


def configure_logging() -> None:
    """
    Configure structlog + stdlib logging.
    Safe to call multiple times (idempotent).
    """
    log_level  = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("LOG_FORMAT", "text").lower()

    level = getattr(logging, log_level, logging.INFO)

    # Shared processors used by both stdlib and structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        # Production: JSON output for log aggregators (Datadog, CloudWatch, etc.)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored key=value output
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Silence noisy third-party loggers
    for noisy in ("aiokafka", "asyncpg", "httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Request-scoped context helpers (used in FastAPI middleware)
# ---------------------------------------------------------------------------

def bind_request_context(
    request_id: str,
    customer_id: str = "",
    channel: str = "",
) -> None:
    """Bind context variables to the current async context (structlog contextvars)."""
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        customer_id=customer_id,
        channel=channel,
    )


def clear_request_context() -> None:
    """Clear per-request context variables."""
    structlog.contextvars.clear_contextvars()
