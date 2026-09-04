"""Tests for HTML parsing module."""

from plotio.html import clean_html_label


def test_clean_html_label_removes_tags() -> None:
    raw_html = '<div>Hello <b>World</b></div>'

    cleaned = clean_html_label(raw_html)

    assert cleaned == 'Hello World'


def test_clean_html_label_converts_br_and_div_to_newline() -> None:
    raw_html = 'Line 1<br>Line 2<div>Line 3</div>'

    cleaned = clean_html_label(raw_html)

    assert cleaned == 'Line 1\nLine 2\nLine 3'


def test_clean_html_label_replaces_nbsp() -> None:
    raw_html = 'Hello&nbsp;World'

    cleaned = clean_html_label(raw_html)

    assert cleaned == 'Hello World'


def test_clean_html_label_preserves_math_equations() -> None:
    raw_html = r'$$x^2 + y^2 = z^2$$ and \(\alpha = \beta\)'

    cleaned = clean_html_label(raw_html)

    assert cleaned == '$x^2 + y^2 = z^2$ and $\\alpha = \\beta$'
