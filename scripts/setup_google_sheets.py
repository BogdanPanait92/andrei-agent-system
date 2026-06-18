#!/usr/bin/env python3
"""Initialize headers on existing Google Sheets (manual creation required)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from googleapiclient.errors import HttpError

from src.integrations.google_sheets import AJUT_HEADERS, EDITOR_HEADERS, GoogleSheetsService
from src.utils.config import settings


def _print_manual_setup(sa_email: str) -> None:
    print("Service accounts cannot create new spreadsheets (Drive quota limit).")
    print("Create sheets manually in your Google account, then share with the SA.\n")
    print("Steps:")
    print("  1. Google Sheets → create 2 spreadsheets")
    print("  2. Tab names: Parteneri (Ajut Cum Pot) and Editori (pipeline video)")
    print(f"  3. Share each with: {sa_email} → Editor")
    print("  4. Copy IDs from URL into .env:")
    print("       GOOGLE_SHEET_AJUT_CUM_POT_ID=...")
    print("       GOOGLE_SHEET_EDITOR_PIPELINE_ID=...")
    print("  5. Re-run this script to write header rows")


def main() -> int:
    if not settings.google_credentials_json:
        print("Set GOOGLE_CREDENTIALS_JSON in .env first")
        return 1

    sa_email = json.loads(settings.google_credentials_json).get("client_email", "unknown")
    ajut_id = settings.google_sheet_ajut_cum_pot_id.strip()
    editor_id = settings.google_sheet_editor_pipeline_id.strip()

    if not ajut_id or not editor_id:
        print("Sheet IDs missing in .env.\n")
        _print_manual_setup(sa_email)
        return 1

    sheets = GoogleSheetsService()
    print(f"Service account: {sa_email}")
    print("Writing header rows on existing sheets...\n")

    try:
        sheets.ensure_headers(ajut_id, settings.google_sheet_ajut_tab, AJUT_HEADERS)
        print(f"OK — Ajut Cum Pot ({ajut_id})")
        sheets.ensure_headers(editor_id, settings.google_sheet_editor_tab, EDITOR_HEADERS)
        print(f"OK — Editori ({editor_id})")
    except HttpError as e:
        print(f"FAIL: HttpError {e.resp.status}")
        print(e.error_details or e)
        print()
        print("Check:")
        print(f"  → Sheet shared with {sa_email} as Editor")
        print("  → Tab names match GOOGLE_SHEET_AJUT_TAB / GOOGLE_SHEET_EDITOR_TAB")
        print("  → Sheet IDs in .env are correct")
        return 1

    print("\nSUCCESS — headers ready. Test with:")
    print("  .\\scripts\\local_run.ps1 google-sheets")
    return 0


if __name__ == "__main__":
    sys.exit(main())