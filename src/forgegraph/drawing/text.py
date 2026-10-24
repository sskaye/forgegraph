"""Where text's letters are: every spacing ForgeGraph sets is measured to them.

Matplotlib gives each text a box sized for the font's tallest letters, deepest descenders and
line spacing, whatever the text says, so a gap measured from that box isn't the gap you see.
ForgeGraph measures to the letters instead, as CSS's `text-box: trim-both cap alphabetic`
does: a text's edges run from the font's capital height down to its baseline, and grow only
where its own letters reach further (a superscript, a parenthesis, a descender). Text set
in a row (tick labels on one axis, a key's entries) shares one set of edges, so it stays
aligned.

Everything here is in points, measured from the text's origin: its start, on its baseline.
A text of several lines is measured from the start of its box, on its last line's baseline,
as matplotlib lays it out; each line's letters are measured where that line sits.

- `font()` makes the font a theme uses at a size and weight;
- `edges()` and `row()` give a text's or a row's visible edges;
- `box()` gives matplotlib's box, to convert matplotlib's paddings into visible gaps;
- `footprint()` gives a drawn text's visible extent on the canvas.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.text import Text
from matplotlib.textpath import TextPath
from matplotlib.transforms import Bbox

from forgegraph.fonts import register_fonts


@dataclass(frozen=True)
class Edges:
    """A text's visible extent in points, from its origin (its start, on its baseline)."""

    left: float  # where its first letter's ink starts
    right: float  # where its last letter's ink ends
    top: float  # above the baseline: the capital height, or higher where its letters reach
    bottom: float  # below the baseline, as a positive distance: 0, or where letters descend
    advance: float  # its laid-out width, from origin to where the next text would start

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top + self.bottom

    @property
    def middle(self) -> float:
        """The height above the baseline of the middle of its edges: where it centres."""
        return (self.top - self.bottom) / 2


def font(family: str, size: float, weight: int | str = "normal") -> FontProperties:
    """The font at a size in points and a weight (a name or a font-file weight number)."""
    register_fonts()
    return FontProperties(family=family, size=size, weight=weight)


def _key(prop: FontProperties) -> tuple:
    family = tuple(prop.get_family())
    return (family, prop.get_size_in_points(), prop.get_weight(), prop.get_style())


@cache
def _outline(text: str, key: tuple) -> Bbox:
    family, size, weight, style = key
    prop = FontProperties(family=list(family), size=size, weight=weight, style=style)
    return TextPath((0, 0), text, prop=prop).get_extents()


@cache
def _capital(key: tuple) -> float:
    return _outline("H", key).y1


@cache
def _box(text: str, key: tuple) -> tuple[float, float, float]:
    top, bottom, advance, _ = _layout(text, key, "left")
    return top, bottom, advance


@cache
def _layout(
    text: str, key: tuple, align: str
) -> tuple[float, float, float, tuple[tuple[str, float, float], ...]]:
    """Matplotlib's box for a text (top, bottom, advance) and where each of its lines starts
    and has its baseline (line, x, y), in points from the box's start on the last line's
    baseline. align: how lines of different widths line up (matplotlib's multialignment)."""
    family, size, weight, style = key
    prop = FontProperties(family=list(family), size=size, weight=weight, style=style)
    fig = Figure(figsize=(2, 2), dpi=72 * _FINE)  # fine enough that pixel rounding is negligible
    FigureCanvasAgg(fig)
    rc: Any = {"text.hinting": "no_hinting"}  # as render.style draws
    with matplotlib.rc_context(rc):
        artist = fig.text(0, 0, text, fontproperties=prop, va="baseline", ha=align, transform=None)
        renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
        extent = artist.get_window_extent(renderer)
        _, lines, _ = artist._get_layout(renderer)  # type: ignore[attr-defined]
    start = extent.x0
    placed = tuple((line, (x - start) / _FINE, y / _FINE) for line, _, (x, y) in lines)
    return extent.y1 / _FINE, -extent.y0 / _FINE, extent.width / _FINE, placed


_FINE = 20  # pixels per point when measuring matplotlib's box


def edges(text: str, prop: FontProperties, align: str = "left") -> Edges:
    """A text's visible edges. A text with no letters has the font's capital height. align:
    how the lines of a text of several lines line up (left, center or right)."""
    key = _key(prop)
    cap = _capital(key)
    if not text.strip():
        return Edges(0.0, 0.0, cap, 0.0, box(text, prop).advance)
    if "\n" not in text:
        ink = _outline(text, key)
        return Edges(ink.x0, ink.x1, max(cap, ink.y1), max(0.0, -ink.y0), box(text, prop).advance)
    _, _, advance, lines = _layout(text, key, align)
    found = [(_outline(line, key), x, y) for line, x, y in lines if line.strip()]
    return Edges(
        min(x + ink.x0 for ink, x, _ in found),
        max(x + ink.x1 for ink, x, _ in found),
        max(y + max(cap, ink.y1) for ink, _, y in found),
        max(0.0, *(-(y + ink.y0) for ink, _, y in found)),
        advance,
    )


def row(texts: list[str], prop: FontProperties) -> Edges:
    """The edges a row of texts shares: the highest top and the deepest bottom of any of them,
    with the left and right of the widest."""
    all_edges = [edges(t, prop) for t in texts] or [edges("", prop)]
    widest = max(all_edges, key=lambda e: e.advance)
    return Edges(
        widest.left,
        widest.right,
        max(e.top for e in all_edges),
        max(e.bottom for e in all_edges),
        widest.advance,
    )


@dataclass(frozen=True)
class Box:
    """Matplotlib's box for a text, in points from its origin."""

    top: float  # above the baseline
    bottom: float  # below the baseline, as a positive distance
    advance: float  # its width


def box(text: str, prop: FontProperties) -> Box:
    """The box matplotlib lays a text out in: taller than its letters above and below."""
    return Box(*_box(text, _key(prop)))


def footprint(artist: Text, renderer: Any) -> Bbox:
    """A drawn text's visible extent on the canvas, in display pixels: upright or turned a
    quarter turn either way."""
    extent = artist.get_window_extent(renderer)
    text = artist.get_text()
    if not artist.get_visible() or not text.strip() or extent.width == 0:
        return Bbox.null()
    prop = artist.get_fontproperties()
    scale = artist.get_figure(root=True).dpi / 72  # type: ignore[union-attr]
    align = getattr(artist, "_multialignment", None) or artist.get_horizontalalignment()
    e, b = edges(text, prop, align), box(text, prop)
    # How much of the box on each side holds no letters, in display pixels.
    cut_start, cut_end = e.left * scale, (b.advance - e.right) * scale
    cut_top, cut_bottom = (b.top - e.top) * scale, (b.bottom - e.bottom) * scale
    angle = round(artist.get_rotation()) % 360
    x0, y0, x1, y1 = extent.x0, extent.y0, extent.x1, extent.y1
    if angle == 0:
        return Bbox.from_extents(x0 + cut_start, y0 + cut_bottom, x1 - cut_end, y1 - cut_top)
    if angle == 90:  # reads upward: its top faces left, its start is at the bottom
        return Bbox.from_extents(x0 + cut_top, y0 + cut_start, x1 - cut_bottom, y1 - cut_end)
    if angle == 270:  # reads downward: its top faces right, its start is at the top
        return Bbox.from_extents(x0 + cut_bottom, y0 + cut_end, x1 - cut_top, y1 - cut_start)
    return extent  # other angles: matplotlib's box (only the watermark, inside the plot)
