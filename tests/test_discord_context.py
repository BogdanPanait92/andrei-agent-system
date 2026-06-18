"""Tests for Discord conversation context and save intent."""

from src.bot.conversation_context import ConversationContext
from src.bot.save_intent import is_save_to_notion_request


def test_save_intent_detects_confirmation() -> None:
    assert is_save_to_notion_request("da, salveaza asta in notion")
    assert is_save_to_notion_request("salvează în Notion")


def test_save_intent_ignores_idea_prefix() -> None:
    assert not is_save_to_notion_request("idee: podcast ACP")


def test_conversation_context_last_exchange() -> None:
    ctx = ConversationContext()
    ctx.add(1, "intrebare despre bere", "recomandare reel")
    last = ctx.get_last(1)
    assert last is not None
    assert "bere" in last.user
    assert "reel" in last.assistant