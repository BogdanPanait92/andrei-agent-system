"""Structured logging configuration."""

import logging
import sys

import structlog

from src.utils.config import settings


def setup_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.app_env == "development"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # google-auth 2.55+ probes an optional Regional Access Boundary endpoint for
    # service accounts; personal projects don't have one, so it logs a harmless warning.
    logging.getLogger("google.oauth2._client").setLevel(logging.ERROR)
    logging.getLogger("google.auth._regional_access_boundary_utils").setLevel(logging.ERROR)


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)