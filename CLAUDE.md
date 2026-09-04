# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Layout

The Python package, tests, and tooling config live at the repo root (`pyproject.toml`, `src/plotio/`, `tests/`) using the standard src layout. Run all commands below from the repo root.

## What this is

plotio is a Python library that renders Draw.io (`.drawio`) XML diagrams natively onto Matplotlib `Axes`, plus a `plotio render input.drawio output.svg` CLI. It parses the mxGraph XML format into typed domain models, then converts those models into Matplotlib artists (patches, `LineCollection`s, `Text`, `FancyArrowPatch`).

## Commands

This project uses `uv`. Run everything through `uv run` rather than activating the venv manually.

```bash
uv run pytest                          # run the full test suite
uv run pytest tests/test_routing.py    # run one test file
uv run pytest tests/test_routing.py::test_resolve_endpoints_waypoints -v  # run a single test
uv run pytest --cov=plotio             # with coverage (project aims for 100%)

uv run ruff check .                    # lint

uv run mypy src                        # type check (strict — see below)
uv run pyright src                     # second type checker, also used in CI-equivalent checks
```

Formatting is left to PyCharm's built-in formatter (run manually in the IDE) rather than `ruff format` — the project intentionally doesn't use ruff as a Black-style auto-formatter, only as a linter. Don't run or suggest `ruff format`/`ruff format --check`.

Golden-file fixtures for rendering tests live in `tests/data/golden/` (`.drawio` input paired with an expected `.png`). Failed golden comparisons dump debug copies to `tests/data/golden/diffs/` (gitignored, safe to delete).

## Architecture

Data flows through the package in one direction: **XML → domain model → geometry/routing → Matplotlib artists**. Each stage is its own module under `src/plotio/`:

1. **`io.py`** — `parse_drawio_xml`: reads the `.drawio` file, finds `mxGraphModel`, computes `coord_scale` (draw.io points → normalized canvas units) from `pageWidth`/`pageScale`. Delegates cell parsing to `parse.py`.
2. **`parse.py`** — walks the flattened `mxCell`/`object` elements under the root cell and classifies each as a node, edge, or edge-label (`_categorize_cell`), then builds `DrawIONode` / `DrawIOEdge` / `DrawIOEdgeLabel` instances. This is also where draw.io style strings (`key=value;...`) get parsed into dicts and handed to the `NodeStyle`/`EdgeStyle`/`LabelStyle` classes in `styles.py`.
3. **`core.py`** — the frozen dataclass domain model: `Point`, `BoundingBox`, `DrawIONode`, `DrawIOEdge`, `DrawIOEdgeLabel`, `DrawIOGraph`. `Point` supports vector arithmetic and numpy conversion (`__array__`). Everything downstream operates on these types, not on raw XML.
4. **`styles.py`** — `DrawioStyle`/`NodeStyle`/`EdgeStyle`/`LabelStyle` hold `raw_styles: dict[str, StyleValue]` and coerce draw.io-specific keys (`strokewidth`, `fillcolor`, `dashed`, etc.) into Matplotlib-equivalent keys (`linewidth`, `facecolor`, `linestyle`) in `__post_init__`. `as_mpl_kwargs()`/`as_mpl_text_kwargs()` filter down to an allowlist of safe Matplotlib kwargs before they ever reach a patch/text constructor.
5. **`routing.py`** + **`geometry.py`** — given a `DrawIOEdge` and its resolved graph, compute where the edge actually starts/ends on each node's perimeter (`resolve_endpoints` → `_resolve_source`/`_resolve_target` → `resolve_node_terminal`/`intersect_ray_with_geometry`), then build the waypoint path (`calculate_edge_path`): explicit waypoints win, otherwise `route_orthogonal` for orthogonal edges, otherwise a straight line. Endpoint resolution and orthogonal routing are order-dependent and hint-driven (each side's resolution feeds the other as a directional hint) — read both functions together before changing one.
6. **`curves.py`** — `interpolate_path` smooths a waypoint path into a Catmull-Rom spline when an edge style has `curved=1`.
7. **`render.py`** — `render_drawio(file_path, ax, config)` is the library entry point; `render(input_path, output_path, config)` is the CLI-facing wrapper that creates a figure and saves it. `artists_from_graph` fans out to `node_artists`/`edge_artists`, which turn styled domain objects into Matplotlib artists. Style resolution follows a fixed precedence via `ChainMap` in `_apply_style_overrides`: **user overrides (via `RenderConfig.*_style_overrides`, keyed by node/edge metadata attribute) → styles extracted from the `.drawio` file → hardcoded default theme**.
8. **`html.py`** — strips HTML formatting (`<br>`, `<div>`, `&nbsp;`, LaTeX-ish `\(...\)`/`$$`) out of draw.io label values into plain text.
9. **`errors.py`** — `PlotioError` base, with `ParseError` (bad/unsupported XML) and `RenderError` (unresolvable geometry/styling at render time) as the two exception types used throughout; parsing/rendering code raises these rather than generic exceptions.

### Type safety

The codebase is strictly typed (mypy + pyright both configured as dev dependencies) and leans on exhaustiveness checking: `ShapeType` and `RouterType` are `Literal` unions, and code branching on them ends in `assert_never(...)` (see `geometry.py`, `render.py`, `routing.py`) so adding a new shape/router variant without updating every consuming `match`/`if` chain is a type error, not a silent runtime gap. When extending `ShapeType`/`RouterType`, grep for `assert_never` to find every place that needs a new case.

### Coordinate scale

All geometry inside `DrawIOGraph`/`DrawIONode`/`DrawIOEdge` is already normalized by `coord_scale` (draw.io px → canvas units in `[0, 1]` range relative to page width) during parsing in `io.py`/`parse.py`. Downstream code (routing, geometry, rendering) should not re-derive or assume raw draw.io pixel coordinates.
