"""Detect requests to add items in Notion Family & Administrative."""

from __future__ import annotations

import re

_FAMILY_PREFIX_STARTS = (
    "tot pentru familie",
    "tot legat de familie",
    "tot pe familie",
)

_FAMILY_INLINE_SIGNALS = (
    "family & administrative",
    "family and administrative",
    "familie si administrative",
    "familie și administrative",
    "familie si admin",
    "familie și admin",
    "chestii ce tin de familie",
    "chestii ce țin de familie",
    "tabul family",
    "tabul familie",
    "tabu familie",
    "in tabu familie",
    "în tabu familie",
    "în family",
    "in family",
    "la family",
    "notion family",
    "family administrative",
)

_BODY_PATTERNS = (
    r"((?:trebuie\s+un\s+nou\s+)(?:dosar|folder)\s+pentru\s+.+?)(?:\.|$)",
    r"(?:trebuie\s+s[aă]\s+)?adaug[aă]\s+o\s+nou[aă]\s+intrare\s+"
    r"(?:în|in|la)\s+.+?(?:familie|family)\s*(?:și|si|&)?\s*administrative[.,]?\s*(.+)$",
    r"(?:adaug[aă]|pune|not[aă])\s+(?:o\s+)?(?:intrare|dosar|not[aă])\s+"
    r"(?:în|in|la)\s+(?:tab(?:ul|u)\s+)?(?:family|familie|administrative)[.,]?\s*(.+)$",
    r"(.+?)\s+(?:și\s+)?pune\s+(?:asta\s+)?(?:în|in|la)\s+tab(?:ul|u)?\s*familie",
    r"(?:trebuie\s+s[aă]\s+)?(?:mi[-\s])?aduc\s+aminte\s+(.+?)(?:\s+(?:și\s+)?pune|\s*$)",
    r"(?:adaug[aă]|pune|not[aă])\s*:\s*(.+)$",
    r"(?:tot\s+)?(?:legat\s+de|pentru|pe)\s+(?:family|familie)(?:\s*&\s*administrative)?[,.]?\s*(.+)$",
    r"(?:legat\s+de\s+(?:family|familie)(?:\s*&\s*administrative)?[,.]?\s*)(.+)$",
)

_TITLE_PATTERNS = (
    r"nu\s+uita\s+c[aă]\s+în\s+(.+?)\s+e\s+ziua\s+(\w+)",
    r"în\s+(.+?)\s+e\s+ziua\s+(\w+)",
    r"nu\s+uita\s+c[aă]\s+(.+?)(?:\.|$)",
    r"trebuie\s+un\s+nou\s+dosar\s+pentru\s+(.+?)(?:\.|$)",
    r"(?:dosar|folder)\s+(?:nou\s+)?pentru\s+(.+?)(?:\.|$)",
    r"intrare\s+(?:nou[aă]\s+)?pentru\s+(.+?)(?:\.|$)",
)

_TITLE_PREFIXES = (
    "trebuie să ",
    "trebuie sa ",
    "trebuie un nou ",
    "trebuie o noua ",
    "trebuie o nouă ",
    "adaugă ",
    "adauga ",
    "notă:",
    "nota:",
)

_TAB_FAMILIE_RE = re.compile(
    r"(?:în|in|la)\s+tab(?:ul|u)?\s*familie|tab(?:ul|u)?\s*familie",
    flags=re.IGNORECASE,
)

_FAMILY_MENTION_RE = re.compile(
    r"(?:"
    r"(?:tot\s+)?(?:legat\s+de|pentru|pe|despre|de)\s+familie"
    r"|(?:în|in|la)\s+tab(?:ul|u)?\s*familie"
    r"|tab(?:ul|u)?\s*familie"
    r"|(?:în|in|la)\s+familie"
    r"|familie\s*(?:și|si|&)\s*administrative"
    r"|chestii\s+ce\s+t[iî]n\s+de\s+familie"
    r"|(?:în|in|la)\s+family"
    r"|(?:legat\s+de|pentru|pe|despre|de)\s+family"
    r")",
    flags=re.IGNORECASE,
)

_MEANINGFUL_HINTS_RE = re.compile(
    r"(?:dosar|intrare|indemniza|școal|scoala|copil|soț|sot|familie|"
    r"ziua|uita|onomastic|aniversar|sarbatoare|sărbătoare|elenie|elena|"
    r"sun[aă]|program|întâlnir|intalnir|doctor|școal|grădini|gradini|"
    r"aduc\s+aminte|georgian)",
    flags=re.IGNORECASE,
)

_LEADING_FILLER_RE = re.compile(
    r"^(?:salut|bună|buna|uite(?:\s+care\s+e\s+treaba)?|deci|ok|hei)[,!.\s]+",
    flags=re.IGNORECASE,
)

_TRAILING_FILLER_RE = re.compile(
    r"[,.\s]+(?:cumva|te\s+rog|pls|please)\s*$",
    flags=re.IGNORECASE,
)

_READ_QUERY_RE = re.compile(
    r"(?:^|\b)(?:ce\s+am|ce\s+avem|ce\s+e|ce\s+este|care\s+sunt|"
    r"arat[aă]|listeaz[aă]|list[aă]|spune[\s-]mi|show|zi[\s-]mi)\b",
    flags=re.IGNORECASE,
)


