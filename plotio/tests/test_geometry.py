import pytest

from plotio.core import BoundingBox, DrawIOEdge, DrawIONode, Point
from plotio.geometry import intersect_ray_with_geometry, resolve_node_terminal, route_orthogonal
from plotio.styles import EdgeStyle, NodeStyle


def test_route_orthogonal_same_point():
    start = Point(10, 10)
    end = Point(10, 10)

    path = route_orthogonal(start, end)

    assert len(path) == 0


def test_route_orthogonal_implicit_vertical_dominant():
    # dx = 10, dy = 50 -> dominant vertical direction.
    start = Point(0, 0)
    end = Point(10, 50)

    path = route_orthogonal(start, end)

    # Vertical -> Horiz -> Vertical
    assert len(path) == 2
    assert path[0] == Point(0, 25)
    assert path[1] == Point(10, 25)


def test_route_orthogonal_implicit_horizontal_dominant():
    # dx = 50, dy = 10 -> dominant horizontal direction.
    start = Point(0, 0)
    end = Point(50, 10)

    path = route_orthogonal(start, end)

    # Horiz -> Vert -> Horiz
    assert len(path) == 2
    assert path[0] == Point(25, 0)
    assert path[1] == Point(25, 10)


def test_route_orthogonal_both_horizontal():
    # Explicitly force horizontal exits and entries.
    start = Point(0, 0)
    end = Point(100, 100)
    style = {'exitx': '1', 'entryx': '0'}

    path = route_orthogonal(start, end, style)

    # Horiz -> Vert -> Horiz
    assert len(path) == 2
    assert path[0] == Point(50, 0)
    assert path[1] == Point(50, 100)


def test_route_orthogonal_both_vertical():
    # Explicitly force vertical exits and entries.
    start = Point(0, 0)
    end = Point(100, 100)
    style = {'exity': '1', 'entryy': '0'}

    path = route_orthogonal(start, end, style)

    # Vert -> Horiz -> Vert
    assert len(path) == 2
    assert path[0] == Point(0, 50)
    assert path[1] == Point(100, 50)


def test_route_orthogonal_exit_horizontal_entry_vertical():
    # Force horizontal exit, vertical entry (L-shape).
    start = Point(0, 0)
    end = Point(100, 100)
    style = {'exitx': '1', 'entryy': '0'}

    path = route_orthogonal(start, end, style)

    # L-shape: Horiz -> Vert -> point should be at (end.x, start.y)
    assert len(path) == 1
    assert path[0] == Point(100, 0)


def test_route_orthogonal_exit_vertical_entry_horizontal():
    # Force vertical exit, horizontal entry (L-shape).
    start = Point(0, 0)
    end = Point(100, 100)
    style = {'exity': '1', 'entryx': '1'}

    path = route_orthogonal(start, end, style)

    # L-shape: Vert -> Horiz -> point should be at (start.x, end.y)
    assert len(path) == 1
    assert path[0] == Point(0, 100)


def test_intersect_ray_ellipse():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'ellipse')
    start = Point(50, 50)
    target = Point(100, 50)

    p = intersect_ray_with_geometry(start, target, node)

    assert p.x == 100
    assert p.y == 50


def test_intersect_ray_rectangle_x_bound():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle')
    start = Point(50, 50)
    target = Point(200, 50)

    p = intersect_ray_with_geometry(start, target, node)

    assert p.x == 100
    assert p.y == 50


def test_intersect_ray_rectangle_y_bound():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    start = Point(50, -50)
    target = Point(50, 50)

    p = intersect_ray_with_geometry(start, target, node)

    assert p.x == 50
    assert p.y == 0


def test_intersect_ray_no_hit():
    # Ray points strictly away from the box -> t_min stays float('inf') -> sets to 0
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    start = Point(150, 150)
    target = Point(200, 200)

    p = intersect_ray_with_geometry(start, target, node)

    assert p.x == 150
    assert p.y == 150


def test_intersect_ray_same_point():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    start = Point(50, 50)
    target = Point(50, 50)

    with pytest.raises(ValueError, match='Ray intersection failed'):
        intersect_ray_with_geometry(start, target, node)


def test_resolve_node_terminal_explicit_entry():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'entryx': '1', 'entryy': '0.5'}))

    pt = resolve_node_terminal(node, edge, is_source=False)

    assert pt.x == 100
    assert pt.y == 50


def test_resolve_node_terminal_explicit_hint_horizontal_dominant():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    hint = Point(200, 75)

    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint, hint_is_explicit=True)

    assert pt.x == 100
    assert pt.y == 75


def test_resolve_node_terminal_explicit_hint_vertical_dominant():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    hint = Point(75, 200)

    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint, hint_is_explicit=True)

    assert pt.x == 75
    assert pt.y == 100


def test_resolve_node_terminal_implicit_hint_horizontal_dominant():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    hint = Point(200, 50)

    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint)

    assert pt.x == 100
    assert pt.y == 50


def test_resolve_node_terminal_implicit_hint_vertical_dominant():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    hint = Point(50, 200)

    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint)

    assert pt.x == 50
    assert pt.y == 100


def test_resolve_node_terminal_implicit_straight_routing():

    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [])
    hint = Point(200, 50)

    pt = resolve_node_terminal(node, edge, is_source=True, hint_pt=hint)

    assert pt.x == 100
    assert pt.y == 50


def test_resolve_node_terminal_missing_hint_error():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [])

    with pytest.raises(ValueError, match='Cannot resolve terminal'):
        resolve_node_terminal(node, edge, is_source=True)


def test_resolve_node_terminal_invalid_explicit_error():
    node = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'entryx': '1'}))

    with pytest.raises(ValueError, match='Invalid terminal definition'):
        resolve_node_terminal(node, edge, is_source=False)
