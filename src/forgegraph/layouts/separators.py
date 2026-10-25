"""A tab's backgrounds and separators, once its tiles are laid out on its grid
(drawing.layout.arrange): each tile's theme background behind its part of the grid, the
layout's color in the gaps, and lines between the tiles and around them.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from forgegraph.drawing.layout import Grid, Placed
from forgegraph.drawing.style import unset
from forgegraph.spec.layout import BLANK


def backgrounds(fig: Figure, grid: Grid, placed: Sequence[Placed]) -> None:
    """Put each tile's theme background behind its part of the grid: its plot box and the
    margins around it."""
    w, h = grid.size
    for p in placed:
        color = p.style.theme["background.color"]
        if unset(color):
            continue
        x0, x1 = grid.column_span(p.area.column, p.area.last_column)
        y0, y1 = grid.row_span(p.area.row, p.area.last_row)
        bounds = (x0 / w, 1 - y1 / h, (x1 - x0) / w, (y1 - y0) / h)
        if p.background is None:
            p.background = Rectangle(
                bounds[:2],
                *bounds[2:],
                transform=fig.transFigure,
                facecolor=str(color),
                edgecolor="none",
                zorder=-10,
            )
            fig.add_artist(p.background)
        else:
            p.background.set_bounds(*bounds)


def separator_lines(
    fig: Figure, grid: Grid, color: str, width_pt: float, between: bool, border: bool
) -> list[Line2D]:
    """Lines through the middle of the gaps. With between, a line runs beside each pair of
    neighbouring cells that aren't one tile (a blank cell counts as a tile of its own), joins
    the line beside the next pair, and reaches across the gap to meet a crossing line or the
    border. With border, a line runs around the outside, through the middle of the space
    between the outer tiles and the figure's edges."""
    areas, rows, columns = grid.areas, len(grid.areas), len(grid.areas[0])
    w, h = grid.size

    def apart(a: str, b: str) -> bool:
        return a != b or a == BLANK

    vertical: set[tuple[int, int]] = set()
    horizontal: set[tuple[int, int]] = set()
    if between:
        vertical = {(r, c) for r in range(rows) for c in range(columns - 1)}
        vertical = {(r, c) for r, c in vertical if apart(areas[r][c], areas[r][c + 1])}
        horizontal = {(r, c) for r in range(rows - 1) for c in range(columns)}
        horizontal = {(r, c) for r, c in horizontal if apart(areas[r][c], areas[r + 1][c])}
    half, out = grid.gap / 2, grid.edge / 2
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for r, c in sorted(vertical):
        x = grid.left[c] + grid.width[c] + grid.margin_r[c] + half
        y0, y1 = grid.row_span(r, r)
        above = (
            half
            if r > 0 and ((r - 1, c) in vertical or {(r - 1, c), (r - 1, c + 1)} & horizontal)
            else (out if r == 0 and border else 0.0)
        )
        below = (
            half
            if r < rows - 1 and ((r + 1, c) in vertical or {(r, c), (r, c + 1)} & horizontal)
            else (out + grid.foot if r == rows - 1 and border else 0.0)
        )
        segments.append(((x, x), (y0 - above, y1 + below)))
    for r, c in sorted(horizontal):
        y = grid.top[r] + grid.height[r] + grid.margin_b[r] + half
        x0, x1 = grid.column_span(c, c)
        left = (
            half
            if c > 0 and ((r, c - 1) in horizontal or {(r, c - 1), (r + 1, c - 1)} & vertical)
            else (out if c == 0 and border else 0.0)
        )
        right = (
            half
            if c < columns - 1 and ((r, c + 1) in horizontal or {(r, c), (r + 1, c)} & vertical)
            else (out if c == columns - 1 and border else 0.0)
        )
        segments.append(((x0 - left, x1 + right), (y, y)))
    for line in grid.lines:
        line.remove()
    lines = []
    for xs, ys in segments:
        line = Line2D(
            [x / w for x in xs],
            [1 - y / h for y in ys],
            transform=fig.transFigure,
            color=color,
            linewidth=width_pt,
            solid_capstyle="butt",
            zorder=-5,
        )
        fig.add_artist(line)
        lines.append(line)
    if border:
        xs = [out, w - out, w - out, out, out]
        ys = [out, out, h - out, h - out, out]
        line = Line2D(
            [x / w for x in xs],
            [1 - y / h for y in ys],
            transform=fig.transFigure,
            color=color,
            linewidth=width_pt,
            solid_joinstyle="miter",
            zorder=-5,
        )
        fig.add_artist(line)
        lines.append(line)
    grid.lines = lines
    return lines


def apply_separators(fig: Figure, grid: Grid, layout_values: dict[str, Any], base: float) -> None:
    """The figure's color in the gaps, blank cells and edges, and the lines between tiles
    and around them."""
    color = layout_values["separators.color"]
    fig.set_facecolor("none" if unset(color) else str(color))
    between = bool(layout_values["separators.line.show"])
    border = bool(layout_values["separators.line.border"])
    if between or border:
        width = float(layout_values["separators.line.width"]) * base
        line_color = str(layout_values["separators.line.color"])
        separator_lines(fig, grid, line_color, width, between, border)
