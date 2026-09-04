import numpy as np

from plotio.core import BoundingBox, Point


def test_point_addition() -> None:
    p1 = Point(1.0, 2.0)
    p2 = Point(3.0, -1.0)

    p3 = p1 + p2

    assert p3.x == 4.0
    assert p3.y == 1.0


def test_point_subtraction() -> None:
    p1 = Point(5.0, 5.0)
    p2 = Point(2.0, 3.0)

    p3 = p1 - p2

    assert p3.x == 3.0
    assert p3.y == 2.0


def test_point_scalar_multiplication() -> None:
    p = Point(2.0, -3.0)

    p2 = p * 2.5

    assert p2.x == 5.0
    assert p2.y == -7.5


def test_point_norm() -> None:
    p = Point(3.0, 4.0)

    assert p.norm() == 5.0


def test_point_unit() -> None:
    p = Point(0.0, 5.0)

    u = p.unit()

    assert u.x == 0.0
    assert u.y == 1.0


def test_bounding_box_center() -> None:
    bbox = BoundingBox(x=10.0, y=20.0, w=30.0, h=40.0)

    center = bbox.center

    assert center.x == 25.0
    assert center.y == 40.0


def test_point_abs() -> None:
    p = abs(Point(-3.0, 4.0))

    assert p.x == 3.0 and p.y == 4.0


def test_point_unit_zero() -> None:
    p = Point(0.0, 0.0).unit()

    assert p.x == 0.0 and p.y == 0.0


def test_point_array() -> None:
    p = Point(1.0, 2.0)

    arr = np.array(p)

    assert arr.shape == (2,)
    assert arr[0] == 1.0 and arr[1] == 2.0
