"""Detect requests to generate voice-over for existing Notion ideas."""

from __future__ import annotations

import re

_PREFIXES = (
    "voiceover:",
    "voice-over:",
    "voice over:",
)

_PATTERNS = (
    r"(?:genereaz[aă]|fa[c]?|fă|ruleaz[aă])\s+voice[- ]?over\s+(?:pentru|pe)\s+(?:ideea\s+)?(.+)$",
    r"voice[- ]?over\s+(?:pentru|pe)\s+(?:ideea\s+)?(.+)$",
    r"(?:ruleaz[aă]|ruleaza)\s+voice[- ]?over\s+pe\s+(.+)$",
)

_STATUS_PREFIX_RE = re.compile(
    r"^(?:(draft|ciorn[aă]?|evaluare|lucru|arhivat)\s*:\s*)(.+)$",
    flags=re.IGNORECASE,
)


def _strip_status_prefix(ref: str) -> tuple[str | None, str]:
    match = _STATUS_PREFIX_RE.match(ref.strip())
    if not match:
        return None, ref.strip()
    status_key = match.group(1).lower()
    body = match.group(2).strip()
    status_map = {
        "draft": "Draft",
        "ciorna": "Draft",
        "ciornă": "Draft",
        "evaluare": "In evaluare",
        "lucru": "In lucru",
        "arhivat": "Arhivat",
    }
    return status_map.get(status_key, None), body


def parse_voiceover_request(query: str) -> tuple[str, str | None] | None:
    """
    Return (idea_reference, optional_status_filter) when user wants voice-over
    on an existing Notion idea. Return None otherwise.
    """
    text = query.strip()
    if not text:
        return None

    lowered = text.lower()
    for prefix in _PREFIXES:
        if lowered.startswith(prefix):
            ref = text[len(prefix) :].strip()
            if ref:
                status, body = _strip_status_prefix(ref)
                return body, status
            return None

    for pattern in _PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            ref = match.group(1).strip(" .,!?:;")
            if ref:
                status, body = _strip_status_prefix(ref)
                return body, status

    return None