#!/usr/bin/env python3
"""CLI: Run daily briefing (WhatsApp/Telegram + Notion)."""

import sys

import src.bootstrap  # noqa: F401

from src.utils.logging import setup_logging, get_logger
from src.jobs.daily_briefing import run_daily_briefing

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    logger.info("run_daily_cli")
    try:
        result = run_daily_briefing()
        print("\n" + "=" * 60)
        print("DAILY BRIEFING")
        print("=" * 60)
        print(result)
        print("=" * 60)
    except Exception as e:
        logger.error("run_daily_failed", error=str(e))
        print(f"Eroare: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()