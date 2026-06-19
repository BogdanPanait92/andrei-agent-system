"""Tests for research / Grok-style chat intent detection."""

from src.bot.research_intent import (
    has_grok_marker,
    is_research_exit,
    parse_research_query,
    wants_save_to_ideas_with_research,
)


def test_research_prefix() -> None:
    assert parse_research_query("research: trenduri AI 2026") == "trenduri AI 2026"


def test_grok_prefix() -> None:
    assert parse_research_query("grok: ce e quantum computing") == "ce e quantum computing"


def test_exploreaza_inline() -> None:
    assert parse_research_query("explorează restaurante fine dining bucuresti") == (
        "restaurante fine dining bucuresti"
    )


def test_empty_research_prefix_enters_mode() -> None:
    assert parse_research_query("research:") == ""


def test_no_implicit_research() -> None:
    assert parse_research_query("ce trenduri AI sunt in 2026") is None


def test_research_exit() -> None:
    assert is_research_exit("research stop")
    assert is_research_exit("ieși din research")


def test_flexible_research_despre() -> None:
    assert (
        parse_research_query("vreau sa faci research despre trenduri parenting 2026")
        == "trenduri parenting 2026"
    )


def test_grok_with_comma() -> None:
    assert parse_research_query("grok, ce e un black hole") == "ce e un black hole"


def test_research_pe_ideea() -> None:
    query = (
        "Salut! Aș vrea să-mi faci research pe ideea marilor filozofe ai lumii "
        "și să creez automat o pagină."
    )
    assert parse_research_query(query) == "marilor filozofe ai lumii"
    assert wants_save_to_ideas_with_research(query)


def test_research_and_adauga_la_idei() -> None:
    query = "vreau sa faci research despre stoici si adauga la idei"
    assert parse_research_query(query) == "stoici"
    assert wants_save_to_ideas_with_research(query)


def test_adauga_idee_with_grok_suffix() -> None:
    query = (
        "Aduaga-mi o noua idee: despre cat de repede trece timpul in viziunea "
        "lui platon- abordare filosofica - grok"
    )
    assert has_grok_marker(query)
    topic = parse_research_query(query)
    assert topic is not None
    assert "platon" in topic.lower()
    assert "timpul" in topic.lower()
    assert wants_save_to_ideas_with_research(query)


def test_fa_research_in_ideas_with_stocheaza() -> None:
    query = (
        "Am o idee noua, stocheaz-o si fa research inn ideas: "
        "despre cat de repede trece viata in viziunea filosofului platon"
    )
    assert (
        parse_research_query(query)
        == "cat de repede trece viata in viziunea filosofului platon"
    )
    assert wants_save_to_ideas_with_research(query)


def test_research_ul_asta_with_context_topic_and_pui_in_idei() -> None:
    query = (
        "Salut! Uite, aș vrea să văd cum filozofii antici tratează ideea timpului. "
        "Vreau tu să faci research-ul ăsta pentru mine și să-l pui în idei."
    )
    assert (
        parse_research_query(query)
        == "filozofii antici tratează ideea timpului"
    )
    assert wants_save_to_ideas_with_research(query)