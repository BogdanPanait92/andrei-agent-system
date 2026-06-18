#!/usr/bin/env python3
"""Quick Discord webhook connectivity test."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from src.integrations.notifier import get_notifier, reset_notifier
from src.utils.config import settings
from src.utils.logging import setup_logging

setup_logging()


def _webhook_ok(url: str) -> bool:
    return bool(url and url.startswith("https://discord") and "webhooks" in url and "your_" not in url)


def main() -> int:
    reset_notifier()
    print("=" * 50)
    print("DISCORD TEST — Andrei AI Agent System")
    print("=" * 50)
    print(f"Provider:      {settings.notifier_provider}")
    print(f"Webhook set:   {'yes' if _webhook_ok(settings.discord_webhook_url) else 'NO'}")
    print()

    if settings.notifier_provider != "discord":
        print("Set NOTIFIER_PROVIDER=discord in .env")
        return 1

    if not _webhook_ok(settings.discord_webhook_url):
        print("Missing DISCORD_WEBHOOK_URL in .env")
        print("Discord → Server Settings → Integrations → Webhooks → New Webhook")
        return 1

    notifier = get_notifier()
    if not notifier.enabled:
        print("Discord notifier not enabled — check webhook URL")
        return 1

    print("Sending test message...")
    ok = notifier.send_message("✅ Test reușit! Andrei AI Agent System e conectat la Discord.")

    if ok:
        print("SUCCESS — verifică canalul Discord.")
        return 0

    print("FAILED — verifică DISCORD_WEBHOOK_URL (valid, neexpirat).")
    return 1


if __name__ == "__main__":
    sys.exit(main())