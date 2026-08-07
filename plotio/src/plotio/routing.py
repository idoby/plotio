"""Edge routing and path generation logic."""

from typing import assert_never

from plotio.core import BoundingBox, DrawIOEdge, DrawIOGraph, Point
from plotio.curves import interpolate_path
from plotio.geometry import resolve_node_terminal
from plotio.styles import StyleValue


def route_orthogonal(start: Point, end: Point, style: dict[str, StyleValue]) -> list[Point]:
    """Generate orthogonal waypoints between two points.

    Args:
        start (Point): The start point.
        end (Point): The end point.
        style (dict[str, StyleValue]): The raw styles dictionary of the edge.

    Returns:
        list[Point]: A list of orthogonal waypoints to route between start and end.

    """
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

    # Infer missing orientations based on relative geometry
    # If neither is explicit, use dominant direction
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
        # Z-shape: Horiz -> Vert -> Horiz
        mid_x = (start.x + end.x) / 2
        return [Point(mid_x, start.y), Point(mid_x, end.y)]
    elif exit_vertical and entry_vertical:
        mid_y = (start.y + end.y) / 2
        return [Point(start.x, mid_y), Point(end.x, mid_y)]
    elif exit_horizontal:
        return [Point(end.x, start.y)]
    else:
        return [Point(start.x, end.y)]


def snap_orthogonal(path: list[Point]) -> list[Point]:
    """Snap near-orthogonal lines strictly to axes.

    Args:
        path (list[Point]): The sequence of points defining the path.

    Returns:
        list[Point]: The new path with nearly orthogonal segments snapped to perfect right angles.

    """
    new_path = list(path)

    for i in [0, -1]:
        p, ref = new_path[i], new_path[i + 1 if i == 0 else i - 1]

        abs_diff = abs(p - ref)
        if abs_diff.x < 0.01:
            new_path[i] = Point(ref.x, p.y)
        elif abs_diff.y < 0.01:
            new_path[i] = Point(p.x, ref.y)

    return new_path


def pt_in_rect(pt_x: float, pt_y: float, bb: BoundingBox) -> bool:
    """Check if a point is within a bounding box."""
    return bb.x <= pt_x <= bb.x + bb.w and bb.y <= pt_y <= bb.y + bb.h


def route_elbow(edge: DrawIOEdge, graph: DrawIOGraph, start_pt: Point, end_pt: Point) -> list[Point]:
    """Generate elbow routing between two points or nodes."""
    source_node = graph.nodes.get(edge.source_id or '')
    target_node = graph.nodes.get(edge.target_id or '')

    src_bb = source_node.bounding_box if source_node else BoundingBox(start_pt.x, start_pt.y, 0, 0)
    tgt_bb = target_node.bounding_box if target_node else BoundingBox(end_pt.x, end_pt.y, 0, 0)

    left = max(src_bb.x, tgt_bb.x)
    right = min(src_bb.x + src_bb.w, tgt_bb.x + tgt_bb.w)
    vertical = abs(left - right) < 1e-5

    horizontal = False
    if not vertical:
        top = max(src_bb.y, tgt_bb.y)
        bottom = min(src_bb.y + src_bb.h, tgt_bb.y + tgt_bb.h)
        horizontal = abs(top - bottom) < 1e-5

    is_vertical = not horizontal and (vertical or edge.style.raw_styles.get('elbow') == 'vertical')
    waypoints: list[Point] = []

    if is_vertical:
        t = max(src_bb.y, tgt_bb.y)
        b = min(src_bb.y + src_bb.h, tgt_bb.y + tgt_bb.h)
        y = b + (t - b) / 2

        x1 = src_bb.x + src_bb.w / 2
        if not pt_in_rect(x1, y, tgt_bb) and not pt_in_rect(x1, y, src_bb):
            waypoints.append(Point(x1, y))

        x2 = tgt_bb.x + tgt_bb.w / 2
        if not pt_in_rect(x2, y, tgt_bb) and not pt_in_rect(x2, y, src_bb):
            waypoints.append(Point(x2, y))

        if len(waypoints) == 1:
            # TODO: Support custom routing centers. This fallback is needed if routingCenterX/Y
            # places the routing center outside the node's bounds.
            raise NotImplementedError('Custom routing centers are not yet supported for Elbow routers.')
    else:
        l = max(src_bb.x, tgt_bb.x)
        r = min(src_bb.x + src_bb.w, tgt_bb.x + tgt_bb.w)
        x = r + (l - r) / 2

        y1 = src_bb.y + src_bb.h / 2
        if not pt_in_rect(x, y1, tgt_bb) and not pt_in_rect(x, y1, src_bb):
            waypoints.append(Point(x, y1))

        y2 = tgt_bb.y + tgt_bb.h / 2
        if not pt_in_rect(x, y2, tgt_bb) and not pt_in_rect(x, y2, src_bb):
            waypoints.append(Point(x, y2))

        if len(waypoints) == 1:
            # TODO: Support custom routing centers. This fallback is needed if routingCenterX/Y
            # places the routing center outside the node's bounds.
            raise NotImplementedError('Custom routing centers are not yet supported for Elbow routers.')

    return waypoints


