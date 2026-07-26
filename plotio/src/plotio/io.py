"""I/O layer for reading and writing Draw.io files."""

import xml.etree.ElementTree as ET
from pathlib import Path

from plotio.constants import DEFAULT_PAGE_HEIGHT, DEFAULT_PAGE_SCALE, DEFAULT_PAGE_WIDTH
from plotio.core import DrawIOGraph
from plotio.errors import ParseError
from plotio.parse import parse_root_cell


def parse_drawio_xml(file_path: Path) -> DrawIOGraph:
    """Parse a Draw.io XML file into domain models.

    Args:
        file_path: Path to the Draw.io XML file.

    Returns:
        The parsed graph.

    Raises:
        FileNotFoundError: If the file does not exist.
        ParseError: If the XML is missing a graph model or root cell.
    """
    if not file_path.exists():
        raise FileNotFoundError(f'Draw.io file not found: {file_path}')

    tree = ET.parse(file_path)
    root = tree.getroot()
    graph_model = root.find('.//mxGraphModel')
    if graph_model is None:
        raise ParseError('Invalid Draw.io XML: No mxGraphModel found.')

    # Calculate scale
    page_width = float(graph_model.get('pageWidth', DEFAULT_PAGE_WIDTH))
    page_height = float(graph_model.get('pageHeight', DEFAULT_PAGE_HEIGHT))
    page_scale_factor = float(graph_model.get('pageScale', DEFAULT_PAGE_SCALE))

    # Scale factor: draw.io points -> canvas units (0.0 to 1.0 width)
    coord_scale = 1.0 / (page_width * page_scale_factor)

    # Flatten cells
    root_cell = graph_model.find('root')
    if root_cell is None:
        raise ParseError('Invalid Draw.io XML: No root cell found.')

    nodes, edges = parse_root_cell(root_cell, coord_scale)

    return DrawIOGraph(width=page_width, height=page_height, coord_scale=coord_scale, nodes=nodes, edges=edges)
