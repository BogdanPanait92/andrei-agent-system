"""Periodic reminder to review open Notion tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from src.integrations.discord import DISCORD_MAX_LEN
from src.integrations.notion import NotionClient
from src.integrations.notifier import get_notifier
from src.integrations.notifier_base import NotifierMixin
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

_FAMILY_OPEN_STATUSES = ("To Do", "In progress")
_IDEA_OPEN_STATUSES = ("In evaluare", "Draft")
_MAX_ITEMS_PER_GROUP = 12
_WEEKDAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "luni": 0,
    "tue": 1,
    "tuesday": 1,
    "marti": 1,
    "marți": 1,
    "wed": 2,
    "wednesday": 2,
    "miercuri": 2,
    "thu": 3,
    "thursday": 3,
    "joi": 3,
    "fri": 4,
    "friday": 4,
    "vineri": 4,
    "sat": 5,
    "saturday": 5,
    "sambata": 5,
    "sâmbătă": 5,
    "sun": 6,
    "sunday": 6,
    "duminica": 6,
    "duminică": 6,
}


def _task_reminder_weekdays() -> frozenset[int]:
    raw = settings.task_reminder_days.strip().lower()
    if not raw:
        return frozenset(range(6))
    days: set[int] = set()
    for token in raw.replace(";", ",").split(","):
        key = token.strip()
        if not key:
            continue
        if key in _WEEKDAY_ALIASES:
            days.add(_WEEKDAY_ALIASES[key])
    return frozenset(days or range(6))


def is_task_reminder_window(now: datetime | None = None) -> bool:
    """True between configured hours on configured weekdays (timezone-aware)."""
    tz = ZoneInfo(settings.timezone)
    current = now.astimezone(tz) if now else datetime.now(tz)
    if current.weekday() not in _task_reminder_weekdays():
        return False
    start_hour = settings.task_reminder_start_hour
    end_hour = settings.task_reminder_end_hour
    return start_hour <= current.hour <= end_hour


@dataclass(frozen=True)
class TaskGroup:
    label: str
    items: list[str]


def _safe_query(callable_obj, *, label: str, **kwargs) -> list[dict]:
    try:
        return callable_obj(**kwargs)
    except Exception as e:
        logger.warning("task_reminder_query_failed", label=label, error=str(e))
        return []


def collect_open_tasks(notion: NotionClient | None = None) -> list[TaskGroup]:
    """Gather open items from Family, Posting Plan, and active Ideas."""
    client = notion or NotionClient()
    groups: list[TaskGroup] = []

    family_seen: set[str] = set()
    family_lines: list[str] = []
    for status in _FAMILY_OPEN_STATUSES:
        for item in _safe_query(
            client.get_family_items, label=f"family:{status}", status=status
        ):
            page_id = item.get("id")
            if not page_id or page_id in family_seen:
                continue
            family_seen.add(page_id)

            title = NotionClient.extract_title(item)
            item_status = NotionClient.extract_text_property(item, "Status") or status
            due = NotionClient.extract_text_property(item, "Due Date")
            line = f"• {title}"
            if due:
                line += f" (deadline: {due[:10]})"
            line += f" [{item_status}]"
            family_lines.append(line)
    if family_lines:
        groups.append(TaskGroup("Family & Administrative", family_lines))

    posting_lines: list[str] = []
    for item in _safe_query(client.get_posting_plan, label="posting_plan"):
        record = NotionClient.posting_plan_record(item)
        if NotionClient.is_posting_done(record["Status"]):
            continue
        line = f"• {record['Titlu']}"
        if record["Prioritate"]:
            line += f" ({record['Prioritate']})"
        if record["Status"]:
            line += f" [{record['Status']}]"
        posting_lines.append(line)
    if posting_lines:
        groups.append(TaskGroup("Posting Plan", posting_lines))

    idea_lines: list[str] = []
    for status in _IDEA_OPEN_STATUSES:
        for idea in _safe_query(client.get_ideas, label=f"ideas:{status}", status=status):
            title = NotionClient.extract_title(idea)
            idea_lines.append(f"• {title} [{status}]")
    if idea_lines:
        groups.append(TaskGroup("Idei", idea_lines))

    return groups


def format_task_reminder_message(groups: list[TaskGroup]) -> str:
    total = sum(len(group.items) for group in groups)
    lines = ["⏰ **Reminder taskuri** — verifică ce mai ai de făcut în Notion"]

    if not groups:
        lines.append(
            "\nNu am găsit taskuri deschise în Family, Posting Plan sau Idei. Ești la zi! ✅"
        )
        return "\n".join(lines)

    for group in groups:
        lines.append(f"\n**{group.label}** ({len(group.items)}):")
        visible = group.items[:_MAX_ITEMS_PER_GROUP]
        lines.extend(visible)
        remaining = len(group.items) - len(visible)
        if remaining > 0:
            lines.append(f"_...și încă {remaining}_")

    lines.append(f"\n**Total: {total} taskuri deschise**")
    return "\n".join(lines)


def _parse_discord_ids(raw: str) -> list[str]:
    ids: list[str] = []
    for token in raw.replace(";", ",").split(","):
        value = token.strip()
        if value:
            ids.append(value)
    return ids


def _first_discord_channel_id() -> str | None:
    ids = _parse_discord_ids(settings.discord_allowed_channel_ids)
    return ids[0] if ids else None


def task_reminder_dm_user_ids() -> list[str]:
    """Discord user IDs that receive task reminders in DM."""
    configured = _parse_discord_ids(settings.task_reminder_discord_dm_user_ids)
    if configured:
        return configured
    if settings.task_reminder_discord_dm:
        return _parse_discord_ids(settings.discord_allowed_user_ids)
    return []


def _post_discord_chunks(
    client: httpx.Client,
    *,
    headers: dict[str, str],
    channel_id: str,
    text: str,
) -> bool:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    for chunk in NotifierMixin.split_message(text, max_len=DISCORD_MAX_LEN):
        response = client.post(url, headers=headers, json={"content": chunk})
        response.raise_for_status()
    return True


def send_discord_bot_dm_message(text: str, user_ids: list[str] | None = None) -> bool:
    """Open a DM with each user and send the reminder privately."""
    token = settings.discord_bot_token.strip()
    recipients = user_ids if user_ids is not None else task_reminder_dm_user_ids()
    if not token or not recipients:
        return False

    headers = {"Authorization": f"Bot {token}"}
    sent_any = False

    with httpx.Client(timeout=30.0) as client:
        for user_id in recipients:
            try:
                dm_response = client.post(
                    "https://discord.com/api/v10/users/@me/channels",
                    headers=headers,
                    json={"recipient_id": user_id},
                )
                dm_response.raise_for_status()
                channel_id = dm_response.json()["id"]
                _post_discord_chunks(
                    client,
                    headers=headers,
                    channel_id=channel_id,
                    text=text,
                )
                sent_any = True
            except httpx.HTTPError as e:
                logger.error(
                    "task_reminder_discord_dm_failed",
                    user_id=user_id,
                    error=str(e),
                )
    return sent_any


def send_discord_bot_channel_message(text: str) -> bool:
    """Post a message in the configured Discord bot channel via REST API."""
    token = settings.discord_bot_token.strip()
    channel_id = _first_discord_channel_id()
    if not token or not channel_id:
        return False

    headers = {"Authorization": f"Bot {token}"}

    with httpx.Client(timeout=30.0) as client:
        try:
            return _post_discord_chunks(
                client,
                headers=headers,
                channel_id=channel_id,
                text=text,
            )
        except httpx.HTTPError as e:
            logger.error("task_reminder_discord_send_failed", error=str(e))
            return False


def _deliver_task_reminder(message: str) -> bool:
    if settings.task_reminder_discord and settings.enable_discord_bot:
        dm_ids = task_reminder_dm_user_ids()
        if settings.task_reminder_discord_dm and dm_ids:
            if send_discord_bot_dm_message(message, dm_ids):
                return True
        elif send_discord_bot_channel_message(message):
            return True

    notifier = get_notifier()
    if notifier.enabled:
        return notifier.send_message(message)

    logger.warning("task_reminder_delivery_unavailable")
    return False


def run_task_reminder(*, send: bool = True, force: bool = False) -> dict:
    """Build and optionally deliver the task-check reminder."""
    if not settings.enable_task_reminder and not force:
        logger.info("task_reminder_disabled")
        return {"sent": False, "status": "disabled", "total": 0}

    if not force and not is_task_reminder_window():
        logger.info("task_reminder_outside_window")
        return {"sent": False, "status": "outside_window", "total": 0}

    logger.info("task_reminder_started", force=force)
    groups = collect_open_tasks()
    message = format_task_reminder_message(groups)
    if force:
        message = f"🧪 **Test reminder taskuri**\n\n{message}"
    total = sum(len(group.items) for group in groups)

    sent = False
    if send:
        sent = _deliver_task_reminder(message)

    logger.info("task_reminder_completed", total=total, sent=sent, force=force)
    return {
        "sent": sent,
        "status": "ok",
        "total": total,
        "message": message,
        "groups": {group.label: len(group.items) for group in groups},
    }


def run_task_reminder_test() -> dict:
    """Send a one-off test reminder, ignoring schedule window."""
    return run_task_reminder(send=True, force=True)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        result = run_task_reminder_test()
        print(result["message"])
        print(f"sent={result['sent']} total={result['total']}")
    else:
        print(run_task_reminder(send=False)["message"])