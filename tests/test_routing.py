"""Tests for routing logic."""

from typing import cast
from unittest.mock import patch

import pytest

from plotio.core import BoundingBox, DrawIOEdge, DrawIOGraph, DrawIONode, Point, RouterType
from plotio.errors import RenderError
from plotio.routing import _resolve_target, calculate_edge_path, resolve_endpoints, route_orthogonal, snap_orthogonal
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
    graph = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={}, edges=[])
    edge1 = DrawIOEdge('e1', '1', '2', [Point(50, 50)], style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    path1 = calculate_edge_path(edge1, graph, start, end)
    assert len(path1) == 3


def test_calculate_edge_path_orthogonal() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    graph = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={}, edges=[])
    edge2 = DrawIOEdge('e1', '1', '2', [], router='orthogonal', style=EdgeStyle({'edgestyle': 'orthogonaledgestyle'}))
    path2 = calculate_edge_path(edge2, graph, start, end)
    assert len(path2) == 4


def test_calculate_edge_path_curved() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    graph = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={}, edges=[])
    edge3 = DrawIOEdge('e1', '1', '2', [Point(50, 50)], style=EdgeStyle({'curved': '1'}))
    path3 = calculate_edge_path(edge3, graph, start, end)
    assert len(path3) > 3


def test_calculate_edge_path_straight() -> None:
    start = Point(0, 0)
    end = Point(100, 100)
    graph = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={}, edges=[])
    edge4 = DrawIOEdge('e4', '1', '2', [])
    path4 = calculate_edge_path(edge4, graph, start, end)
    assert len(path4) == 2
    assert path4[0] == start
    assert path4[1] == end


def test_calculate_edge_path_elbow() -> None:
    start = Point(100, 50)
    end = Point(300, 250)
    node1 = DrawIONode('1', BoundingBox(0, 0, 100, 100), shape='rectangle')
    node2 = DrawIONode('2', BoundingBox(300, 200, 100, 100), shape='rectangle')
    graph = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={'1': node1, '2': node2}, edges=[])

    # SideToSide default (horizontal distance > vertical)
    edge5 = DrawIOEdge('e5', '1', '2', [], router='elbow', style=EdgeStyle({'edgestyle': 'elbowedgestyle'}))
    path5 = calculate_edge_path(edge5, graph, start, end)

    assert len(path5) == 4
    assert path5[0] == start
    assert path5[1] == Point(200, 50)
    assert path5[2] == Point(200, 250)
    assert path5[3] == end

    # TopToBottom override
    edge6 = DrawIOEdge(
        'e6', '1', '2', [], router='elbow', style=EdgeStyle({'edgestyle': 'elbowedgestyle', 'elbow': 'vertical'})
    )
    path6 = calculate_edge_path(edge6, graph, start, end)
    assert len(path6) == 4
    assert path6[1] == Point(50, 150)


def test_calculate_edge_path_elbow_overlapping() -> None:
    # Overlapping horizontally, y1 inside tgt, y2 outside src (forces len(waypoints) == 1 in SideToSide)
    node1 = DrawIONode('1', BoundingBox(0, 0, 100, 40), shape='rectangle')
    node2 = DrawIONode('2', BoundingBox(0, -50, 100, 200), shape='rectangle')
    graph1 = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={'1': node1, '2': node2}, edges=[])
    edge1 = DrawIOEdge('e1', '1', '2', [], router='elbow', style=EdgeStyle({'edgestyle': 'elbowedgestyle'}))
    calculate_edge_path(edge1, graph1, Point(0, 0), Point(0, 0))

    # Overlapping vertically, x1 inside tgt, x2 outside src (forces len(waypoints) == 1 in TopToBottom)
    node3 = DrawIONode('3', BoundingBox(0, 0, 40, 100), shape='rectangle')
    node4 = DrawIONode('4', BoundingBox(-50, 0, 200, 100), shape='rectangle')
    graph2 = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={'3': node3, '4': node4}, edges=[])
    edge2 = DrawIOEdge(
        'e2', '3', '4', [], router='elbow', style=EdgeStyle({'edgestyle': 'elbowedgestyle', 'elbow': 'vertical'})
    )
    calculate_edge_path(edge2, graph2, Point(0, 0), Point(0, 0))

    # Empty waypoints fallback (when nodes have 0 size and overlap exactly)
    node5 = DrawIONode('5', BoundingBox(0, 0, 0, 0), shape='rectangle')
    node6 = DrawIONode('6', BoundingBox(0, 0, 0, 0), shape='rectangle')
    graph3 = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={'5': node5, '6': node6}, edges=[])
    edge3 = DrawIOEdge('e3', '5', '6', [], router='elbow', style=EdgeStyle({'edgestyle': 'elbowedgestyle'}))
    # Catch RenderError because ray from 0,0 to 0,0 fails
    with pytest.raises(RenderError):
        resolve_endpoints(edge3, graph3)
    # Test _resolve_target explicitly to cover line 270 empty elbow_pts
    with pytest.raises(RenderError):
        _resolve_target(edge3, graph3, Point(0, 0), False)


def test_custom_routing_center_fallback() -> None:
    node1 = DrawIONode('1', BoundingBox(0, 0, 100, 40), shape='rectangle')
    node2 = DrawIONode('2', BoundingBox(0, -50, 100, 200), shape='rectangle')
    graph1 = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={'1': node1, '2': node2}, edges=[])
    edge1 = DrawIOEdge('e1', '1', '2', [], router='elbow', style=EdgeStyle({'edgestyle': 'elbowedgestyle'}))

    with (
        patch('plotio.routing.pt_in_rect', side_effect=[False, False, True, True]),
        pytest.raises(NotImplementedError, match='Custom routing centers'),
    ):
        calculate_edge_path(edge1, graph1, Point(0, 0), Point(0, 0))

    node3 = DrawIONode('3', BoundingBox(0, 0, 40, 100), shape='rectangle')
    node4 = DrawIONode('4', BoundingBox(-50, 0, 200, 100), shape='rectangle')
    graph2 = DrawIOGraph(width=1000, height=1000, coord_scale=1.0, nodes={'3': node3, '4': node4}, edges=[])
    edge2 = DrawIOEdge(
        'e2', '3', '4', [], router='elbow', style=EdgeStyle({'edgestyle': 'elbowedgestyle', 'elbow': 'vertical'})
    )

    with (
        patch('plotio.routing.pt_in_rect', side_effect=[False, False, True, True]),
        pytest.raises(NotImplementedError, match='Custom routing centers'),
    ):
        calculate_edge_path(edge2, graph2, Point(0, 0), Point(0, 0))


def test_invalid_router() -> None:
    edge = DrawIOEdge('e1', '1', '2', [], router=cast(RouterType, 'invalid'))
    graph = DrawIOGraph(1000, 1000, 1.0, {}, [])
    with pytest.raises(AssertionError):
        calculate_edge_path(edge, graph, Point(0, 0), Point(100, 100))

    # Also test with curves enabled
    edge2 = DrawIOEdge(
        'e2', '1', '2', [Point(50, 50)], router=cast(RouterType, 'invalid'), style=EdgeStyle({'curved': '0'})
    )
    with pytest.raises(AssertionError):
        calculate_edge_path(edge2, graph, Point(0, 0), Point(100, 100))
