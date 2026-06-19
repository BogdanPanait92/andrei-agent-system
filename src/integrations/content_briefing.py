"""Content Creation briefing from Notion Posting Plan."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.integrations.notion import NotionClient
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "content_briefing_state.json"


class ContentBriefingService:
    def __init__(self) -> None:
        self._notion = NotionClient()

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

    def _get_rows(self) -> list[dict[str, str]]:
        return [
            NotionClient.posting_plan_record(page)
            for page in self._notion.get_posting_plan(limit=100)
        ]

    def get_incomplete_rows(self) -> list[dict]:
        """Posting plan items missing oras and/or prioritate (active pipeline only)."""
        incomplete: list[dict] = []
        for row in self._get_rows():
            if NotionClient.is_posting_done(row.get("Status", "")):
                continue
            missing: list[str] = []
            if not row.get("Oras", "").strip():
                missing.append("oraș")
            if not row.get("Prioritate", "").strip():
                missing.append("prioritate")
            if missing:
                incomplete.append({**row, "_missing": missing})
        return incomplete

    def get_current_done_titles(self) -> set[str]:
        titles: set[str] = set()
        for row in self._get_rows():
            if NotionClient.is_posting_done(row.get("Status", "")):
                title = row.get("Titlu", "").strip()
                if title:
                    titles.add(title)
        return titles

    def _get_seen_titles(self) -> set[str]:
        state = self._load_state()
        seen = {t.strip() for t in state.get("seen_done_titles", []) if t.strip()}
        current_done = self.get_current_done_titles()
        pruned = seen & current_done
        if pruned != seen:
            state["seen_done_titles"] = sorted(pruned)
            self._save_state(state)
            logger.info("content_briefing_seen_pruned", removed=sorted(seen - pruned))
        return pruned

    def get_newly_done_rows(self) -> list[dict]:
        seen = self._get_seen_titles()
        newly_done: list[dict] = []
        for row in self._get_rows():
            if not NotionClient.is_posting_done(row.get("Status", "")):
                continue
            title = row.get("Titlu", "").strip()
            if title and title not in seen:
                newly_done.append(row)
        return newly_done

    def build_section(self) -> str:
        incomplete = self.get_incomplete_rows()
        newly_done = self.get_newly_done_rows()
        lines = ["**Content Creation (Notion → Posting Plan)**", ""]

        lines.append("**De completat (lipsește oraș sau prioritate):**")
        if incomplete:
            for row in incomplete:
                titlu = row.get("Titlu", "Fără titlu")
                missing = ", ".join(row["_missing"])
                status = row.get("Status", "") or "-"
                oras = row.get("Oras", "") or "-"
                prioritate = row.get("Prioritate", "") or "-"
                lines.append(
                    f"- {titlu} | lipsește: {missing} | status: {status} | "
                    f"oraș: {oras} | prioritate: {prioritate}"
                )
        else:
            lines.append("- Nimic de completat.")

        lines.append("")
        lines.append("**Gata de postat (Posted de la ultimul briefing):**")
        if newly_done:
            for row in newly_done:
                titlu = row.get("Titlu", "Fără titlu")
                oras = row.get("Oras", "") or "-"
                prioritate = row.get("Prioritate", "") or "-"
                lines.append(
                    f"- {titlu} | oraș: {oras} | prioritate: {prioritate}"
                )
        else:
            lines.append("- Nimic nou de postat.")

        return "\n".join(lines)

    def finalize(self, reported_titles: list[str] | None = None) -> None:
        now = datetime.now(ZoneInfo(settings.timezone)).isoformat()
        state = self._load_state()
        seen = self._get_seen_titles()

        if reported_titles is not None:
            seen.update(t.strip() for t in reported_titles if t.strip())
        else:
            seen.update(self.get_current_done_titles())

        seen &= self.get_current_done_titles()
        state["last_briefing_at"] = now
        state["seen_done_titles"] = sorted(seen)
        self._save_state(state)
        logger.info(
            "content_briefing_finalized",
            seen_done=len(state["seen_done_titles"]),
            reported=len(reported_titles or []),
        )

    def build_and_finalize(self) -> str:
        newly_done = self.get_newly_done_rows()
        section = self.build_section()
        reported = [row.get("Titlu", "").strip() for row in newly_done if row.get("Titlu", "").strip()]
        self.finalize(reported_titles=reported)
        return section

    def run(self) -> str:
        if not settings.notion_posting_plan_db_id:
            return "**Content Creation:** Posting Plan neconfigurat (NOTION_POSTING_PLAN_DB_ID)."
        return self.build_and_finalize()


def append_to_daily_briefing(crew_output: str) -> str:
    if not settings.notion_posting_plan_db_id:
        return crew_output
    try:
        service = ContentBriefingService()
        section = service.build_and_finalize()
        return f"{crew_output}\n\n---\n\n{section}"
    except Exception as e:
        logger.error("content_briefing_failed", error=str(e))
        return f"{crew_output}\n\n---\n\n**Content Creation:** Eroare la citire Notion ({e})."