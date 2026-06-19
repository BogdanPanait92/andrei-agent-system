"""Detect natural-language requests to save a new content idea."""

from __future__ import annotations

import re

from src.bot.research_intent import has_grok_marker
from src.bot.save_intent import (
    has_save_to_ideas_signal,
    is_save_previous_exchange_request,
    strip_save_to_ideas_tail,
)

_PREFIXES = (
    "idee:",
    "idea:",
    "idee+salveaza:",
    "idee+salvează:",
    "idee + salveaza:",
    "idee + salvează:",
    "am o idee:",
    "am o idee ",
    "o idee:",
    "pune o idee:",
    "pune idee:",
    "adauga o idee:",
    "adaugă o idee:",
    "adauga o idee noua:",
    "adaugă o idee nouă:",
)

_TOPIC_LEADING_PATTERNS = (
    r"^(?:salut[,!]?\s*)?"
    r"(?:am\s+o\s+nou[aă]\s+idee\s+despre\s+)(.+?)$",
    r"^(?:salut[,!]?\s*)?"
    r"(?:mi-a\s+venit(?:\s+\w+){0,4}\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?\s+)"
    r"(?:s[aă]\s+fac\s+un\s+clip\s+despre\s+)(.+?)$",
    r"^(?:salut[,!]?\s*)?"
    r"(?:mi-a\s+venit(?:\s+\w+){0,4}\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?\s+despre\s+)(.+?)$",
    r"^(?:salut[,!]?\s*)?"
    r"(?:am\s+o\s+idee\s+despre\s+)(.+?)$",
    r"^(?:salut[,!]?\s*)?"
    r"(?:idee\s+(?:nou[aă]\s+)?despre\s+)(.+?)$",
    r"^(?:salut[,!]?\s*)?"
    r"(?:adaug[aă](?:-mi|-o)?\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?\s+despre\s+)(.+?)$",
    r"^(?:salut[,!]?\s*)?"
    r"(?:pune(?:-mi|-o)?\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?\s+despre\s+)(.+?)$",
    r"^(?:salut[,!]?\s*)?"
    r"(?:un\s+(?:clip|video)\s+despre\s+)(.+?)$",
)

_BODY_PATTERNS = (
    r"subiectul\s+(?:clipului\s+)?(?:este|e)\s+(.+?)(?:\.|$)",
    r"(?:noteaz[aă](?:-[oml]|ă|-mi)?\s+(?:la|in|în)\s+idei[,:]?\s*)"
    r"(?:un\s+)?(?:nou[aă]\s+)?(?:idee\s+de\s+clip[,.]?\s*)?"
    r"(?:subiectul\s+clipului\s+(?:este|e)\s+)?(.+)$",
    r"(?:ad(?:aug[aă]|uag[aă])(?:-mi|-o)?\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?[,:]?\s*)(.+)$",
    r"(?:pune(?:-mi|-o)?\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?[,:]?\s*)(.+)$",
    r"(?:noteaz[aă](?:-mi|-o)?\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?[,:]?\s*)(.+)$",
    r"(?:adaug[aă](?:-o|-mi)?\s+(?:la|in|în)\s+idei[,:]?\s*)(.+)$",
    r"(?:salveaz[aă](?:-o|-mi)?\s+(?:la|in|în)\s+idei[,:]?\s*)(.+)$",
    r"(?:pune(?:-o|-l|-mi)?\s+(?:la|in|în)\s+idei[,:]?\s*)(?:ideea\s+asta[:\s]+)?(.+)$",
    r"(?:pune\s+in\s+idei[,:]?\s*)(?:ideea\s+asta[:\s]+)?(.+)$",
    r"(?:ideea\s+asta[:\s]+)(.+)$",
    r"(?:a[sș]\s+vrea\s+s[aă]\s+fac)\s+(.+)$",
    r"(?:vreau\s+s[aă]\s+fac)\s+(.+)$",
    r"(?:sa\s+fac|să\s+fac)\s+un\s+clip\s+despre\s+(.+?)$",
    r"(?:sa\s+fac|să\s+fac)\s+(.+)$",
    r"(?:ideea\s+(?:e|este)[:\s]+)\s*(.+)$",
)

_DESPRE_TOPIC_RE = re.compile(r"despre\s+(.+)$", flags=re.IGNORECASE)

