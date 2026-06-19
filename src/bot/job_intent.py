"""Detect requests to save a note in Notion Job tab/database."""

from __future__ import annotations

import re

_JOB_PREFIX_STARTS = (
    "tot pentru job",
    "tot legat de job",
    "tot pe job",
)

_JOB_INLINE_SIGNALS = (
    "tabul job",
    "legat de job",
    "despre job",
    "în job",
    "in job",
    "la job",
    "notion job",
    "în notion job",
    "in notion job",
)

_BODY_PATTERNS = (
    r"^(?:tot\s+)?(?:pentru|pe)\s+job,?\s*(.+)$",
    r"(?:tot\s+)?legat\s+de\s+job,?\s*(?:a[sș]\s+vrea\s+s[aă]\s+)?"
    r"(?:notesc|notez|salvez|salveaz[aă]|noteaz[aă])\s+(?:chestia\s+asta,?\s*)?(?:c[aă]\s+)?(.+)$",
    r"(?:a[sș]\s+vrea\s+s[aă]\s+)(?:pui|pun|adaug[aă]|salvez|salveaz[aă]|notez|noteaz[aă])\s+"
    r"(?:o\s+)?(?:chestie\s+)?(?:în|in|la)\s+(?:tabul\s+)?job[\.:,]?\s*(.+)$",
    r"(?:pune|pui|adaug[aă]|salveaz[aă]|noteaz[aă])\s+(?:o\s+)?(?:chestie\s+)?"
    r"(?:în|in|la)\s+(?:tabul\s+)?job[\.:,]?\s*(.+)$",
    r"(?:not[aă]\s+(?:în|in|la)\s+(?:tabul\s+)?job[\.:,]?\s*)(.+)$",
    r"(?:legat\s+de\s+job[\.:,]?\s*)(.+)$",
)

_TITLE_PREFIXES = (
    "ideea e că",
    "ideea e ca",
    "ideea este că",
    "ideea este ca",
    "ar fi bine să-mi",
    "ar fi bine sa-mi",
    "ar fi bine să",
    "ar fi bine sa",
    "mi-a zis că",
    "mi-a zis ca",
    "cosmin mi-a zis că",
    "cosmin mi-a zis ca",
    "nota:",
    "notă:",
    "că ",
    "ca ",
)

_MEANINGFUL_HINTS = (
    "ideea",
    "septembrie",
    "birou",
    "job",
    "notă",
    "nota",
    "curs",
    "workday",
    "work day",
    "inteligen",
    "proiect",
    "task",
    "deadline",
    "client",
    "office",
    "cosmin",
    "document",
    "proces",
    "pagin",
    "pagina",
    "tehnic",
)


def _has_job_signal(text: str) -> bool:
    lowered = text.lower().strip()
    if lowered.startswith(_JOB_PREFIX_STARTS):
        return True
    if re.match(r"^pentru job[,:\s]", lowered):
        return True
    return any(signal in lowered for signal in _JOB_INLINE_SIGNALS)


def _extract_body(query: str) -> str:
    text = query.strip()
    for pattern in _BODY_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            body = match.group(1).strip(" .,!?:;")
            if body:
                return body
    return text


def extract_job_title(content: str, max_len: int = 80) -> str:
    text = " ".join(content.strip().split())
    while True:
        lowered = text.lower()
        stripped = False
        for prefix in _TITLE_PREFIXES:
            if lowered.startswith(prefix):
                text = text[len(prefix) :].strip()
                stripped = True
                break
        if not stripped:
            break
    for sep in (".", ";"):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    if " și " in text:
        text = text.split(" și ", 1)[0].strip()
    if not text:
        return "Notă Job"
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(" ", 1)[0]
    return cut or text[:max_len]


def parse_job_request(query: str) -> str | None:
    """
    Return job note body when user wants to save in Notion Job tab.
    Return None otherwise.
    """
    text = query.strip()
    if not text or not _has_job_signal(text):
        return None

    body = _extract_body(text)
    if not body:
        return None

    lowered = body.lower()
    if lowered in _JOB_INLINE_SIGNALS:
        return None
    if body.lower() == text.lower() and not any(hint in lowered for hint in _MEANINGFUL_HINTS):
        return None

    return body