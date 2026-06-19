"""Smart alerts for deadlines, balance, and burnout."""

from datetime import datetime, timedelta

from src.integrations.google_services import GoogleServices
from src.integrations.notion import NotionClient
from src.integrations.notifier import Notifier, get_notifier
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _check_deadline_alerts(notion: NotionClient, notifier: Notifier) -> int:
    sent = 0
    try:
        tasks = notion.get_family_items(status="To Do") + notion.get_family_items(
            status="In progress"
        )
        today = datetime.now().date()
        for task in tasks:
            due = NotionClient.extract_text_property(task, "Due Date")
            if not due:
                continue
            try:
                due_date = datetime.strptime(due[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            days_left = (due_date - today).days
            title = NotionClient.extract_title(task)
            if days_left <= 0:
                notifier.send_alert("deadline", f"⚠️ DEPĂȘIT: {title} (deadline: {due})")
                sent += 1
            elif days_left <= 2:
                notifier.send_alert("deadline", f"{title} — deadline în {days_left} zile ({due})")
                sent += 1
    except Exception as e:
        logger.error("deadline_check_failed", error=str(e))
    return sent


def _check_family_balance(google: GoogleServices, notifier: Notifier) -> int:
    sent = 0
    try:
        events = google.get_upcoming_events(days=3)
        work_hours = 0
        family_keywords = ("familie", "copil", "soție", "family", "kids", "personal")
        has_family_time = False

        for ev in events:
            summary = ev.get("summary", "").lower()
            if any(kw in summary for kw in family_keywords):
                has_family_time = True
            start = ev.get("start", {}).get("dateTime")
            end = ev.get("end", {}).get("dateTime")
            if start and end:
                try:
                    s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    if "familie" not in summary and "family" not in summary:
                        work_hours += (e - s).total_seconds() / 3600
                except ValueError:
                    pass

        if work_hours > 30:
            notifier.send_alert(
                "burnout",
                f"Ai {work_hours:.0f}h de muncă programate în 3 zile. "
                "Consideră o pauză sau timp de calitate cu familia.",
            )
            sent += 1

        if not has_family_time:
            notifier.send_alert(
                "family",
                "Nu ai timp de familie programat în următoarele 3 zile. "
                "Poate un moment de calitate diseară sau weekend?",
            )
            sent += 1
    except Exception as e:
        logger.error("family_balance_check_failed", error=str(e))
    return sent


def run_smart_alerts() -> dict:
    logger.info("smart_alerts_started")
    notifier = get_notifier()
    if not notifier.enabled:
        logger.warning("notifier_disabled_skipping_alerts")
        return {"sent": 0, "status": "notifier_disabled"}

    notion = NotionClient()
    google = GoogleServices()

    deadline_alerts = _check_deadline_alerts(notion, notifier)
    balance_alerts = _check_family_balance(google, notifier)
    total = deadline_alerts + balance_alerts

    logger.info("smart_alerts_completed", sent=total)
    return {"sent": total, "deadlines": deadline_alerts, "balance": balance_alerts}


if __name__ == "__main__":
    print(run_smart_alerts())