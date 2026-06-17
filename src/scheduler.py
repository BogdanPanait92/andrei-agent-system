"""APScheduler for daily/weekly cron jobs."""

import signal
import sys

import src.bootstrap  # noqa: F401

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.jobs.alerts import run_smart_alerts
from src.jobs.daily_briefing import run_daily_briefing
from src.jobs.weekly_review import run_weekly_review
from src.utils.config import settings
from src.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

DAY_MAP = {
    "monday": "mon", "tuesday": "tue", "wednesday": "wed",
    "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
}


def create_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=settings.timezone)

    scheduler.add_job(
        run_daily_briefing,
        CronTrigger(
            hour=settings.daily_briefing_hour,
            minute=settings.daily_briefing_minute,
        ),
        id="daily_briefing",
        name="Daily Briefing",
        replace_existing=True,
    )

    weekly_day = DAY_MAP.get(settings.weekly_review_day.lower(), "sun")
    scheduler.add_job(
        run_weekly_review,
        CronTrigger(day_of_week=weekly_day, hour=settings.weekly_review_hour, minute=0),
        id="weekly_review",
        name="Weekly Review",
        replace_existing=True,
    )

    scheduler.add_job(
        run_smart_alerts,
        CronTrigger(hour="9,14,18", minute=0),
        id="smart_alerts",
        name="Smart Alerts",
        replace_existing=True,
    )

    return scheduler


def main() -> None:
    setup_logging()
    if not settings.enable_scheduler:
        logger.info("scheduler_disabled")
        sys.exit(0)

    scheduler = create_scheduler()
    logger.info(
        "scheduler_started",
        daily=f"{settings.daily_briefing_hour}:{settings.daily_briefing_minute:02d}",
        weekly=f"{settings.weekly_review_day} {settings.weekly_review_hour}:00",
    )

    def shutdown(signum, frame):
        logger.info("scheduler_shutting_down")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("scheduler_stopped")


if __name__ == "__main__":
    main()