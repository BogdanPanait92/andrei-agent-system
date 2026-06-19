"""Detect requests to save a note in Notion Ajut Cum Pot."""

from __future__ import annotations

import re

_ACP = r"(?:ajut\s+cum\s+pot|\bacp\b)"

# Voice transcription often inserts pauses: "ajut, cum pot" / "ajut cum, pot"
_AJUT_FRAGMENTED_RE = re.compile(
    r"ajut\s*[,.]?\s*cum\s*[,.]?\s*pot",
    flags=re.IGNORECASE,
)

_AJUT_PREFIX_STARTS = (
    "tot legat de ajut cum pot",
    "legat de ajut cum pot",
    "tot pentru ajut cum pot",
    "pentru ajut cum pot",
    "tot pe ajut cum pot",
    "tot despre ajut cum pot",
    "despre ajut cum pot",
    "tot legat de acp",
    "legat de acp",
    "tot pentru acp",
    "pentru acp",
    "tot pe acp",
    "tot despre acp",
    "despre acp",
    "ajut cum pot,",
    "ajut cum pot:",
    "acp,",
    "acp:",
)

_AJUT_INLINE_SIGNALS = (
    "tabul ajut cum pot",
    "în ajut cum pot",
    "in ajut cum pot",
    "la ajut cum pot",
    "notion ajut cum pot",
    "în acp",
    "in acp",
    "la acp",
    "tabul acp",
)

_BODY_PATTERNS = (
    rf"^(?:salut[,!]?\s*)?(?:uite,?\s*)?(?:tot\s+)?(?:legat\s+de|pentru|pe|despre)\s+{_ACP},?\s*(.+)$",
    rf"^(?:tot\s+)?despre\s+{_ACP},?\s*(.+)$",
    rf"^(?:tot\s+)?(?:pentru|pe)\s+{_ACP},?\s*(.+)$",
    rf"(?:tot\s+)?legat\s+de\s+{_ACP},?\s*(?:a[sș]\s+vrea\s+s[aă]\s+)?"
    r"(?:notesc|notez|salvez|salveaz[aă]|noteaz[aă])\s+(?:chestia\s+asta,?\s*)?(?:c[aă]\s+)?(.+)$",
    rf"(?:a[sș]\s+vrea\s+s[aă]\s+)(?:pui|pun|adaug[aă]|salvez|salveaz[aă]|notez|noteaz[aă])\s+"
    rf"(?:o\s+)?(?:chestie\s+)?(?:în|in|la)\s+(?:tabul\s+)?{_ACP}[\.:,]?\s*(.+)$",
    rf"(?:pune|pui|adaug[aă]|salveaz[aă]|noteaz[aă])\s+(?:o\s+)?(?:chestie\s+)?"
    rf"(?:în|in|la)\s+(?:tabul\s+)?{_ACP}[\.:,]?\s*(.+)$",
    rf"(?:not[aă]\s+(?:în|in|la|pentru)\s+(?:tabul\s+)?{_ACP}[\.:,]?\s*)(.+)$",
    rf"(?:legat\s+de\s+{_ACP}[\.:,]?\s*)(.+)$",
    rf"^(?:salut[,!]?\s*)?(?:uite,?\s*)?{_ACP},?\s*(.+)$",
)

_READ_QUERY_RE = re.compile(
    r"^(?:ce\s+am|ce\s+avem|ce\s+e|ce\s+este|care\s+sunt|"
    r"arat[aă]|listeaz[aă]|list[aă]|spune[\s-]mi|show|zi[\s-]mi)\b",
    flags=re.IGNORECASE,
)

_NOTE_CONTEXT_RE = re.compile(
    rf"(?:tot\s+)?(?:legat\s+de|pentru|pe|despre)\s+{_ACP}\b|"
    rf"(?:în|in|la)\s+(?:tabul\s+)?{_ACP}\b|"
    rf"tabul\s+{_ACP}\b|"
    rf"(?:pune|pui|adaug|salvez|salveaz|notez|noteaz|notesc)\s+.*?\b{_ACP}\b|"
    rf"^\s*(?:salut[,!]?\s*)?(?:uite,?\s*)?{_ACP}\s*[,.:]",
    flags=re.IGNORECASE,
)

_ACP_MENTION_RE = re.compile(_ACP, flags=re.IGNORECASE)

_BODY_PREFIXES = (
    "salut!",
    "salut,",
    "uite,",
    "uite ",
    "deci,",
    "deci ",
    "ok,",
    "ok ",
)

_TITLE_PREFIXES = (
    "trebuie să-i spunem lui",
    "trebuie sa-i spunem lui",
    "trebuie să-i spunem",
    "trebuie sa-i spunem",
    "trebuie să-i spun lui",
    "trebuie sa-i spun lui",
    "trebuie să",
    "trebuie sa",
    "asta este pentru",
    "asta e pentru",
    "ideea e că",
    "ideea e ca",
    "ar fi bine să",
    "ar fi bine sa",
    "că ",
    "ca ",
)

