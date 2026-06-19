"""Tests for Ajut Cum Pot save intent."""

from src.bot.ajut_intent import extract_ajut_title, parse_ajut_request


def test_parse_ajut_request_legat_de_acp() -> None:
    query = (
        "Salut! Uite, tot legat de ajut cum pot, trebuie să-i spunem lui Sorin să trimită "
        "datele de facturare către Alex, pentru că am cumpărat telefonul și cu laptopul "
        "și trebuie cumva să-i dăm lui Alex datele de facturare. Asta este pentru Sorin."
    )
    body = parse_ajut_request(query)
    assert body is not None
    assert "sorin" in body.lower()
    assert "alex" in body.lower()
    assert "factur" in body.lower()


def test_parse_ajut_request_tot_pentru_acp() -> None:
    query = "Tot pentru ACP, trebuie să contactăm ONG-ul pentru campania de primăvară."
    body = parse_ajut_request(query)
    assert body is not None
    assert "ong" in body.lower() or "campanie" in body.lower()


def test_parse_ajut_request_despre_ajut_cum_pot() -> None:
    query = "Despre ajut cum pot: vreau să notăm că avem nevoie de 2 voluntari la eveniment."
    body = parse_ajut_request(query)
    assert body is not None
    assert "voluntar" in body.lower() or "eveniment" in body.lower()


def test_parse_ajut_request_pune_in_acp() -> None:
    query = "Pune în ACP: partener nou Fundația X, follow-up săptămâna viitoare."
    body = parse_ajut_request(query)
    assert body is not None
    assert "partener" in body.lower() or "funda" in body.lower()


def test_parse_ajut_request_notesc_legat_de() -> None:
    query = (
        "Legat de ajut cum pot, notesc că trebuie să trimitem raportul de sponsorizări până vineri."
    )
    body = parse_ajut_request(query)
    assert body is not None
    assert "raport" in body.lower() or "sponsor" in body.lower()


def test_parse_ajut_request_acp_direct() -> None:
    query = "ACP, am discutat cu Maria despre bugetul pentru Q3."
    body = parse_ajut_request(query)
    assert body is not None
    assert "buget" in body.lower() or "maria" in body.lower()


def test_extract_ajut_title_summary() -> None:
    body = (
        "trebuie să-i spunem lui Sorin să trimită datele de facturare către Alex, "
        "pentru că am cumpărat telefonul și cu laptopul"
    )
    title = extract_ajut_title(body)
    assert "sorin" in title.lower()
    assert "alex" in title.lower()
    assert "factur" in title.lower()
    assert "→" in title


def test_parse_ajut_request_voice_pause_in_phrase() -> None:
    query = (
        "Salut. Uite, tot legat de ajut, cum pot, trebuie să-i spunem Alexandrei să creeze "
        "un post plan pentru social media, pentru că mi se pare că acum nu facem suficient "
        "în social media și Alexandra s-a oferit să ajute strict pe asta."
    )
    body = parse_ajut_request(query)
    assert body is not None
    assert "alexandr" in body.lower()
    assert "social" in body.lower() or "post" in body.lower()


def test_normalize_ajut_query_collapses_pauses() -> None:
    from src.bot.ajut_intent import normalize_ajut_query

    assert "ajut cum pot" in normalize_ajut_query("tot legat de ajut, cum pot,").lower()


def test_no_ajut_intent_for_list_query() -> None:
    assert parse_ajut_request("ce am în ajut cum pot") is None
    assert parse_ajut_request("listează partenerii ACP") is None


def test_no_ajut_intent_without_signal() -> None:
    assert parse_ajut_request("ce am în calendar azi") is None