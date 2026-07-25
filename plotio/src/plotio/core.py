"""Core domain models for the plotio package."""

from dataclasses import dataclass, field

import numpy as np

from plotio.styles import EdgeStyle, LabelStyle, NodeStyle


@dataclass(frozen=True)
class Point:
    """A 2D point with vector operations."""

    x: float
    y: float

    def __add__(self, other: 'Point') -> 'Point':
        """Add two points."""
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Point') -> 'Point':
        """Subtract one point from another."""
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Point':
        """Multiply a point by a scalar."""
        return Point(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> 'Point':
        """Divide a point by a scalar."""
        return Point(self.x / scalar, self.y / scalar)

    def __abs__(self) -> 'Point':
        """Get the absolute value of the point's coordinates."""
        return Point(abs(self.x), abs(self.y))

    def norm(self) -> float:
        """Calculate the Euclidean norm of the point."""
        return float(np.sqrt(self.x**2 + self.y**2).item())

    def unit(self) -> 'Point':
        """Get a unit vector pointing in the same direction."""
        n = self.norm()
        if n == 0:
            return Point(0.0, 0.0)
        return self / n

    def __array__(self, dtype: type | np.dtype | None = None, copy: bool | None = None) -> np.ndarray:
        """Convert the point to a numpy array."""
        return np.array([self.x, self.y], dtype=dtype, copy=copy)


@dataclass(frozen=True)
class BoundingBox:
    """A 2D bounding box."""

    x: float
    y: float
    w: float
    h: float

    @property
    def center(self) -> Point:
        """Get the center point of the bounding box."""
        return Point(self.x + self.w / 2, self.y + self.h / 2)


@dataclass(frozen=True)
class DrawIONode:
    """A single node (vertex) in the Draw.io graph."""

    id: str

    bounding_box: BoundingBox
    shape: str | None
    label: str = ''

    style: NodeStyle = field(default_factory=NodeStyle)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DrawIOEdgeLabel:
    """A label attached to an edge."""

    id: str

    position: float
    label: str

    y_offset: float
    offset: Point

    style: LabelStyle = field(default_factory=LabelStyle)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DrawIOEdge:
    """An edge connecting nodes or points."""

    id: str

    source_id: str | None
    target_id: str | None

    waypoints: list[Point]

    fixed_source: Point | None = None
    fixed_target: Point | None = None

    labels: list[DrawIOEdgeLabel] = field(default_factory=list)

    style: EdgeStyle = field(default_factory=EdgeStyle)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DrawIOGraph:
    """The root graph object containing all nodes and edges."""

    width: float
    height: float

    coord_scale: float

    nodes: dict[str, DrawIONode]
    edges: list[DrawIOEdge]
