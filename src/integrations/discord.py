"""Discord webhook notifications for alerts, briefings, and reminders."""

import httpx

from src.integrations.notifier_base import NotifierMixin, strip_markdown
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

DISCORD_MAX_LEN = 2000


class DiscordNotifier(NotifierMixin):
    """
    Discord via Incoming Webhook.

    Setup: Server Settings → Integrations → Webhooks → New Webhook → copy URL.
    """

    def __init__(self) -> None:
        self.webhook_url = settings.discord_webhook_url.strip()
        self.username = settings.discord_webhook_username or "Andrei AI"
        self._enabled = bool(self.webhook_url and self.webhook_url.startswith("https://discord"))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self._enabled:
            logger.warning("discord_not_configured")
            return False

        plain = strip_markdown(text)
        chunks = self.split_message(plain, max_len=DISCORD_MAX_LEN)

        with httpx.Client(timeout=30.0) as client:
            for chunk in chunks:
                payload = {
                    "content": chunk,
                    "username": self.username,
                }
                try:
                    response = client.post(self.webhook_url, json=payload)
                    if response.status_code == 429:
                        logger.warning("discord_rate_limited")
                        return False
                    response.raise_for_status()
                except httpx.HTTPError as e:
                    logger.error("discord_send_failed", error=str(e))
                    return False
        return True

    def send_daily_briefing(self, briefing: str) -> bool:
        header = "🌅 **Daily Briefing - Andrei**\n\n"
        return self.send_message(header + briefing)

    def send_weekly_review(self, review: str) -> bool:
        header = "📊 **Weekly Review - Duminică**\n\n"
        return self.send_message(header + review)

    def send_alert(self, alert_type: str, message: str) -> bool:
        icons = {
            "deadline": "⏰",
            "family": "👨‍👩‍👧",
            "burnout": "🔥",
            "content": "🎬",
            "ajut_cum_pot": "💚",
            "balance": "⚖️",
        }
        icon = icons.get(alert_type, "🔔")
        label = alert_type.replace("_", " ").title()
        text = f"{icon} **Alertă {label}**\n\n{message}"
        return self.send_message(text)