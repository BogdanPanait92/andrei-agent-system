#!/usr/bin/env python3
"""Quick Telegram connectivity test."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from src.integrations.notifier import get_notifier, reset_notifier
from src.utils.config import settings
from src.utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main() -> int:
    reset_notifier()
    print("=" * 50)
    print("TELEGRAM TEST — Andrei AI Agent System")
    print("=" * 50)
    print(f"Provider:     {settings.notifier_provider}")
    token_ok = (
        settings.telegram_bot_token
        and "your_" not in settings.telegram_bot_token
        and not settings.telegram_bot_token.startswith("123456789:")
    )
    chat_ok = (
        settings.telegram_chat_id
        and settings.telegram_chat_id != "123456789"
    )
    print(f"Token set:    {'yes' if token_ok else 'NO (placeholder)'}")
    print(f"Chat ID set:  {'yes' if chat_ok else 'NO (placeholder)'}")
    print()

    if settings.notifier_provider != "telegram":
        print("Set NOTIFIER_PROVIDER=telegram in .env")
        return 1

    if not token_ok:
        print("Missing TELEGRAM_BOT_TOKEN in .env")
        print("Get one from @BotFather on Telegram → /newbot")
        return 1

    if not chat_ok:
        print("Missing TELEGRAM_CHAT_ID in .env")
        print("Send /start to your bot, then visit:")
        print(f"  https://api.telegram.org/bot{settings.telegram_bot_token[:10]}.../getUpdates")
        return 1

    notifier = get_notifier()
    if not notifier.enabled:
        print("Notifier not enabled — check .env values")
        return 1

    message = "✅ Test reușit! Andrei AI Agent System e conectat la Telegram."
    print("Sending test message...")
    ok = notifier.send_message(message)

    if ok:
        print("SUCCESS — verifică Telegram, ar trebui să vezi mesajul.")
        return 0

    print("FAILED — mesajul nu a fost trimis. Verifică token și chat ID.")
    return 1


if __name__ == "__main__":
    sys.exit(main())