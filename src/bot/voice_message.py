"""Discord voice message detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord


def get_voice_attachment(message: discord.Message) -> discord.Attachment | None:
    """Return the first voice-note attachment on a message, if any."""
    for attachment in message.attachments:
        if attachment.duration is not None:
            return attachment
        content_type = (attachment.content_type or "").lower()
        filename = (attachment.filename or "").lower()
        if content_type.startswith("audio/") and "voice" in filename:
            return attachment
    return None