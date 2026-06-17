#!/usr/bin/env python3
"""CLI: Run smart alerts check."""

import sys

import src.bootstrap  # noqa: F401

from src.utils.logging import setup_logging, get_logger
from src.jobs.alerts import run_smart_alerts

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    logger.info("run_alerts_cli")
    try:
        result = run_smart_alerts()
        print(f"Alerte trimise: {result}")
    except Exception as e:
        logger.error("run_alerts_failed", error=str(e))
        print(f"Eroare: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()