"""Rendering logic for plotio."""

from collections import ChainMap
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

import matplotlib.axes as maxes
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.text as mtext
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib.artist import Artist
from matplotlib.collections import LineCollection
from matplotlib.patches import FancyArrowPatch

from plotio.core import BoundingBox, DrawIOEdge, DrawIOEdgeLabel, DrawIOGraph, DrawIONode, Point
from plotio.errors import RenderError
from plotio.geometry import get_path_point_and_tangent, label_anchor
from plotio.io import parse_drawio_xml
from plotio.routing import calculate_edge_path, resolve_endpoints
from plotio.styles import StyleValue


@dataclass
class RenderConfig:
    """Configuration for rendering options and style overrides."""

    dpi: int = 300
    transparent: bool = True
    draw_bounding_boxes: bool = False
    mutation_scale_base: float = 15.0
    global_font_scale: float = 1.0
    node_style_overrides: dict[str, dict[str, dict[str, StyleValue]]] | None = None
    edge_style_overrides: dict[str, dict[str, dict[str, StyleValue]]] | None = None
    label_style_overrides: dict[str, dict[str, dict[str, StyleValue]]] | None = None


def render_drawio(file_path: Path | str, ax: maxes.Axes, config: RenderConfig | None = None) -> list[Artist]:
    """Render a Draw.io XML file onto a Matplotlib Axes object.

    Args:
        file_path: Path to the Draw.io XML file.
        ax: Matplotlib Axes to draw onto.
        config: Optional configuration for rendering.

    Returns:
        List of created matplotlib Artist objects.
    """
    if config is None:
        config = RenderConfig()

    file_path = Path(file_path)
    graph = parse_drawio_xml(file_path)

    bbox = ax.get_window_extent().transformed(ax.figure.dpi_scale_trans.inverted())
    width_points = bbox.width * 72
    font_scale = width_points * graph.coord_scale * config.global_font_scale

    artists = artists_from_graph(graph, config=config, font_scale=font_scale)

    transform = mtransforms.Affine2D().scale(1, -1) + ax.transData

    for artist in artists:
        artist.set_figure(ax.figure)
        artist.set_transform(transform)
        tight_bbox = artist.get_tightbbox(ax.figure.canvas.get_renderer())  # type: ignore[attr-defined]
        if tight_bbox is not None:
            bbox_data = tight_bbox.transformed(ax.transData.inverted())
            ax.update_datalim(bbox_data)

        if isinstance(artist, LineCollection):
            ax.add_collection(artist)
        elif isinstance(artist, mpatches.Patch):
            ax.add_patch(artist)
        else:
            ax.add_artist(artist)

    return artists


def render(input_path: str, output_path: str, config: RenderConfig | None = None) -> None:
    """High-level public render function.

    Args:
        input_path: Path to the Draw.io XML file.
        output_path: Path to save the rendered output.
        config: Optional configuration for rendering.
    """
    if config is None:
        config = RenderConfig()

    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    ax.axis('off')
    render_drawio(input_path, ax, config=config)
    fig.savefig(output_path, bbox_inches='tight', pad_inches=0.1, dpi=config.dpi, transparent=config.transparent)
    plt.close(fig)


def artists_from_graph(graph: DrawIOGraph, config: RenderConfig, font_scale: float = 1.0) -> list[Artist]:
    artists: list[Artist] = []

    for node in graph.nodes.values():
        artists.extend(node_artists(node, graph.coord_scale, config, font_scale))

    for edge in graph.edges:
        artists.extend(edge_artists(graph, edge, config, font_scale))

    return artists


