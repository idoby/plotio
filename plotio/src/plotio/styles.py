"""Style definition and coercion for plotio."""

from dataclasses import dataclass, field

StyleValue = str | int | float


@dataclass
class DrawioStyle:
    """Base style configuration."""

    raw_styles: dict[str, StyleValue] = field(default_factory=dict)

    def as_mpl_kwargs(self) -> dict[str, StyleValue]:
        """Convert styles to Matplotlib kwargs for patches and lines."""
        kwargs = {}
        # Only preserve safe matplotlib keys
        safe_keys = {'linewidth', 'linestyle', 'edgecolor', 'facecolor', 'alpha', 'color'}
        for k, v in self.raw_styles.items():
            if k in safe_keys:
                kwargs[k] = v
        return kwargs

    def as_mpl_text_kwargs(self) -> dict[str, StyleValue]:
        """Convert styles to Matplotlib kwargs for text."""
        kwargs = {}
        # Only preserve safe matplotlib text keys
        safe_keys = {
            'fontsize',
            'fontfamily',
            'color',
            'backgroundcolor',
            'horizontalalignment',
            'verticalalignment',
            'zorder',
        }
        for k, v in self.raw_styles.items():
            if k in safe_keys:
                kwargs[k] = v
        return kwargs

    def __post_init__(self) -> None:
        """Parse raw font styles into typed properties after initialization."""
        if 'fontsize' in self.raw_styles:
            try:
                self.raw_styles['fontsize'] = float(self.raw_styles['fontsize'])
            except ValueError:
                pass

        if 'fontcolor' in self.raw_styles:
            val = self.raw_styles['fontcolor']
            self.raw_styles['color'] = 'black' if val == 'default' else val


@dataclass
class NodeStyle(DrawioStyle):
    """Style configuration for nodes."""

    def __post_init__(self) -> None:
        """Parse raw styles into typed properties after initialization."""
        # Perform JIT type coercion
        if 'strokewidth' in self.raw_styles:
            try:
                self.raw_styles['linewidth'] = float(self.raw_styles['strokewidth'])
            except ValueError:
                pass

        if 'fillcolor' in self.raw_styles:
            val = self.raw_styles['fillcolor']
            self.raw_styles['facecolor'] = 'white' if val == 'default' else val

        if 'strokecolor' in self.raw_styles:
            val = self.raw_styles['strokecolor']
            self.raw_styles['edgecolor'] = 'black' if val == 'default' else val

        super().__post_init__()


@dataclass
class EdgeStyle(DrawioStyle):
    """Style configuration for edges."""

    def __post_init__(self) -> None:
        """Parse raw styles into typed properties after initialization."""
        super().__post_init__()
        if 'strokewidth' in self.raw_styles:
            try:
                self.raw_styles['linewidth'] = float(self.raw_styles['strokewidth'])
            except ValueError:
                pass

        if 'dashed' in self.raw_styles:
            self.raw_styles['linestyle'] = 'dashed' if self.raw_styles['dashed'] == '1' else 'solid'

        if 'strokecolor' in self.raw_styles:
            val = self.raw_styles['strokecolor']
            self.raw_styles['color'] = 'black' if val == 'default' else val


@dataclass
class LabelStyle(DrawioStyle):
    """Style configuration for labels."""

