"""Edge routing and path generation logic."""

from plotio.core import DrawIOEdge, DrawIOGraph, Point
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


def calculate_edge_path(edge: DrawIOEdge, start_pt: Point, end_pt: Point) -> list[Point]:
    """Orchestrate waypoints, orthogonal routes, and curved interpolations.

    Args:
        edge (DrawIOEdge): The edge being routed.
        start_pt (Point): The resolved start point.
        end_pt (Point): The resolved end point.

    Returns:
        list[Point]: The final sequence of points defining the visual path of the edge.

    """
    edge_style = edge.style.raw_styles.get('edgestyle', '')

    if edge.waypoints:
        waypoints = edge.waypoints
    elif edge_style == 'orthogonaledgestyle':
        waypoints = route_orthogonal(start_pt, end_pt, edge.style.raw_styles)
    else:
        waypoints = []

    path = [start_pt] + waypoints + [end_pt]

    if len(path) >= 2:
        if edge.style.raw_styles.get('curved') == '1':
            path = interpolate_path(path)
        elif edge_style == 'orthogonaledgestyle':
            path = snap_orthogonal(path)

    return path


def _resolve_source(edge: DrawIOEdge, graph: DrawIOGraph) -> tuple[Point | None, bool]:
    """Resolve the precise start point of an edge on its source node."""
    target_center_hint = None
    if edge.target_id and edge.target_id in graph.nodes:
        target_center_hint = graph.nodes[edge.target_id].bounding_box.center

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
    else:
        next_hint = target_center_hint
        start_hint_is_explicit = False

    start_pt = None
    if edge.source_id and edge.source_id in graph.nodes:
        source_node = graph.nodes[edge.source_id]
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

    source_fixed = edge.style.raw_styles.get('exitx') is not None

    prev_hint: Point | None = None
    end_hint_is_explicit = False
    if edge.waypoints:
        prev_hint = edge.waypoints[-1]
        end_hint_is_explicit = True
    elif start_pt:
        prev_hint = start_pt
        if edge.fixed_source or start_hint_is_explicit or source_fixed:
            end_hint_is_explicit = True
        else:
            end_hint_is_explicit = False
    else:
        prev_hint = source_center_hint
        end_hint_is_explicit = False

    end_pt = None
    if edge.target_id and edge.target_id in graph.nodes:
        target_node = graph.nodes[edge.target_id]
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
