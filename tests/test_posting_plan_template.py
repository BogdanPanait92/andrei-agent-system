"""Tests for Posting Plan page body template."""

from src.integrations.notion import NotionClient
from src.integrations.posting_plan_template import POSTING_PLAN_STATEMENT_DEFAULT


def test_posting_plan_template_blocks_structure() -> None:
    blocks = NotionClient._posting_plan_template_blocks()
    types = [b["type"] for b in blocks]
    assert types[0] == "paragraph"
    assert "Statement:" in blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
    assert POSTING_PLAN_STATEMENT_DEFAULT in blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
    assert "divider" in types
    assert "to_do" in types
    todo = next(b for b in blocks if b["type"] == "to_do")
    assert todo["to_do"]["rich_text"][0]["text"]["content"] == "Trial reels"
    assert todo["to_do"]["checked"] is False
    paragraph_text = "".join(
        b["paragraph"]["rich_text"][0]["text"]["content"]
        for b in blocks
        if b["type"] == "paragraph"
    )
    assert "prețuri:" in paragraph_text
    assert "locație:" in paragraph_text