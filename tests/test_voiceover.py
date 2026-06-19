"""Tests for voice-over script brief."""

from src.integrations.voiceover import VOICEOVER_OUTPUT_STRUCTURE, VOICEOVER_SCRIPT_BRIEF


def test_voiceover_brief_requires_two_variants() -> None:
    assert "2 variante" in VOICEOVER_SCRIPT_BRIEF
    assert "VARIANTA 1" in VOICEOVER_OUTPUT_STRUCTURE
    assert "VARIANTA 2" in VOICEOVER_OUTPUT_STRUCTURE


def test_voiceover_length_guidance() -> None:
    assert "150" in VOICEOVER_SCRIPT_BRIEF
    assert "90 de secunde" in VOICEOVER_SCRIPT_BRIEF


def test_voiceover_bans_cliche_intros() -> None:
    assert "Te-ai întrebat vreodată" in VOICEOVER_SCRIPT_BRIEF
    assert "În lumea de astăzi" in VOICEOVER_SCRIPT_BRIEF


def test_voiceover_storyteller_role() -> None:
    assert "storyteller" in VOICEOVER_SCRIPT_BRIEF
    assert "20 de ani" in VOICEOVER_SCRIPT_BRIEF