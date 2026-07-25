"""HTML parsing utilities for Draw.io labels."""

from html.parser import HTMLParser


class _LabelHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ('br', 'div'):
            self.text_parts.append('\n')


def clean_html_label(label: str) -> str:
    """Clean HTML formatting from a Draw.io label using html.parser.

    Args:
        label: The raw HTML label string.

    Returns:
        The cleaned plain text label.
    """
    label = label.replace('&nbsp;', ' ')
    label = label.replace('$$', '$')
    label = label.replace('\\(', '$').replace('\\)', '$')

    parser = _LabelHTMLParser()
    parser.feed(label)
    text = ''.join(parser.text_parts)
    return text.strip()
