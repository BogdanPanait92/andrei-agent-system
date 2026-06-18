"""Google Docs, Drive, and Calendar API integration."""

import json
from datetime import datetime, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _is_retryable_google_error(exc: BaseException) -> bool:
    if not isinstance(exc, HttpError):
        return False
    status = exc.resp.status
    if status in (429, 500, 502, 503, 504):
        return True
    if status == 404:
        return True
    if status == 400:
        details = str(exc)
        return "FAILED_PRECONDITION" in details or "Precondition check failed" in details
    return False


def _execute_google_request(request: Callable[[], dict]) -> dict:
    @retry(
        retry=retry_if_exception(_is_retryable_google_error),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _run() -> dict:
        return request()

    return _run()

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
        self._resolved_calendar_id: str | None = None

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

    def list_accessible_calendars(self) -> list[dict]:
        """List calendars in the service account's calendarList.

        Note: shared personal calendars often do NOT appear here even when
        events.list works — use GOOGLE_CALENDAR_ID with the Integrate calendar ID.
        """
        try:
            result = _execute_google_request(
                lambda: self.calendar.calendarList()
                .list(showHidden=True, minAccessRole="reader")
                .execute()
            )
            return result.get("items", [])
        except HttpError as e:
            logger.error("google_calendar_list_failed", error=str(e))
            return []

    def _verify_calendar_access(self, calendar_id: str) -> bool:
        try:
            _execute_google_request(
                lambda: self.calendar.calendars().get(calendarId=calendar_id).execute()
            )
            return True
        except HttpError:
            return False

    def _resolve_calendar_id(self) -> str | None:
        """Resolve calendar ID — configured value, calendarList, or primary."""
        if self._resolved_calendar_id:
            return self._resolved_calendar_id

        configured = settings.google_calendar_id.strip()
        candidates: list[str] = []

        if configured:
            candidates.append(configured)

        for cal in self.list_accessible_calendars():
            cal_id = cal.get("id")
            if cal_id and cal_id not in candidates:
                candidates.append(cal_id)

        for cal_id in candidates:
            if self._verify_calendar_access(cal_id):
                self._resolved_calendar_id = cal_id
                logger.info("google_calendar_resolved", calendar_id=cal_id)
                return cal_id

        logger.warning("google_calendar_not_resolved", configured=configured)
        return None

    def _fetch_events(self, time_min: str, time_max: str, max_results: int = 20) -> list[dict]:
        calendar_id = self._resolve_calendar_id()
        if not calendar_id:
            return []
        events_result = _execute_google_request(
            lambda: self.calendar.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events_result.get("items", [])

    def get_upcoming_events(self, days: int = 7, max_results: int = 20) -> list[dict]:
        try:
            now = datetime.utcnow().isoformat() + "Z"
            end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
            return self._fetch_events(now, end, max_results)
        except (HttpError, ValueError) as e:
            logger.error("google_calendar_failed", error=str(e))
            return []

    def _local_day_bounds(self) -> tuple[str, str]:
        """Today 00:00–23:59 in configured timezone (e.g. Europe/Bucharest)."""
        tz = ZoneInfo(settings.timezone)
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        return start.isoformat(), end.isoformat()

    def get_today_events(self) -> list[dict]:
        try:
            today_start, today_end = self._local_day_bounds()
            return self._fetch_events(today_start, today_end)
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
            calendar_id = self._resolve_calendar_id() or settings.google_calendar_id
            return (
                self.calendar.events()
                .insert(calendarId=calendar_id, body=event)
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