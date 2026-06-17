"""Daily briefing job - Telegram + Notion."""

from src.graph.workflow import run_workflow
from src.utils.logging import get_logger

logger = get_logger(__name__)


def run_daily_briefing() -> str:
    logger.info("daily_briefing_started")
    result = run_workflow(mode="daily", query="Generare daily briefing automat")
    logger.info("daily_briefing_completed", length=len(result))
    return result


if __name__ == "__main__":
    print(run_daily_briefing())