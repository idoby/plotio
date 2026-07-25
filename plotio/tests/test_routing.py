"""Tests for routing logic."""

from plotio.core import BoundingBox, DrawIOEdge, DrawIOGraph, DrawIONode, Point
from plotio.routing import calculate_edge_path, resolve_endpoints, route_orthogonal, snap_orthogonal
from plotio.styles import EdgeStyle, NodeStyle


def test_route_orthogonal_same_point() -> None:
    start = Point(10, 10)
    end = Point(10, 10)
    path = route_orthogonal(start, end, {})
    assert len(path) == 0


def test_route_orthogonal_implicit_vertical_dominant() -> None:
    start = Point(0, 0)
    end = Point(10, 50)
    path = route_orthogonal(start, end, {})
    assert len(path) == 2
    assert path[0] == Point(0, 25)
    assert path[1] == Point(10, 25)


def test_route_orthogonal_implicit_horizontal_dominant() -> None:
    start = Point(0, 0)
    end = Point(50, 10)
    path = route_orthogonal(start, end, {})
    assert len(path) == 2
    assert path[0] == Point(25, 0)
    assert path[1] == Point(25, 10)


def test_route_orthogonal_both_horizontal() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    path = route_orthogonal(start, end, {'exitx': '1', 'entryx': '0'})
    assert len(path) == 2
    assert path[0] == Point(50, 0)
    assert path[1] == Point(50, 100)


def test_route_orthogonal_both_vertical() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    path = route_orthogonal(start, end, {'exity': '1', 'entryy': '0'})
    assert len(path) == 2
    assert path[0] == Point(0, 50)
    assert path[1] == Point(100, 50)


def test_route_orthogonal_exit_horizontal_entry_vertical() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    path = route_orthogonal(start, end, {'exitx': '1', 'entryy': '0'})
    assert len(path) == 1
    assert path[0] == Point(100, 0)


def test_route_orthogonal_exit_vertical_entry_horizontal() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    path = route_orthogonal(start, end, {'exity': '1', 'entryx': '1'})
    assert len(path) == 1
    assert path[0] == Point(0, 100)


def test_snap_orthogonal_minor() -> None:
    path = [Point(0, 0.005), Point(50, 0), Point(100, 0.005)]
    snapped = snap_orthogonal(path)
    assert snapped[0] == Point(0, 0)
    assert snapped[-1] == Point(100, 0)


def test_snap_orthogonal_major() -> None:
    path2 = [Point(0, 1), Point(50, 0), Point(100, 1)]
    snapped2 = snap_orthogonal(path2)
    assert snapped2[0] == Point(0, 1)
    assert snapped2[-1] == Point(100, 1)


def test_snap_orthogonal_x() -> None:
    path3 = [Point(0.005, 0), Point(0, 50), Point(-0.005, 100)]
    snapped3 = snap_orthogonal(path3)
    assert snapped3[0] == Point(0, 0)
    assert snapped3[-1] == Point(0, 100)


def _setup_graph() -> DrawIOGraph:
    node1 = DrawIONode('1', BoundingBox(0, 0, 100, 100), 'rectangle', '', NodeStyle())
    node2 = DrawIONode('2', BoundingBox(200, 0, 100, 100), 'rectangle', '', NodeStyle())
    return DrawIOGraph(width=1000, height=1000, coord_scale=1, nodes={'1': node1, '2': node2}, edges=[])


def test_resolve_endpoints_implicit() -> None:
    graph = _setup_graph()
    edge = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle())
    s, e = resolve_endpoints(edge, graph)
    assert s is not None
    assert e is not None
    assert s.x == 100
    assert s.y == 50
    assert e.x == 200
    assert e.y == 50


def test_resolve_endpoints_fixed_fallback() -> None:
    graph = _setup_graph()
    edge2 = DrawIOEdge('e2', None, None, [], fixed_source=Point(10, 10), fixed_target=Point(20, 20), style=EdgeStyle())
    s2, e2 = resolve_endpoints(edge2, graph)
    assert s2 == Point(10, 10)
    assert e2 == Point(20, 20)


def test_resolve_endpoints_fixed_target() -> None:
    graph = _setup_graph()
    edge4 = DrawIOEdge('e4', '1', '2', [], style=EdgeStyle({'entryx': '1', 'entryy': '0.5'}))
    s4, e4 = resolve_endpoints(edge4, graph)
    assert s4 is not None
    assert e4 is not None
    assert s4.x == 100
    assert s4.y == 50
    assert e4.x == 300
    assert e4.y == 50


def test_resolve_endpoints_waypoints() -> None:
    graph = _setup_graph()
    edge5 = DrawIOEdge('e5', '1', '2', [Point(150, 50)], style=EdgeStyle())
    s5, e5 = resolve_endpoints(edge5, graph)
    assert s5 is not None
    assert e5 is not None
    assert s5.x == 100
    assert s5.y == 50
    assert e5.x == 200
    assert e5.y == 50


def test_resolve_endpoints_missing_source() -> None:
    graph = _setup_graph()
    edge6 = DrawIOEdge('e6', 'MISSING', '2', [], style=EdgeStyle({'entryx': '0', 'entryy': '0'}))
    s6, e6 = resolve_endpoints(edge6, graph)
    assert s6 is None
    assert e6 is not None
    assert e6 is not None
    assert e6.x == 200
    assert e6.y == 0


def test_calculate_edge_path_waypoints() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    edge1 = DrawIOEdge('e1', '1', '2', [Point(50, 50)], style=EdgeStyle())
    path1 = calculate_edge_path(edge1, start, end)
    assert path1 == [start, Point(50, 50), end]


def test_calculate_edge_path_orthogonal() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    edge2 = DrawIOEdge('e1', '1', '2', [], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    path2 = calculate_edge_path(edge2, start, end)
    assert len(path2) == 4


def test_calculate_edge_path_curved() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    edge3 = DrawIOEdge('e1', '1', '2', [Point(50, 0), Point(50, 100)], style=EdgeStyle({'curved': '1'}))
    path3 = calculate_edge_path(edge3, start, end)
    assert len(path3) == 20


def test_calculate_edge_path_straight() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    edge4 = DrawIOEdge('e4', '1', '2', [], style=EdgeStyle({'edgestyle': 'straight'}))
    path4 = calculate_edge_path(edge4, start, end)
    assert path4 == [start, end]
