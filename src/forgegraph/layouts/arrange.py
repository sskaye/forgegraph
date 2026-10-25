"""Placing a tab's tiles on its grid, so that their plot boxes line up.

Each pass measures, for every tile, the room its titles, tick labels and keys need on each
side of its plot box, to their letters (render.figure.visible_extent). A column's left margin
is the most room any tile starting in it needs on its left; its right margin, the most any
tile ending in it needs on its right; rows work the same way, top and bottom. Columns and rows
are separated by the layout's gap. What's left of the format's width, after the margins and
gaps, is shared among the columns' plot boxes by column_widths, and likewise for heights; a
tile spanning several columns or rows runs across the margins and gaps inside it, so its plot
box lines up with the ones beside it. With the format's height auto, each row is as tall as
the tallest plot box its tiles' plot_area.aspect needs at their widths (a tile spanning rows
shares what it lacks among them); width auto works the same way across columns. Tick labels
change with the plot boxes' sizes, so the passes repeat until nothing moves, as for one graph
(render.figure.layout). Tiles are never scaled: a figure too small for them is an error naming
the tiles that don't fit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from forgegraph.drawing import spacing
from forgegraph.drawing.figure import MARGIN_IN, PASSES, LayoutError, visible_extent
from forgegraph.drawing.style import Style, isolated, unset
from forgegraph.drawing.text import measure
from forgegraph.spec.layout import BLANK, Area

Room = tuple[float, float, float, float]  # left, right, bottom, top, in inches


@dataclass
class Placed:
    """A tile on the grid: its name, area, Axes and style, and the patch behind it in its
    theme's background color."""

    name: str
    area: Area
    ax: Axes
    style: Style
    background: Rectangle | None = None

    @property
    def aspect(self) -> float:
        return float(self.style.theme["plot_area.aspect"])


@dataclass
class Grid:
    """A tab's grid as laid out, in inches from the figure's top left: where each column's
    and row's plot boxes start, and their sizes and margins."""

    areas: list[list[str]]
    left: list[float]
    width: list[float]
    margin_l: list[float]
    margin_r: list[float]
    top: list[float]
    height: list[float]
    margin_t: list[float]
    margin_b: list[float]
    size: tuple[float, float]
    gap: float
    edge: float  # between the outer tiles and the figure's edges
    foot: float  # below the last row, for the footnote
    lines: list[Line2D] = field(default_factory=list)

    def column_span(self, first: int, last: int) -> tuple[float, float]:
        """From the left of `first` column's margin to the right of `last`'s, in inches."""
        return (
            self.left[first] - self.margin_l[first],
            self.left[last] + self.width[last] + self.margin_r[last],
        )

    def row_span(self, first: int, last: int) -> tuple[float, float]:
        """From the top of `first` row's margin to the bottom of `last`'s, in inches."""
        return (
            self.top[first] - self.margin_t[first],
            self.top[last] + self.height[last] + self.margin_b[last],
        )


def _measure(fig: Figure, placed: Sequence[Placed]) -> dict[str, Room]:
    for p in placed:
        with isolated(p.style):
            spacing.apply(p.ax, p.style)
    measure(fig)
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    dpi = fig.dpi
    rooms = {}
    for p in placed:
        extent, box = visible_extent(p.ax, renderer), p.ax.bbox
        rooms[p.name] = (
            (box.x0 - extent.x0) / dpi,
            (extent.x1 - box.x1) / dpi,
            (box.y0 - extent.y0) / dpi,
            (extent.y1 - box.y1) / dpi,
        )
    return rooms


def _margins(
    placed: Sequence[Placed], rooms: dict[str, Room], count: int, across: bool
) -> tuple[list[float], list[float]]:
    """Each column's left and right margins (across), or each row's top and bottom."""
    near, far = [0.0] * count, [0.0] * count
    for p in placed:
        left, right, bottom, top = rooms[p.name]
        a = p.area
        if across:
            near[a.column] = max(near[a.column], left)
            far[a.last_column] = max(far[a.last_column], right)
        else:
            near[a.row] = max(near[a.row], top)
            far[a.last_row] = max(far[a.last_row], bottom)
    return near, far


def _shared(total: float, weights: list[float] | None, count: int) -> list[float]:
    w = weights or [1.0] * count
    return [total * x / sum(w) for x in w]


def _sizes_from_aspect(
    placed: Sequence[Placed],
    other: list[float],
    other_margins: tuple[list[float], list[float]],
    margins: tuple[list[float], list[float]],
    gap: float,
    count: int,
    across: bool,
) -> list[float]:
    """Sizes along one direction (column widths when across, row heights otherwise) from the
    sizes along the other, so that each tile's plot box is as long as its aspect asks: each
    column or row takes the most its one-cell tiles need, then a spanning tile that still
    lacks room shares what it lacks evenly among its columns or rows."""

    def extent(sizes: list[float], m: tuple[list[float], list[float]], lo: int, hi: int) -> float:
        inner = sum(m[1][i] + gap + m[0][i + 1] for i in range(lo, hi))
        return sum(sizes[lo : hi + 1]) + inner

    def along(a: Area) -> tuple[int, int]:
        return (a.column, a.last_column) if across else (a.row, a.last_row)

    def against(a: Area) -> tuple[int, int]:
        return (a.row, a.last_row) if across else (a.column, a.last_column)

    def want(p: Placed) -> float:
        length = extent(other, other_margins, *against(p.area))
        return length * p.aspect if across else length / p.aspect

    sizes = [0.0] * count
    for p in placed:
        lo, hi = along(p.area)
        if lo == hi:
            sizes[lo] = max(sizes[lo], want(p))
    for p in placed:
        lo, hi = along(p.area)
        short = want(p) - extent(sizes, margins, lo, hi)
        if lo != hi and short > 0:
            for i in range(lo, hi + 1):
                sizes[i] += short / (hi - lo + 1)
    return sizes


