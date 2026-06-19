"""Tests for Discord conversation context and save intent."""

from src.bot.conversation_context import ConversationContext
from src.bot.save_intent import (
    is_save_previous_exchange_request,
    is_save_to_notion_request,
    parse_save_ideas_hint,
)


def test_save_intent_detects_confirmation() -> None:
    assert is_save_to_notion_request("da, salveaza asta in notion")
    assert is_save_to_notion_request("salvează în Notion")


def test_save_intent_ignores_idea_prefix() -> None:
    assert not is_save_to_notion_request("idee: podcast ACP")


def test_save_previous_bare_adauga_la_idei() -> None:
    assert is_save_previous_exchange_request("Adauga la idei")
    assert is_save_previous_exchange_request("adaugă la idei")


def test_save_previous_with_reference() -> None:
    query = (
        "Adauga la idei raspunsul tau de mai sus legat de problemele vietii"
    )
    assert is_save_previous_exchange_request(query)
    assert parse_save_ideas_hint(query) == "problemele vietii"


def test_save_previous_not_new_idea_with_body() -> None:
    assert not is_save_previous_exchange_request(
        "adauga la idei un clip despre viata unui fluture"
    )


def test_conversation_context_last_exchange() -> None:
    ctx = ConversationContext()
    ctx.add(1, "intrebare despre bere", "recomandare reel")
    last = ctx.get_last(1)
    assert last is not None
    assert "bere" in last.user
    assert "reel" in last.assistant


def test_conversation_skips_save_meta_for_substantive() -> None:
    ctx = ConversationContext()
    ctx.add(
        1,
        "idei despre probleme simple ale lumii",
        "Poți construi fiecare clip pornind de la un exemplu concret.",
    )
    ctx.add(1, "Adauga la idei", "✅ **Salvat în Notion → Ideas** (status: Draft)")
    substantive = ctx.get_last_substantive(1)
    assert substantive is not None
    assert "probleme simple" in substantive.user
    assert "exemplu concret" in substantive.assistant