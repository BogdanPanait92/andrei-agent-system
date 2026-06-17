"""Shared notification formatting for Telegram and WhatsApp."""

import re


def strip_markdown(text: str) -> str:
    """Convert basic Markdown to plain text (for WhatsApp)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


class NotifierMixin:
    """Common high-level notification methods."""

    def send_daily_briefing(self, briefing: str) -> bool:
        header = "🌅 Daily Briefing - Andrei\n\n"
        return self.send_message(header + briefing)

    def send_weekly_review(self, review: str) -> bool:
        header = "📊 Weekly Review - Duminică\n\n"
        return self.send_message(header + review)

    def send_alert(self, alert_type: str, message: str) -> bool:
        icons = {
            "deadline": "⏰",
            "family": "👨‍👩‍👧",
            "burnout": "🔥",
            "content": "🎬",
            "ajut_cum_pot": "💚",
            "balance": "⚖️",
        }
        icon = icons.get(alert_type, "🔔")
        label = alert_type.replace("_", " ").title()
        text = f"{icon} Alertă {label}\n\n{message}"
        return self.send_message(text)

    def send_reminder(self, title: str, details: str) -> bool:
        text = f"📌 Reminder: {title}\n\n{details}"
        return self.send_message(text)

    @staticmethod
    def split_message(text: str, max_len: int = 4000) -> list[str]:
        if len(text) <= max_len:
            return [text]
        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break
            split_at = text.rfind("\n", 0, max_len)
            if split_at == -1:
                split_at = max_len
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()
        return chunks