"""Tests for Discord voice message detection and transcription."""

from unittest.mock import MagicMock, patch

import pytest

from src.bot.voice_message import get_voice_attachment
from src.integrations.voice_transcription import VoiceTranscriptionService


def _attachment(
    *,
    duration: float | None = None,
    content_type: str | None = None,
    filename: str = "file.bin",
) -> MagicMock:
    att = MagicMock()
    att.duration = duration
    att.content_type = content_type
    att.filename = filename
    return att


def test_get_voice_attachment_by_duration() -> None:
    message = MagicMock()
    message.attachments = [_attachment(duration=4.5, filename="voice-message.ogg")]
    assert get_voice_attachment(message) is message.attachments[0]


def test_get_voice_attachment_by_filename() -> None:
    message = MagicMock()
    message.attachments = [
        _attachment(content_type="audio/ogg", filename="voice-message.ogg")
    ]
    assert get_voice_attachment(message) is message.attachments[0]


def test_get_voice_attachment_ignores_regular_audio() -> None:
    message = MagicMock()
    message.attachments = [_attachment(content_type="audio/mpeg", filename="song.mp3")]
    assert get_voice_attachment(message) is None


def test_get_voice_attachment_no_attachments() -> None:
    message = MagicMock()
    message.attachments = []
    assert get_voice_attachment(message) is None


@patch("src.integrations.voice_transcription.OpenAI")
def test_transcribe_returns_text(mock_openai_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.audio.transcriptions.create.return_value = MagicMock(
        text="  ce taskuri am azi  "
    )

    with patch("src.integrations.voice_transcription.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test"
        mock_settings.discord_voice_model = "whisper-1"
        mock_settings.discord_voice_language = "ro"
        result = VoiceTranscriptionService().transcribe(b"audio", "voice.ogg")

    assert result == "ce taskuri am azi"
    mock_client.audio.transcriptions.create.assert_called_once()
    call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
    assert call_kwargs["model"] == "whisper-1"
    assert call_kwargs["language"] == "ro"


def test_transcribe_requires_api_key() -> None:
    with patch("src.integrations.voice_transcription.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            VoiceTranscriptionService().transcribe(b"audio")