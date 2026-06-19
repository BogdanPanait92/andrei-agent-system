"""Tests for research-on-by-default routing in Discord bot."""

from src.bot.discord_bot import AndreiDiscordBot


def _bot() -> AndreiDiscordBot:
    bot = AndreiDiscordBot.__new__(AndreiDiscordBot)
    bot._research_disabled_channels = set()
    return bot


def test_research_is_default_for_plain_question() -> None:
    bot = _bot()
    mode, _ = bot._resolve_mode_and_query("ce trenduri AI sunt in 2026?", channel_id=42)
    assert mode == "research"


def test_research_stop_switches_to_agent() -> None:
    bot = _bot()
    bot._resolve_mode_and_query("research stop", channel_id=42)
    mode, _ = bot._resolve_mode_and_query("ce trenduri AI sunt in 2026?", channel_id=42)
    assert mode == "chat"


def test_research_command_reenables_after_stop() -> None:
    bot = _bot()
    bot._resolve_mode_and_query("research stop", channel_id=42)
    bot._resolve_mode_and_query("research", channel_id=42)
    mode, _ = bot._resolve_mode_and_query("explica quantum computing", channel_id=42)
    assert mode == "research"


def test_priority_intents_bypass_default_research() -> None:
    bot = _bot()
    mode, _ = bot._resolve_mode_and_query("am filmat la Momo", channel_id=42)
    assert mode == "filmed_location"


def test_noteaza_la_idei_uses_research_save_when_research_on() -> None:
    bot = _bot()
    query = (
        "Notează la idei un nou idee de clip. "
        "Subiectul clipului este filozofia grecilor antici."
    )
    mode, resolved = bot._resolve_mode_and_query(query, channel_id=42)
    assert mode == "research_save"
    assert resolved == "filozofia grecilor antici"


def test_mi_a_venit_idee_clip_routes_research_save() -> None:
    bot = _bot()
    query = (
        "Mi-a venit acum o idee nouă să fac un clip despre "
        "reproducerea la mamifere."
    )
    mode, resolved = bot._resolve_mode_and_query(query, channel_id=42)
    assert mode == "research_save"
    assert resolved == "reproducerea la mamifere"


def test_noteaza_o_la_idei_at_end_routes_research_save() -> None:
    bot = _bot()
    query = (
        "Salut, am o nouă idee despre problema zbuciumului intern la grecii antici. "
        "Notează-o la idei și fă tot ce trebuie să faci."
    )
    mode, resolved = bot._resolve_mode_and_query(query, channel_id=42)
    assert mode == "research_save"
    assert resolved == "problema zbuciumului intern la grecii antici"


def test_family_administrative_uses_agent_not_research() -> None:
    bot = _bot()
    mode, _ = bot._resolve_mode_and_query(
        "ce am în Family & Administrative azi?", channel_id=42
    )
    assert mode == "chat"


def test_familie_si_administrative_romanian() -> None:
    bot = _bot()
    mode, _ = bot._resolve_mode_and_query(
        "ce am in familie si administrative azi?", channel_id=42
    )
    assert mode == "chat"


def test_posting_plan_uses_agent_not_research() -> None:
    bot = _bot()
    mode, _ = bot._resolve_mode_and_query(
        "adaugă în posting plan: Clip vlog, oras=București", channel_id=42
    )
    assert mode == "chat"


def test_calendar_uses_agent_not_research() -> None:
    bot = _bot()
    mode, _ = bot._resolve_mode_and_query("ce am în calendar azi?", channel_id=42)
    assert mode == "chat"


def test_noteaza_la_idei_direct_save_when_research_stopped() -> None:
    bot = _bot()
    bot._resolve_mode_and_query("research stop", channel_id=42)
    query = "adauga la idei un clip despre viata unui fluture"
    mode, resolved = bot._resolve_mode_and_query(query, channel_id=42)
    assert mode == "idea_note"
    assert resolved == "un clip despre viata unui fluture"