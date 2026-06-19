"""Tests for periodic task-check reminders."""

from unittest.mock import MagicMock

from datetime import datetime
from zoneinfo import ZoneInfo

from src.jobs.task_reminder import (
    collect_open_tasks,
    format_task_reminder_message,
    is_task_reminder_window,
    run_task_reminder,
    run_task_reminder_test,
    task_reminder_dm_user_ids,
)


def _family_page(title: str, status: str, due: str = "") -> dict:
    props = {
        "Name": {"title": [{"plain_text": title}]},
        "Status": {"select": {"name": status}},
    }
    if due:
        props["Due Date"] = {"date": {"start": due}}
    return {"id": f"family-{title}", "properties": props}


def _posting_page(title: str, status: str, priority: str = "p2") -> dict:
    return {
        "id": f"posting-{title}",
        "properties": {
            "Name": {"title": [{"plain_text": title}]},
            "Status": {"select": {"name": status}},
            "Prioritate": {"select": {"name": priority}},
            "Oras": {"rich_text": [{"plain_text": "București"}]},
        },
    }


def _idea_page(title: str, status: str) -> dict:
    return {
        "id": f"idea-{title}",
        "properties": {
            "Name": {"title": [{"plain_text": title}]},
            "Status": {"select": {"name": status}},
        },
    }


def test_collect_open_tasks_groups_items() -> None:
    notion = MagicMock()
    notion.get_family_items.side_effect = lambda status=None, limit=50: {
        "To Do": [_family_page("Ziua Georgianei", "To Do", "2026-06-25")],
        "In Progress": [_family_page("Dosar indemnizații", "In Progress")],
    }.get(status or "", [])
    notion.get_posting_plan.return_value = [
        _posting_page("Clip parenting", "Planned"),
        _posting_page("Clip vechi", "Posted"),
    ]
    notion.get_ideas.side_effect = lambda status=None, limit=20: {
        "Draft": [_idea_page("Podcast ACP", "Draft")],
        "In evaluare": [],
    }.get(status or "", [])

    groups = collect_open_tasks(notion)
    labels = [group.label for group in groups]
    assert "Family & Administrative" in labels
    assert "Posting Plan" in labels
    assert "Idei" in labels
    assert sum(len(group.items) for group in groups) == 4


def test_format_task_reminder_message_lists_totals() -> None:
    from src.jobs.task_reminder import TaskGroup

    message = format_task_reminder_message(
        [TaskGroup("Family & Administrative", ["• Task 1 [To Do]"])]
    )
    assert "Reminder taskuri" in message
    assert "Family & Administrative" in message
    assert "Total: 1 taskuri deschise" in message


def test_format_task_reminder_message_empty() -> None:
    message = format_task_reminder_message([])
    assert "Ești la zi" in message


def test_task_reminder_window_weekday_hours(monkeypatch) -> None:
    monkeypatch.setattr("src.jobs.task_reminder.settings.timezone", "Europe/Bucharest")
    monkeypatch.setattr("src.jobs.task_reminder.settings.task_reminder_start_hour", 8)
    monkeypatch.setattr("src.jobs.task_reminder.settings.task_reminder_end_hour", 18)
    monkeypatch.setattr(
        "src.jobs.task_reminder.settings.task_reminder_days",
        "mon,tue,wed,thu,fri,sat",
    )
    tz = ZoneInfo("Europe/Bucharest")
    assert is_task_reminder_window(datetime(2026, 6, 19, 10, 0, tzinfo=tz))
    assert not is_task_reminder_window(datetime(2026, 6, 19, 7, 30, tzinfo=tz))
    assert not is_task_reminder_window(datetime(2026, 6, 19, 19, 0, tzinfo=tz))
    assert not is_task_reminder_window(datetime(2026, 6, 21, 10, 0, tzinfo=tz))


def test_run_task_reminder_skips_outside_window(monkeypatch) -> None:
    monkeypatch.setattr("src.jobs.task_reminder.settings.enable_task_reminder", True)
    monkeypatch.setattr("src.jobs.task_reminder.is_task_reminder_window", lambda now=None: False)

    result = run_task_reminder(send=False)
    assert result["status"] == "outside_window"
    assert result["sent"] is False


def test_task_reminder_dm_user_ids_prefers_explicit_config(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.jobs.task_reminder.settings.task_reminder_discord_dm_user_ids",
        "111,222",
    )
    monkeypatch.setattr(
        "src.jobs.task_reminder.settings.discord_allowed_user_ids",
        "333",
    )
    assert task_reminder_dm_user_ids() == ["111", "222"]


def test_deliver_task_reminder_uses_dm_when_configured(monkeypatch) -> None:
    monkeypatch.setattr("src.jobs.task_reminder.settings.task_reminder_discord", True)
    monkeypatch.setattr("src.jobs.task_reminder.settings.enable_discord_bot", True)
    monkeypatch.setattr("src.jobs.task_reminder.settings.task_reminder_discord_dm", True)
    monkeypatch.setattr("src.jobs.task_reminder.task_reminder_dm_user_ids", lambda: ["999"])
    monkeypatch.setattr(
        "src.jobs.task_reminder.send_discord_bot_dm_message",
        lambda text, user_ids=None: user_ids == ["999"],
    )

    from src.jobs.task_reminder import _deliver_task_reminder

    assert _deliver_task_reminder("hello") is True


def test_run_task_reminder_test_bypasses_window(monkeypatch) -> None:
    monkeypatch.setattr("src.jobs.task_reminder.settings.enable_task_reminder", True)
    monkeypatch.setattr("src.jobs.task_reminder.is_task_reminder_window", lambda now=None: False)
    monkeypatch.setattr("src.jobs.task_reminder.collect_open_tasks", lambda: [])
    monkeypatch.setattr("src.jobs.task_reminder._deliver_task_reminder", lambda message: True)

    result = run_task_reminder(send=True, force=True)
    assert result["status"] == "ok"
    assert result["sent"] is True
    assert "Test reminder" in result["message"]


def test_run_task_reminder_can_skip_send(monkeypatch) -> None:
    monkeypatch.setattr("src.jobs.task_reminder.settings.enable_task_reminder", True)
    monkeypatch.setattr("src.jobs.task_reminder.is_task_reminder_window", lambda now=None: True)
    notion = MagicMock()
    notion.get_family_items.return_value = []
    notion.get_posting_plan.return_value = []
    notion.get_ideas.return_value = []
    monkeypatch.setattr("src.jobs.task_reminder.collect_open_tasks", lambda: [])

    result = run_task_reminder(send=False)
    assert result["status"] == "ok"
    assert result["sent"] is False
    assert "Reminder taskuri" in result["message"]