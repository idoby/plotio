"""IO handling and XML parsing for plotio."""

from pathlib import Path


def parse_drawio_xml(file_path: Path):
    """Parse a Draw.io XML file into domain models."""
