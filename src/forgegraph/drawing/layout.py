"""Laying a figure out by what's visible: one graph, or a layout's tab of tiles on its grid.

Width and height are in mm. ForgeGraph lays the figure out itself rather than with
matplotlib's layout engines, which space text by its box (see forgegraph.drawing.text). One
graph is a grid of one tile (layout), MARGIN_IN from the figure's edges; a layout's tab is a
grid of its tiles (arrange), so that their plot boxes line up.

Each pass measures, for every tile, the room its titles, tick labels and keys need on each
side of its plot box, to their letters (visible_extent, room). A column's left margin is the
most room any tile starting in it needs on its left; its right margin, the most any tile
ending in it needs on its right; rows work the same way, top and bottom. Columns and rows are
separated by the layout's gap. What's left of the format's width, after the margins and gaps,
is shared among the columns' plot boxes by column_widths, and likewise for heights; a tile
spanning several columns or rows runs across the margins and gaps inside it, so its plot box
lines up with the ones beside it. With the format's height auto, each row is as tall as the
tallest plot box its tiles' plot_area.aspect needs at their widths (a tile spanning rows
shares what it lacks among them); width auto works the same way across columns. Tick labels
change with the plot boxes' sizes, so the passes repeat until nothing moves (arrange). Tiles
are never scaled: a figure too small for them is an error naming the tiles that don't fit.

A footnote is written small at the bottom right, below everything else.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from forgegraph.drawing import spacing, text
from forgegraph.drawing.errors import LayoutError
from forgegraph.drawing.figure import WATERMARK, inches
from forgegraph.drawing.key import keys
from forgegraph.drawing.markup import literal
from forgegraph.drawing.style import Style, isolated
from forgegraph.spec.layout import Area

MARGIN_IN = 0.04  # space kept between what's drawn and the figure's edges
PASSES = 6  # layout passes; if none settles, the last two passes' most room is used
FOOTNOTE = "forgegraph-footnote"

Room = tuple[float, float, float, float]  # left, right, bottom, top, in inches


def tick_marks(ax: Axes, renderer: Any) -> list[Bbox]:
    """The Axes' tick marks in view, in display pixels."""
    out = []
    for axis in (ax.xaxis, ax.yaxis):
        lo, hi = sorted(axis.get_view_interval())
        for tick in [*axis.get_major_ticks(), *axis.get_minor_ticks()]:
            if not lo <= tick.get_loc() <= hi:
                continue
            for line in (tick.tick1line, tick.tick2line):
                if line.get_visible():
                    out.append(line.get_window_extent(renderer))
    return out


def texts_of(ax: Axes) -> list[Text]:
    """The Axes' titles, its texts and its tick labels in view."""
    out: list[Text] = [ax.title, ax.xaxis.label, ax.yaxis.label, *ax.texts]
    out += [ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()]  # e.g. a date axis's year
    for axis in (ax.xaxis, ax.yaxis):
        lo, hi = sorted(axis.get_view_interval())
        for tick in axis.get_major_ticks():
            if lo <= tick.get_loc() <= hi:
                out += [tick.label1, tick.label2]
    return out


def visible_extent(ax: Axes, renderer: Any) -> Bbox:
    """Everything drawn for an Axes and any Axes inside it, measured to letters and lines, in
    display pixels. The watermark, drawn over the plot box, isn't included."""
    boxes = []
    for each in spacing.axes_family(ax):
        boxes.append(each.bbox)
        for side, spine in each.spines.items():  # a box line is centred on the box's edge
            if spine.get_visible():
                half = spine.get_linewidth() / 2 * ax.figure.dpi / 72  # type: ignore[union-attr]
                grow = {
                    "left": (half, 0, 0, 0),
                    "right": (0, 0, half, 0),
                    "bottom": (0, half, 0, 0),
                    "top": (0, 0, 0, half),
                }.get(side, (half, half, half, half))  # a color bar's outline: every side
                b = each.bbox
                boxes.append(
                    Bbox.from_extents(
                        b.x0 - grow[0], b.y0 - grow[1], b.x1 + grow[2], b.y1 + grow[3]
                    )
                )
        boxes += tick_marks(each, renderer)
        for t in texts_of(each):
            if t.get_visible() and t.get_text().strip() and t.get_gid() != WATERMARK:
                boxes.append(text.footprint(t, renderer))
        boxes += [k.bbox() for k in keys(each) if k.outside]  # its frame, drawn or not
    return Bbox.union([b for b in boxes if b.width > 0 or b.height > 0])


