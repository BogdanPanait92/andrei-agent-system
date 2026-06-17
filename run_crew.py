#!/usr/bin/env python3
"""CLI: Run the Andrei AI crew with a custom query."""

import argparse
import sys

import src.bootstrap  # noqa: F401

from src.utils.logging import setup_logging, get_logger
from src.graph.workflow import run_workflow

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Andrei AI Agent System - Run multi-agent crew",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help='Query for the crew (e.g. "analizeaza saptamana")',
    )
    parser.add_argument(
        "--mode",
        choices=["custom", "daily", "weekly"],
        default="custom",
        help="Execution mode",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Skip WhatsApp/Telegram/Notion notifications",
    )
    args = parser.parse_args()

    query = args.query or "Status general și recomandări"
    logger.info("run_crew_cli", query=query, mode=args.mode)

    try:
        if args.no_notify:
            from src.crew.main_crew import run_crew
            result = run_crew(query=query, mode=args.mode)
        else:
            result = run_workflow(mode=args.mode, query=query)

        print("\n" + "=" * 60)
        print("REZULTAT CREW")
        print("=" * 60)
        print(result)
        print("=" * 60)
    except Exception as e:
        logger.error("run_crew_failed", error=str(e))
        print(f"Eroare: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()