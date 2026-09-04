"""Tests for geometry logic."""

import math

import pytest

from plotio.core import BoundingBox, DrawIOEdge, DrawIONode, Point
from plotio.errors import RenderError
from plotio.geometry import get_path_point_and_tangent, intersect_ray_with_geometry, label_anchor, resolve_node_terminal
from plotio.styles import EdgeStyle, NodeStyle


def test_intersect_ray_ellipse() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'ellipse', '', NodeStyle())
    start = Point(50, 50)
    target = Point(100, 50)
    p = intersect_ray_with_geometry(start, target, node)
    assert p.x == 100
    assert p.y == 50


def test_intersect_ray_rectangle_x_bound() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    start = Point(50, 50)
    target = Point(200, 50)
    p = intersect_ray_with_geometry(start, target, node)
    assert p.x == 100
    assert p.y == 50


def test_intersect_ray_rectangle_y_bound() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    start = Point(50, -50)
    target = Point(50, 50)
    p = intersect_ray_with_geometry(start, target, node)
    assert p.x == 50
    assert p.y == 0


def test_intersect_ray_no_hit() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    start = Point(150, 150)
    target = Point(200, 200)
    p = intersect_ray_with_geometry(start, target, node)
    assert p.x == 150
    assert p.y == 150


def test_intersect_ray_same_point() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    start = Point(50, 50)
    target = Point(50, 50)
    with pytest.raises(RenderError, match='Ray intersection failed'):
        intersect_ray_with_geometry(start, target, node)


def test_resolve_node_terminal_explicit_entry() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'entryx': '1', 'entryy': '0.5'}))
    pt = resolve_node_terminal(node, edge, is_source=False, hint_pt=None)
    assert pt.x == 100
    assert pt.y == 50


def test_resolve_node_terminal_explicit_hint_horizontal_dominant() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    hint = Point(200, 75)
    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint, hint_is_explicit=True)
    assert pt.x == 100
    assert pt.y == 75


def test_resolve_node_terminal_explicit_hint_vertical_dominant() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    hint = Point(75, 200)
    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint, hint_is_explicit=True)
    assert pt.x == 75
    assert pt.y == 100


def test_resolve_node_terminal_implicit_hint_horizontal_dominant() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    hint = Point(200, 50)
    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint)
    assert pt.x == 100
    assert pt.y == 50


def test_resolve_node_terminal_implicit_hint_vertical_dominant() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    hint = Point(50, 200)
    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint)
    assert pt.x == 50
    assert pt.y == 100


def test_resolve_node_terminal_implicit_straight_routing() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle())
    hint = Point(200, 50)
    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint)
    assert pt.x == 100
    assert pt.y == 50


def test_resolve_node_terminal_missing_hint_error() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle())
    with pytest.raises(RenderError, match='Cannot resolve terminal'):
        resolve_node_terminal(node, edge, is_source=True, hint_pt=None)


def test_resolve_node_terminal_invalid_explicit_error() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'entryx': '1'}))
    with pytest.raises(RenderError, match='Invalid terminal definition'):
        resolve_node_terminal(node, edge, is_source=False, hint_pt=None)


def test_label_anchor_center_middle() -> None:
    bbox = BoundingBox(10, 10, 100, 100)
    p = label_anchor(bbox, 'center', 'middle', 'center', 'middle', 0, 0, 0, 0, 0)
    assert p.x == 60
    assert p.y == 60


def test_label_anchor_left_top() -> None:
    bbox = BoundingBox(10, 10, 100, 100)
    p = label_anchor(bbox, 'left', 'top', 'right', 'bottom', 5, 5, 5, 5, 5)
    assert p.x == 10 - (5 + 5)
    assert p.y == 10 - (5 + 5)


def test_label_anchor_center_left() -> None:
    bbox = BoundingBox(10, 10, 100, 100)
    p = label_anchor(bbox, 'center', 'middle', 'left', 'top', 0, 1, 2, 3, 4)
    assert p.x == 10 + 3
    assert p.y == 10 + 1


def test_label_anchor_center_right() -> None:
    bbox = BoundingBox(10, 10, 100, 100)
    p = label_anchor(bbox, 'center', 'middle', 'right', 'bottom', 0, 1, 2, 3, 4)
    assert p.x == 110 - 4
    assert p.y == 110 - 2


def test_label_anchor_right_bottom() -> None:
    bbox = BoundingBox(10, 10, 100, 100)
    p = label_anchor(bbox, 'right', 'bottom', 'center', 'middle', 0, 1, 2, 3, 4)
    assert p.x == 110 + 3
    assert p.y == 110 + 1


def test_label_anchor_unsupported_horizontal() -> None:
    bbox = BoundingBox(10, 10, 100, 100)
    with pytest.raises(RenderError, match='Unsupported label horizontal position'):
        label_anchor(bbox, 'invalid', 'middle', 'center', 'middle', 0, 0, 0, 0, 0)


def test_label_anchor_unsupported_vertical() -> None:
    bbox = BoundingBox(10, 10, 100, 100)
    with pytest.raises(RenderError, match='Unsupported label vertical position'):
        label_anchor(bbox, 'center', 'invalid', 'center', 'middle', 0, 0, 0, 0, 0)


def test_get_path_point_and_tangent_empty() -> None:
    pt, tgt = get_path_point_and_tangent([], 0)
    assert pt == Point(0, 0)
    assert tgt == Point(1, 0)


def test_get_path_point_and_tangent_single() -> None:
    pt, tgt = get_path_point_and_tangent([Point(10, 10)], 0)
    assert pt == Point(10, 10)
    assert tgt == Point(1, 0)


def test_get_path_point_and_tangent_start() -> None:
    path = [Point(0, 0), Point(100, 0)]
    pt, tgt = get_path_point_and_tangent(path, -1)
    assert pt == Point(0, 0)
    assert tgt == Point(1, 0)


def test_get_path_point_and_tangent_end() -> None:
    path = [Point(0, 0), Point(100, 0)]
    pt, tgt = get_path_point_and_tangent(path, 1)
    assert pt == Point(100, 0)
    assert tgt == Point(1, 0)


def test_get_path_point_and_tangent_midpoint() -> None:
    path = [Point(0, 0), Point(100, 0)]
    pt, tgt = get_path_point_and_tangent(path, 0)
    assert pt == Point(50, 0)
    assert tgt == Point(1, 0)


def test_get_path_point_and_tangent_zero_length() -> None:
    pt, tgt = get_path_point_and_tangent([Point(10, 10), Point(10, 10)], 0)
    assert pt == Point(10, 10)
    assert tgt == Point(1, 0)


def test_get_path_point_and_tangent_nan_fallback() -> None:
    pt, tgt = get_path_point_and_tangent([Point(0, 0), Point(float('nan'), 0)], 1.0)
    assert math.isnan(pt.x)
    assert math.isnan(tgt.x)