_IDEA_ACTION_RE = re.compile(
    r"(?:"
    r"adaug[aă](?:-mi|-o)?\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?"
    r"|pune(?:-mi|-o)?\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?"
    r"|noteaz[aă](?:-mi|-o)?\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?"
    r"|mi-a\s+venit(?:\s+\w+){0,4}\s+(?:o\s+)?(?:nou[aă]\s+)?idee(?:\s+nou[aă])?"
    r"|am\s+o\s+(?:nou[aă]\s+)?idee"
    r")",
    flags=re.IGNORECASE,
)

_IDEA_STARTS = (
    "am o idee",
    "am o nouă idee",
    "am o noua idee",
    "mi-a venit o idee",
    "pune o idee",
    "pune idee",
    "adauga o idee",
    "adaugă o idee",
)


def _clean_topic(topic: str) -> str:
    return topic.strip(" .,!?:;")


def _extract_from_patterns(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            body = _clean_topic(match.group(1))
            if body:
                return body
    return None


def _extract_idea_topic(query: str) -> str | None:
    text = query.strip()
    if not text:
        return None

    stripped = strip_save_to_ideas_tail(text)
    topic = _extract_from_patterns(stripped, _TOPIC_LEADING_PATTERNS)
    if topic:
        return topic

    topic = _extract_from_patterns(stripped, _BODY_PATTERNS)
    if topic and topic.lower() != stripped.lower():
        return topic

    topic = _extract_from_patterns(text, _BODY_PATTERNS)
    if topic and topic.lower() != text.lower():
        return topic

    if stripped and stripped.lower() != text.lower():
        despre = _DESPRE_TOPIC_RE.search(stripped)
        if despre:
            return _clean_topic(despre.group(1))
        if len(stripped) > 10:
            return stripped

    return None


def parse_idea_request(query: str) -> str | None:
    """
    Return idea text when the user wants a new idea saved/planned.
    Return None otherwise.
    """
    text = query.strip()
    if not text:
        return None

    lowered = text.lower()
    if has_grok_marker(text):
        return None
    if (
        re.search(r"(?:fa[c]?|faci|fac)\s+research(?:-ul)?\b", lowered)
        or re.search(r"research(?:-ul)?(?:\s+(?:ăsta|asta))?", lowered)
        or "research in ideas" in lowered
        or "research inn ideas" in lowered
        or "research pe" in lowered
        or "research despre" in lowered
    ):
        return None
    for prefix in _PREFIXES:
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip() or None

    plan_triggers = (
        "cum as implementa",
        "cum aș implementa",
        "sugestii de implementare",
        "sugestii implementare",
        "plan de implementare",
        "cum implementez",
    )
    if any(t in lowered for t in plan_triggers) and len(text) > 20:
        return text

    if is_save_previous_exchange_request(text):
        return None

    if (
        has_save_to_ideas_signal(text)
        or lowered.startswith(_IDEA_STARTS)
        or _IDEA_ACTION_RE.search(text)
    ):
        return _extract_idea_topic(text)

    return None


def is_direct_idea_save_request(query: str) -> bool:
    """True when the user names a new idea to save (not a save-previous or research-only command)."""
    text = query.strip()
    if not text:
        return False
    if is_save_previous_exchange_request(text):
        return False

    lowered = text.lower()
    idea = parse_idea_request(text)
    if not idea:
        return False

    for prefix in _PREFIXES:
        if lowered.startswith(prefix):
            return True

    if (
        re.search(r"(?:fa[c]?|faci|fac)\s+research(?:-ul)?\b", lowered)
        or re.search(r"research(?:-ul)?(?:\s+(?:ăsta|asta))?", lowered)
        or "research in ideas" in lowered
        or "research pe" in lowered
        or "research despre" in lowered
    ):
        return False

    plan_triggers = (
        "cum as implementa",
        "cum aș implementa",
        "sugestii de implementare",
        "sugestii implementare",
        "plan de implementare",
        "cum implementez",
    )
    if any(t in lowered for t in plan_triggers):
        return False

    return (
        has_save_to_ideas_signal(text)
        or lowered.startswith(_IDEA_STARTS)
        or bool(_IDEA_ACTION_RE.search(text))
    )