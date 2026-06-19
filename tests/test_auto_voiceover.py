"""Tests for auto voice-over batch logic."""

from unittest.mock import MagicMock, patch

from src.integrations.idea_voiceover import IdeaVoiceoverService


def test_ideas_missing_voiceover_skips_existing() -> None:
    service = IdeaVoiceoverService()
    service._notion = MagicMock()
    service._notion.get_ideas.return_value = [
        {"id": "a", "properties": {}},
        {"id": "b", "properties": {}},
    ]
    service._notion.idea_has_voiceover.side_effect = lambda page_id: page_id == "a"
    service._notion.extract_title.side_effect = lambda idea: idea["id"]

    missing = service.ideas_missing_voiceover(statuses=["Draft"])

    assert len(missing) == 1
    assert missing[0]["id"] == "b"


def test_run_auto_batch_respects_limit() -> None:
    service = IdeaVoiceoverService()
    service._notion = MagicMock()
    service.ideas_missing_voiceover = MagicMock(
        return_value=[{"id": "1"}, {"id": "2"}, {"id": "3"}]
    )
    service._notion.extract_title.side_effect = lambda idea: f"idea-{idea['id']}"
    service.run_for_idea = MagicMock(return_value="script output")

    with patch("src.integrations.idea_voiceover.settings") as mock_settings:
        mock_settings.auto_voiceover_max_per_run = 2
        result = service.run_auto_batch()

    assert result["processed"] == ["idea-1", "idea-2"]
    assert service.run_for_idea.call_count == 2