"""Weekly review job - runs on Sunday."""

from src.graph.workflow import run_workflow
from src.utils.logging import get_logger

logger = get_logger(__name__)


def run_weekly_review() -> str:
    logger.info("weekly_review_started")
    result = run_workflow(mode="weekly", query="Generare weekly review duminică")
    logger.info("weekly_review_completed", length=len(result))
    return result


if __name__ == "__main__":
    print(run_weekly_review())