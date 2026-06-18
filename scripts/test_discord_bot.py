#!/usr/bin/env python3
"""Validate Discord bot configuration (no live connection)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.bootstrap  # noqa: F401

from src.utils.config import settings


def main() -> int:
    print("=" * 50)
    print("DISCORD BOT CONFIG — Andrei AI Agent System")
    print("=" * 50)
    print(f"ENABLE_DISCORD_BOT:          {settings.enable_discord_bot}")
    print(f"DISCORD_BOT_TOKEN set:       {'yes' if settings.discord_bot_token.strip() else 'NO'}")
    print(f"DISCORD_ALLOWED_CHANNEL_IDS: {settings.discord_allowed_channel_ids or 'NOT SET'}")
    print(f"DISCORD_ALLOWED_USER_IDS:    {settings.discord_allowed_user_ids or '(any user)'}")
    print()

    missing = []
    if not settings.enable_discord_bot:
        missing.append("ENABLE_DISCORD_BOT=true")
    if not settings.discord_bot_token.strip():
        missing.append("DISCORD_BOT_TOKEN")
    if not settings.discord_allowed_channel_ids.strip():
        missing.append("DISCORD_ALLOWED_CHANNEL_IDS")

    if missing:
        print("Missing:")
        for item in missing:
            print(f"  - {item}")
        print()
        print("Setup:")
        print("  1. https://discord.com/developers/applications → New Application")
        print("  2. Bot → Reset Token → copy to DISCORD_BOT_TOKEN")
        print("  3. Bot → MESSAGE CONTENT INTENT = ON")
        print("  4. OAuth2 → invite bot to your server")
        print("  5. Copy channel ID → DISCORD_ALLOWED_CHANNEL_IDS")
        return 1

    try:
        import discord  # noqa: F401
    except ImportError:
        print("FAIL: discord.py not installed. Run: pip install discord.py")
        return 1

    print("SUCCESS — config looks good. Start with:")
    print("  .\\scripts\\local_run.ps1 discord-bot")
    return 0


if __name__ == "__main__":
    sys.exit(main())