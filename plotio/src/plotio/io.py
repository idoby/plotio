"""XML parsing logic for Draw.io files."""

from pathlib import Path


def parse_drawio_xml(file_path: Path) -> None:
    """Parse a Draw.io XML file into domain models."""
