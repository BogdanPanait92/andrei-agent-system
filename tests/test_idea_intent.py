"""Tests for natural-language idea save intent."""

from src.bot.idea_intent import is_direct_idea_save_request, parse_idea_request


def test_idea_prefix() -> None:
    assert parse_idea_request("idee: podcast ACP") == "podcast ACP"


def test_natural_language_save() -> None:
    query = (
        "Sală frate, mi-a venit o idee și da, s-o pui tu în idei, "
        "aș vrea să fac un clip despre cât de scurtă este viața"
    )
    assert parse_idea_request(query) == "un clip despre cât de scurtă este viața"


def test_pune_in_idei_ideea_asta() -> None:
    assert (
        parse_idea_request(
            "Pune in idei ideea asta: cat de scurta e viata unui fluture"
        )
        == "cat de scurta e viata unui fluture"
    )


def test_adauga_mi_o_idee_without_grok() -> None:
    assert (
        parse_idea_request(
            "Adauga-mi o noua idee: un clip despre viata unui fluture"
        )
        == "un clip despre viata unui fluture"
    )


def test_adauga_la_idei() -> None:
    assert (
        parse_idea_request("adauga la idei un clip despre viata unui fluture")
        == "un clip despre viata unui fluture"
    )


def test_bare_adauga_la_idei_is_not_new_idea() -> None:
    assert parse_idea_request("Adauga la idei") is None


def test_noteaza_la_idei_clip_subiect() -> None:
    query = (
        "Notează la idei un nou idee de clip. "
        "Subiectul clipului este filozofia grecilor antici."
    )
    assert parse_idea_request(query) == "filozofia grecilor antici"
    assert is_direct_idea_save_request(query)


def test_direct_save_not_research_combo() -> None:
    query = "fa research despre platon si adauga la idei"
    assert not is_direct_idea_save_request(query)


def test_mi_a_venit_acum_idee_clip_despre() -> None:
    query = (
        "Mi-a venit acum o idee nouă să fac un clip despre "
        "reproducerea la mamifere."
    )
    assert parse_idea_request(query) == "reproducerea la mamifere"
    assert is_direct_idea_save_request(query)


def test_noteaza_o_la_idei_at_end_of_sentence() -> None:
    query = (
        "Salut, am o nouă idee despre problema zbuciumului intern la grecii antici. "
        "Notează-o la idei și fă tot ce trebuie să faci."
    )
    assert parse_idea_request(query) == "problema zbuciumului intern la grecii antici"
    assert is_direct_idea_save_request(query)


def test_no_implicit_idea() -> None:
    assert parse_idea_request("ce idei am in draft") is None


def test_adauga_o_idee_noua_despre() -> None:
    query = "adauga o idee noua despre platon si timpul"
    assert parse_idea_request(query) == "platon si timpul"
    assert is_direct_idea_save_request(query)


def test_adauga_o_idee_noua_colon() -> None:
    query = "adaugă o idee nouă: un clip despre platon"
    assert parse_idea_request(query) == "un clip despre platon"
    assert is_direct_idea_save_request(query)


def test_pune_o_idee_noua_despre() -> None:
    query = "pune o idee noua despre parenting"
    assert parse_idea_request(query) == "parenting"
    assert is_direct_idea_save_request(query)


def test_pune_o_idee_prefix() -> None:
    query = "pune o idee: platon si timpul"
    assert parse_idea_request(query) == "platon si timpul"
    assert is_direct_idea_save_request(query)


def test_pune_idee_noua_routes_research_save() -> None:
    from src.bot.discord_bot import AndreiDiscordBot

    bot = AndreiDiscordBot.__new__(AndreiDiscordBot)
    bot._research_disabled_channels = set()
    mode, topic = bot._resolve_mode_and_query(
        "pune o idee noua despre reproducerea la mamifere", channel_id=42
    )
    assert mode == "research_save"
    assert "mamifere" in topic.lower()