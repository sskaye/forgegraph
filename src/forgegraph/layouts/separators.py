"""A tab's backgrounds and separators, once its tiles are laid out on its grid
(drawing.layout.arrange): each tile's theme background behind its part of the grid, with its
corners rounded by separators.corner_radius; the first tile's theme background in the gaps;
and lines between the tiles and around them, in the separators' line style, whose members
the layout doesn't set are its first tile's theme's general line.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle

from forgegraph.drawing.layout import Grid, Placed
from forgegraph.drawing.style import LINE_STYLES, LineStyle, Style, unset
from forgegraph.spec.layout import BLANK

LINE = ("style", "width", "color", "cap", "join")  # a line style's members


def line_style(
    values: dict[str, Any], first: Style, base: float, at: str = "separators.line"
) -> LineStyle:
    """A layout's line style (at: the separators' line, or the tab bar's): each member the
    layout sets, else its first tile's theme's general line; its width times the layout's
    base size."""

    def member(name: str) -> Any:
        path = f"{at}.{name}"
        return values[path] if path in values else first.theme[f"line.{name}"]

    style = member("style")
    return LineStyle(
        "none" if unset(style) else LINE_STYLES[style],
        float(member("width")) * base,
        str(member("color")),
        str(member("cap")),
        str(member("join")),
    )


def text_member(values: dict[str, Any], first: Style, at: str, name: str) -> Any:
    """A layout's text style's member (at: its path): the layout's, else its first tile's
    theme's general text."""
    path = f"{at}.{name}"
    return values[path] if path in values else first.theme[f"text.{name}"]


def gap_color(first: Style) -> str:
    """The gaps' color: the first tile's theme background ("none": transparent)."""
    color = first.theme["background.color"]
    return "none" if unset(color) else str(color)


def backgrounds(fig: Figure, grid: Grid, placed: Sequence[Placed], radius: float = 0.0) -> None:
    """Put each tile's theme background behind its part of the grid: its plot box and the
    margins around it, its corners rounded radius points."""
    w, h = grid.size
    for p in placed:
        color = p.style.theme["background.color"]
        if unset(color):
            continue
        x0, x1 = grid.column_span(p.area.column, p.area.last_column)
        y0, y1 = grid.row_span(p.area.row, p.area.last_row)
        if radius > 0:  # in inches, so the corners stay round
            if p.background is not None:
                p.background.remove()
            p.background = FancyBboxPatch(
                (x0, h - y1),
                x1 - x0,
                y1 - y0,
                boxstyle=f"round,pad=0,rounding_size={radius / 72}",
                transform=fig.dpi_scale_trans,
                facecolor=str(color),
                edgecolor="none",
                zorder=-10,
            )
            fig.add_artist(p.background)
            continue
        bounds = (x0 / w, 1 - y1 / h, (x1 - x0) / w, (y1 - y0) / h)
        if not isinstance(p.background, Rectangle):
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
    fig: Figure, grid: Grid, look: LineStyle, between: bool, border: bool
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
            color=look.color,
            linewidth=look.width,
            linestyle=cast(Any, look.style),
            solid_capstyle=cast(Any, look.cap),
            dash_capstyle=cast(Any, look.cap),
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
            color=look.color,
            linewidth=look.width,
            linestyle=cast(Any, look.style),
            solid_joinstyle=cast(Any, look.join),
            dash_joinstyle=cast(Any, look.join),
            zorder=-5,
        )
        fig.add_artist(line)
        lines.append(line)
    grid.lines = lines
    return lines


def apply_separators(
    fig: Figure, grid: Grid, layout_values: dict[str, Any], base: float, first: Style
) -> None:
    """The first tile's theme background in the gaps, blank cells and edges, and the lines
    between tiles and, with border.show, around them, when the line style draws a line."""
    fig.set_facecolor(gap_color(first))
    look = line_style(layout_values, first, base)
    if look.visible:
        separator_lines(fig, grid, look, True, bool(layout_values["separators.border.show"]))
