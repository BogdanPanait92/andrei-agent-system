"""Tests for direct Notion ideas listing."""

from src.integrations.ideas_list import IdeasListService


def test_parse_draft_query() -> None:
    assert IdeasListService.parse_status_from_query("care sunt ideile in draft") == "Draft"


def test_parse_all_ideas_query() -> None:
    assert IdeasListService.parse_status_from_query("toate ideile din notion") == ""


def test_parse_ignores_idea_mode() -> None:
    assert IdeasListService.parse_status_from_query("idee: podcast ACP") is None


def test_parse_in_lucru() -> None:
    assert IdeasListService.parse_status_from_query("idei in lucru") == "In lucru"