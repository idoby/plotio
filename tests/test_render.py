import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from matplotlib.testing.compare import compare_images
from matplotlib.text import Text

from plotio.core import BoundingBox, DrawIOEdge, DrawIOEdgeLabel, DrawIOGraph, DrawIONode, Point
from plotio.errors import RenderError
from plotio.render import (
    RenderConfig,
    _apply_style_overrides,
    _create_polyline_edge,
    edge_artists,
    node_artists,
    render,
    render_drawio,
)
from plotio.styles import EdgeStyle, LabelStyle, NodeStyle, StyleValue


def get_golden_tests() -> list[Path]:
    """Discover all golden test .drawio files."""
    golden_dir = Path(__file__).parent / 'data' / 'golden'
    return list(golden_dir.glob('*.drawio'))


@pytest.mark.parametrize('drawio_file', get_golden_tests(), ids=lambda p: p.stem)
def test_golden_render(drawio_file: Path, tmp_path: Path) -> None:
    """Test that rendering a .drawio file produces the expected golden PNG."""
    golden_png_file = drawio_file.with_suffix('.png')
    output_png_file = tmp_path / drawio_file.with_suffix('.png').name

    # Render directly to the temporary path
    render(str(drawio_file), str(output_png_file), config=RenderConfig(transparent=False))

    # Compare images with a tolerance
    result = compare_images(str(golden_png_file), str(output_png_file), tol=1.0)

    if result is not None:
        diff_dir = drawio_file.parent / 'diffs'
        diff_dir.mkdir(exist_ok=True)
        shutil.copy(output_png_file, diff_dir / f'{drawio_file.stem}_generated.png')
        shutil.copy(golden_png_file, diff_dir / f'{drawio_file.stem}_expected.png')

        # compare_images generates a diff image in the same directory as the output file
        # result['diff'] is the path to the diff image
        if isinstance(result, dict) and 'diff' in result and Path(str(result['diff'])).exists():
            shutil.copy(str(result['diff']), diff_dir / f'{drawio_file.stem}_diff.png')

        pytest.fail(
            f'Rendered PNG does not match golden for {drawio_file.name}. Compare files in {diff_dir}\nError: {result}'
        )


def test_node_artists_default_colors() -> None:
    node = DrawIONode(
        '1', BoundingBox(0, 0, 10, 10), 'rectangle', '', NodeStyle({'fillcolor': 'default', 'strokecolor': 'default'})
    )
    artists = node_artists(node, 1.0, RenderConfig())
    assert len(artists) == 1
    assert isinstance(artists[0], Rectangle)
    assert artists[0].get_facecolor() == (1.0, 1.0, 1.0, 1.0)  # white


def test_node_artists_bounding_boxes() -> None:
    node = DrawIONode('1', BoundingBox(0, 0, 10, 10), 'rectangle', '', NodeStyle())
    artists = node_artists(node, 1.0, RenderConfig(draw_bounding_boxes=True))
    assert len(artists) == 2  # bbox + node
    assert isinstance(artists[0], Rectangle)
    assert artists[0].get_edgecolor() == (1.0, 0.0, 0.0, 1.0)  # red bounding box


def test_node_artists_shapes() -> None:
    node_rect = DrawIONode('1', BoundingBox(0, 0, 10, 10), 'rectangle', '', NodeStyle())
    assert isinstance(node_artists(node_rect, 1.0, RenderConfig())[0], Rectangle)

    node_step = DrawIONode('1', BoundingBox(0, 0, 10, 10), 'step', '', NodeStyle())
    assert isinstance(node_artists(node_step, 1.0, RenderConfig())[0], Polygon)

    node_step_fixed = DrawIONode('1', BoundingBox(0, 0, 10, 10), 'step', '', NodeStyle({'fixedsize': '1', 'size': '5'}))
    assert isinstance(node_artists(node_step_fixed, 1.0, RenderConfig())[0], Polygon)

    node_ellipse = DrawIONode('2', BoundingBox(0, 0, 10, 10), 'ellipse', '', NodeStyle())
    assert isinstance(node_artists(node_ellipse, 1.0, RenderConfig())[0], Ellipse)

    node_rounded = DrawIONode('1', BoundingBox(0, 0, 10, 10), 'rounded_rectangle', '', NodeStyle({'arcsize': '20'}))
    assert isinstance(node_artists(node_rounded, 1.0, RenderConfig())[0], FancyBboxPatch)


