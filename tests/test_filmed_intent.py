"""Tests for filmed location → Posting Plan intent."""

from src.bot.filmed_intent import parse_filmed_location


def test_am_filmat_la_simple() -> None:
    req = parse_filmed_location("am filmat la Caru cu Bere")
    assert req is not None
    assert req.location == "Caru cu Bere"
    assert req.due_date is None


def test_am_filmat_with_iso_due_date() -> None:
    req = parse_filmed_location("am filmat la Momo, due date 2026-06-25")
    assert req is not None
    assert req.location == "Momo"
    assert req.due_date == "2026-06-25"


def test_am_filmat_with_romanian_date() -> None:
    req = parse_filmed_location("am filmat la Frescoloco pe 25 iunie")
    assert req is not None
    assert req.location == "Frescoloco"
    assert req.due_date == "2026-06-25"


def test_am_filmat_in_oras_la_restaurant() -> None:
    req = parse_filmed_location(
        "Salut! Vreau să-mi adaug un restaurant nou. "
        "Am filmat în București, la restaurantul CioCioCio."
    )
    assert req is not None
    assert req.location == "CioCioCio"
    assert req.oras == "București"
    assert req.due_date is None


def test_am_filmat_in_oras_la_restaurant_fara_virgula() -> None:
    req = parse_filmed_location("am filmat în Cluj la restaurantul Frescoloco")
    assert req is not None
    assert req.location == "Frescoloco"
    assert req.oras == "Cluj"


def test_am_filmat_in_oras_restaurant_nou_nimit() -> None:
    req = parse_filmed_location(
        "Salut! Am filmat în București un nou restaurant numit CioCioCio."
    )
    assert req is not None
    assert req.location == "CioCioCio"
    assert req.oras == "București"
    assert req.due_date is None


def test_no_filmed_intent() -> None:
    assert parse_filmed_location("ce am in posting plan") is None