"""Detect requests to save the previous Discord exchange to Notion."""

from __future__ import annotations

import re

_SAVE_PATTERNS = (
    r"\bsalveaz[aă]\b.*\b(notion|asta|asta|o|ideea)\b",
    r"\bsalveaz[aă]\b.*\b(in|în)\s+notion\b",
    r"\bda\b.*\bsalveaz",
    r"\byes\b.*\bsave\b.*\bnotion\b",
    r"\bsave\b.*\b(notio|notion)\b",
    r"\badaug[aă]\b.*\b(notion|idei)\b",
    r"\bnoteaz[aă]\b.*\bnotion\b",
)


def is_save_to_notion_request(query: str) -> bool:
    lowered = query.strip().lower()
    if not lowered:
        return False
    if any(lowered.startswith(p) for p in ("idee:", "idea:")):
        return False
    return any(re.search(pattern, lowered) for pattern in _SAVE_PATTERNS)