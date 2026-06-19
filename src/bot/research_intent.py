"""Detect research / Grok-style chat mode (knowledge + automatic web research)."""

from __future__ import annotations

import re

_PREFIXES = (
    "research:",
    "explorează:",
    "exploreaza:",
    "grok:",
    "chat+:",
    "întreabă:",
    "intreaba:",
)

_INLINE_PREFIXES = (
    "research ",
    "explorează ",
    "exploreaza ",
    "grok ",
    "grok, ",
    "chat+ ",
)

_FLEXIBLE_PATTERNS = (
    r"(?:vreau\s+(?:s[aă]\s+)?(?:s[aă]\s+)?mi\s+)?(?:faci|fac|faceți|face)\s+research\s+despre\s+(.+)$",
    r"(?:vreau\s+(?:s[aă]\s+)?(?:s[aă]\s+)?mi\s+)?(?:faci|fac|faceți|face)\s+research\s+pe\s+(?:ideea\s+)?(.+)$",
    r"(?:po[tț]i\s+(?:s[aă]\s+)?(?:faci|face)\s+research\s+despre)\s+(.+)$",
    r"(?:po[tț]i\s+(?:s[aă]\s+)?(?:faci|face)\s+research\s+pe\s+(?:ideea\s+)?)(.+)$",
    r"(?:fa[ce]?\s+research(?:-ul)?(?:\s+(?:ăsta|asta|acesta))?\s+despre)\s+(.+)$",
    r"(?:fa[ce]?\s+research(?:-ul)?(?:\s+(?:ăsta|asta|acesta))?\s+pe\s+(?:ideea\s+)?)(.+)$",
    r"(?:fa[ce]?\s+research\s+despre)\s+(.+)$",
    r"(?:fa[ce]?\s+research\s+pe\s+(?:ideea\s+)?)(.+)$",
    r"(?:research\s+despre)\s+(.+)$",
    r"(?:research\s+pe\s+(?:ideea\s+)?)(.+)$",
    r"(?:fa[c]?\s+research\s+(?:in|inn)\s+ideas[,:]?\s*)(?:despre\s+)?(.+)$",
    r"(?:research\s+(?:in|inn)\s+ideas[,:]?\s*)(?:despre\s+)?(.+)$",
    r"(?:vreau\s+(?:s[aă]\s+)?(?:afl[aă]|explor[aă]|investig[aă]))\s+(.+)$",
    r"^grok[,:]\s*(.+)$",
    r"^research[,:]\s*(.+)$",
)

_RESEARCH_ACTION_RE = re.compile(
    r"(?:"
    r"(?:tu\s+)?(?:s[aă]\s+)?(?:fa[c]?|faci|fac|faceți|face)\s+research(?:-ul)?"
    r"(?:\s+(?:ăsta|asta|acesta))?"
    r"|research\s+(?:in|inn)\s+ideas"
    r"|(?:vreau|po[tț]i).{0,80}research(?:-ul)?"
    r")",
    flags=re.IGNORECASE,
)

_TOPIC_CONTEXT_PATTERNS = (
    r"(?:a[sș]\s+vrea\s+s[aă]\s+)?(?:s[aă]\s+)?v[aă]d\s+cum\s+(.+?)(?:\.|$)",
    r"(?:a[sș]\s+vrea\s+s[aă]\s+)?(?:s[aă]\s+)?v[aă]d\s+(.+?)(?:\.|$)",
    r"(?:interes(?:ează|eaza)(?:-m[aă])?\s+)(?:cum\s+)?(.+?)(?:\.|$)",
    r"(?:despre|pe)\s+(.+?)(?:\.|,\s*(?:vreau|și|si)\b)",
)

_TAIL_NOISE_RE = re.compile(
    r"\s+(?:si|și)\s+(?:"
    r"(?:sa|să)\s+creez\b.*"
    r"|(?:sa|să)-?l?\s+(?:pui|pune|salveaz|adaug).*$"
    r"|(?:sa|să)\s+(?:salvez|salvezi).*$"
    r")",
    flags=re.IGNORECASE,
)