def node_artists(node: DrawIONode, scale: float, config: RenderConfig, font_scale: float = 1.0) -> list[Artist]:
    node_style_overrides = config.node_style_overrides or {}
    label_style_overrides = config.label_style_overrides or {}

    artists: list[Artist] = []

    edge_color = node.style.raw_styles.get('strokecolor', 'black')
    if edge_color == 'default':
        edge_color = 'black'

    fill_color = node.style.raw_styles.get('fillcolor', 'white')
    if fill_color == 'default':
        fill_color = 'white'

    default_theme: dict[str, StyleValue] = {
        'facecolor': str(fill_color),
        'edgecolor': str(edge_color),
        'linewidth': float(node.style.raw_styles.get('strokewidth', '1.0')),
        'zorder': 2,
    }

    drawio_kwargs = node.style.as_mpl_kwargs()
    node_styles = _apply_style_overrides(node.metadata, drawio_kwargs, node_style_overrides, default_theme)

    bbox = node.bounding_box

    if config.draw_bounding_boxes:
        bbox_patch = mpatches.Rectangle(
            (bbox.x, bbox.y), bbox.w, bbox.h, facecolor='none', edgecolor='red', linewidth=0.5, zorder=4
        )
        artists.append(bbox_patch)

    if node.shape is not None:
        patch: mpatches.Patch
        if node.shape == 'ellipse':
            patch = mpatches.Ellipse((bbox.x + bbox.w / 2, bbox.y + bbox.h / 2), bbox.w, bbox.h, **node_styles)  # type: ignore[arg-type]
        elif node.shape == 'rounded_rectangle':
            arc_size = float(node.style.raw_styles.get('arcsize', 12)) / 100.0
            r = min(bbox.w, bbox.h) * arc_size
            box_style_dict = {'pad': 0, 'rounding_size': r}
            box_style = 'round,' + ','.join([f'{k}={v}' for k, v in box_style_dict.items()])
            node_styles['boxstyle'] = box_style
            patch = mpatches.FancyBboxPatch((bbox.x, bbox.y), bbox.w, bbox.h, **node_styles)  # type: ignore[arg-type]
        elif node.shape == 'rectangle':
            patch = mpatches.Rectangle((bbox.x, bbox.y), bbox.w, bbox.h, **node_styles)  # type: ignore[arg-type]
        elif node.shape == 'step':
            fixed = node.style.raw_styles.get('fixedsize', '0') != '0'
            size_str = node.style.raw_styles.get('size')

            x0, y0, w, h = bbox.x, bbox.y, bbox.w, bbox.h

            if fixed:
                size_val = float(str(size_str)) if size_str is not None else 20.0
                size_val = size_val * scale
                s = max(0, min(w, size_val))
            else:
                size_val = float(str(size_str)) if size_str is not None else 0.2
                s = w * max(0, min(1, size_val))

            verts = [
                (x0, y0),
                (x0 + w - s, y0),
                (x0 + w, y0 + h / 2),
                (x0 + w - s, y0 + h),
                (x0, y0 + h),
                (x0 + s, y0 + h / 2),
                (x0, y0),
            ]
            patch = mpatches.Polygon(verts, **node_styles)  # type: ignore[arg-type]
        else:
            assert_never(node.shape)

        artists.append(patch)

    if node.label:
        position_x = str(node.style.raw_styles.get('labelposition', 'center'))
        position_y = str(node.style.raw_styles.get('verticallabelposition', 'middle'))

        spacing_global = float(node.style.raw_styles.get('spacing', 0)) * scale
        spacing_top = float(node.style.raw_styles.get('spacingtop', 0)) * scale
        spacing_bottom = float(node.style.raw_styles.get('spacingbottom', 0)) * scale
        spacing_left = float(node.style.raw_styles.get('spacingleft', 0)) * scale
        spacing_right = float(node.style.raw_styles.get('spacingright', 0)) * scale

        halignment = str(node.style.raw_styles.get('align', 'center'))
        valignment = _vertical_align_map[str(node.style.raw_styles.get('verticalalign', 'middle'))]

        label_default: dict[str, StyleValue] = {
            'horizontalalignment': halignment,
            'verticalalignment': valignment,
            'fontsize': int(node.style.raw_styles.get('fontsize', '12')) * font_scale,
            'fontfamily': str(node.style.raw_styles.get('fontfamily', 'sans-serif')),
            'color': str(node.style.raw_styles.get('fontcolor', 'black')),
            'zorder': 3,
        }
        label_kwargs_mpl = node.style.as_mpl_text_kwargs()
        label_styles = _apply_style_overrides(node.metadata, label_kwargs_mpl, label_style_overrides, label_default)

        label_anchor_pt = label_anchor(
            bbox,
            position_x,
            position_y,
            halignment,
            valignment,
            spacing_global,
            spacing_top,
            spacing_bottom,
            spacing_left,
            spacing_right,
        )
        artists.append(
            mtext.Text(label_anchor_pt.x, label_anchor_pt.y, node.label, **label_styles)  # type: ignore[arg-type]
        )

    return artists


