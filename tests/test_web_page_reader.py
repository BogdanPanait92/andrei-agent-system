"""Tests for web page text extraction."""

from src.integrations.web_page_reader import html_to_text, is_fetchable_url


def test_html_to_text_strips_tags() -> None:
    html = "<html><body><h1>Titlu</h1><p>Text util aici.</p></body></html>"
    assert "Titlu" in html_to_text(html)
    assert "Text util" in html_to_text(html)


def test_is_fetchable_url() -> None:
    assert is_fetchable_url("https://example.com/page")
    assert not is_fetchable_url("ftp://example.com")