"""Background job: voice-over scripts for Notion ideas missing them."""

from src.integrations.idea_voiceover import IdeaVoiceoverService
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def run_auto_voiceover(max_count: int | None = None) -> dict:
    if not settings.enable_auto_voiceover:
        logger.info("auto_voiceover_disabled")
        return {"processed": [], "errors": [], "pending_remaining": 0, "skipped": True}

    logger.info("auto_voiceover_started")
    result = IdeaVoiceoverService().run_auto_batch(max_count=max_count)
    logger.info(
        "auto_voiceover_completed",
        processed=len(result["processed"]),
        errors=len(result["errors"]),
        pending_remaining=result["pending_remaining"],
    )
    return result


if __name__ == "__main__":
    print(run_auto_voiceover())