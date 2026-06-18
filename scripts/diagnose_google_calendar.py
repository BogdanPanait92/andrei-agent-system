#!/usr/bin/env python3
"""Deep diagnostics for Google Calendar + service account access."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from googleapiclient.errors import HttpError

from src.integrations.google_services import GoogleServices
from src.utils.config import settings


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)


def main() -> int:
    section("CONFIG")
    creds = json.loads(settings.google_credentials_json)
    sa_email = creds.get("client_email")
    project_id = creds.get("project_id")
    print(f"Service account: {sa_email}")
    print(f"GCP project:     {project_id}")
    print(f"Calendar ID:   {settings.google_calendar_id}")

    g = GoogleServices()
    cal = g.calendar

    section("1. calendarList.list")
    try:
        result = (
            cal.calendarList()
            .list(showHidden=True, minAccessRole="reader")
            .execute()
        )
        items = result.get("items", [])
        print(f"OK — {len(items)} calendar(s)")
        for c in items:
            print(f"  - {c.get('summary')} | id={c.get('id')} | role={c.get('accessRole')}")
    except HttpError as e:
        print(f"HttpError {e.resp.status}: {e.error_details or e}")

    section("2. calendars.get (metadata only)")
    calendar_id = settings.google_calendar_id.strip()
    try:
        meta = cal.calendars().get(calendarId=calendar_id).execute()
        print(f"OK — summary={meta.get('summary')} timezone={meta.get('timeZone')}")
    except HttpError as e:
        print(f"HttpError {e.resp.status}: {e.error_details or e}")

    section("3. events.list (direct, no resolve)")
    try:
        from datetime import datetime, timedelta

        now = datetime.utcnow().isoformat() + "Z"
        end = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
        ev = (
            cal.events()
            .list(
                calendarId=calendar_id,
                timeMin=now,
                timeMax=end,
                maxResults=5,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = ev.get("items", [])
        print(f"OK — {len(items)} event(s)")
        for e in items:
            print(f"  - {e.get('summary')} | {e.get('start')}")
    except HttpError as e:
        print(f"HttpError {e.resp.status}: {e.error_details or e}")

    section("4. freeBusy.query (ACL-free check)")
    try:
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        body = {
            "timeMin": now.isoformat() + "Z",
            "timeMax": (now + timedelta(days=1)).isoformat() + "Z",
            "items": [{"id": calendar_id}],
        }
        fb = cal.freebusy().query(body=body).execute()
        cal_fb = fb.get("calendars", {}).get(calendar_id, {})
        print(f"Result: {json.dumps(cal_fb, indent=2)}")
    except HttpError as e:
        print(f"HttpError {e.resp.status}: {e.error_details or e}")

    section("5. Drive API (same credentials, different API)")
    try:
        files = g.drive.files().list(pageSize=1, fields="files(id,name)").execute()
        print(f"OK — drive files sample: {files.get('files', [])}")
    except HttpError as e:
        print(f"HttpError {e.resp.status}: {e.error_details or e}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())