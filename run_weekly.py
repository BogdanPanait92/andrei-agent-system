#!/usr/bin/env python3
"""CLI: Run weekly review (Sunday)."""

import sys

import src.bootstrap  # noqa: F401

from src.utils.logging import setup_logging, get_logger
from src.jobs.weekly_review import run_weekly_review

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    logger.info("run_weekly_cli")
    try:
        result = run_weekly_review()
        print("\n" + "=" * 60)
        print("WEEKLY REVIEW")
        print("=" * 60)
        print(result)
        print("=" * 60)
    except Exception as e:
        logger.error("run_weekly_failed", error=str(e))
        print(f"Eroare: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()