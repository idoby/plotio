"""Custom exceptions for the plotio package."""


class PlotioError(Exception):
    """Base exception for all plotio errors."""


class ParseError(PlotioError):
    """Raised when there is an error parsing a Draw.io file."""


class RenderError(PlotioError):
    """Raised when an error occurs during rendering."""
