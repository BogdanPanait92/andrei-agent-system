"""Tests for Notion Posting Plan helpers."""

from src.integrations.notion import NotionClient


def test_is_posting_done() -> None:
    assert NotionClient.is_posting_done("Posted")
    assert NotionClient.is_posting_done("postat")
    assert not NotionClient.is_posting_done("Planned")


def test_posting_plan_record() -> None:
    page = {
        "properties": {
            "Nume": {"title": [{"plain_text": "Clip test"}]},
            "Oras": {"rich_text": [{"plain_text": "București"}]},
            "Prioritate": {"select": {"name": "p2"}},
            "Status": {"select": {"name": "Planned"}},
        }
    }
    rec = NotionClient.posting_plan_record(page)
    assert rec["Titlu"] == "Clip test"
    assert rec["Oras"] == "București"
    assert rec["Prioritate"] == "p2"
    assert rec["Status"] == "Planned"


def test_normalize_posting_priority() -> None:
    assert NotionClient.normalize_posting_priority("p1") == "p1"
    assert NotionClient.normalize_posting_priority("P2") == "p2"
    assert NotionClient.normalize_posting_priority("high") is None


def test_extract_title_supports_nume() -> None:
    page = {"properties": {"Nume": {"title": [{"plain_text": "Momo"}]}}}
    assert NotionClient.extract_title(page) == "Momo"