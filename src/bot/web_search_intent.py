"""Detect explicit user requests for web search."""

from __future__ import annotations

import re

_PREFIXES = (
    "caută:",
    "cauta:",
    "caută pe net:",
    "cauta pe net:",
    "caută pe internet:",
    "cauta pe internet:",
    "search:",
    "search web:",
    "web:",
)

_INLINE_PREFIXES = (
    "caută pe net ",
    "cauta pe net ",
    "caută pe internet ",
    "cauta pe internet ",
    "verifică pe internet ",
    "verifica pe internet ",
    "search online ",
    "search pe net ",
)

_FLEXIBLE_PATTERNS = (
    r"(?:vreau\s+(?:s[aă]\s+)?(?:cau[tț][iă]?\s+)?(?:pe\s+)?(?:net|internet)\s+despre)\s+(.+)$",
    r"(?:po[tț]i\s+(?:s[aă]\s+)?cau[tț][aă]\s+pe\s+net\s+despre)\s+(.+)$",
    r"(?:fa[ce]?\s+(?:o\s+)?cautare\s+(?:pe\s+)?(?:net|web)\s+despre)\s+(.+)$",
    r"(?:caut[aă]\s+pe\s+net\s+despre)\s+(.+)$",
    r"^caut[aă][,:]\s*(.+)$",
    r"^search[,:]\s*(.+)$",
)


def _extract_flexible_body(query: str) -> str | None:
    text = query.strip()
    for pattern in _FLEXIBLE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            body = match.group(1).strip(" .,!?:;")
            if body:
                return body
    return None


def parse_web_search_query(query: str) -> str | None:
    """
    Return the search query when the user explicitly asked for web search.
    Return None otherwise (no implicit search).
    """
    text = query.strip()
    if not text:
        return None

    lowered = text.lower()
    for prefix in _PREFIXES:
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip() or None

    for prefix in _INLINE_PREFIXES:
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip() or None

    flexible = _extract_flexible_body(text)
    if flexible:
        return flexible

    return None