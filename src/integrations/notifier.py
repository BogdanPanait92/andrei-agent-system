"""Unified notifier factory — Telegram or WhatsApp."""

from typing import Protocol

from src.integrations.notifier_base import NotifierMixin
from src.integrations.telegram_bot import TelegramNotifier
from src.integrations.whatsapp import WhatsAppNotifier
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Notifier(Protocol):
    @property
    def enabled(self) -> bool: ...

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool: ...
    def send_daily_briefing(self, briefing: str) -> bool: ...
    def send_weekly_review(self, review: str) -> bool: ...
    def send_alert(self, alert_type: str, message: str) -> bool: ...
    def send_reminder(self, title: str, details: str) -> bool: ...


_notifier_instance: Notifier | None = None


def get_notifier() -> Notifier:
    """Return configured notifier (telegram or whatsapp)."""
    global _notifier_instance
    if _notifier_instance is not None:
        return _notifier_instance

    provider = settings.notifier_provider
    if provider == "whatsapp":
        _notifier_instance = WhatsAppNotifier()
        logger.info("notifier_initialized", provider="whatsapp")
    else:
        _notifier_instance = TelegramNotifier()
        logger.info("notifier_initialized", provider="telegram")

    return _notifier_instance


def reset_notifier() -> None:
    """Reset cached instance (useful for tests)."""
    global _notifier_instance
    _notifier_instance = None