def edge_artists(graph: DrawIOGraph, edge: DrawIOEdge, config: RenderConfig, font_scale: float = 1.0) -> list[Artist]:
    edge_style_overrides = config.edge_style_overrides or {}
    label_style_overrides = config.label_style_overrides or {}

    start_pt, end_pt = resolve_endpoints(edge, graph)
    if not start_pt or not end_pt:
        raise RenderError(f'Cannot resolve endpoints for edge {edge.id}: {start_pt=}, {end_pt=}')

    path = calculate_edge_path(edge, start_pt, end_pt)

    stroke_width = float(edge.style.raw_styles.get('strokewidth', '1.0'))
    end_size = float(edge.style.raw_styles.get('endsize', '6'))
    mutation_scale = end_size / 6.0 * 15

    edge_color = edge.style.raw_styles.get('strokecolor', 'black')
    if edge_color == 'default':
        edge_color = 'black'

    default_theme: dict[str, StyleValue] = {
        'color': str(edge_color),
        'linewidth': stroke_width,
        'linestyle': 'dashed' if edge.style.raw_styles.get('dashed') == '1' else 'solid',
        'capstyle': 'round',
        'joinstyle': 'round',
        'mutation_scale': mutation_scale,
        'zorder': 1,
    }

    drawio_kwargs = edge.style.as_mpl_kwargs()
    edge_styles = _apply_style_overrides(edge.metadata, drawio_kwargs, edge_style_overrides, default_theme)

    start_arrow_type = str(edge.style.raw_styles.get('startarrow', 'none'))
    end_arrow_type = str(edge.style.raw_styles.get('endarrow', 'classic'))

    artists = _create_polyline_edge(path, start_arrow_type, end_arrow_type, edge_styles, config.mutation_scale_base)

    for label in edge.labels:
        artists.append(_create_edge_label_artist(label, path, label_style_overrides, graph.coord_scale, font_scale))

    return artists


_vertical_align_map = {'top': 'top', 'middle': 'center', 'bottom': 'bottom'}


def _apply_style_overrides(
    metadata: dict[str, str],
    drawio_kwargs: dict[str, StyleValue],
    overrides: dict[str, dict[str, dict[str, StyleValue]]],
    default_theme: dict[str, StyleValue],
) -> dict[str, StyleValue]:
    """Resolve styles using a ChainMap of inheritance."""
    user_overrides: dict[str, StyleValue] = {}
    if overrides:
        for attr, vmap in overrides.items():
            if attr in metadata and metadata[attr] in vmap:
                style_updates = vmap[metadata[attr]]
                for k, v in style_updates.items():
                    user_overrides[k] = v

    # Inheritance: user overrides -> drawio extracted styles -> default theme
    return dict(ChainMap(user_overrides, drawio_kwargs, default_theme))


