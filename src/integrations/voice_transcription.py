"""Transcribe audio using OpenAI Whisper."""

from __future__ import annotations

from io import BytesIO

from openai import OpenAI

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VoiceTranscriptionService:
    def transcribe(self, audio_bytes: bytes, filename: str = "voice-message.ogg") -> str:
        if not audio_bytes:
            raise ValueError("Fișierul audio e gol.")

        api_key = settings.openai_api_key.strip()
        if not api_key or "your_" in api_key:
            raise RuntimeError(
                "OPENAI_API_KEY nu e configurat — necesar pentru transcrierea mesajelor vocale."
            )

        client = OpenAI(api_key=api_key)
        kwargs: dict = {
            "model": settings.discord_voice_model,
            "file": (filename, BytesIO(audio_bytes)),
        }
        language = settings.discord_voice_language.strip()
        if language:
            kwargs["language"] = language

        response = client.audio.transcriptions.create(**kwargs)
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError(
                "Transcrierea e goală — încearcă din nou sau vorbește mai clar."
            )

        logger.info("voice_transcription_completed", chars=len(text))
        return text