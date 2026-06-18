"""Basic configuration tests."""

import src.bootstrap  # noqa: F401

from src.utils.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.user_name == "Andrei"
    assert settings.timezone == "Europe/Bucharest"
    assert settings.memory_provider in ("supabase", "pinecone")


def test_llm_providers_order():
    settings = Settings(llm_fallback_order="grok,anthropic,openai")
    assert settings.llm_providers == ["grok", "anthropic", "openai"]