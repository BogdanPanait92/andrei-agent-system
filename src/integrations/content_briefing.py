"""Content Creation sheet briefing: missing fields + newly Done items."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.integrations.google_sheets import GoogleSheetsService
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "content_briefing_state.json"
DONE_STATUSES = {"done", "gata", "postat", "posted"}


class ContentBriefingService:
    def __init__(self) -> None:
        self._sheets = GoogleSheetsService()

    def _load_state(self) -> dict:
        if not STATE_FILE.exists():
            return {"last_briefing_at": None, "seen_done_titles": []}
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"last_briefing_at": None, "seen_done_titles": []}

    def _save_state(self, state: dict) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _is_done(self, status: str) -> bool:
        return status.strip().lower() in DONE_STATUSES

    def get_incomplete_rows(self) -> list[dict]:
        """Rows missing link and/or instructions (active pipeline only)."""
        incomplete: list[dict] = []
        for row in self._sheets.get_editor_materials():
            if self._is_done(row.get("Status", "")):
                continue
            missing: list[str] = []
            if not row.get("Link video", "").strip():
                missing.append("link video")
            if not row.get("Instructiuni", "").strip():
                missing.append("instructiuni")
            if missing:
                incomplete.append({**row, "_missing": missing})
        return incomplete

    def get_current_done_titles(self) -> set[str]:
        titles: set[str] = set()
        for row in self._sheets.get_editor_materials():
            if self._is_done(row.get("Status", "")):
                title = row.get("Titlu", "").strip()
                if title:
                    titles.add(title)
        return titles

    def get_newly_done_rows(self) -> list[dict]:
        """Done rows not yet reported in a previous briefing."""
        state = self._load_state()
        seen = {t.strip() for t in state.get("seen_done_titles", []) if t.strip()}
        newly_done: list[dict] = []
        for row in self._sheets.get_editor_materials():
            if not self._is_done(row.get("Status", "")):
                continue
            title = row.get("Titlu", "").strip()
            if title and title not in seen:
                newly_done.append(row)
        return newly_done

    def build_section(self) -> str:
        incomplete = self.get_incomplete_rows()
        newly_done = self.get_newly_done_rows()
        lines = ["**Content Creation (Google Sheets)**", ""]

        lines.append("**De completat (lipseste link sau instructiuni):**")
        if incomplete:
            for row in incomplete:
                titlu = row.get("Titlu", "Fara titlu")
                missing = ", ".join(row["_missing"])
                status = row.get("Status", "") or "-"
                assignat = row.get("Assignat", "") or "-"
                lines.append(f"- {titlu} | lipseste: {missing} | status: {status} | assignat: {assignat}")
        else:
            lines.append("- Nimic de completat.")

        lines.append("")
        lines.append("**Gata de postat (Done de la ultimul briefing):**")
        if newly_done:
            for row in newly_done:
                titlu = row.get("Titlu", "Fara titlu")
                link = row.get("Link video", "") or "-"
                assignat = row.get("Assignat", "") or "-"
                lines.append(f"- {titlu} | link: {link} | assignat: {assignat}")
        else:
            lines.append("- Nimic nou de postat.")

        return "\n".join(lines)

    def finalize(self) -> None:
        """Mark current Done items as seen after briefing was sent."""
        now = datetime.now(ZoneInfo(settings.timezone)).isoformat()
        state = {
            "last_briefing_at": now,
            "seen_done_titles": sorted(self.get_current_done_titles()),
        }
        self._save_state(state)
        logger.info(
            "content_briefing_finalized",
            seen_done=len(state["seen_done_titles"]),
        )

    def run(self) -> str:
        """Build section and update Done snapshot."""
        if not settings.google_sheet_editor_pipeline_id:
            return "**Content Creation:** Sheet neconfigurat (GOOGLE_SHEET_EDITOR_PIPELINE_ID)."
        section = self.build_section()
        self.finalize()
        return section


def append_to_daily_briefing(crew_output: str) -> str:
    """Append Content Creation section to daily briefing output."""
    if not settings.google_sheet_editor_pipeline_id:
        return crew_output
    try:
        service = ContentBriefingService()
        section = service.build_section()
        service.finalize()
        return f"{crew_output}\n\n---\n\n{section}"
    except Exception as e:
        logger.error("content_briefing_failed", error=str(e))
        return f"{crew_output}\n\n---\n\n**Content Creation:** Eroare la citire Sheets ({e})."