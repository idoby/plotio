"""XML parsing logic for Draw.io files post-IO."""

import xml.etree.ElementTree as ET
from typing import Literal, TypedDict

from plotio.core import BoundingBox, DrawIOEdge, DrawIOEdgeLabel, DrawIONode, Point, RouterType, ShapeType
from plotio.errors import ParseError
from plotio.html import clean_html_label
from plotio.styles import EdgeStyle, LabelStyle, NodeStyle, StyleValue


class CellData(TypedDict):
    cell: ET.Element
    metadata: dict[str, str]


def _categorize_cell(cell: ET.Element) -> Literal['node', 'edge', 'edge_label', 'unknown']:
    """Determine the logical type of a Draw.io cell."""
    if cell.get('edge') == '1':
        return 'edge'
    if cell.get('vertex') == '1':
        style_dict = _parse_style_string(cell.get('style', ''))
        if style_dict.get('edgelabel') in ('1', ''):
            return 'edge_label'
        return 'node'
    return 'unknown'


def parse_root_cell(root_cell: ET.Element, scale: float) -> tuple[dict[str, DrawIONode], list[DrawIOEdge]]:
    """Parse the root cell element of the XML.

    Args:
        root_cell: The root cell XML element.
        scale: The coordinate scaling factor.

    Returns:
        A tuple of (nodes dict, edges list).

    Raises:
        ParseError: If invalid cells are encountered.
    """
    raw_cells: dict[str, CellData] = {}
    for item in root_cell:
        if item.tag == 'mxCell':
            cid = item.get('id')
            if not cid:
                raise ParseError('mxCell without id encountered.')

            raw_cells[cid] = {'cell': item, 'metadata': item.attrib.copy()}
        elif item.tag == 'object':
            cell = item.find('mxCell')
            if cell is None:
                raise ParseError('object without mxCell encountered.')
            cid = item.get('id') or (cell.get('id') if cell is not None else None)
            if not cid:
                raise ParseError('object without id encountered.')

            metadata = cell.attrib.copy()
            metadata.update(item.attrib)
            raw_cells[cid] = {'cell': cell, 'metadata': metadata}
        else:
            raise ParseError(f'Unexpected element in root cell: {item.tag}')

    nodes: dict[str, DrawIONode] = {}
    edges: list[DrawIOEdge] = []
    edge_labels_by_parent: dict[str, list[DrawIOEdgeLabel]] = {}

    for cid, data in raw_cells.items():
        cell = data['cell']
        cell_type = _categorize_cell(cell)

        if cell_type == 'edge_label':
            label = _parse_edge_label(cid, cell, data['metadata'], scale)
            if label:
                parent_id = data['metadata'].get('parent')
                if parent_id:
                    if parent_id not in edge_labels_by_parent:
                        edge_labels_by_parent[parent_id] = []
                    edge_labels_by_parent[parent_id].append(label)
        elif cell_type == 'node':
            node = _parse_vertex(cid, cell, data['metadata'], scale)
            if node:
                nodes[cid] = node

    for cid, data in raw_cells.items():
        cell = data['cell']
        if cell.get('edge') == '1':
            edge_labels = edge_labels_by_parent.get(cid, [])
            edge = _parse_edge(cid, cell, data['metadata'], scale, edge_labels)
            if edge:
                edges.append(edge)

    return nodes, edges


def _parse_style_string(style_str: str) -> dict[str, StyleValue]:
    """Parse a Draw.io style string into a dictionary."""
    style_dict: dict[str, StyleValue] = {}
    for p in style_str.split(';'):
        if '=' in p:
            k, v = p.split('=', 1)
            k = k.strip().lower()
            v = v.strip()
            if k not in ['fontfamily', 'fontcolor', 'labelbackgroundcolor', 'fillcolor', 'strokecolor']:
                v = v.lower()
            style_dict[k] = v
        elif p:
            style_dict[p.strip().lower()] = ''
    return style_dict


