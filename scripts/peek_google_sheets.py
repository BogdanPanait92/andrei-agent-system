#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import src.bootstrap  # noqa: F401

from src.integrations.google_sheets import GoogleSheetsService
from src.utils.config import settings

g = GoogleSheetsService()
for label, sid, tab in [
    ("Ajut", settings.google_sheet_ajut_cum_pot_id, settings.google_sheet_ajut_tab),
    ("Editor", settings.google_sheet_editor_pipeline_id, settings.google_sheet_editor_tab),
]:
    print(f"=== {label} | tab: {tab} ===")
    meta = g.sheets.spreadsheets().get(
        spreadsheetId=sid, fields="properties.title,sheets.properties.title"
    ).execute()
    print("File title:", meta["properties"]["title"])
    print("All tabs:", [s["properties"]["title"] for s in meta.get("sheets", [])])
    print("Configured tab:", tab)
    result = (
        g.sheets.spreadsheets()
        .values()
        .get(spreadsheetId=sid, range=f"'{tab}'!A1:G10")
        .execute()
    )
    rows = result.get("values", [])
    print(f"Rows: {len(rows)}")
    for i, row in enumerate(rows, 1):
        print(f"  {i}: {row}")
    print()