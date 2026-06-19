"""Web search via DuckDuckGo — used only when the user explicitly requests it."""

from __future__ import annotations

from src.integrations.web_page_reader import fetch_page_text
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class WebSearchService:
    def search(self, query: str, max_results: int | None = None) -> list[dict[str, str]]:
        if not query.strip():
            return []

        limit = max_results or settings.web_search_max_results
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore[no-redef]

            with DDGS() as ddgs:
                raw = list(ddgs.text(query.strip(), max_results=limit))
        except ImportError as e:
            raise RuntimeError(
                "Pachetul ddgs nu e instalat. Rulează: pip install ddgs"
            ) from e
        except Exception as e:
            logger.error("web_search_failed", query=query[:80], error=str(e))
            raise

        results: list[dict[str, str]] = []
        for item in raw:
            results.append(
                {
                    "title": str(item.get("title", "")).strip(),
                    "snippet": str(item.get("body", "")).strip(),
                    "url": str(item.get("href", "")).strip(),
                }
            )
        logger.info("web_search_completed", query=query[:80], results=len(results))
        return results

    def enrich_with_page_content(
        self, results: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        if not settings.web_search_fetch_pages:
            return [dict(item) for item in results]

        enriched: list[dict[str, str]] = []
        pages_read = 0
        max_pages = settings.web_search_max_pages_to_read

        for item in results:
            row = dict(item)
            url = row.get("url", "")
            if pages_read < max_pages and url:
                try:
                    row["page_content"] = fetch_page_text(url)
                    row["page_read"] = "ok"
                    pages_read += 1
                    logger.info("web_page_fetched", url=url[:120])
                except Exception as e:
                    row["page_content"] = ""
                    row["page_read"] = f"error: {str(e)[:120]}"
                    logger.warning("web_page_fetch_failed", url=url[:120], error=str(e))
            else:
                row["page_content"] = ""
                row["page_read"] = "skipped" if pages_read >= max_pages else "no_url"
            enriched.append(row)

        return enriched

    @staticmethod
    def format_links_message(results: list[dict[str, str]], query: str) -> str:
        if not results:
            return f"🔍 **Căutare web:** {query}\n\nNiciun rezultat găsit."

        lines = [f"🔍 **Căutare web:** {query}", "", "**Linkuri găsite:**", ""]
        for idx, item in enumerate(results, start=1):
            title = item.get("title") or "Fără titlu"
            url = item.get("url") or ""
            snippet = item.get("snippet", "")
            lines.append(f"{idx}. **{title}**")
            if url:
                lines.append(f"   {url}")
            if snippet:
                lines.append(f"   _{snippet[:200]}_")
            lines.append("")

        if settings.web_search_fetch_pages:
            lines.append("_Citesc paginile și revin cu sugestii..._")
        return "\n".join(lines).strip()

    @staticmethod
    def format_for_prompt(results: list[dict[str, str]]) -> str:
        if not results:
            return (
                "--- Rezultate căutare web ---\n"
                "Niciun rezultat găsit. Spune utilizatorului căutarea nu a returnat date."
            )

        lines = [f"--- Rezultate căutare web ({len(results)}) ---"]
        for idx, item in enumerate(results, start=1):
            lines.append(f"{idx}. {item.get('title') or 'Fără titlu'}")
            if item.get("snippet"):
                lines.append(f"   Snippet: {item['snippet'][:500]}")
            if item.get("url"):
                lines.append(f"   URL: {item['url']}")
            page_content = item.get("page_content", "")
            page_read = item.get("page_read", "")
            if page_content:
                lines.append(f"   Conținut citit din pagină ({len(page_content)} chars):")
                lines.append(f"   {page_content}")
            elif page_read and page_read != "skipped":
                lines.append(f"   Conținut pagină: indisponibil ({page_read})")
            lines.append("")

        lines.append(
            "Instrucțiune: Utilizatorul a primit deja lista de linkuri. "
            "Oferă acum DOAR sugestii concrete și acționabile bazate pe snippet-uri "
            "și pe conținutul citit din pagini. Citează sursele (titlu/URL). "
            "Nu repeta lista de linkuri — doar analiză și recomandări pentru Andrei."
        )
        return "\n".join(lines).strip()

    @staticmethod
    def format_for_research_prompt(results: list[dict[str, str]]) -> str:
        if not results:
            return (
                "--- Research web ---\n"
                "Căutarea nu a returnat rezultate. Răspunde din cunoștințele tale generale "
                "și menționează că nu ai găsit surse web relevante pentru întrebare."
            )

        lines = [f"--- Research web ({len(results)} surse) ---"]
        for idx, item in enumerate(results, start=1):
            lines.append(f"{idx}. {item.get('title') or 'Fără titlu'}")
            if item.get("snippet"):
                lines.append(f"   Snippet: {item['snippet'][:500]}")
            if item.get("url"):
                lines.append(f"   URL: {item['url']}")
            page_content = item.get("page_content", "")
            page_read = item.get("page_read", "")
            if page_content:
                lines.append(f"   Conținut citit ({len(page_content)} chars):")
                lines.append(f"   {page_content}")
            elif page_read and page_read != "skipped":
                lines.append(f"   Conținut pagină: indisponibil ({page_read})")
            lines.append("")

        lines.append(
            "Instrucțiune: Combină aceste surse cu cunoștințele tale într-un răspuns "
            "conversațional ca Grok/ChatGPT — organizat natural pe subiect, NU ca plan "
            "de content (fără Rezumat/De ce merită/Pași de implementare). Integrează "
            "informația în text. La final: „Surse” cu 2-5 linkuri. Dacă web contrazice "
            "cunoștințele tale, prioritizează sursele recente."
        )
        return "\n".join(lines).strip()