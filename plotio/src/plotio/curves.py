"""Curve and spline interpolation for curved edges."""

import numpy as np

from plotio.core import Point


def catmull_rom_spline(p0: Point, p1: Point, p2: Point, p3: Point, n_points: int = 20) -> list[Point]:
    """Generate n_points between p1 and p2 using a Centripetal Catmull-Rom spline.

    Args:
        p0 (Point): The control point before the start point.
        p1 (Point): The start point of the spline segment.
        p2 (Point): The end point of the spline segment.
        p3 (Point): The control point after the end point.
        n_points (int, optional): The number of points to interpolate. Defaults to 20.

    Returns:
        list[Point]: The interpolated points along the spline segment.

    """
    p0_arr = np.array([p0.x, p0.y])
    p1_arr = np.array([p1.x, p1.y])
    p2_arr = np.array([p2.x, p2.y])
    p3_arr = np.array([p3.x, p3.y])

    alpha = 0.5

    def tj(ti: float, pi: np.ndarray, pj: np.ndarray) -> float:
        d = np.linalg.norm(pi - pj)
        d = max(d, 1e-5)
        return float((d**alpha) + ti)

    t0 = 0.0
    t1 = tj(t0, p0_arr, p1_arr)
    t2 = tj(t1, p1_arr, p2_arr)
    t3 = tj(t2, p2_arr, p3_arr)

    t = np.linspace(t1, t2, n_points)[:, np.newaxis]

    # Barry-Goldman pyramidal geometric construction
    a1 = (t1 - t) / (t1 - t0) * p0_arr + (t - t0) / (t1 - t0) * p1_arr
    a2 = (t2 - t) / (t2 - t1) * p1_arr + (t - t1) / (t2 - t1) * p2_arr
    a3 = (t3 - t) / (t3 - t2) * p2_arr + (t - t2) / (t3 - t2) * p3_arr

    b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
    b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3

    path = (t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2

    return [Point(p[0].item(), p[1].item()) for p in path]


def bezier_curve(p0: Point, p1: Point, p2: Point, p3: Point, n_points: int = 30) -> list[Point]:
    """Generate a Cubic Bezier curve.

    Args:
        p0 (Point): The start point.
        p1 (Point): The first control point.
        p2 (Point): The second control point.
        p3 (Point): The end point.
        n_points (int, optional): The number of points to interpolate. Defaults to 30.

    Returns:
        list[Point]: The interpolated points along the curve.

    """
    t = np.linspace(0, 1, n_points)[:, np.newaxis]
    p0_arr = np.array([p0.x, p0.y])
    p1_arr = np.array([p1.x, p1.y])
    p2_arr = np.array([p2.x, p2.y])
    p3_arr = np.array([p3.x, p3.y])

    path = (1 - t) ** 3 * p0_arr + 3 * (1 - t) ** 2 * t * p1_arr + 3 * (1 - t) * t**2 * p2_arr + t**3 * p3_arr

    return [Point(p[0].item(), p[1].item()) for p in path]


def quadratic_bezier_curve(p0: Point, p1: Point, p2: Point, n_points: int = 30) -> list[Point]:
    """Generate a Quadratic Bezier curve.

    Args:
        p0 (Point): The start point.
        p1 (Point): The control point.
        p2 (Point): The end point.
        n_points (int, optional): The number of points to interpolate. Defaults to 30.

    Returns:
        list[Point]: The interpolated points along the curve.

    """
    t = np.linspace(0, 1, n_points)[:, np.newaxis]
    p0_arr = np.array([p0.x, p0.y])
    p1_arr = np.array([p1.x, p1.y])
    p2_arr = np.array([p2.x, p2.y])

    path = (1 - t) ** 2 * p0_arr + 2 * (1 - t) * t * p1_arr + t**2 * p2_arr

    return [Point(p[0].item(), p[1].item()) for p in path]


def interpolate_path(path: list[Point], resolution: int = 20) -> list[Point]:
    """Smooth a polyline using spline or bezier curves.

    Args:
        path (list[Point]): The list of points defining the polyline.
        resolution (int, optional): The number of interpolated points per segment. Defaults to 20.

    Returns:
        list[Point]: The smoothed path.

    """
    if len(path) < 3:
        return list(path)

    if len(path) == 3:
        return quadratic_bezier_curve(path[0], path[1], path[2], resolution)
    elif len(path) == 4:
        return bezier_curve(path[0], path[1], path[2], path[3], resolution)

    points = [path[0]] + path + [path[-1]]
    smooth_path = []

    for i in range(len(points) - 3):
        p0, p1, p2, p3 = points[i], points[i + 1], points[i + 2], points[i + 3]
        segment = catmull_rom_spline(p0, p1, p2, p3, n_points=resolution)
        smooth_path.extend(segment)

    return smooth_path
