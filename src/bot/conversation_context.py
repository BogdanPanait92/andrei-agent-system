"""Short-lived per-channel conversation memory for Discord follow-ups."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import time


@dataclass(frozen=True)
class Exchange:
    user: str
    assistant: str
    created_at: float


class ConversationContext:
    def __init__(self, max_exchanges: int = 6) -> None:
        self._max = max_exchanges
        self._channels: dict[int, deque[Exchange]] = defaultdict(
            lambda: deque(maxlen=self._max)
        )

    def add(self, channel_id: int, user: str, assistant: str) -> None:
        user_text = user.strip()
        assistant_text = assistant.strip()
        if not user_text or not assistant_text:
            return
        self._channels[channel_id].append(
            Exchange(user=user_text, assistant=assistant_text, created_at=time())
        )

    def get_last(self, channel_id: int) -> Exchange | None:
        items = self._channels.get(channel_id)
        if not items:
            return None
        return items[-1]

    @staticmethod
    def is_meta_exchange(exchange: Exchange) -> bool:
        from src.bot.save_intent import is_save_to_notion_request

        if is_save_to_notion_request(exchange.user):
            return True
        assistant = exchange.assistant.strip()
        return assistant.startswith("✅ **Salvat") or assistant.startswith("✅ Salvat")

    def get_last_substantive(self, channel_id: int) -> Exchange | None:
        items = self._channels.get(channel_id)
        if not items:
            return None
        for exchange in reversed(items):
            if not self.is_meta_exchange(exchange):
                return exchange
        return None

    def format_for_prompt(self, channel_id: int, limit: int = 3) -> str:
        items = list(self._channels.get(channel_id, []))[-limit:]
        if not items:
            return ""
        lines = ["--- Conversație recentă în acest canal ---"]
        for ex in items:
            lines.append(f"Andrei: {ex.user}")
            lines.append(f"Agent: {ex.assistant[:1500]}")
            lines.append("")
        return "\n".join(lines).strip()