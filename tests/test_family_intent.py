"""Tests for Family & Administrative intent."""

from src.bot.discord_bot import AndreiDiscordBot
from src.bot.family_intent import extract_family_title, parse_family_request


def test_parse_family_indemnizatii_voice() -> None:
    query = (
        "Trebuie să adaug o nouă intrare în chestii ce țin de familie, "
        "familie și administrative. Trebuie un nou dosar pentru indemnizații."
    )
    body = parse_family_request(query)
    assert body is not None
    assert "indemniza" in body.lower()
    assert extract_family_title(body) == "Dosar indemnizații"


def test_pentru_familie_reminder_elenie() -> None:
    query = "pentru familie, nu uita că în trei zile e ziua Elenie."
    body = parse_family_request(query)
    assert body is not None
    assert "elenie" in body.lower()
    assert extract_family_title(body) == "Ziua Elenie - în trei zile"


def test_family_routes_to_family_note_not_research() -> None:
    bot = AndreiDiscordBot.__new__(AndreiDiscordBot)
    bot._research_disabled_channels = set()
    query = (
        "Trebuie să adaug o nouă intrare în chestii ce țin de familie, "
        "familie și administrative. Trebuie un nou dosar pentru indemnizații."
    )
    mode, _ = bot._resolve_mode_and_query(query, channel_id=42)
    assert mode == "family_note"


def test_familie_mention_at_end_of_sentence() -> None:
    query = "Nu uita că în trei zile e ziua Elenie, pentru familie."
    body = parse_family_request(query)
    assert body is not None
    assert "elenie" in body.lower()
    assert extract_family_title(body) == "Ziua Elenie - în trei zile"


def test_despre_familie_in_middle() -> None:
    query = "Am de notat despre familie că trebuie să sun școala vineri."
    body = parse_family_request(query)
    assert body is not None
    assert "școal" in body.lower() or "scoal" in body.lower()


def test_de_familie_at_end() -> None:
    query = "Notează: ziua Eleniei în 3 zile, de familie."
    body = parse_family_request(query)
    assert body is not None
    assert "elenie" in body.lower()


def test_elenie_reminder_routes_family_note() -> None:
    bot = AndreiDiscordBot.__new__(AndreiDiscordBot)
    bot._research_disabled_channels = set()
    mode, _ = bot._resolve_mode_and_query(
        "pentru familie, nu uita că în trei zile e ziua Elenie.", channel_id=42
    )
    assert mode == "family_note"


def test_tabu_familie_georgiana_voice() -> None:
    query = (
        "Salut! Uite care e treaba, trebuie să-mi aduc aminte săptămâna viitoare, "
        "că e ziua Georgianei și pune asta în tabu familie, cumva."
    )
    body = parse_family_request(query)
    assert body is not None
    assert "georgian" in body.lower()
    assert extract_family_title(body) == "Ziua Georgianei - săptămâna viitoare"


def test_familie_at_end_routes_family_note() -> None:
    bot = AndreiDiscordBot.__new__(AndreiDiscordBot)
    bot._research_disabled_channels = set()
    mode, _ = bot._resolve_mode_and_query(
        "Nu uita că în trei zile e ziua Elenie, pentru familie.", channel_id=42
    )
    assert mode == "family_note"


def test_georgiana_tabu_routes_family_note() -> None:
    bot = AndreiDiscordBot.__new__(AndreiDiscordBot)
    bot._research_disabled_channels = set()
    query = (
        "Salut! Uite care e treaba, trebuie să-mi aduc aminte săptămâna viitoare, "
        "că e ziua Georgianei și pune asta în tabu familie, cumva."
    )
    mode, _ = bot._resolve_mode_and_query(query, channel_id=42)
    assert mode == "family_note"