def _parse_vertex(cid: str, cell: ET.Element, metadata: dict[str, str], scale: float) -> DrawIONode:
    geo = cell.find('mxGeometry')
    if geo is None:
        raise ParseError(f'Vertex cell {cid} missing mxGeometry.')

    x, y, w, h = [float(geo.get(k, 0)) for k in ['x', 'y', 'width', 'height']]
    style_str = cell.get('style', '')
    style_dict = _parse_style_string(style_str)

    if 'shape' not in style_dict:
        if 'edgelabel' in style_dict or 'text' in style_dict:
            shape: ShapeType | None = None
        elif 'ellipse' in style_dict:
            shape = 'ellipse'
        elif style_dict.get('rounded') == '1':
            shape = 'rounded_rectangle'
        else:
            shape = 'rectangle'
    else:
        shape_str = str(style_dict['shape'])
        if shape_str == 'rectangle':
            shape = 'rectangle'
        elif shape_str == 'ellipse':
            shape = 'ellipse'
        elif shape_str == 'rounded_rectangle':
            shape = 'rounded_rectangle'
        elif shape_str == 'step':
            shape = 'step'
        else:
            raise ParseError(f'Unsupported shape {shape_str}')

    label = metadata.get('value') or metadata.get('label') or ''
    label = clean_html_label(label)

    geometry = BoundingBox(x * scale, y * scale, w * scale, h * scale)

    return DrawIONode(
            id=cid, bounding_box=geometry, shape=shape, label=label, style=NodeStyle(style_dict), metadata=metadata
    )


def _parse_edge_label(cid: str, cell: ET.Element, metadata: dict[str, str], scale: float) -> DrawIOEdgeLabel:
    geo = cell.find('mxGeometry')
    if geo is None:
        raise ParseError(f'Edge label cell {cid} missing mxGeometry.')

    # x is relative position (-1 to 1 usually, or 0 to 1)
    # y is orthogonal offset
    x = float(geo.get('x', 0))
    y = float(geo.get('y', 0)) * scale

    offset = Point(0, 0)
    if (off := geo.find('mxPoint[@as="offset"]')) is not None:
        ox = float(off.get('x', 0)) * scale
        oy = float(off.get('y', 0)) * scale
        offset = Point(ox, oy)

    style_str = cell.get('style', '')
    style_dict = _parse_style_string(style_str)

    label = metadata.get('value') or metadata.get('label') or ''
    label = clean_html_label(label)

    return DrawIOEdgeLabel(
            id=cid, label=label, style=LabelStyle(style_dict), position=x, y_offset=y, offset=offset, metadata=metadata
    )


def _parse_edge(
        cid: str, cell: ET.Element, metadata: dict[str, str], scale: float, labels: list[DrawIOEdgeLabel] | None = None
) -> DrawIOEdge:
    if labels is None:
        labels = []

    geo = cell.find('mxGeometry')
    if geo is None:
        raise ParseError(f'Edge cell {cid} missing mxGeometry.')

    source_id = cell.get('source')
    target_id = cell.get('target')

    style_str = cell.get('style', '')
    style_dict = _parse_style_string(style_str)

    waypoints = []
    if (arr := geo.find('Array[@as="points"]')) is not None:
        for pt in arr.findall('mxPoint'):
            pt_x = float(pt.get('x', 0)) * scale
            pt_y = float(pt.get('y', 0)) * scale
            waypoints.append(Point(pt_x, pt_y))

    fixed_source, fixed_target = None, None
    if (source_pt := geo.find('mxPoint[@as="sourcePoint"]')) is not None:
        pt_x = float(source_pt.get('x', 0)) * scale
        pt_y = float(source_pt.get('y', 0)) * scale
        fixed_source = Point(pt_x, pt_y)
    if (target_pt := geo.find('mxPoint[@as="targetPoint"]')) is not None:
        pt_x = float(target_pt.get('x', 0)) * scale
        pt_y = float(target_pt.get('y', 0)) * scale
        fixed_target = Point(pt_x, pt_y)

    router_raw = str(style_dict.get('edgestyle', '')).lower()

    router: RouterType
    if not router_raw or router_raw == 'none':
        router = 'straight'
    elif router_raw == 'orthogonaledgestyle':
        router = 'orthogonal'
    elif router_raw == 'elbowedgestyle':
        router = 'elbow'
    elif router_raw in ('entityrelationedgestyle', 'loopedgestyle', 'segmentedgestyle'):
        raise ParseError(f'Unsupported edge style: {router_raw}. Please use straight or orthogonal routing.')
    else:
        raise ParseError(f'Unknown edge style: {router_raw}')

    return DrawIOEdge(
            id=cid,
            source_id=source_id,
            target_id=target_id,
            waypoints=waypoints,
            router=router,
            style=EdgeStyle(style_dict),
            metadata=metadata,
            fixed_source=fixed_source,
            fixed_target=fixed_target,
            labels=labels,
    )