def test_edge_artists_default_colors() -> None:
    graph = DrawIOGraph(100, 100, 1.0, {}, [])
    edge = DrawIOEdge(
        'e1',
        None,
        None,
        [Point(0, 0), Point(10, 10)],
        fixed_source=Point(0, 0),
        fixed_target=Point(10, 10),
        style=EdgeStyle({'strokecolor': 'default'}),
    )
    artists = edge_artists(graph, edge, RenderConfig())
    assert len(artists) >= 1


def test_edge_artists_arrows() -> None:
    graph = DrawIOGraph(100, 100, 1.0, {}, [])
    edge = DrawIOEdge(
        'e1',
        None,
        None,
        [Point(0, 0), Point(10, 10)],
        fixed_source=Point(0, 0),
        fixed_target=Point(10, 10),
        style=EdgeStyle({'startarrow': 'classic', 'endarrow': 'classic'}),
    )
    artists = edge_artists(graph, edge, RenderConfig())
    # LineCollection + StartArrow + EndArrow
    assert len(artists) == 3
    assert any(isinstance(a, FancyArrowPatch) for a in artists)

    edge_none = DrawIOEdge(
        'e2',
        None,
        None,
        [Point(0, 0), Point(10, 10)],
        fixed_source=Point(0, 0),
        fixed_target=Point(10, 10),
        style=EdgeStyle({'startarrow': 'none', 'endarrow': 'none'}),
    )
    artists_none = edge_artists(graph, edge_none, RenderConfig())
    assert len(artists_none) == 1


def test_edge_artists_labels() -> None:
    graph = DrawIOGraph(100, 100, 1.0, {}, [])
    edge = DrawIOEdge(
        'e1',
        None,
        None,
        [Point(0, 0), Point(10, 10)],
        fixed_source=Point(0, 0),
        fixed_target=Point(10, 10),
        style=EdgeStyle(),
    )
    label = DrawIOEdgeLabel('L1', 0.5, 'Label', 0.0, Point(0, 0), LabelStyle())
    edge.labels.append(label)
    artists = edge_artists(graph, edge, RenderConfig())
    assert any(isinstance(a, Text) for a in artists)


def test_edge_artists_errors() -> None:
    graph = DrawIOGraph(100, 100, 1.0, {}, [])
    edge_no_points = DrawIOEdge('e1', None, None, [], style=EdgeStyle())
    with pytest.raises(RenderError, match='Cannot resolve endpoints'):
        edge_artists(graph, edge_no_points, RenderConfig())

    with pytest.raises(RenderError, match='Edge path must contain at least 2 points'):
        _create_polyline_edge([Point(0, 0)], 'none', 'none', {})


def test_apply_style_overrides() -> None:
    metadata = {'type': 'important'}
    drawio: dict[str, StyleValue] = {'color': 'blue', 'width': 1.0}
    overrides: dict[str, dict[str, dict[str, StyleValue]]] = {'type': {'important': {'color': 'red', 'zorder': 5.0}}}
    defaults: dict[str, StyleValue] = {'color': 'black', 'zorder': 1.0}

    result = _apply_style_overrides(metadata, drawio, overrides, defaults)
    assert result['color'] == 'red'
    assert result['width'] == 1.0
    assert result['zorder'] == 5.0


def test_render_no_config(tmp_path: Path) -> None:
    drawio_file = get_golden_tests()[0]
    output_png = tmp_path / 'no_config.png'
    render(str(drawio_file), str(output_png))
    assert output_png.exists()


def test_render_drawio_no_config() -> None:
    drawio_file = get_golden_tests()[0]
    _, ax = plt.subplots()
    render_drawio(str(drawio_file), ax)
    assert len(ax.artists) > 0 or len(ax.collections) > 0 or len(ax.patches) > 0