def calculate_edge_path(edge: DrawIOEdge, graph: DrawIOGraph, start_pt: Point, end_pt: Point) -> list[Point]:
    """Orchestrate waypoints, orthogonal routes, and curved interpolations.

    Args:
        edge (DrawIOEdge): The edge being routed.
        graph (DrawIOGraph): The parent graph.
        start_pt (Point): The resolved start point.
        end_pt (Point): The resolved end point.

    Returns:
        list[Point]: The final sequence of points defining the visual path of the edge.

    """
    if edge.waypoints:
        waypoints = edge.waypoints
    else:
        match edge.router:
            case 'orthogonal':
                waypoints = route_orthogonal(start_pt, end_pt, edge.style.raw_styles)
            case 'elbow':
                waypoints = route_elbow(edge, graph, start_pt, end_pt)
            case 'straight':
                waypoints = []
            case _:
                assert_never(edge.router)

    path = [start_pt] + waypoints + [end_pt]

    if len(path) >= 2:
        if edge.style.raw_styles.get('curved') == '1':
            path = interpolate_path(path)
        else:
            match edge.router:
                case 'orthogonal' | 'elbow':
                    path = snap_orthogonal(path)
                case 'straight':
                    pass
                case _:
                    assert_never(edge.router)

    return path


def _resolve_source(edge: DrawIOEdge, graph: DrawIOGraph) -> tuple[Point | None, bool]:
    """Resolve the precise start point of an edge on its source node."""
    target_center_hint = None
    if edge.target_id and edge.target_id in graph.nodes:
        target_center_hint = graph.nodes[edge.target_id].bounding_box.center

    source_node = graph.nodes[edge.source_id] if edge.source_id and edge.source_id in graph.nodes else None

    target_fixed = edge.style.raw_styles.get('entryx') is not None

    next_hint: Point | None = None
    start_hint_is_explicit = False
    if edge.waypoints:
        next_hint = edge.waypoints[0]
        start_hint_is_explicit = True
    elif edge.fixed_target:
        next_hint = edge.fixed_target
        start_hint_is_explicit = True
    elif target_fixed and edge.target_id and edge.target_id in graph.nodes:
        next_hint = resolve_node_terminal(graph.nodes[edge.target_id], edge, is_source=False)
        start_hint_is_explicit = False
    elif not edge.waypoints and edge.router == 'elbow':
        # Calculate elbow waypoints using centers to get an orthogonal hint
        dummy_start = source_node.bounding_box.center if source_node else Point(0, 0)
        dummy_end = target_center_hint or Point(0, 0)
        elbow_pts = route_elbow(edge, graph, dummy_start, dummy_end)
        if elbow_pts:
            next_hint = elbow_pts[0]
        else:
            next_hint = target_center_hint
        start_hint_is_explicit = False
    else:
        next_hint = target_center_hint
        start_hint_is_explicit = False

    start_pt = None
    if source_node:
        start_pt = resolve_node_terminal(
                source_node, edge, is_source=True, hint_pt=next_hint, hint_is_explicit=start_hint_is_explicit
        )
    if not start_pt:
        start_pt = edge.fixed_source

    return start_pt, start_hint_is_explicit


def _resolve_target(
        edge: DrawIOEdge, graph: DrawIOGraph, start_pt: Point | None, start_hint_is_explicit: bool
) -> Point | None:
    """Resolve the precise end point of an edge on its target node."""
    source_center_hint = None
    if edge.source_id and edge.source_id in graph.nodes:
        source_center_hint = graph.nodes[edge.source_id].bounding_box.center

    target_node = graph.nodes[edge.target_id] if edge.target_id and edge.target_id in graph.nodes else None

    source_fixed = edge.style.raw_styles.get('exitx') is not None

    prev_hint: Point | None = None
    end_hint_is_explicit = False
    if edge.waypoints:
        prev_hint = edge.waypoints[-1]
        end_hint_is_explicit = True
    elif start_pt and not (not edge.waypoints and edge.router == 'elbow'):
        prev_hint = start_pt
        if edge.fixed_source or start_hint_is_explicit or source_fixed:
            end_hint_is_explicit = True
        else:
            end_hint_is_explicit = False
    elif not edge.waypoints and edge.router == 'elbow':
        dummy_start = source_center_hint or Point(0, 0)
        dummy_end = target_node.bounding_box.center if target_node else Point(0, 0)
        elbow_pts = route_elbow(edge, graph, dummy_start, dummy_end)
        if elbow_pts:
            prev_hint = elbow_pts[-1]
        else:
            prev_hint = dummy_start
        end_hint_is_explicit = False
    else:
        prev_hint = source_center_hint
        end_hint_is_explicit = False

    end_pt = None
    if target_node:
        end_pt = resolve_node_terminal(
                target_node, edge, is_source=False, hint_pt=prev_hint, hint_is_explicit=end_hint_is_explicit
        )
    if not end_pt:
        end_pt = edge.fixed_target

    return end_pt


def resolve_endpoints(edge: DrawIOEdge, graph: DrawIOGraph) -> tuple[Point | None, Point | None]:
    """Resolve the precise start and end points of an edge on its connected nodes.

    Args:
        edge (DrawIOEdge): The edge to resolve endpoints for.
        graph (DrawIOGraph): The parent graph containing the nodes.

    Returns:
        tuple[Point | None, Point | None]: The resolved start and end points.

    """
    start_pt, start_hint_is_explicit = _resolve_source(edge, graph)
    end_pt = _resolve_target(edge, graph, start_pt, start_hint_is_explicit)
    return start_pt, end_pt