def _create_polyline_edge(
    path: list[Point],
    start_arrow_type: str | None,
    end_arrow_type: str | None,
    style_kwargs: dict[str, StyleValue],
    mutation_scale_base: float = 15.0,
) -> list[Artist]:
    if len(path) < 2:
        raise RenderError(f'Edge path must contain at least 2 points (got {len(path)}): {path}')

    artists: list[Artist] = []
    p_first = p_second = path[0]
    if start_arrow_type is None or start_arrow_type.lower() == 'none':
        start_arrow_type = None
        new_first = path[0]
    else:
        p_first, p_second = path[0], path[1]
        start_diff = (p_second - p_first).unit()
        new_first = p_first - start_diff * 0.005

    p_last = p_prev = path[-1]
    if end_arrow_type is None or end_arrow_type.lower() == 'none':
        end_arrow_type = None
        new_last = path[-1]
    else:
        p_last, p_prev = path[-1], path[-2]
        end_diff = (p_last - p_prev).unit()
        new_last = p_last - end_diff * 0.005

    path = [new_first] + path[1:-1] + [new_last]
    path_np = [np.asarray(p) for p in path]

    ms = float(style_kwargs.pop('mutation_scale', mutation_scale_base))

    lc = LineCollection([path_np], **style_kwargs)  # type: ignore[arg-type]
    artists.append(lc)

    if start_arrow_type is not None:
        arrow_style_kwargs = style_kwargs.copy()
        arrow_style_kwargs['linewidth'] = 0
        arrow_style_kwargs.pop('linestyle', None)
        arrow = FancyArrowPatch(
            (p_second.x, p_second.y),
            (p_first.x, p_first.y),
            arrowstyle='-|>',
            mutation_scale=ms,
            shrinkA=0,
            shrinkB=0,
            **arrow_style_kwargs,  # type: ignore[arg-type]
        )
        artists.append(arrow)
    if end_arrow_type is not None:
        arrow_style_kwargs = style_kwargs.copy()
        arrow_style_kwargs['linewidth'] = 0
        arrow_style_kwargs.pop('linestyle', None)
        arrow = FancyArrowPatch(
            (p_prev.x, p_prev.y),
            (p_last.x, p_last.y),
            arrowstyle='-|>',
            mutation_scale=ms,
            shrinkA=0,
            shrinkB=0,
            **arrow_style_kwargs,  # type: ignore[arg-type]
        )
        artists.append(arrow)

    return artists


def _create_edge_label_artist(
    label_obj: DrawIOEdgeLabel,
    path: list[Point],
    label_style_overrides: dict[str, dict[str, dict[str, StyleValue]]],
    scale: float,
    font_scale: float = 1.0,
) -> Artist:
    pos_pt, tangent = get_path_point_and_tangent(path, label_obj.position)

    ortho = Point(-tangent.y, tangent.x)
    base_pt = pos_pt + ortho * label_obj.y_offset + label_obj.offset

    bbox = BoundingBox(base_pt.x, base_pt.y, 0, 0)

    position_x = str(label_obj.style.raw_styles.get('labelposition', 'center'))
    position_y = str(label_obj.style.raw_styles.get('verticallabelposition', 'middle'))

    halign = str(label_obj.style.raw_styles.get('align', 'center'))
    valign_raw = str(label_obj.style.raw_styles.get('verticalalign', 'middle'))
    valign = _vertical_align_map.get(valign_raw, 'center')

    spacing_global = float(label_obj.style.raw_styles.get('spacing', 0)) * scale
    spacing_top = float(label_obj.style.raw_styles.get('spacingtop', 0)) * scale
    spacing_bottom = float(label_obj.style.raw_styles.get('spacingbottom', 0)) * scale
    spacing_left = float(label_obj.style.raw_styles.get('spacingleft', 0)) * scale
    spacing_right = float(label_obj.style.raw_styles.get('spacingright', 0)) * scale

    final_anchor = label_anchor(
        bbox,
        position_x,
        position_y,
        halign,
        valign,
        spacing_global,
        spacing_top,
        spacing_bottom,
        spacing_left,
        spacing_right,
    )

    default_theme: dict[str, StyleValue] = {
        'horizontalalignment': halign,
        'verticalalignment': valign,
        'fontsize': int(label_obj.style.raw_styles.get('fontsize', '11')) * font_scale,
        'fontfamily': str(label_obj.style.raw_styles.get('fontfamily', 'sans-serif')),
        'color': str(label_obj.style.raw_styles.get('fontcolor', 'black')),
        'zorder': 3,
        'backgroundcolor': str(label_obj.style.raw_styles.get('labelbackgroundcolor', 'none')),
    }

    drawio_kwargs = label_obj.style.as_mpl_text_kwargs()
    label_styles = _apply_style_overrides(label_obj.metadata, drawio_kwargs, label_style_overrides, default_theme)

    return mtext.Text(final_anchor.x, final_anchor.y, label_obj.label, **label_styles)  # type: ignore[arg-type]
