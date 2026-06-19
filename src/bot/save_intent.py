"""Detect requests to save the previous Discord exchange to Notion."""

from __future__ import annotations

import re

_SAVE_TO_IDEI_RE = re.compile(
    r"(?:"
    r"(?:adaug[aă]|noteaz[aă]|salveaz[aă]|pune|pui)"
    r"(?:-[oml]|ă|-mi)?"
    r"\s+"
    r"(?:o\s+)?"
    r"(?:in|în|la)\s+"
    r"(?:notion\s+)?idei"
    r"|s-o\s+pui(?:\s+tu)?\s+(?:in|în)\s+idei"
    r"|pune(?:-l|-o|-mi)?\s+(?:in|în|la)\s+idei"
    r")",
    flags=re.IGNORECASE,
)

_SAVE_TAIL_RE = re.compile(
    r"(?:[.,;]?\s*)"
    r"(?:"
    r"(?:și|si|apoi|plus)\s+"
    r"(?:"
    r"(?:noteaz[aă]|adaug[aă]|salveaz[aă]|pune)(?:-[oml]|ă|-mi)?\s+(?:la|in|în)\s+idei"
    r"|fa\s+tot\s+ce\s+trebuie(?:\s+s[aă]\s+faci)?"
    r")"
    r".*)$",
    flags=re.IGNORECASE,
)

_SAVE_PATTERNS = (
    r"\bsalveaz[aă]\b.*\b(notion|asta|o|ideea)\b",
    r"\bsalveaz[aă]\b.*\b(in|în)\s+notion\b",
    r"\bda\b.*\bsalveaz",
    r"\byes\b.*\bsave\b.*\bnotion\b",
    r"\bsave\b.*\b(notio|notion)\b",
    r"\badaug[aă]\b.*\b(notion|idei)\b",
    r"\bnoteaz[aă]\b.*\b(notion|idei)\b",
)


def has_save_to_ideas_signal(query: str) -> bool:
    """True when the message asks to save/add to Notion Ideas (anywhere in the sentence)."""
    return bool(_SAVE_TO_IDEI_RE.search(query.strip()))


def strip_save_to_ideas_tail(query: str) -> str:
    """Remove trailing save-to-ideas instructions and filler from a message."""
    text = query.strip()
    text = _SAVE_TAIL_RE.sub("", text).strip()
    match = _SAVE_TO_IDEI_RE.search(text)
    if match and match.start() > 0:
        text = text[: match.start()].strip(" .,!?:;")
    return text

_REFERENCE_PHRASES = (
    "raspunsul tau",
    "raspunsul tău",
    "raspunsul de mai sus",
    "de mai sus",
    "ce ai zis",
    "ce ziceai",
    "din conversatie",
    "din conversație",
    "mesajul anterior",
    "ultimul raspuns",
    "ultimul răspuns",
    "recomandarea ta",
    "recomandarile tale",
    "recomandările tale",
    "ce mi-ai dat",
    "ce mi ai dat",
    "despre ce am vorbit",
    "legat de",
    "referitor la",
)

_STRIP_SAVE_PREFIX = re.compile(
    r"^(?:da[,.]?\s*)?"
    r"(?:salveaz[aă]|adaug[aă]|noteaz[aă])\s+"
    r"(?:asta\s+)?(?:in|în|la)\s+"
    r"(?:notion\s+)?(?:idei|ideas?)\s*"
    r"(?:raspunsul(?:\s+tau|\s+tău)?(?:\s+de\s+mai\s+sus)?\s*)?"
    r"[,.:]*\s*",
    flags=re.IGNORECASE,
)

_HINT_PATTERNS = (
    re.compile(r"legat de\s+(.+)$", flags=re.IGNORECASE),
    re.compile(r"referitor la\s+(.+)$", flags=re.IGNORECASE),
    re.compile(
        r"raspunsul(?:\s+tau|\s+tău)?(?:\s+de\s+mai\s+sus)?\s+(?:legat de\s+)?(.+)$",
        flags=re.IGNORECASE,
    ),
    re.compile(r"despre\s+(.+)$", flags=re.IGNORECASE),
)


def is_save_to_notion_request(query: str) -> bool:
    lowered = query.strip().lower()
    if not lowered:
        return False
    if any(lowered.startswith(p) for p in ("idee:", "idea:")):
        return False
    return any(re.search(pattern, lowered) for pattern in _SAVE_PATTERNS)


def is_save_previous_exchange_request(query: str) -> bool:
    """True when the user wants the prior bot reply saved, not a new idea in the message."""
    if not is_save_to_notion_request(query):
        return False

    lowered = query.strip().lower()
    if any(ref in lowered for ref in _REFERENCE_PHRASES):
        return True

    remainder = _STRIP_SAVE_PREFIX.sub("", lowered).strip(" .,!?:;")
    if not remainder:
        return True
    if len(remainder) < 12 and any(ref in remainder for ref in _REFERENCE_PHRASES):
        return True
    return False


def parse_save_ideas_hint(query: str) -> str | None:
    """Extract a short topic hint from a save-previous command for the Notion title."""
    text = query.strip()
    if not text:
        return None
    for pattern in _HINT_PATTERNS:
        match = pattern.search(text)
        if match:
            hint = match.group(1).strip(" .,!?:;")
            if hint and not is_save_to_notion_request(hint):
                return hint
    return None