"""Geometry and intersection logic.

Math and geometry logic is preserved exactly as in the original drawio_render_utils.py.
"""

import numpy as np

from .core import BoundingBox, DrawIOEdge, DrawIONode, Point


def intersect_ray_with_geometry(start: Point, target: Point, node: DrawIONode) -> Point:
    """Calculate the intersection point of a ray from start to target with the given node's bounding box.

    Args:
        start (Point): The start point of the ray.
        target (Point): The target point the ray passes through.
        node: The node containing the bounding box to intersect with.

    Raises:
        ValueError: If start and target are the same point.

    Returns:
        Point: The intersection point on the node's perimeter.

    """
    bbox = node.bounding_box
    dx = target.x - start.x
    dy = target.y - start.y

    if dx == 0 and dy == 0:
        raise ValueError(f'Ray intersection failed: start and target are the same point for node {node.id}')

    if node.shape == 'ellipse':
        # Ellipse intersection
        rx, ry = bbox.w / 2, bbox.h / 2
        term = (dx / (rx or 1e-9)) ** 2 + (dy / (ry or 1e-9)) ** 2
        t = 1.0 / np.sqrt(term) if term > 0 else 0

        p = Point(start.x + t * dx, start.y + t * dy)
        return p
    else:
        # Rectangle intersection
        t_min = float('inf')

        # X boundaries
        for bx in [bbox.x, bbox.x + bbox.w]:
            if dx != 0:
                t = (bx - start.x) / dx
                if t > 0 and bbox.y <= start.y + t * dy <= bbox.y + bbox.h:
                    t_min = min(t_min, t)

        # Y boundaries
        for by in [bbox.y, bbox.y + bbox.h]:
            if dy != 0:
                t = (by - start.y) / dy
                if t > 0 and bbox.x <= start.x + t * dx <= bbox.x + bbox.w:
                    t_min = min(t_min, t)

        if t_min == float('inf'):
            t_min = 0

        p = Point(start.x + t_min * dx, start.y + t_min * dy)
        return p


def label_anchor(
    bbox: BoundingBox,
    position_x: str,
    position_y: str,
    halignment: str,
    valignment: str,
    global_spacing: float,
    spacing_top: float,
    spacing_bottom: float,
    spacing_left: float,
    spacing_right: float,
) -> Point:
    """Calculate the anchor point for a label based on alignment and offsets.

    Args:
        bbox (BoundingBox): The bounding box of the element.
        position_x (str): Horizontal position relative to the element (left, center, right).
        position_y (str): Vertical position relative to the element (top, middle, bottom).
        halignment (str): Horizontal alignment inside the label area.
        valignment (str): Vertical alignment inside the label area.
        global_spacing (float): Global spacing applied to all sides.
        spacing_top (float): Extra top spacing.
        spacing_bottom (float): Extra bottom spacing.
        spacing_left (float): Extra left spacing.
        spacing_right (float): Extra right spacing.

    Raises:
        ValueError: If an unsupported position is specified.

    Returns:
        Point: The calculated anchor point.

    """
    match position_x:
        case 'left':
            x = bbox.x - (global_spacing + spacing_right)
        case 'right':
            x = bbox.x + bbox.w + (global_spacing + spacing_left)
        case 'center':
            match halignment:
                case 'left':
                    x = bbox.x + (global_spacing + spacing_left)
                case 'right':
                    x = bbox.x + bbox.w - (global_spacing + spacing_right)
                case _:
                    x = bbox.x + bbox.w / 2 + (spacing_left - spacing_right) / 2
        case _:
            raise ValueError(f'Unsupported label horizontal position: {position_x}')

    match position_y:
        case 'top':
            y = bbox.y - (global_spacing + spacing_bottom)
        case 'bottom':
            y = bbox.y + bbox.h + (global_spacing + spacing_top)
        case 'middle':
            match valignment:
                case 'top':
                    y = bbox.y + (global_spacing + spacing_top)
                case 'bottom':
                    y = bbox.y + bbox.h - (global_spacing + spacing_bottom)
                case _:
                    y = bbox.y + bbox.h / 2 + (spacing_top - spacing_bottom) / 2
        case _:
            raise ValueError(f'Unsupported label vertical position: {position_y}')

    return Point(x, y)


