#!/usr/bin/env python3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import src.bootstrap  # noqa: F401

from src.integrations.google_services import GoogleServices

g = GoogleServices()
cal = g.calendar
items = cal.calendarList().list(showHidden=True, minAccessRole="reader").execute().get("items", [])
print(f"Found {len(items)} calendar(s):\n")
for c in items:
    print(f"  id:         {c.get('id')}")
    print(f"  summary:    {c.get('summary')}")
    print(f"  accessRole: {c.get('accessRole')}")
    print()

if items:
    cid = items[0]["id"]
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=3)).isoformat() + "Z"
    ev = (
        cal.events()
        .list(calendarId=cid, timeMin=now, timeMax=end, singleEvents=True, orderBy="startTime", maxResults=5)
        .execute()
    )
    print(f"Events in '{items[0].get('summary')}' (next 3 days): {len(ev.get('items', []))}")
    for e in ev.get("items", []):
        print(f"  - {e.get('summary')} | {e.get('start')}")