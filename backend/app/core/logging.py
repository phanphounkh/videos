"""Structured logging setup.

WHAT: configures `structlog` so every log line is a set of key/value pairs.
WHY:  we will emit domain events (render_started, script_generated, ...) that we
      want to filter and search later. Free-text log strings are hard to query;
      structured events are not. In production we print JSON so a log collector
      can parse it; in development we print colourised, human-readable lines.
HOW:  call `configure_logging()` once at startup, then anywhere in the codebase:

          log = get_logger(__name__)
          log.info("render_started", project_id=str(project.id))

Never log secrets (tokens, API keys, passwords).
"""

import logging
import sys

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_json or settings.is_production
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
