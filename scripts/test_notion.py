#!/usr/bin/env python3
"""Test Notion API connection and database access."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from src.integrations.notion import NotionClient
from src.utils.config import settings


def _ok_token(key: str) -> bool:
    return bool(key) and "xxxx" not in key and "your_" not in key


def main() -> int:
    print("=" * 50)
    print("NOTION TEST — Andrei AI Agent System")
    print("=" * 50)

    if not _ok_token(settings.notion_api_key):
        print("FAIL: Set NOTION_API_KEY in .env (from notion.so/my-integrations)")
        return 1

    dbs = {
        "Tasks": settings.notion_tasks_db_id,
        "Ideas": settings.notion_ideas_db_id,
        "Posting Plan": settings.notion_posting_plan_db_id,
        "Ajut Cum Pot": settings.notion_ajut_cum_pot_db_id,
        "Journal": settings.notion_journal_db_id,
    }

    try:
        notion = NotionClient()
        print("OK: API token accepted")
    except Exception as e:
        print(f"FAIL: Cannot connect — {e}")
        return 1

    any_ok = False
    for name, db_id in dbs.items():
        if not db_id or "xxxx" in db_id:
            print(f"SKIP: {name} — no database ID in .env")
            continue
        try:
            rows = notion.query_database(db_id)
            print(f"OK: {name} — {len(rows)} item(s)")
            any_ok = True
        except Exception as e:
            print(f"FAIL: {name} — {e}")
            print(f"      → Share database with your integration in Notion")

    if settings.notion_briefings_page_id and "xxxx" not in settings.notion_briefings_page_id:
        try:
            notion.client.blocks.children.list(block_id=settings.notion_briefings_page_id)
            print("OK: Briefings page — accessible")
        except Exception as e:
            print(f"FAIL: Briefings page — {e}")
    else:
        print("SKIP: Briefings page — optional (NOTION_BRIEFINGS_PAGE_ID)")

    if not any_ok:
        print("\nConfigure at least NOTION_TASKS_DB_ID for daily briefing.")
        return 1

    print("\nSUCCESS — Notion is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())