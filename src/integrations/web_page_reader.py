"""Fetch and extract readable text from web pages."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse

import httpx

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (compatible; AndreiAI/1.0; +https://github.com/andreia-agent)"
)


def is_fetchable_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def html_to_text(html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    cleaned = re.sub(r"(?is)<!--.*?-->", " ", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def fetch_page_text(url: str) -> str:
    if not is_fetchable_url(url):
        raise ValueError(f"URL invalid: {url}")

    timeout = settings.web_search_fetch_timeout_seconds
    max_bytes = settings.web_search_page_max_bytes
    char_limit = settings.web_search_page_char_limit

    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        response = client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise ValueError(f"Tip conținut nesuportat: {content_type or 'necunoscut'}")

        raw = response.content[:max_bytes]
        html = raw.decode(response.encoding or "utf-8", errors="replace")
        text = html_to_text(html)
        if not text:
            raise ValueError("Pagina nu conține text extras")
        return text[:char_limit]