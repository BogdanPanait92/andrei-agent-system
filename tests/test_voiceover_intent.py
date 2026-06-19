"""Tests for existing-idea voice-over intent detection."""

from src.bot.voiceover_intent import parse_voiceover_request


def test_voiceover_prefix() -> None:
    assert parse_voiceover_request("voiceover: platon timp") == ("platon timp", None)


def test_genereaza_voiceover_pe_ideea() -> None:
    assert parse_voiceover_request(
        "genereaza voice-over pe ideea despre fluturi"
    ) == ("despre fluturi", None)


def test_voiceover_with_draft_status() -> None:
    assert parse_voiceover_request("voiceover: draft: platon") == ("platon", "Draft")


def test_no_voiceover_on_new_idea() -> None:
    assert parse_voiceover_request("idee: podcast ACP") is None