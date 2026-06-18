"""Direct Notion Ideas listing — bypasses LLM to avoid hallucinated idea lists."""

from __future__ import annotations

from src.integrations.notion import IDEA_STATUSES, NotionClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IdeasListService:
    def __init__(self) -> None:
        self._notion = NotionClient()

    @staticmethod
    def parse_status_from_query(query: str) -> str | None:
        """
        Return status filter (or '' for all ideas).
        Return None if the query is not a list-ideas request.
        """
        lowered = query.strip().lower()
        if not lowered:
            return None

        blocked = (
            "idee:",
            "idea:",
            "am o idee:",
            "cum as implementa",
            "cum aș implementa",
            "plan de implementare",
            "sugestii de implementare",
            "sugestii implementare",
        )
        if any(lowered.startswith(p) for p in blocked):
            return None

        if "idei" not in lowered and "ideile" not in lowered:
            return None

        list_signals = (
            "care sunt",
            "ce idei",
            "lista",
            "listă",
            "toate",
            "din notion",
            "in draft",
            "în draft",
            "in evaluare",
            "în evaluare",
            "in lucru",
            "în lucru",
            "arhivat",
            "draft",
            "status",
        )
        if not any(signal in lowered for signal in list_signals):
            return None

        if any(w in lowered for w in ("draft", "ciorna", "ciornă")):
            return "Draft"
        if "evaluare" in lowered:
            return "In evaluare"
        if "lucru" in lowered:
            return "In lucru"
        if "arhivat" in lowered:
            return "Arhivat"
        return ""

    def run(self, status: str = "") -> str:
        resolved = NotionClient.normalize_idea_status(status) if status else None
        if status and not resolved:
            allowed = ", ".join(IDEA_STATUSES)
            return f"Status invalid: `{status}`. Valori acceptate: {allowed}."

        try:
            ideas = self._notion.get_ideas(status=status or None, limit=50)
        except Exception as e:
            logger.error("ideas_list_failed", error=str(e), status=status)
            return f"Eroare la citirea ideilor din Notion: {e}"

        if not ideas:
            if resolved:
                return f"Nu ai idei cu status **{resolved}** în Notion Ideas."
            return "Nu există idei în baza Notion Ideas."

        if resolved:
            header = f"**Idei Notion — status {resolved}** ({len(ideas)}):"
        else:
            header = f"**Toate ideile din Notion Ideas** ({len(ideas)}):"

        lines = [header, ""]
        for idx, idea in enumerate(ideas, start=1):
            title = NotionClient.extract_title(idea)
            idea_status = NotionClient.extract_text_property(idea, "status") or "—"
            category = NotionClient.extract_text_property(idea, "Category") or "—"
            notes = NotionClient.extract_text_property(idea, "Notes") or "—"
            lines.append(f"{idx}. **{title}**")
            lines.append(f"   - Status: {idea_status}")
            lines.append(f"   - Categorie: {category}")
            if notes != "—":
                lines.append(f"   - Notes: {notes}")
            lines.append("")

        lines.append("_Sursă: Notion Ideas (citire directă, fără generare AI)._")
        return "\n".join(lines).strip()