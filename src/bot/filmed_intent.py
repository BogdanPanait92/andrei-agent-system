"""Detect 'am filmat la ...' → add Posting Plan row in Notion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

_FILMED_CITY_AT_RE = re.compile(
    r"(?:tocmai\s+)?am\s+filmat\s+în\s+(.+?),\s*la\s+(?:restaurantul\s+)?(.+)$",
    flags=re.IGNORECASE,
)
_FILMED_CITY_AT_INLINE_RE = re.compile(
    r"(?:tocmai\s+)?am\s+filmat\s+în\s+(.+?)\s+la\s+(?:restaurantul\s+)?(.+)$",
    flags=re.IGNORECASE,
)
_FILMED_CITY_NAMED_RESTAURANT_RE = re.compile(
    r"(?:tocmai\s+)?am\s+filmat\s+în\s+(.+?)\s+un(?:\s+nou)?\s+restaurant\s+numit\s+(.+)$",
    flags=re.IGNORECASE,
)
_FILMED_CITY_VENUE_COMMA_RE = re.compile(
    r"(?:tocmai\s+)?am\s+filmat\s+în\s+(.+?),\s*(?:restaurantul\s+)?(.+)$",
    flags=re.IGNORECASE,
)

_FILMED_CITY_VENUE_PATTERNS = (
    _FILMED_CITY_NAMED_RESTAURANT_RE,
    _FILMED_CITY_AT_RE,
    _FILMED_CITY_AT_INLINE_RE,
    _FILMED_CITY_VENUE_COMMA_RE,
)

_FILMED_PATTERNS = (
    r"(?:tocmai\s+)?am\s+filmat\s+(?:la|pentru)\s+(.+)$",
    r"(?:tocmai\s+)?am\s+filmat\s+(.+)$",
    r"filmat\s+(?:la|pentru)\s+(.+)$",
)

_DATE_ISO_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_DATE_DMY_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b")
_DATE_RO_RE = re.compile(
    r"(?:due\s*date|data|postez\s+pe|pe)\s*(\d{1,2})\s+"
    r"(ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie)"
    r"(?:\s+(\d{4}))?",
    flags=re.IGNORECASE,
)

_MONTHS = {
    "ianuarie": 1,
    "februarie": 2,
    "martie": 3,
    "aprilie": 4,
    "mai": 5,
    "iunie": 6,
    "iulie": 7,
    "august": 8,
    "septembrie": 9,
    "octombrie": 10,
    "noiembrie": 11,
    "decembrie": 12,
}

_TAIL_DATE_NOISE_RE = re.compile(
    r"(?:,|\s)+(?:due\s*date|data|postez\s+pe|pe)\s+.+$",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class FilmedLocationRequest:
    location: str
    oras: str = ""
    due_date: str | None = None  # ISO YYYY-MM-DD


def _parse_due_date(text: str) -> str | None:
    match = _DATE_ISO_RE.search(text)
    if match:
        return match.group(1)

    match = _DATE_DMY_RE.search(text)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None

    match = _DATE_RO_RE.search(text)
    if match:
        day = int(match.group(1))
        month = _MONTHS.get(match.group(2).lower())
        year = int(match.group(3)) if match.group(3) else datetime.now().year
        if month:
            try:
                return datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                return None
    return None


def _clean_location(raw: str, source_text: str) -> str:
    body = _TAIL_DATE_NOISE_RE.sub("", raw.strip())
    body = body.strip(" .,!?:;")
    if not body:
        return ""
    body = _DATE_ISO_RE.sub("", body).strip(" ,.")
    body = _DATE_DMY_RE.sub("", body).strip(" ,.")
    return body


def _parse_city_and_venue(text: str) -> FilmedLocationRequest | None:
    for pattern in _FILMED_CITY_VENUE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        oras = _clean_location(match.group(1), text)
        location = _clean_location(match.group(2), text)
        if location:
            return FilmedLocationRequest(
                location=location,
                oras=oras,
                due_date=_parse_due_date(text),
            )
    return None


def parse_filmed_location(query: str) -> FilmedLocationRequest | None:
    """
    Return location + optional city and due date when user reports filming on site.
    Return None otherwise.
    """
    text = query.strip()
    if not text:
        return None

    city_venue = _parse_city_and_venue(text)
    if city_venue is not None:
        return city_venue

    for pattern in _FILMED_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        raw_location = match.group(1)
        due_date = _parse_due_date(text)
        location = _clean_location(raw_location, text)
        if location:
            return FilmedLocationRequest(location=location, due_date=due_date)

    return None


def serialize_filmed_request(req: FilmedLocationRequest) -> str:
    return f"{req.location}|||{req.oras}|||{req.due_date or ''}"


def deserialize_filmed_request(payload: str) -> FilmedLocationRequest:
    parts = payload.split("|||")
    if len(parts) >= 3:
        location, oras, due = parts[0], parts[1], parts[2]
        return FilmedLocationRequest(
            location=location.strip(),
            oras=oras.strip(),
            due_date=due.strip() or None,
        )
    if len(parts) == 2:
        location, due = parts[0], parts[1]
        return FilmedLocationRequest(
            location=location.strip(),
            due_date=due.strip() or None,
        )
    return FilmedLocationRequest(location=payload.strip(), due_date=None)