def _has_family_signal(text: str) -> bool:
    lowered = text.lower().strip()
    if _FAMILY_MENTION_RE.search(lowered) or _TAB_FAMILIE_RE.search(lowered):
        return True
    if re.search(r"aduc\s+aminte", lowered) and _TAB_FAMILIE_RE.search(lowered):
        return True
    if lowered.startswith(_FAMILY_PREFIX_STARTS):
        return True
    if re.search(r"familie.{0,30}administrative", lowered):
        return True
    if re.search(r"family.{0,30}administrative", lowered):
        return True
    if re.search(
        r"adaug[aă]\s+o\s+nou[aă]\s+intrare\s+(?:în|in|la)\s+.+?(?:familie|family|administrative)",
        lowered,
    ):
        return True
    return any(signal in lowered for signal in _FAMILY_INLINE_SIGNALS)


def _strip_family_context(text: str) -> str:
    cleaned = re.sub(
        r"\s*(?:și\s+)?pune\s+(?:asta\s+)?(?:în|in|la)\s+tab(?:ul|u)?\s*familie.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = _FAMILY_MENTION_RE.sub("", cleaned)
    cleaned = _TRAILING_FILLER_RE.sub("", cleaned)
    cleaned = _LEADING_FILLER_RE.sub("", cleaned.strip())
    cleaned = re.sub(r"^[,.:\s\-–—]+", "", cleaned)
    cleaned = re.sub(r"[,.:\s\-–—]+$", "", cleaned)
    return cleaned.strip()


def _extract_body(query: str) -> str:
    text = query.strip()
    for pattern in _BODY_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            body = match.group(1).strip(" .,!?:;")
            if body:
                return body

    tab_save = re.search(
        r"(.+?)\s+(?:și\s+)?pune\s+(?:asta\s+)?(?:în|in|la)\s+tab(?:ul|u)?\s*familie",
        text,
        flags=re.IGNORECASE,
    )
    if tab_save:
        body = _strip_family_context(tab_save.group(1))
        if body:
            return body

    trailing = re.search(
        r"(.+?)[,.;]?\s*(?:pentru|despre|de|legat de|în|in|la|pe)\s+familie\s*\.?$",
        text,
        flags=re.IGNORECASE,
    )
    if trailing:
        body = trailing.group(1).strip(" .,!?:;")
        if body:
            return body

    leading = re.search(
        r"^(?:pentru|despre|de|legat de|în|in|la|pe)\s+familie[,.:;\s-]+(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if leading:
        body = leading.group(1).strip(" .,!?:;")
        if body:
            return body

    if _FAMILY_MENTION_RE.search(text):
        stripped = _strip_family_context(text)
        if stripped:
            return stripped

    return text


def extract_family_title(content: str, max_len: int = 80) -> str:
    text = " ".join(content.strip().split())

    reminder = re.search(
        r"nu\s+uita\s+c[aă]\s+în\s+(.+?)\s+e\s+ziua\s+(\w+)",
        text,
        flags=re.IGNORECASE,
    )
    if reminder:
        return f"Ziua {reminder.group(2)} - în {reminder.group(1).strip()}"[:max_len]

    named_day = re.search(r"în\s+(.+?)\s+e\s+ziua\s+(\w+)", text, flags=re.IGNORECASE)
    if named_day:
        return f"Ziua {named_day.group(2)} - în {named_day.group(1).strip()}"[:max_len]

    birthday = re.search(r"(?:c[aă]\s+)?e\s+ziua\s+(\w+)", text, flags=re.IGNORECASE)
    if birthday:
        name = birthday.group(1)
        if re.search(r"s[aă]pt[aă]m[aâ]na\s+viitoare", text, flags=re.IGNORECASE):
            return f"Ziua {name} - săptămâna viitoare"[:max_len]
        return f"Ziua {name}"[:max_len]

    remind = re.search(
        r"(?:mi[-\s])?aduc\s+aminte\s+(.+?)(?:\.|$)",
        text,
        flags=re.IGNORECASE,
    )
    if remind:
        snippet = remind.group(1).strip(" .,!?:;")
        if snippet:
            return f"Aducere aminte: {snippet}"[:max_len]

    for pattern in _TITLE_PATTERNS[3:]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            title = match.group(1).strip(" .,!?:;")
            if title:
                if not title.lower().startswith("dosar"):
                    title = f"Dosar {title}"
                return title[:max_len]

    forget = re.search(r"nu\s+uita\s+c[aă]\s+(.+?)(?:\.|$)", text, flags=re.IGNORECASE)
    if forget:
        return f"Nu uita: {forget.group(1).strip()}"[:max_len]

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
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if parts:
                text = parts[-1]
            break

    if not text:
        return "Notă Family"
    if len(text.split()) <= 4 and not text.lower().startswith("dosar"):
        text = f"Dosar {text}"
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(" ", 1)[0]
    return cut or text[:max_len]


def parse_family_request(query: str) -> str | None:
    """Return family note body when user wants to save in Family & Administrative."""
    text = query.strip()
    if not text or _READ_QUERY_RE.search(text) or not _has_family_signal(text):
        return None

    body = _extract_body(text)
    if not body:
        return None

    lowered = body.lower()
    if body.lower() == text.lower():
        if not _MEANINGFUL_HINTS_RE.search(lowered):
            return None

    return body