_SAVE_WITH_RESEARCH_SIGNALS = (
    "adauga la idei",
    "adaugă la idei",
    "adauga in idei",
    "adaugă în idei",
    "salveaza in idei",
    "salvează în idei",
    "salveaza la idei",
    "salvează la idei",
    "noteaza la idei",
    "notează la idei",
    "noteaza in idei",
    "notează în idei",
    "pune in idei",
    "pune în idei",
    "pui in idei",
    "pui în idei",
    "sa-l pui in idei",
    "să-l pui în idei",
    "pune-l in idei",
    "pune-l în idei",
    "stocheaz-o",
    "stocheaza-o",
    "stochează-o",
    "stocheaza",
    "stochează",
    "in ideas",
    "inn ideas",
    "pune in notion ideas",
    "pune în notion ideas",
    "salveaza in notion",
    "salvează în notion",
    "creez o pagina",
    "creez pagina",
    "creez automat",
    "sa creez o pagina",
    "să creez o pagină",
    "sa creez pagina",
    "să creez pagina",
    "sa creez automat",
    "să creez automat",
)

_GROK_SUFFIX_RE = re.compile(r"[-–—,]\s*grok\s*$|\s+grok\s*$", flags=re.IGNORECASE)

_IDEA_SAVE_PREFIX_RE = re.compile(
    r"^(?:ad(?:aug[aă]|uag[aă])(?:-mi)?|pune(?:-mi)?|salveaz[aă](?:-mi)?)"
    r"\s+(?:o\s+)?(?:nou[aă]\s+)?idee[,:]?\s*",
    flags=re.IGNORECASE,
)

_EXIT_PHRASES = frozenset(
    {
        "research stop",
        "stop research",
        "exit research",
        "iesi din research",
        "ieși din research",
        "opreste research",
        "oprește research",
        "inchide research",
        "închide research",
    }
)


def is_research_exit(query: str) -> bool:
    return query.strip().lower() in _EXIT_PHRASES


def _clean_research_topic(topic: str) -> str:
    cleaned = _TAIL_NOISE_RE.sub("", topic.strip()).strip(" .,!?:;")
    return cleaned


def _extract_flexible_body(query: str) -> str | None:
    text = query.strip()
    for pattern in _FLEXIBLE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            body = _clean_research_topic(match.group(1))
            if body:
                return body
    return None


def _extract_contextual_topic(query: str) -> str | None:
    """Topic named earlier in the sentence (e.g. before 'research-ul ăsta')."""
    text = query.strip()
    for pattern in _TOPIC_CONTEXT_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            body = _clean_research_topic(match.group(1))
            if body:
                return body
    return None


def _has_research_action(query: str) -> bool:
    return bool(_RESEARCH_ACTION_RE.search(query.strip()))


def has_grok_marker(query: str) -> bool:
    text = query.strip()
    lowered = text.lower()
    return (
        lowered.startswith("grok")
        or bool(_GROK_SUFFIX_RE.search(text))
    )


def _extract_grok_topic(query: str) -> str | None:
    text = query.strip()
    if not has_grok_marker(text):
        return None

    for prefix in _INLINE_PREFIXES:
        if text.lower().startswith(prefix):
            body = _clean_research_topic(text[len(prefix) :].strip())
            if body:
                return body

    body = _GROK_SUFFIX_RE.sub("", text).strip()
    body = _IDEA_SAVE_PREFIX_RE.sub("", body).strip()
    return _clean_research_topic(body) or None


def wants_save_to_ideas_with_research(query: str) -> bool:
    """True when the user wants research output saved to Notion Ideas in the same turn."""
    from src.bot.save_intent import has_save_to_ideas_signal

    if has_save_to_ideas_signal(query):
        return True
    lowered = query.strip().lower()
    if any(signal in lowered for signal in _SAVE_WITH_RESEARCH_SIGNALS):
        return True
    if has_grok_marker(query) and _IDEA_SAVE_PREFIX_RE.search(query):
        return True
    return False


def parse_research_query(query: str) -> str | None:
    """
    Return the research question when the user explicitly entered research mode.
    Return None otherwise.
    """
    text = query.strip()
    if not text:
        return None

    lowered = text.lower()
    for prefix in _PREFIXES:
        if lowered.startswith(prefix):
            return _clean_research_topic(text[len(prefix) :].strip()) or None

    for prefix in _INLINE_PREFIXES:
        if lowered.startswith(prefix):
            return _clean_research_topic(text[len(prefix) :].strip()) or None

    flexible = _extract_flexible_body(text)
    if flexible:
        return flexible

    if _has_research_action(text):
        contextual = _extract_contextual_topic(text)
        if contextual:
            return contextual

    grok_topic = _extract_grok_topic(text)
    if grok_topic:
        return grok_topic

    return None