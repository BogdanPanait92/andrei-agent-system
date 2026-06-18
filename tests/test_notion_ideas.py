"""Tests for Notion idea suggestion helpers."""

from src.integrations.notion import NotionClient


def test_infer_idea_category_acp() -> None:
    assert NotionClient.infer_idea_category("podcast cu voluntarii ACP") == "ACP"


def test_infer_idea_category_video() -> None:
    assert NotionClient.infer_idea_category("un vlog despre parenting") == "Video"


def test_infer_idea_category_content() -> None:
    assert NotionClient.infer_idea_category("postare pe blog despre productivitate") == "content creation"


def test_extract_idea_title_truncates() -> None:
    long = "curs online despre parenting și echilibru muncă-familie pentru părinți ocupați " * 3
    title = NotionClient.extract_idea_title(long)
    assert len(title) <= 80


def test_extract_plan_summary_skips_heading() -> None:
    plan = "1. **Rezumat** — Un curs scurt pentru părinți.\n2. Pași..."
    assert "curs" in NotionClient.extract_plan_summary(plan).lower()


def test_normalize_idea_status_draft() -> None:
    assert NotionClient.normalize_idea_status("draft") == "Draft"
    assert NotionClient.normalize_idea_status("In lucru") == "In lucru"


def test_normalize_idea_status_invalid() -> None:
    assert NotionClient.normalize_idea_status("bogus") is None