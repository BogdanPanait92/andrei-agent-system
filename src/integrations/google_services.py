"""Google Docs, Drive, and Calendar API integration."""

import json
from datetime import datetime, timedelta
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


class GoogleServices:
    def __init__(self) -> None:
        self._calendar = None
        self._docs = None
        self._drive = None
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
    def calendar(self):
        if not self._calendar:
            self._calendar = build("calendar", "v3", credentials=self._get_credentials())
        return self._calendar

    @property
    def docs(self):
        if not self._docs:
            self._docs = build("docs", "v1", credentials=self._get_credentials())
        return self._docs

    @property
    def drive(self):
        if not self._drive:
            self._drive = build("drive", "v3", credentials=self._get_credentials())
        return self._drive

    def get_upcoming_events(self, days: int = 7, max_results: int = 20) -> list[dict]:
        try:
            now = datetime.utcnow().isoformat() + "Z"
            end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
            events_result = (
                self.calendar.events()
                .list(
                    calendarId=settings.google_calendar_id,
                    timeMin=now,
                    timeMax=end,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return events_result.get("items", [])
        except (HttpError, ValueError) as e:
            logger.error("google_calendar_failed", error=str(e))
            return []

    def get_today_events(self) -> list[dict]:
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat() + "Z"
            today_end = datetime.utcnow().replace(hour=23, minute=59, second=59).isoformat() + "Z"
            events_result = (
                self.calendar.events()
                .list(
                    calendarId=settings.google_calendar_id,
                    timeMin=today_start,
                    timeMax=today_end,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return events_result.get("items", [])
        except (HttpError, ValueError) as e:
            logger.error("google_calendar_today_failed", error=str(e))
            return []

    def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        description: str = "",
    ) -> dict | None:
        try:
            event: dict[str, Any] = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start, "timeZone": settings.timezone},
                "end": {"dateTime": end, "timeZone": settings.timezone},
            }
            return (
                self.calendar.events()
                .insert(calendarId=settings.google_calendar_id, body=event)
                .execute()
            )
        except HttpError as e:
            logger.error("google_create_event_failed", error=str(e))
            return None

    def create_document(self, title: str, content: str = "") -> dict | None:
        try:
            doc = self.docs.documents().create(body={"title": title}).execute()
            doc_id = doc.get("documentId")
            if content and doc_id:
                requests = [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content,
                        }
                    }
                ]
                self.docs.documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests}
                ).execute()
            if settings.google_drive_folder_id and doc_id:
                self.drive.files().update(
                    fileId=doc_id,
                    addParents=settings.google_drive_folder_id,
                    fields="id, parents",
                ).execute()
            return doc
        except HttpError as e:
            logger.error("google_create_doc_failed", error=str(e))
            return None

    def list_drive_files(self, folder_id: str | None = None, limit: int = 20) -> list[dict]:
        try:
            folder = folder_id or settings.google_drive_folder_id
            query = f"'{folder}' in parents" if folder else None
            results = (
                self.drive.files()
                .list(q=query, pageSize=limit, fields="files(id, name, mimeType, modifiedTime)")
                .execute()
            )
            return results.get("files", [])
        except HttpError as e:
            logger.error("google_drive_list_failed", error=str(e))
            return []

    @staticmethod
    def format_events_for_context(events: list[dict]) -> str:
        if not events:
            return "Niciun eveniment programat."
        lines = []
        for ev in events:
            start = ev.get("start", {})
            time_str = start.get("dateTime", start.get("date", "N/A"))
            lines.append(f"- {ev.get('summary', 'Fără titlu')} ({time_str})")
        return "\n".join(lines)