def _put(
    fig: Figure,
    areas: list[list[str]],
    placed: Sequence[Placed],
    rooms: dict[str, Room],
    gap: float,
    width: float | None,
    height: float | None,
    column_widths: list[float] | None,
    row_heights: list[float] | None,
    edge: float,
    foot: float = 0.0,
) -> tuple[bool, Grid]:
    """Size the figure and place every plot box with this room around each, and `edge`
    between the outer tiles and the figure's edges. Returns whether nothing moved (the layout
    has settled), and the grid as placed."""
    rows, columns = len(areas), len(areas[0])
    ml, mr = _margins(placed, rooms, columns, across=True)
    mt, mb = _margins(placed, rooms, rows, across=False)
    around_w = 2 * edge + sum(ml) + sum(mr) + gap * (columns - 1)
    around_h = 2 * edge + sum(mt) + sum(mb) + gap * (rows - 1) + foot
    if width is not None and height is not None:
        widths = _shared(width - around_w, column_widths, columns)
        heights = _shared(height - around_h, row_heights, rows)
    elif width is not None:
        widths = _shared(width - around_w, column_widths, columns)
        heights = _sizes_from_aspect(placed, widths, (ml, mr), (mt, mb), gap, rows, across=False)
    else:
        assert height is not None
        heights = _shared(height - around_h, row_heights, rows)
        widths = _sizes_from_aspect(placed, heights, (mt, mb), (ml, mr), gap, columns, across=True)
    _check_room(placed, widths, heights)
    fig_w, fig_h = around_w + sum(widths), around_h + sum(heights)
    left, x = [], edge
    for c in range(columns):
        left.append(x + ml[c])
        x += ml[c] + widths[c] + mr[c] + gap
    top, y = [], edge
    for r in range(rows):
        top.append(y + mt[r])
        y += mt[r] + heights[r] + mb[r] + gap
    grid = Grid(areas, left, widths, ml, mr, top, heights, mt, mb, (fig_w, fig_h), gap, edge, foot)
    old_size = fig.get_size_inches()
    fig.set_size_inches(fig_w, fig_h)
    moved = 0.0
    for p in placed:
        a = p.area
        x0 = left[a.column]
        x1 = left[a.last_column] + widths[a.last_column]
        y0 = top[a.row]
        y1 = top[a.last_row] + heights[a.last_row]
        position = (x0 / fig_w, 1 - y1 / fig_h, (x1 - x0) / fig_w, (y1 - y0) / fig_h)
        old = p.ax.get_position().bounds
        p.ax.set_position(position)
        moved = max(moved, *(abs(a_ - b) for a_, b in zip(old, position, strict=True)))
    settled = abs(old_size[0] - fig_w) < 1e-3 and abs(old_size[1] - fig_h) < 1e-3 and moved < 1e-4
    return settled, grid


def _check_room(placed: Sequence[Placed], widths: list[float], heights: list[float]) -> None:
    tight = [
        p.name
        for p in placed
        if any(widths[c] <= 0 for c in range(p.area.column, p.area.last_column + 1))
        or any(heights[r] <= 0 for r in range(p.area.row, p.area.last_row + 1))
    ]
    if tight:
        names = ", ".join(f"'{n}'" for n in tight)
        raise LayoutError(
            f"size: too small for the titles, tick labels and keys around the plot box of "
            f"tile {names}; make the format larger or its base size smaller, or give the "
            f"tiles fewer columns or rows"
        )


def arrange(
    fig: Figure,
    areas: list[list[str]],
    placed: Sequence[Placed],
    gap: float,
    width: float | None,
    height: float | None,
    column_widths: list[float] | None = None,
    row_heights: list[float] | None = None,
    edge: float = MARGIN_IN,
    foot: float = 0.0,
) -> Grid:
    """Lay the tiles out on the grid until nothing moves (see the module's description).
    Sizes are in inches; width or height None is auto; edge is the space between the outer
    tiles and the figure's edges. If no pass settles, it lays out once
    more with, for each tile, the most room either of the last two passes needed, as
    render.figure.layout does."""
    last: dict[str, Room] = {p.name: (0.0, 0.0, 0.0, 0.0) for p in placed}
    both = dict(last)
    sizes = (gap, width, height, column_widths, row_heights, edge, foot)
    for _ in range(PASSES):
        rooms = _measure(fig, placed)
        settled, grid = _put(fig, areas, placed, rooms, *sizes)
        if settled:
            break
        both = {
            n: cast(Room, tuple(max(a, b) for a, b in zip(last[n], rooms[n], strict=True)))
            for n in rooms
        }
        last = rooms
    else:
        _, grid = _put(fig, areas, placed, both, *sizes)
    for p in placed:
        with isolated(p.style):
            spacing.apply(p.ax, p.style)
    return grid


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