_MEANINGFUL_HINTS = (
    "sorin",
    "alex",
    "alexandr",
    "social",
    "post",
    "plan",
    "factur",
    "telefon",
    "laptop",
    "partener",
    "voluntar",
    "voluntari",
    "ong",
    "funda",
    "trimite",
    "spun",
    "cumpărat",
    "cumparat",
    "buget",
    "proiect",
    "eveniment",
    "donat",
    "sponsor",
    "campanie",
    "ajut",
    "acp",
)


def normalize_ajut_query(text: str) -> str:
    """Collapse voice-pause variants of 'ajut cum pot' into one phrase."""
    return _AJUT_FRAGMENTED_RE.sub("ajut cum pot", text)


def _is_read_query(text: str) -> bool:
    return bool(_READ_QUERY_RE.match(text.strip()))


def _has_ajut_signal(text: str) -> bool:
    lowered = text.lower().strip()
    if not _ACP_MENTION_RE.search(lowered):
        return False
    if _is_read_query(lowered):
        return False
    if lowered.startswith(_AJUT_PREFIX_STARTS):
        return True
    if _NOTE_CONTEXT_RE.search(text):
        return True
    return any(signal in lowered for signal in _AJUT_INLINE_SIGNALS)


def _extract_body(query: str) -> str:
    text = query.strip()
    for pattern in _BODY_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            body = match.group(1).strip(" .,!?:;")
            if body:
                return body
    if _NOTE_CONTEXT_RE.search(text):
        cleaned = _ACP_MENTION_RE.sub("", text, count=1)
        for prefix in (
            "tot legat de",
            "legat de",
            "tot pentru",
            "pentru",
            "tot pe",
            "tot despre",
            "despre",
            "tabul",
            "în",
            "in",
            "la",
        ):
            cleaned = re.sub(rf"^{re.escape(prefix)}\s*", "", cleaned.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.strip(" ,.:;")
        if cleaned:
            return cleaned
    return text


def _strip_body_prefixes(text: str) -> str:
    result = text.strip()
    while True:
        lowered = result.lower()
        stripped = False
        for prefix in _BODY_PREFIXES:
            if lowered.startswith(prefix):
                result = result[len(prefix) :].strip()
                stripped = True
                break
        if not stripped:
            break
    return result


def extract_ajut_title(content: str, max_len: int = 80) -> str:
    text = _strip_body_prefixes(" ".join(content.strip().split()))
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

    billing = re.search(
        r"(?:lui\s+)?(\w+)\s+s[aă]\s+.+?(?:datele?\s+de\s+)?factur\w*.*?(?:către|catre|la)\s+(\w+)",
        text,
        flags=re.IGNORECASE,
    )
    if billing:
        return (
            f"{billing.group(1).capitalize()} → {billing.group(2).capitalize()}: date facturare"
        )[:max_len]

    social_plan = re.search(
        r"(?:lui\s+)?(\w+)\s+s[aă]\s+(.+?(?:post|social|plan).+?)(?:,|\.|;|$|\s+pentru\s+c[aă]\b)",
        text,
        flags=re.IGNORECASE,
    )
    if social_plan:
        person = social_plan.group(1).strip().capitalize()
        action = social_plan.group(2).strip(" .,;")
        title = f"{person}: {action}"
        if len(title) <= max_len:
            return title
        cut = title[:max_len].rsplit(" ", 1)[0]
        return cut or title[:max_len]

    person_action = re.search(
        r"(?:lui\s+)?(\w+)\s+s[aă]\s+(.+?)(?:,|\.|;|$|\s+pentru\s+c[aă]\b)",
        text,
        flags=re.IGNORECASE,
    )
    if person_action:
        person = person_action.group(1).strip().capitalize()
        action = person_action.group(2).strip(" .,;")
        title = f"{person}: {action}"
        if len(title) <= max_len:
            return title
        cut = title[:max_len].rsplit(" ", 1)[0]
        return cut or title[:max_len]

    for sep in (".", ";"):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    if " pentru că " in text.lower():
        text = re.split(r"\s+pentru\s+c[aă]\s+", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    if " și " in text.lower():
        text = re.split(r"\s+și\s+", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()

    if not text:
        return "Notă Ajut Cum Pot"
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(" ", 1)[0]
    return cut or text[:max_len]


def parse_ajut_request(query: str) -> str | None:
    """Return Ajut Cum Pot note body when user wants to save. None otherwise."""
    text = normalize_ajut_query(query.strip())
    if not text or not _has_ajut_signal(text):
        return None

    body = _extract_body(text)
    if not body:
        return None

    body = _strip_body_prefixes(body)
    lowered = body.lower()
    if lowered in _AJUT_INLINE_SIGNALS:
        return None
    if body.lower() == text.lower() and not any(hint in lowered for hint in _MEANINGFUL_HINTS):
        return None

    return body