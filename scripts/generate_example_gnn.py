"""Render the README's colored GNN example figure.

Recolors tests/data/golden/test_gnn_arch.drawio by the `graph_layer`
attribute on each cell, via RenderConfig.node_style_overrides, and writes
the result to assets/example_gnn.png. Does not touch the golden fixture
used by the test suite.

Diagram from "RAPNet: Accelerating Algebraic Multigrid with Learned Sparse
Corrections" (ICML 2026): https://arxiv.org/abs/2605.26854
"""

import colorsys
from pathlib import Path

from plotio.render import RenderConfig, render

ROOT = Path(__file__).resolve().parent.parent

SOURCE = ROOT / 'tests' / 'data' / 'golden' / 'test_gnn_arch.drawio'
OUTPUT = ROOT / 'assets' / 'example_gnn.png'

# Brand palette (see assets/logo.drawio), muted for use as fill on dense text-heavy diagrams.
BRAND_PALETTE = {
    'fine': '#FF6B6B',
    'fine_fine': '#FFD166',
    'gnn_block': '#48CAE4',
    'coarse': '#5D3FD3',
    'correction': '#5D3FD3',
}
SATURATION_FACTOR = 0.8
FONT_SCALE = 1.6


def desaturate(hex_color: str, factor: float) -> str:
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(h, s * factor, v)
    return f'#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}'


def main() -> None:
    palette = {k: desaturate(v, SATURATION_FACTOR) for k, v in BRAND_PALETTE.items()}
    config = RenderConfig(
        node_style_overrides={'graph_layer': {k: {'facecolor': v} for k, v in palette.items()}},
        global_font_scale=FONT_SCALE,
    )
    render(str(SOURCE), str(OUTPUT), config=config)


if __name__ == '__main__':
    main()
