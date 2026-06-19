"""Tests for explicit web search intent detection."""

from src.bot.web_search_intent import parse_web_search_query


def test_prefix_cauta() -> None:
    assert parse_web_search_query("caută: trenduri reels 2026") == "trenduri reels 2026"


def test_inline_cauta_pe_net() -> None:
    assert parse_web_search_query("caută pe net caru cu bere cluj") == "caru cu bere cluj"


def test_no_implicit_search() -> None:
    assert parse_web_search_query("ce content sa fac la caru cu bere") is None


def test_search_prefix() -> None:
    assert parse_web_search_query("search: burnout parenting") == "burnout parenting"


def test_flexible_cauta_pe_net() -> None:
    assert (
        parse_web_search_query("vreau sa cauti pe net despre caru cu bere cluj")
        == "caru cu bere cluj"
    )