"""Google Sheets integration for Ajut Cum Pot partners and editor pipeline."""

from __future__ import annotations

import json
import string
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.integrations.google_services import _execute_google_request
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

AJUT_HEADERS = [
    "Partener",
    "Persoana contact",
    "Telefon/Email",
    "Locatie",
    "Status",
    "Note",
    "Urmatorul pas",
]

EDITOR_HEADERS = [
    "Titlu",
    "Link video",
    "Instructiuni",
    "Status",
    "Assignat",
    "Deadline",
    "Note",
]


def _col_letter(index: int) -> str:
    """0-based column index to Sheets letter (A, B, ..., Z, AA)."""
    result = ""
    n = index + 1
    while n:
        n, rem = divmod(n - 1, 26)
        result = string.ascii_uppercase[rem] + result
    return result


class GoogleSheetsService:
    def __init__(self) -> None:
        self._sheets = None
        self._credentials = None

    def _get_credentials(self):
        if self._credentials:
            return self._credentials
        if not settings.google_credentials_json:
            raise ValueError("GOOGLE_CREDENTIALS_JSON not configured")
        creds_dict = json.loads(settings.google_credentials_json)
        self._credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        return self._credentials

    @property
    def sheets(self):
        if not self._sheets:
            self._sheets = build("sheets", "v4", credentials=self._get_credentials())
        return self._sheets

    def read_records(self, spreadsheet_id: str, tab: str) -> list[dict[str, str]]:
        if not spreadsheet_id:
            return []
        result = _execute_google_request(
            lambda: self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{tab}'!A1:Z1000")
            .execute()
        )
        values = result.get("values", [])
        if not values:
            return []
        headers = [str(h).strip() for h in values[0]]
        records: list[dict[str, str]] = []
        for row in values[1:]:
            if not any(str(cell).strip() for cell in row):
                continue
            record = {headers[i]: str(row[i]).strip() if i < len(row) else "" for i in range(len(headers))}
            records.append(record)
        return records

    def append_record(
        self,
        spreadsheet_id: str,
        tab: str,
        headers: list[str],
        record: dict[str, str],
    ) -> dict:
        row = [record.get(header, "") for header in headers]
        return _execute_google_request(
            lambda: self.sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=f"'{tab}'!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            )
            .execute()
        )

    def _find_row_number(
        self,
        spreadsheet_id: str,
        tab: str,
        key_header: str,
        key_value: str,
    ) -> int | None:
        result = _execute_google_request(
            lambda: self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{tab}'!A1:Z1000")
            .execute()
        )
        values = result.get("values", [])
        if len(values) < 2:
            return None
        headers = [str(h).strip() for h in values[0]]
        if key_header not in headers:
            return None
        key_idx = headers.index(key_header)
        target = key_value.strip().lower()
        for row_offset, row in enumerate(values[1:], start=2):
            cell = str(row[key_idx]).strip().lower() if key_idx < len(row) else ""
            if cell == target:
                return row_offset
        return None

    def update_record(
        self,
        spreadsheet_id: str,
        tab: str,
        key_header: str,
        key_value: str,
        updates: dict[str, str],
        headers: list[str],
    ) -> bool:
        row_num = self._find_row_number(spreadsheet_id, tab, key_header, key_value)
        if not row_num:
            return False

        header_row = _execute_google_request(
            lambda: self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{tab}'!1:1")
            .execute()
        ).get("values", [[]])[0]
        sheet_headers = [str(h).strip() for h in header_row]

        data: list[dict[str, Any]] = []
        for field, value in updates.items():
            if not value or field not in sheet_headers:
                continue
            col = _col_letter(sheet_headers.index(field))
            data.append({"range": f"'{tab}'!{col}{row_num}", "values": [[value]]})

        if not data:
            return True

        _execute_google_request(
            lambda: self.sheets.spreadsheets()
            .values()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"valueInputOption": "USER_ENTERED", "data": data},
            )
            .execute()
        )
        return True

    def ensure_headers(self, spreadsheet_id: str, tab: str, headers: list[str]) -> None:
        existing = _execute_google_request(
            lambda: self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{tab}'!1:1")
            .execute()
        ).get("values", [])
        if existing and [str(c).strip() for c in existing[0]] == headers:
            return
        end_col = _col_letter(len(headers) - 1)
        _execute_google_request(
            lambda: self.sheets.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=f"'{tab}'!A1:{end_col}1",
                valueInputOption="USER_ENTERED",
                body={"values": [headers]},
            )
            .execute()
        )

    def create_spreadsheet(self, title: str, tab: str, headers: list[str]) -> str:
        created = _execute_google_request(
            lambda: self.sheets.spreadsheets()
            .create(
                body={
                    "properties": {"title": title},
                    "sheets": [{"properties": {"title": tab}}],
                }
            )
            .execute()
        )
        spreadsheet_id = created["spreadsheetId"]
        self.ensure_headers(spreadsheet_id, tab, headers)
        return spreadsheet_id

    # --- Ajut Cum Pot partners ---

    def get_ajut_partners(self, status: str = "") -> list[dict[str, str]]:
        records = self.read_records(
            settings.google_sheet_ajut_cum_pot_id,
            settings.google_sheet_ajut_tab,
        )
        if status:
            status_lower = status.strip().lower()
            records = [r for r in records if r.get("Status", "").lower() == status_lower]
        return records

    def add_ajut_partner(
        self,
        partener: str,
        persoana_contact: str = "",
        telefon_email: str = "",
        locatie: str = "",
        status: str = "",
        note: str = "",
        urmatorul_pas: str = "",
    ) -> dict:
        record = {
            "Partener": partener.strip(),
            "Persoana contact": persoana_contact.strip(),
            "Telefon/Email": telefon_email.strip(),
            "Locatie": locatie.strip(),
            "Status": status.strip(),
            "Note": note.strip(),
            "Urmatorul pas": urmatorul_pas.strip(),
        }
        return self.append_record(
            settings.google_sheet_ajut_cum_pot_id,
            settings.google_sheet_ajut_tab,
            AJUT_HEADERS,
            record,
        )

    def update_ajut_partner(self, partener: str, **fields: str) -> bool:
        field_map = {
            "persoana_contact": "Persoana contact",
            "telefon_email": "Telefon/Email",
            "locatie": "Locatie",
            "status": "Status",
            "note": "Note",
            "urmatorul_pas": "Urmatorul pas",
        }
        updates = {field_map[k]: v for k, v in fields.items() if v and k in field_map}
        return self.update_record(
            settings.google_sheet_ajut_cum_pot_id,
            settings.google_sheet_ajut_tab,
            "Partener",
            partener,
            updates,
            AJUT_HEADERS,
        )

    # --- Editor pipeline ---

    def get_editor_rows_missing_fields(self) -> list[dict[str, str]]:
        """Active rows (not Done) missing link and/or instructions."""
        done = {"done", "gata", "postat", "posted"}
        missing_rows: list[dict[str, str]] = []
        for row in self.get_editor_materials():
            if row.get("Status", "").strip().lower() in done:
                continue
            lacks_link = not row.get("Link video", "").strip()
            lacks_instr = not row.get("Instructiuni", "").strip()
            if lacks_link or lacks_instr:
                missing_rows.append(row)
        return missing_rows

    def get_editor_materials(self, status: str = "", assignat: str = "") -> list[dict[str, str]]:
        records = self.read_records(
            settings.google_sheet_editor_pipeline_id,
            settings.google_sheet_editor_tab,
        )
        if status:
            status_lower = status.strip().lower()
            records = [r for r in records if r.get("Status", "").lower() == status_lower]
        if assignat:
            assignat_lower = assignat.strip().lower()
            records = [r for r in records if r.get("Assignat", "").lower() == assignat_lower]
        return records

    def add_editor_material(
        self,
        titlu: str,
        link_video: str = "",
        instructiuni: str = "",
        status: str = "",
        assignat: str = "",
        deadline: str = "",
        note: str = "",
    ) -> dict:
        record = {
            "Titlu": titlu.strip(),
            "Link video": link_video.strip(),
            "Instructiuni": instructiuni.strip(),
            "Status": status.strip(),
            "Assignat": assignat.strip(),
            "Deadline": deadline.strip(),
            "Note": note.strip(),
        }
        return self.append_record(
            settings.google_sheet_editor_pipeline_id,
            settings.google_sheet_editor_tab,
            EDITOR_HEADERS,
            record,
        )

    def update_editor_material(self, titlu: str, **fields: str) -> bool:
        field_map = {
            "link_video": "Link video",
            "instructiuni": "Instructiuni",
            "status": "Status",
            "assignat": "Assignat",
            "deadline": "Deadline",
            "note": "Note",
        }
        updates = {field_map[k]: v for k, v in fields.items() if v and k in field_map}
        return self.update_record(
            settings.google_sheet_editor_pipeline_id,
            settings.google_sheet_editor_tab,
            "Titlu",
            titlu,
            updates,
            EDITOR_HEADERS,
        )

    @staticmethod
    def format_records(records: list[dict[str, str]], key_fields: list[str]) -> str:
        if not records:
            return (
                "SHEETS_EMPTY: 0 inregistrari in Google Sheets (doar headere, fara date). "
                "Raspunde utilizatorului ca lista e goala. NU inventa inregistrari."
            )
        lines = []
        for record in records:
            parts = [f"{field}: {record.get(field, '')}" for field in key_fields if record.get(field)]
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)