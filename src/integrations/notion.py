"""Notion API integration for tasks, ideas, posting plan, journal."""

from datetime import datetime
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class NotionClient:
    def __init__(self) -> None:
        settings.validate_required("notion_api_key")
        self.client = Client(auth=settings.notion_api_key)

    def query_database(
        self,
        database_id: str,
        filter_obj: dict | None = None,
        sorts: list | None = None,
    ) -> list[dict]:
        try:
            kwargs: dict[str, Any] = {"database_id": database_id}
            if filter_obj:
                kwargs["filter"] = filter_obj
            if sorts:
                kwargs["sorts"] = sorts
            response = self.client.databases.query(**kwargs)
            return response.get("results", [])
        except APIResponseError as e:
            logger.error("notion_query_failed", database_id=database_id, error=str(e))
            raise

    def create_page(self, database_id: str, properties: dict, children: list | None = None) -> dict:
        try:
            payload: dict[str, Any] = {
                "parent": {"database_id": database_id},
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

    def get_ideas(self, limit: int = 20) -> list[dict]:
        if not settings.notion_ideas_db_id:
            return []
        return self.query_database(settings.notion_ideas_db_id)[:limit]

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

    def create_idea(self, title: str, category: str = "General", notes: str = "") -> dict:
        props: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Category": {"select": {"name": category}},
        }
        if notes:
            props["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
        return self.create_page(settings.notion_ideas_db_id, props)

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
        if prop_name not in props:
            return ""
        prop = props[prop_name]
        if prop.get("rich_text"):
            return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else ""
        if prop.get("select"):
            return prop["select"]["name"] if prop["select"] else ""
        if prop.get("date") and prop["date"]:
            return prop["date"].get("start", "")
        return ""