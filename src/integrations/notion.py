"""Notion API integration for tasks, ideas, posting plan, journal."""

import re
from datetime import datetime
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

NOTION_RICH_TEXT_LIMIT = 2000
IDEA_CATEGORIES = (
    "General",
    "Video",
    "LinkedIn",
    "ACP",
    "content creation",
    "Creativ",
    "Test",
)
IDEA_STATUSES = ("Draft", "In evaluare", "In lucru", "Arhivat")
IDEA_DEFAULT_STATUS = "Draft"
IDEA_STATUS_PROPERTY = "status"


class NotionClient:
    def __init__(self) -> None:
        settings.validate_required("notion_api_key")
        self.client = Client(auth=settings.notion_api_key)
        self._data_source_cache: dict[str, str] = {}

    def _resolve_data_source_id(self, database_id: str) -> str:
        """Resolve database ID to data_source_id (Notion API 2025-09-03)."""
        if database_id in self._data_source_cache:
            return self._data_source_cache[database_id]

        db = self.client.databases.retrieve(database_id=database_id)
        sources = db.get("data_sources", [])
        if not sources:
            raise ValueError(f"No data sources found for database {database_id}")
        data_source_id = sources[0]["id"]
        self._data_source_cache[database_id] = data_source_id
        return data_source_id

    def query_database(
        self,
        database_id: str,
        filter_obj: dict | None = None,
        sorts: list | None = None,
    ) -> list[dict]:
        try:
            data_source_id = self._resolve_data_source_id(database_id)
            kwargs: dict[str, Any] = {}
            if filter_obj:
                kwargs["filter"] = filter_obj
            if sorts:
                kwargs["sorts"] = sorts
            response = self.client.data_sources.query(data_source_id, **kwargs)
            return response.get("results", [])
        except APIResponseError as e:
            logger.error("notion_query_failed", database_id=database_id, error=str(e))
            raise

    def create_page(self, database_id: str, properties: dict, children: list | None = None) -> dict:
        try:
            data_source_id = self._resolve_data_source_id(database_id)
            payload: dict[str, Any] = {
                "parent": {"type": "data_source_id", "data_source_id": data_source_id},
                "properties": properties,
            }
            if children:
                payload["children"] = children
            return self.client.pages.create(**payload)
        except APIResponseError as e:
            logger.error("notion_create_failed", database_id=database_id, error=str(e))
            raise

    def update_page(self, page_id: str, properties: dict) -> dict:
        try:
            return self.client.pages.update(page_id=page_id, properties=properties)
        except APIResponseError as e:
            logger.error("notion_update_failed", page_id=page_id, error=str(e))
            raise

    def append_to_page(self, page_id: str, children: list) -> dict:
        try:
            return self.client.blocks.children.append(block_id=page_id, children=children)
        except APIResponseError as e:
            logger.error("notion_append_failed", page_id=page_id, error=str(e))
            raise

    def get_tasks(self, status: str | None = None, limit: int = 50) -> list[dict]:
        if not settings.notion_tasks_db_id:
            return []
        filter_obj = None
        if status:
            filter_obj = {
                "property": "Status",
                "select": {"equals": status},
            }
        return self.query_database(settings.notion_tasks_db_id, filter_obj)[:limit]

    @staticmethod
    def normalize_idea_status(status: str) -> str | None:
        if not status.strip():
            return None
        normalized = {
            "draft": "Draft",
            "in evaluare": "In evaluare",
            "in lucru": "In lucru",
            "arhivat": "Arhivat",
        }
        key = status.strip().lower()
        if key in normalized:
            return normalized[key]
        return status if status in IDEA_STATUSES else None

    def get_ideas(self, status: str | None = None, limit: int = 20) -> list[dict]:
        if not settings.notion_ideas_db_id:
            return []
        filter_obj = None
        resolved = self.normalize_idea_status(status) if status else None
        if resolved:
            filter_obj = {
                "property": IDEA_STATUS_PROPERTY,
                "status": {"equals": resolved},
            }
        return self.query_database(settings.notion_ideas_db_id, filter_obj)[:limit]

    def get_posting_plan(self, limit: int = 30) -> list[dict]:
        if not settings.notion_posting_plan_db_id:
            return []
        return self.query_database(
            settings.notion_posting_plan_db_id,
            sorts=[{"property": "Date", "direction": "ascending"}],
        )[:limit]

    def get_ajut_cum_pot_items(self, limit: int = 20) -> list[dict]:
        if not settings.notion_ajut_cum_pot_db_id:
            return []
        return self.query_database(settings.notion_ajut_cum_pot_db_id)[:limit]

    def find_task_by_title(self, title: str) -> dict | None:
        title_lower = title.strip().lower()
        for task in self.get_tasks():
            if self.extract_title(task).strip().lower() == title_lower:
                return task
        return None

    def update_task(
        self,
        page_id: str,
        status: str | None = None,
        priority: str | None = None,
        due_date: str | None = None,
        client: str | None = None,
    ) -> dict:
        props: dict[str, Any] = {}
        if status:
            props["Status"] = {"select": {"name": status}}
        if priority:
            props["Priority"] = {"select": {"name": priority}}
        if due_date:
            props["Due Date"] = {"date": {"start": due_date}}
        if client:
            props["Client"] = {"rich_text": [{"text": {"content": client}}]}
        if not props:
            raise ValueError("No task fields provided to update")
        return self.update_page(page_id, props)

    def create_task(
        self,
        title: str,
        status: str = "To Do",
        priority: str = "Medium",
        due_date: str | None = None,
        client: str | None = None,
    ) -> dict:
        props: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"select": {"name": status}},
            "Priority": {"select": {"name": priority}},
        }
        if due_date:
            props["Due Date"] = {"date": {"start": due_date}}
        if client:
            props["Client"] = {"rich_text": [{"text": {"content": client}}]}
        return self.create_page(settings.notion_tasks_db_id, props)

    def create_idea(
        self,
        title: str,
        category: str = "General",
        notes: str = "",
        status: str = IDEA_DEFAULT_STATUS,
        children: list | None = None,
    ) -> dict:
        if category not in IDEA_CATEGORIES:
            category = "General"
        resolved_status = self.normalize_idea_status(status) or IDEA_DEFAULT_STATUS
        props: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": self._truncate_rich_text(title)}}]},
            "Category": {"select": {"name": category}},
            IDEA_STATUS_PROPERTY: {"status": {"name": resolved_status}},
        }
        if notes:
            props["Notes"] = {
                "rich_text": [{"text": {"content": self._truncate_rich_text(notes)}}]
            }
        return self.create_page(settings.notion_ideas_db_id, props, children=children)

    @staticmethod
    def _truncate_rich_text(text: str, limit: int = NOTION_RICH_TEXT_LIMIT) -> str:
        return text[:limit] if text else ""

    @classmethod
    def _paragraph_blocks(cls, text: str) -> list[dict]:
        if not text.strip():
            return []
        blocks: list[dict] = []
        chunk = text.strip()
        while chunk:
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": cls._truncate_rich_text(chunk)}}
                        ]
                    },
                }
            )
            chunk = chunk[NOTION_RICH_TEXT_LIMIT:]
        return blocks

    @classmethod
    def _heading_block(cls, text: str, level: int = 2) -> dict:
        key = f"heading_{level}"
        return {
            "object": "block",
            "type": key,
            key: {
                "rich_text": [{"type": "text", "text": {"content": cls._truncate_rich_text(text)}}]
            },
        }

    _SECTION_RE = re.compile(
        r"^\s*(?:\d+[\.\)]\s*)?(?:\*\*)?([^*\n]+?)(?:\*\*)?\s*(?:—|-|:)\s*",
        re.MULTILINE,
    )

    @classmethod
    def _plan_to_blocks(cls, plan_text: str) -> list[dict]:
        """Split structured agent output into Notion headings + paragraphs."""
        if not plan_text.strip():
            return []

        lines = plan_text.strip().splitlines()
        blocks: list[dict] = []
        section_title: str | None = None
        section_lines: list[str] = []

        def flush_section() -> None:
            nonlocal section_title, section_lines
            if section_title:
                blocks.append(cls._heading_block(section_title, level=3))
            body = "\n".join(section_lines).strip()
            blocks.extend(cls._paragraph_blocks(body))
            section_title = None
            section_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if section_lines:
                    section_lines.append("")
                continue

            match = cls._SECTION_RE.match(stripped)
            is_numbered_section = bool(re.match(r"^\d+[\.\)]", stripped))
            if match and is_numbered_section:
                flush_section()
                section_title = match.group(1).strip()
                remainder = stripped[match.end() :].strip()
                if remainder:
                    section_lines.append(remainder)
                continue

            section_lines.append(stripped)

        flush_section()
        return blocks if blocks else cls._paragraph_blocks(plan_text)

    @staticmethod
    def infer_idea_category(idea_text: str, plan_text: str = "") -> str:
        combined = f"{idea_text} {plan_text}".lower()
        if any(k in combined for k in ("ajut cum pot", "acp", "voluntar", "partener ong", "fundație")):
            return "ACP"
        if "linkedin" in combined:
            return "LinkedIn"
        if any(k in combined for k in ("video", "youtube", "vlog", "podcast", "reel", "tiktok")):
            return "Video"
        if any(
            k in combined
            for k in ("content creation", "postare", "material", "editor", "blog", "newsletter")
        ):
            return "content creation"
        return "General"

    @staticmethod
    def extract_idea_title(idea_text: str, max_len: int = 80) -> str:
        text = " ".join(idea_text.strip().split())
        if not text:
            return "Idee nouă"
        if len(text) <= max_len:
            return text
        cut = text[:max_len].rsplit(" ", 1)[0]
        return cut or text[:max_len]

    @staticmethod
    def extract_plan_summary(plan_text: str, max_len: int = 500) -> str:
        if not plan_text.strip():
            return ""
        for line in plan_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if "rezumat" in stripped.lower():
                continue
            if stripped.startswith(("**", "#", "1.", "1)")):
                cleaned = stripped.lstrip("0123456789.)#* ").strip()
                if cleaned:
                    return cleaned[:max_len]
            return stripped[:max_len]
        return plan_text.strip()[:max_len]

    def save_idea_suggestion(self, idea_text: str, plan_text: str, source: str = "Discord") -> dict | None:
        if not settings.notion_ideas_db_id:
            logger.warning("notion_ideas_db_not_configured")
            return None

        title = self.extract_idea_title(idea_text)
        category = self.infer_idea_category(idea_text, plan_text)
        summary = self.extract_plan_summary(plan_text) or self._truncate_rich_text(idea_text, 500)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        children: list[dict] = [
            self._heading_block(f"Plan de implementare ({source}, {now})"),
            *self._plan_to_blocks(plan_text),
            self._heading_block("Ideea originală", level=3),
            *self._paragraph_blocks(idea_text),
        ]

        page = self.create_idea(title=title, category=category, notes=summary, children=children)
        logger.info(
            "idea_suggestion_saved",
            title=title,
            page_id=page.get("id"),
            plan_chars=len(plan_text),
            blocks=len(children),
        )
        return page

    def save_briefing(self, title: str, content: str, briefing_type: str = "daily") -> dict | None:
        if not settings.notion_briefings_page_id:
            logger.warning("notion_briefings_page_not_configured")
            return None
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        children = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"{title} - {now}"}}]
                },
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                },
            },
        ]
        return self.append_to_page(settings.notion_briefings_page_id, children)

    def save_journal_entry(self, title: str, content: str, mood: str = "Reflectiv") -> dict:
        props: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Mood": {"select": {"name": mood}},
            "Content": {"rich_text": [{"text": {"content": content[:2000]}}]},
            "Date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        }
        return self.create_page(settings.notion_journal_db_id, props)

    @staticmethod
    def extract_title(page: dict) -> str:
        props = page.get("properties", {})
        for key in ("Name", "Title", "Task"):
            if key in props and props[key].get("title"):
                return props[key]["title"][0]["plain_text"]
        return "Untitled"

    @staticmethod
    def extract_text_property(page: dict, prop_name: str) -> str:
        props = page.get("properties", {})
        prop = props.get(prop_name)
        if prop is None:
            for key, value in props.items():
                if key.lower() == prop_name.lower():
                    prop = value
                    break
        if not prop:
            return ""
        if prop.get("rich_text"):
            return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else ""
        if prop.get("select"):
            return prop["select"]["name"] if prop["select"] else ""
        if prop.get("status"):
            return prop["status"]["name"] if prop["status"] else ""
        if prop.get("date") and prop["date"]:
            return prop["date"].get("start", "")
        return ""