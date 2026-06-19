"""Generate voice-over scripts for ideas already saved in Notion."""

from __future__ import annotations

from src.crew.main_crew import run_crew
from src.integrations.notion import NotionClient
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IdeaVoiceoverService:
    def __init__(self) -> None:
        self._notion = NotionClient()

    def find_ideas(self, query: str, status: str | None = None) -> list[dict]:
        return self._notion.find_ideas_matching(query, status=status, limit=50)

    def ideas_missing_voiceover(self, statuses: list[str | None] | None = None) -> list[dict]:
        """Return Notion idea pages that have no voice-over section yet."""
        status_filters = statuses if statuses is not None else self._configured_statuses()
        if not status_filters:
            status_filters = [None]

        missing: list[dict] = []
        seen_ids: set[str] = set()
        for status in status_filters:
            for idea in self._notion.get_ideas(status=status, limit=50):
                page_id = idea.get("id")
                if not page_id or page_id in seen_ids:
                    continue
                seen_ids.add(page_id)
                if self._notion.idea_has_voiceover(page_id):
                    continue
                missing.append(idea)
        return missing

    @staticmethod
    def _configured_statuses() -> list[str | None]:
        raw = settings.auto_voiceover_statuses.strip()
        if not raw or raw.lower() in {"all", "*"}:
            return [None]
        statuses: list[str | None] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            resolved = NotionClient.normalize_idea_status(part)
            statuses.append(resolved or part)
        return statuses or [None]

    def run_for_idea(self, idea: dict, *, source: str = "Discord-voiceover") -> str:
        page_id = idea["id"]
        title = self._notion.extract_title(idea)

        if self._notion.idea_has_voiceover(page_id):
            logger.info("idea_voiceover_skip_existing", title=title, page_id=page_id)
            return ""

        notes = self._notion.extract_text_property(idea, "Notes")
        try:
            page_body = self._notion.get_page_blocks_text(page_id)
        except Exception as e:
            logger.warning("idea_voiceover_blocks_failed", error=str(e), page_id=page_id)
            page_body = ""

        background = "\n\n".join(
            part for part in (notes, page_body) if part and part.strip()
        )

        output = run_crew(
            query=title,
            mode="voiceover",
            extra_context=background,
        )
        self._notion.append_voiceover_to_idea(page_id, output, source=source)
        logger.info("idea_voiceover_generated", title=title, page_id=page_id)
        return output

    def run(self, idea_query: str, status: str | None = None) -> str:
        if not idea_query.strip():
            return (
                "Spune-mi ce idee din Notion vrei, de ex.:\n"
                "`voiceover: platon timp` sau `generează voice-over pe ideea despre fluturi`"
            )

        try:
            matches = self.find_ideas(idea_query, status=status)
        except Exception as e:
            logger.error("idea_voiceover_find_failed", error=str(e), query=idea_query)
            return f"Eroare la citirea ideilor din Notion: {e}"

        if not matches:
            scope = f" (status {status})" if status else ""
            return (
                f"Nu am găsit nicio idee{scope} care să conțină **{idea_query}**.\n"
                "Încearcă `ce idei am in draft` pentru listă, apoi `voiceover: titlul`."
            )

        if len(matches) > 1:
            lines = [
                f"Am găsit **{len(matches)}** idei — fii mai specific în titlu:",
                "",
            ]
            for idx, idea in enumerate(matches[:10], start=1):
                title = self._notion.extract_title(idea)
                idea_status = self._notion.extract_text_property(idea, "status") or "—"
                lines.append(f"{idx}. **{title}** (status: {idea_status})")
            if len(matches) > 10:
                lines.append(f"_...și încă {len(matches) - 10}._")
            lines.append("")
            lines.append("Exemplu: `voiceover: cat de repede trece viata platon`")
            return "\n".join(lines)

        idea = matches[0]
        title = self._notion.extract_title(idea)
        try:
            output = self.run_for_idea(idea)
        except Exception as e:
            logger.error("idea_voiceover_crew_failed", error=str(e), title=title)
            return f"Eroare la generarea voice-over: {e}"

        if not output:
            return f"Ideea **{title}** are deja voice-over în Notion."

        return (
            f"**Voice-over pentru:** {title}\n\n{output}\n\n"
            f"✅ **Adăugat în Notion** — deschide pagina ideii pentru variantele A și B."
        )

    def run_auto_batch(self, max_count: int | None = None) -> dict:
        """Process ideas without voice-over, up to max_count per run."""
        limit = max_count if max_count is not None else settings.auto_voiceover_max_per_run
        pending = self.ideas_missing_voiceover()
        processed: list[str] = []
        errors: list[tuple[str, str]] = []

        for idea in pending:
            if len(processed) >= limit:
                break
            title = self._notion.extract_title(idea)
            try:
                output = self.run_for_idea(idea, source="Auto-voiceover")
                if output:
                    processed.append(title)
            except Exception as e:
                logger.error("auto_voiceover_failed", title=title, error=str(e))
                errors.append((title, str(e)))

        return {
            "processed": processed,
            "errors": errors,
            "pending_remaining": max(0, len(pending) - len(processed)),
        }