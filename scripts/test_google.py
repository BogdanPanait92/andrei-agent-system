#!/usr/bin/env python3
"""Test Google Calendar API connection."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from src.integrations.google_services import GoogleServices
from src.utils.config import settings


def main() -> int:
    print("=" * 50)
    print("GOOGLE CALENDAR TEST — Andrei AI Agent System")
    print("=" * 50)

    if not settings.google_credentials_json or settings.google_credentials_json.startswith('{"type":"service_account",...'):
        print("FAIL: Set GOOGLE_CREDENTIALS_JSON in .env (full service account JSON, one line)")
        return 1

    try:
        import json
        sa_email = json.loads(settings.google_credentials_json).get("client_email", "unknown")
        print(f"Service account: {sa_email}")
        print(f"Calendar ID:   {settings.google_calendar_id}")
        print()

        google = GoogleServices()
        calendars = google.list_accessible_calendars()
        print(f"calendarList entries: {len(calendars)}")
        if calendars:
            for c in calendars:
                print(f"  - {c.get('summary')} → {c.get('id')}")
        else:
            print("  (empty is normal for service accounts — shared calendars may not appear here)")
        print()

        resolved = google._resolve_calendar_id()
        print(f"Resolved calendar: {resolved or 'NONE'}")
        if not resolved:
            print("\nFAIL: Cannot access configured calendar.")
            print(f"  → Share with: {sa_email}")
            print("  → calendar.google.com → Settings → Integrate calendar → Calendar ID")
            print("  → Permission: 'See all event details' (not just free/busy)")
            return 1

        today = google.get_today_events()
        upcoming = google.get_upcoming_events(days=3)
        print(f"Events today: {len(today)}")
        print(f"Events in next 3 days: {len(upcoming)}")
        if today:
            print("\nToday:")
            print(GoogleServices.format_events_for_context(today))
        elif upcoming:
            print("\nUpcoming:")
            print(GoogleServices.format_events_for_context(upcoming[:5]))
        else:
            print("\nNo events in range (calendar access OK).")

        print("\nSUCCESS — Google Calendar is ready.")
        return 0
    except Exception as e:
        print(f"FAIL: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())