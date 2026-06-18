#!/usr/bin/env python3
"""Start the Discord chat bot for interactive agent conversations."""

import sys

import src.bootstrap  # noqa: F401

from src.bot.discord_bot import run_discord_bot
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def main() -> int:
    if not settings.enable_discord_bot:
        print("Set ENABLE_DISCORD_BOT=true in .env")
        return 1

    if not settings.discord_bot_token.strip():
        print("Missing DISCORD_BOT_TOKEN in .env")
        print("Discord Developer Portal → Applications → Bot → Reset Token")
        return 1

    if not settings.discord_allowed_channel_ids.strip():
        print("Set DISCORD_ALLOWED_CHANNEL_IDS in .env (channel ID where you chat)")
        print("Discord → right-click channel → Copy Channel ID")
        return 1

    logger.info("discord_bot_starting")
    try:
        run_discord_bot()
    except KeyboardInterrupt:
        logger.info("discord_bot_stopped")
    except Exception as e:
        logger.error("discord_bot_failed", error=str(e))
        print(f"Eroare: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())