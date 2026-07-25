"""Tests for curve interpolation logic."""

from plotio.core import Point
from plotio.curves import bezier_curve, catmull_rom_spline, interpolate_path, quadratic_bezier_curve


def test_quadratic_bezier() -> None:
    p0 = Point(0, 0)
    p1 = Point(50, 100)
    p2 = Point(100, 0)

    path = quadratic_bezier_curve(p0, p1, p2, n_points=5)
    assert len(path) == 5
    assert path[0] == p0
    assert path[-1] == p2
    assert path[2].y > 0


def test_cubic_bezier() -> None:
    p0 = Point(0, 0)
    p1 = Point(0, 100)
    p2 = Point(100, 100)
    p3 = Point(100, 0)

    path = bezier_curve(p0, p1, p2, p3, n_points=5)
    assert len(path) == 5
    assert path[0] == p0
    assert path[-1] == p3


def test_catmull_rom() -> None:
    p0 = Point(0, 0)
    p1 = Point(50, 50)
    p2 = Point(100, 50)
    p3 = Point(150, 0)

    path = catmull_rom_spline(p0, p1, p2, p3, n_points=5)
    assert len(path) == 5
    assert abs(path[0].x - p1.x) < 1e-5
    assert abs(path[0].y - p1.y) < 1e-5
    assert abs(path[-1].x - p2.x) < 1e-5
    assert abs(path[-1].y - p2.y) < 1e-5


def test_interpolate_path_straight() -> None:
    short = [Point(0, 0), Point(10, 10)]
    assert len(interpolate_path(short)) == 2


def test_interpolate_path_quadratic() -> None:
    path3 = [Point(0, 0), Point(50, 100), Point(100, 0)]
    assert len(interpolate_path(path3, 10)) == 10


def test_interpolate_path_cubic() -> None:
    path4 = [Point(0, 0), Point(0, 100), Point(100, 100), Point(100, 0)]
    assert len(interpolate_path(path4, 10)) == 10


def test_interpolate_path_catmull() -> None:
    path5 = [Point(0, 0), Point(50, 50), Point(100, 50), Point(150, 0), Point(200, 100)]
    res = interpolate_path(path5, 5)
    assert len(res) == 20
