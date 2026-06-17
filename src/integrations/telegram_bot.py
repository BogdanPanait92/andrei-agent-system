"""Telegram bot for alerts, briefings, and reminders."""

import asyncio

import httpx

from src.integrations.notifier_base import NotifierMixin
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramNotifier(NotifierMixin):
    def __init__(self) -> None:
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self._enabled = bool(self.token and self.chat_id)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _run_async(self, coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, coro).result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    async def _send_message_async(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_preview: bool = True,
    ) -> bool:
        if not self._enabled:
            logger.warning("telegram_not_configured")
            return False

        url = TELEGRAM_API.format(token=self.token, method="sendMessage")
        chunks = self.split_message(text, max_len=4000)

        async with httpx.AsyncClient(timeout=30.0) as client:
            for chunk in chunks:
                payload = {
                    "chat_id": self.chat_id,
                    "text": chunk,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": disable_preview,
                }
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                except httpx.HTTPError as e:
                    logger.error("telegram_send_failed", error=str(e))
                    return False
        return True

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        return self._run_async(self._send_message_async(text, parse_mode))

    def send_daily_briefing(self, briefing: str) -> bool:
        header = "🌅 *Daily Briefing - Andrei*\n\n"
        return self.send_message(header + briefing, parse_mode="Markdown")

    def send_weekly_review(self, review: str) -> bool:
        header = "📊 *Weekly Review - Duminică*\n\n"
        return self.send_message(header + review, parse_mode="Markdown")

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
        text = f"{icon} *Alertă {alert_type.replace('_', ' ').title()}*\n\n{message}"
        return self.send_message(text, parse_mode="Markdown")

    def send_reminder(self, title: str, details: str) -> bool:
        text = f"📌 *Reminder: {title}*\n\n{details}"
        return self.send_message(text, parse_mode="Markdown")