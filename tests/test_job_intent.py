"""Tests for Job tab save intent."""

from src.bot.job_intent import extract_job_title, parse_job_request


def test_parse_job_request_tabul_job() -> None:
    query = (
        "Aș vrea să pui o chestie în tabul job. "
        "Ideea e că din septembrie cel mai probabil o să ne ducem la birou "
        "și vreau să iei asta în considerare."
    )
    body = parse_job_request(query)
    assert body is not None
    assert "septembrie" in body
    assert "birou" in body


def test_extract_job_title_strips_ideea_prefix() -> None:
    title = extract_job_title(
        "Ideea e că din septembrie cel mai probabil o să ne ducem la birou "
        "și vreau să iei asta în considerare."
    )
    assert "septembrie" in title.lower()
    assert "birou" in title.lower()
    assert "considerare" not in title.lower()


def test_parse_job_request_legat_de_job_notesc() -> None:
    query = (
        "Tot legat de job, aș vrea să notesc chestia asta, "
        "că ar fi bine să fac un curs pe Workday fix pe dezvoltarea inteligenței artificiale."
    )
    body = parse_job_request(query)
    assert body is not None
    assert "workday" in body.lower()
    assert "inteligen" in body.lower()


def test_extract_job_title_workday_curs() -> None:
    title = extract_job_title(
        "ar fi bine să fac un curs pe Workday fix pe dezvoltarea inteligenței artificiale."
    )
    assert "workday" in title.lower()
    assert "curs" in title.lower()


def test_parse_job_request_tot_pentru_job() -> None:
    query = (
        "Tot pentru job, Cosmin mi-a zis că ar fi bine să-mi creez o pagină strict "
        "pe documentarea proceselor tehnice."
    )
    body = parse_job_request(query)
    assert body is not None
    assert "cosmin" in body.lower()
    assert "document" in body.lower()
    assert "proces" in body.lower()


def test_no_job_intent_for_general_question() -> None:
    assert parse_job_request("ce am de făcut pentru job azi") is None


def test_no_job_intent_without_signal() -> None:
    assert parse_job_request("ce am în calendar azi") is None