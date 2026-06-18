#!/usr/bin/env python3
"""Diagnose Google Sheets API access step by step."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.integrations.google_sheets import GoogleSheetsService
from src.utils.config import settings


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)


def main() -> int:
    creds = json.loads(settings.google_credentials_json)
    sa_email = creds.get("client_email")
    project_id = creds.get("project_id")

    section("CONFIG")
    print(f"GCP project:     {project_id}")
    print(f"Service account: {sa_email}")
    print(f"Ajut sheet ID:   {settings.google_sheet_ajut_cum_pot_id or 'NOT SET'}")
    print(f"Editor sheet ID: {settings.google_sheet_editor_pipeline_id or 'NOT SET'}")

    sheets_svc = GoogleSheetsService()
    creds_obj = sheets_svc._get_credentials()

    section("1. Sheets API — get spreadsheet metadata (read)")
    for label, sheet_id in [
        ("Ajut Cum Pot", settings.google_sheet_ajut_cum_pot_id),
        ("Editori", settings.google_sheet_editor_pipeline_id),
    ]:
        if not sheet_id:
            print(f"  {label}: skip (no ID)")
            continue
        try:
            meta = (
                sheets_svc.sheets.spreadsheets()
                .get(spreadsheetId=sheet_id, fields="properties.title,sheets.properties.title")
                .execute()
            )
            tabs = [s["properties"]["title"] for s in meta.get("sheets", [])]
            print(f"  {label}: OK — '{meta['properties']['title']}' tabs={tabs}")
        except HttpError as e:
            print(f"  {label}: HttpError {e.resp.status}")
            print(f"    {e.error_details or e}")

    section("2. Sheets API — read first row")
    ajut_id = settings.google_sheet_ajut_cum_pot_id.strip()
    if ajut_id:
        try:
            row = (
                sheets_svc.sheets.spreadsheets()
                .values()
                .get(spreadsheetId=ajut_id, range=f"'{settings.google_sheet_ajut_tab}'!1:1")
                .execute()
            )
            print(f"  Headers: {row.get('values', [])}")
        except HttpError as e:
            print(f"  HttpError {e.resp.status}: {e.error_details or e}")

    section("3. Sheets API — enabled? (read public sheet)")
    try:
        sheets_svc.sheets.spreadsheets().get(
            spreadsheetId="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            fields="properties.title",
        ).execute()
        print("  Sheets API: OK (read works)")
    except HttpError as e:
        print(f"  Sheets API: FAIL {e.resp.status} — enable Google Sheets API in GCP")

    section("4. SA cannot auto-create sheets (Drive quota)")
    print("  Service accounts have no Drive storage for new files.")
    print("  → Create sheets in YOUR Google account and share with SA as Editor.")

    section("5. Drive API — list files (same credentials)")
    try:
        drive = build("drive", "v3", credentials=creds_obj)
        files = drive.files().list(pageSize=3, fields="files(id,name,mimeType)").execute()
        print(f"  OK — {len(files.get('files', []))} file(s) visible to SA")
        for f in files.get("files", []):
            print(f"    - {f.get('name')} ({f.get('mimeType')})")
    except HttpError as e:
        print(f"  HttpError {e.resp.status}: {e.error_details or e}")

    section("6. Google Sheets API enabled check (Service Usage)")
    try:
        serviceusage = build("serviceusage", "v1", credentials=creds_obj)
        name = f"projects/{project_id}/services/sheets.googleapis.com"
        state = serviceusage.services().get(name=name).execute()
        print(f"  sheets.googleapis.com state: {state.get('state', 'unknown')}")
    except HttpError as e:
        print(f"  Cannot check API state (need Service Usage API): {e.resp.status}")
        print("  Manually verify: GCP Console → APIs → Google Sheets API → Enabled")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())