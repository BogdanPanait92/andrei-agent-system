"""Notifier configuration tests."""

import src.bootstrap  # noqa: F401

from src.integrations.notifier import get_notifier, reset_notifier
from src.integrations.notifier_base import strip_markdown
from src.integrations.telegram_bot import TelegramNotifier
from src.integrations.whatsapp import WhatsAppNotifier, _normalize_phone
from src.utils.config import Settings


def test_strip_markdown():
    assert strip_markdown("*bold* text") == "bold text"
    assert strip_markdown("**strong**") == "strong"


def test_normalize_phone():
    assert _normalize_phone("+40 722 123 456") == "40722123456"
    assert _normalize_phone("40722123456") == "40722123456"


def test_telegram_notifier_disabled():
    reset_notifier()
    n = TelegramNotifier()
    assert n.enabled is False


def test_whatsapp_notifier_disabled():
    n = WhatsAppNotifier()
    assert n.enabled is False


def test_get_notifier_telegram_default():
    reset_notifier()
    settings = Settings(notifier_provider="telegram")
    # Factory reads global settings; default is telegram
    n = get_notifier()
    assert isinstance(n, TelegramNotifier)


def test_notifier_provider_config():
    settings = Settings(notifier_provider="whatsapp")
    assert settings.notifier_provider == "whatsapp"