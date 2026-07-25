"""Geometry and intersection logic.

Math and geometry logic is preserved exactly as in the original drawio_render_utils.py.
"""

import numpy as np

from .core import Point


def intersect_ray_with_geometry(start: Point, target: Point, node) -> Point:
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


def route_orthogonal(start: Point, end: Point, style: dict | None = None) -> list[Point]:
    if style is None:
        style = {}

    if abs(start.x - end.x) <= 1e-5 or abs(start.y - end.y) <= 1e-5:
        return []

    ex_x = float(style.get('exitx', 0.5))
    ex_y = float(style.get('exity', 0.5))
    en_x = float(style.get('entryx', 0.5))
    en_y = float(style.get('entryy', 0.5))

    exit_horizontal = ex_x in [0, 1]
    exit_vertical = ex_y in [0, 1]
    entry_horizontal = en_x in [0, 1]
    entry_vertical = en_y in [0, 1]

    if not exit_horizontal and not exit_vertical:
        if abs(start.x - end.x) >= abs(start.y - end.y):
            exit_horizontal = True
        else:
            exit_vertical = True

    if not entry_horizontal and not entry_vertical:
        if abs(start.x - end.x) >= abs(start.y - end.y):
            entry_horizontal = True
        else:
            entry_vertical = True

    if exit_horizontal and entry_horizontal:
        mid_x = (start.x + end.x) / 2
        return [Point(mid_x, start.y), Point(mid_x, end.y)]
    elif exit_vertical and entry_vertical:
        mid_y = (start.y + end.y) / 2
        return [Point(start.x, mid_y), Point(end.x, mid_y)]
    elif exit_horizontal:
        return [Point(end.x, start.y)]
    else:
        return [Point(start.x, end.y)]


def resolve_node_terminal(
    node, edge, is_source: bool, hint_pt: Point | None = None, hint_is_explicit: bool = False
) -> Point:
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
