"""Detect when the user talks about Notion/Google workspace tabs (not Ideas)."""

from __future__ import annotations

import re

from src.bot.idea_intent import parse_idea_request
from src.bot.save_intent import has_save_to_ideas_signal

_IDEAS_CONTEXT_RE = re.compile(
    r"(?:"
    r"notion\s+ideas|"
    r"(?:in|în|la)\s+idei|"
    r"idei\s+(?:draft|in\s+lucru|ready|gata)|"
    r"(?:adaug|noteaz|pune|salveaz).{0,50}(?:in|în|la)\s+idei|"
    r"voice[\s-]?over|"
    r"\bidee\s*:"
    r")",
    flags=re.IGNORECASE,
)

_WORKSPACE_RE = re.compile(
    r"(?:"
    r"(?:pentru|despre|de|legat de|în|in|la|pe)\s+familie\b|"
    r"(?:în|in|la)\s+tab(?:ul|u)?\s*familie|"
    r"tab(?:ul|u)?\s*familie|"
    r"aduc\s+aminte.{0,120}familie|"
    r"nu\s+uita.{0,80}(?:familie|ziua|elenie|elena)|"
    r"famil(?:y|ie)\s*(?:&|and|și|si)?\s*administrative|"
    r"chestii\s+ce\s+t[iî]n\s+de\s+familie|"
    r"(?:în|in|la)\s+famil(?:y|ie)\b|"
    r"adaug[aă]\s+o\s+nou[aă]\s+intrare|"
    r"(?:dosar|folder)\s+(?:nou\s+)?pentru|"
    r"posting\s+plan|"
    r"plan\s+(?:de\s+)?postar[eă]|"
    r"(?:adaug[aă]|pune).{0,40}\bpostar[eă]\b|"
    r"(?:tabul\s+)?job\b|"
    r"notion\s+job|"
    r"(?:în|in|la)\s+job\b|"
    r"ajut\s+cum\s+pot|"
    r"\bacp\b|"
    r"tabul\s+ajut|"
    r"content\s+creation|"
    r"gata\s+de\s+postat|"
    r"\bcalendar\b|"
    r"(?:în|in)\s+calendar|"
    r"briefing(?:\s+zilnic|\s+saptamanal|\s+săptămânal)?|"
    r"marcheaz[aă].{0,50}(?:done|finalizat)|"
    r"adaug[aă]\s*:|"
    r"(?:ce\s+am|ce\s+avem|listeaz[aă]).{0,40}"
    r"(?:posting\s+plan|famil(?:y|ie)|calendar|job|ajut|acp|content\s+creation)"
    r")",
    flags=re.IGNORECASE,
)


def mentions_non_ideas_notion_workspace(query: str) -> bool:
    """
    True when the message is about Notion/Calendar workspace tabs other than Ideas.
    These should use the full agent (tools), not implicit research mode.
    """
    text = query.strip()
    if not text:
        return False

    if has_save_to_ideas_signal(text):
        return False
    if parse_idea_request(text):
        return False

    lowered = text.lower()
    if _IDEAS_CONTEXT_RE.search(lowered):
        return False
    if re.search(r"ce\s+idei\b", lowered):
        return False

    return bool(_WORKSPACE_RE.search(text))