def get_path_point_and_tangent(path: list[Point], relative_pos: float) -> tuple[Point, Point]:
    """Calculate the point and tangent vector along a path at a relative position.

    Args:
        path (list[Point]): A sequence of points defining the path.
        relative_pos (float): The relative position along the path (-1 to 1).

    Returns:
        tuple[Point, Point]: The coordinate point and tangent unit vector at the position.

    """
    if not path:
        return Point(0, 0), Point(1, 0)
    if len(path) == 1:
        return path[0], Point(1, 0)

    lengths = []
    total_len = 0.0
    for i in range(len(path) - 1):
        length = (path[i + 1] - path[i]).norm()
        lengths.append(length)
        total_len += length

    dist = (relative_pos + 1) / 2 * total_len
    dist = max(0.0, min(total_len, dist))

    current_dist = 0.0
    for i, length in enumerate(lengths):
        if current_dist + length >= dist - 1e-9:
            remaining = dist - current_dist
            p1 = path[i]
            p2 = path[i + 1]
            if length > 0:
                t = remaining / length
                pos = p1 + (p2 - p1) * t
                tangent = (p2 - p1).unit()
            else:
                pos = p1
                tangent = Point(1, 0)

            return pos, tangent
        current_dist += length

    p1 = path[-2]
    p2 = path[-1]
    return p2, (p2 - p1).unit()


def resolve_node_terminal(
    node: DrawIONode, edge: DrawIOEdge, is_source: bool, hint_pt: Point | None = None, hint_is_explicit: bool = False
) -> Point:
    """Resolve the precise terminal point on a node for an edge.

    Args:
        node (DrawIONode): The node to attach to.
        edge (DrawIOEdge): The edge being routed.
        is_source (bool): True if resolving the source terminal, False for target.
        hint_pt (Point | None, optional): An optional hint point to route towards. Defaults to None.
        hint_is_explicit (bool, optional): True if the hint point is explicitly defined by the user. Defaults to False.

    Raises:
        ValueError: If the terminal definition is invalid or missing when required.

    Returns:
        Point: The resolved connection point on the node perimeter.

    """
    bbox = node.bounding_box
    center = bbox.center

    if is_source:
        x_key, y_key = 'exitx', 'exity'
    else:
        x_key, y_key = 'entryx', 'entryy'

    px_str = edge.style.raw_styles.get(x_key)
    py_str = edge.style.raw_styles.get(y_key)

    if px_str is not None and py_str is not None:
        px = float(px_str)
        py = float(py_str)
        return Point(bbox.x + px * bbox.w, bbox.y + py * bbox.h)
    elif px_str is None and py_str is None:
        if hint_pt is not None:
            if edge.style.raw_styles.get('edgestyle') == 'orthogonaledgestyle':
                dx = hint_pt.x - center.x
                dy = hint_pt.y - center.y

                if abs(dx) >= abs(dy):
                    px = 1.0 if dx > 0 else 0.0
                    if hint_is_explicit and bbox.h > 0:
                        py = (hint_pt.y - bbox.y) / bbox.h
                        py = max(0.0, min(1.0, py))
                    else:
                        py = 0.5
                else:
                    if hint_is_explicit and bbox.w > 0:
                        px = (hint_pt.x - bbox.x) / bbox.w
                        px = max(0.0, min(1.0, px))
                    else:
                        px = 0.5
                    py = 1.0 if dy > 0 else 0.0

                return Point(bbox.x + px * bbox.w, bbox.y + py * bbox.h)

            return intersect_ray_with_geometry(center, hint_pt, node)
        else:
            raise ValueError('Cannot resolve terminal')
    else:
        raise ValueError('Invalid terminal definition')
