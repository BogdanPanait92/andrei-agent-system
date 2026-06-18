#!/usr/bin/env python3
"""Test Google Sheets integration."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from src.integrations.google_sheets import GoogleSheetsService
from src.utils.config import settings


def main() -> int:
    print("=" * 50)
    print("GOOGLE SHEETS TEST — Andrei AI Agent System")
    print("=" * 50)

    if not settings.google_credentials_json:
        print("FAIL: GOOGLE_CREDENTIALS_JSON not set")
        return 1

    missing = []
    if not settings.google_sheet_ajut_cum_pot_id:
        missing.append("GOOGLE_SHEET_AJUT_CUM_POT_ID")
    if not settings.google_sheet_editor_pipeline_id:
        missing.append("GOOGLE_SHEET_EDITOR_PIPELINE_ID")

    if missing:
        print("Missing sheet IDs in .env.")
        print()
        print("Create sheets manually in Google Sheets, share with service account,")
        print("then add IDs from the URL (between /d/ and /edit):")
        for key in missing:
            print(f"  {key}=...")
        print()
        print("Then run: .\\venv\\Scripts\\python.exe scripts\\setup_google_sheets.py")
        return 1

    sheets = GoogleSheetsService()

    partners = sheets.get_ajut_partners()
    print(f"\nAjut Cum Pot partners: {len(partners)} row(s)")
    if partners:
        print(GoogleSheetsService.format_records(partners[:5], ["Partener", "Locatie", "Status"]))

    materials = sheets.get_editor_materials()
    print(f"\nEditor pipeline: {len(materials)} row(s)")
    if materials:
        print(GoogleSheetsService.format_records(materials[:5], ["Titlu", "Status", "Assignat"]))

    print("\nSUCCESS — Google Sheets is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())