def room(ax: Axes, renderer: Any) -> Room:
    """The room what's drawn around the Axes' plot box takes on each side, in inches."""
    extent, box, dpi = visible_extent(ax, renderer), ax.bbox, ax.figure.dpi  # type: ignore[union-attr]
    return (
        (box.x0 - extent.x0) / dpi,
        (extent.x1 - box.x1) / dpi,
        (box.y0 - extent.y0) / dpi,
        (extent.y1 - box.y1) / dpi,
    )


def add_footnote(fig: Figure, words: str, style: Style) -> Text:
    """The figure's footnote, in the theme's footnote look; laying out places it."""
    note = fig.text(
        0,
        0,
        literal(words),
        fontproperties=style.font("footnote.size", "font.weight"),
        color=style.color("footnote.color"),
        ha="right",
        va="baseline",
        gid=FOOTNOTE,
    )
    note.gap = style.pt("footnote.gap")  # type: ignore[attr-defined]
    fig.footnote = note  # type: ignore[attr-defined]
    return note


def footnote_room(fig: Figure) -> float:
    """The room a figure's footnote needs below everything else, in inches: its gap and its
    letters."""
    note = getattr(fig, "footnote", None)
    if note is None:
        return 0.0
    e = text.edges(note.get_text(), note.get_fontproperties())
    return (float(note.gap) + e.top + e.bottom) / 72


def place_footnote(fig: Figure, right: float, bottom: float) -> None:
    """Put the footnote's letters `right` and `bottom` inches from the figure's bottom right."""
    note = getattr(fig, "footnote", None)
    if note is None:
        return
    w, h = fig.get_size_inches()
    e = text.edges(note.get_text(), note.get_fontproperties())
    cut = (e.advance - e.right) / 72  # its box reaches past its last letter by this much
    note.set_position((1 - (right - cut) / w, (bottom + e.bottom / 72) / h))


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
    """A grid as laid out, in inches from the figure's top left: where each column's and
    row's plot boxes start, and their sizes and margins."""

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
    text.measure(fig)
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    return {p.name: room(p.ax, renderer) for p in placed}


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
    tiles and the figure's edges, foot the room below the last row for the footnote.

    It has settled when a pass changes the figure's size by under 0.001 in and moves every
    plot box by under 0.0001 of the figure. Tick labels can keep it from settling,
    alternating between two states (a taller box gets more, wider labels, which shrink the
    box again), so after PASSES unsettled passes it lays out once more with, for each tile,
    the most room either of the last two passes needed: both states' labels fit. Earlier
    passes, made while the figure was still far from its size, don't count."""
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


def layout(fig: Figure, ax: Axes, style: Style) -> Grid:
    """Size the figure and place one graph's plot box from what's drawn around it, as a grid
    of one tile MARGIN_IN from the figure's edges, with room for its footnote below: with
    both of the format's sizes given, the plot box takes the space left; with one auto, it
    keeps the theme's plot_area.aspect and the figure is fitted around it."""
    width = inches(style.format["figure.width"])
    height = inches(style.format["figure.height"])
    placed = [Placed("graph", Area(0, 0), ax, style)]
    try:
        grid = arrange(fig, [["graph"]], placed, 0.0, width, height, foot=footnote_room(fig))
    except LayoutError:  # a graph alone has no tiles to name
        raise LayoutError(
            "size: too small for the titles, tick labels and keys around the plot box; "
            "make the format larger or its base font smaller"
        ) from None
    place_footnote(fig, MARGIN_IN, MARGIN_IN)
    return grid
