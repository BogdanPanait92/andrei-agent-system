"""Tests for Notion plan block parsing."""

from src.integrations.notion import NotionClient


def test_plan_blocks_keep_numbered_steps_together() -> None:
    plan = """Rezumat — Ideea despre fluture.

Pași de implementare —
1. Notează 3-4 gânduri personale.
2. Alege un format scurt: Reel 30-45 sec.
3. Filmare simplă în natură.

Quick win — Azi, 15 minute."""
    blocks = NotionClient._plan_to_blocks(plan)
    headings = [
        b[b["type"]]["rich_text"][0]["plain_text"]
        for b in blocks
        if b["type"].startswith("heading")
    ]
    assert headings == ["Rezumat", "Pași de implementare", "Quick win"]
    paragraphs = [
        b["paragraph"]["rich_text"][0]["plain_text"]
        for b in blocks
        if b["type"] == "paragraph"
    ]
    assert any("Notează 3-4" in p for p in paragraphs)
    assert any("Alege un format scurt" in p for p in paragraphs)