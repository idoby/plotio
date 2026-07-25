"""Constants and configuration for plotio."""

from dataclasses import dataclass

DEFAULT_PAGE_WIDTH: float = 850.0
DEFAULT_PAGE_HEIGHT: float = 1100.0
DEFAULT_PAGE_SCALE: float = 1.0


@dataclass
class PlotioConfig:
    """Global configuration for plotio rendering."""

    mutation_scale_base: float = 15.0
    default_stroke_width: float = 1.0
