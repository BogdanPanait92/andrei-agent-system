"""Tests for Content Creation briefing state logic."""

from src.integrations.content_briefing import ContentBriefingService


def test_finalize_only_reports_newly_done(monkeypatch) -> None:
    service = ContentBriefingService()

    monkeypatch.setattr(
        service,
        "get_newly_done_rows",
        lambda: [{"Titlu": "Restaurant Frescoloco", "Oras": "București", "Prioritate": "p1"}],
    )
    monkeypatch.setattr(
        service,
        "get_current_done_titles",
        lambda: {"Restaurant Frescoloco", "Old Done Item"},
    )
    monkeypatch.setattr(service, "_get_seen_titles", lambda: set())

    section = service.build_section()
    assert "Restaurant Frescoloco" in section
    service.finalize(reported_titles=["Restaurant Frescoloco"])

    state = service._load_state()
    assert state["seen_done_titles"] == ["Restaurant Frescoloco"]


def test_incomplete_rows_missing_oras_or_prioritate(monkeypatch) -> None:
    service = ContentBriefingService()
    rows = [
        {"Titlu": "Momo", "Oras": "", "Prioritate": "p1", "Status": "Planned"},
        {"Titlu": "Picnic", "Oras": "Cluj", "Prioritate": "", "Status": "Planned"},
        {"Titlu": "Done", "Oras": "", "Prioritate": "", "Status": "Posted"},
    ]
    monkeypatch.setattr(service, "_get_rows", lambda: rows)

    incomplete = service.get_incomplete_rows()
    titles = {row["Titlu"] for row in incomplete}
    assert titles == {"Momo", "Picnic"}
    momo = next(row for row in incomplete if row["Titlu"] == "Momo")
    assert "oraș" in momo["_missing"]
    picnic = next(row for row in incomplete if row["Titlu"] == "Picnic")
    assert "prioritate" in picnic["_missing"]