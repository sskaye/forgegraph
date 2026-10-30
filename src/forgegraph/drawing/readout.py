"""The readouts an HTML page shows on a graph's data points (drawing/page.py).

Drawing an xy graph attaches what its readouts need to its axes (attach). Once the figure is
final, marks() finds each data point: a marker or a line's point, where it is in points from
the figure's top left with its marker's radius, or a bar, as its box. Each comes with the
lines its readout shows, as (name, value) pairs of HTML:

- the x and y axes': the axis's title, or with none, the point's column's name; and the
  point's value, with its error bar's distances and their aggregation where it has one;
- then its series' color, marker shape and line style, each only where it varies: the key's
  title, or with none, the column's name, and the point's group. Two that name the same
  column share a line.

A category is written as its label, and a date in its axis's date format. A number with an
error bar is rounded to the error's significant digit, the error to one significant figure:
8.0 ± 0.4. One without is written in the series' value_label.format for a value, or the
axis's tick label format on the base axis; at auto, with one more decimal than the tick
labels, which are rounded for reading along an axis, not for reading one value.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from weakref import WeakKeyDictionary

import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import to_hex
from matplotlib.dates import num2date
from matplotlib.figure import Figure

from forgegraph.drawing.axes import number_text
from forgegraph.drawing.markup import to_html
from forgegraph.drawing.style import unset
from forgegraph.fonts import font_file

COLUMN_NAME = "column_name"
SERIES = "__forgegraph_series__"  # xy's: the series a row belongs to
MINUS = "\u2212"
STYLED = ("color", "marker_shape", "line_style")  # in the readout's order


@dataclass(frozen=True)
class Look:
    """How a series' readouts look: its value labels' font (family, weight number, size in
    points) and color, and the graph's background and axis line colors."""

    family: str
    weight: int
    size: float
    color: str
    background: str
    border: str

    @property
    def font(self) -> Path:
        return font_file(self.family, self.weight)


@dataclass(frozen=True)
class Mark:
    """One data point a readout shows: where it is, in points from the figure's top left;
    its marker's radius in points (0 for a line's point without one); for a bar, its box
    (left, top, right, bottom, in points) instead; the color of the ring around it; its look;
    and its readout's lines, (name, value) pairs of HTML."""

    x: float
    y: float
    radius: float
    box: tuple[float, float, float, float] | None
    ring: str
    look: Look
    lines: tuple[tuple[str, str], ...]


@dataclass
class _Drawing:
    drawn: Any  # xy.Drawn
    gt: dict[str, Any]


_DRAWINGS: WeakKeyDictionary[Axes, _Drawing] = WeakKeyDictionary()


def attach(ax: Axes, drawn: Any, gt: dict[str, Any]) -> None:
    """Keep what the readouts of the graph drawn into ax need (xy.draw)."""
    _DRAWINGS[ax] = _Drawing(drawn, gt)


def marks(fig: Figure) -> list[Mark]:
    """Every data point in the figure's graphs, as it is drawn now."""
    return [m for ax in fig.axes if ax in _DRAWINGS for m in _of(ax, _DRAWINGS[ax])]


def _of(ax: Axes, d: _Drawing) -> list[Mark]:
    fig = ax.figure
    assert isinstance(fig, Figure)
    to_pt = 72 / fig.dpi
    height = fig.get_size_inches()[1] * 72
    r = d.drawn.roles
    border = to_hex(ax.spines["left"].get_edgecolor())
    paper = ax.get_facecolor() if ax.patch.get_visible() else fig.get_facecolor()
    out = []
    for s in d.drawn.series:
        lines = _lines(ax, s, d)
        look = _look(s, to_hex(paper, keep_alpha=False), border)
        rings = s.ring if isinstance(s.ring, list) else [s.ring] * len(s.x)
        if s.line is not None and (s.shows("marker") or s.shows("line")):
            radius = s.look.marker_size / 2 if s.shows("marker") else 0.0
            px, py = (s.x, s.y) if r.base == "x" else (s.y, s.x)
            at = s.line.get_transform().transform(
                np.c_[np.asarray(px, dtype=float), np.asarray(py, dtype=float)]
            )
            for i, (x, y) in enumerate(at):
                if np.isfinite(x) and np.isfinite(y):
                    out.append(
                        Mark(x * to_pt, height - y * to_pt, radius, None, rings[i], look, lines[i])
                    )
        if s.bars is not None:
            b = s.bars
            whole = np.isfinite(b.places) & np.isfinite(b.bottom) & np.isfinite(b.top)
            for i, box in zip(np.flatnonzero(whole), b.rectangles(), strict=True):
                left, right = box.x0 * to_pt, box.x1 * to_pt
                top, bottom = height - box.y1 * to_pt, height - box.y0 * to_pt
                centre = ((left + right) / 2, (top + bottom) / 2)
                out.append(Mark(*centre, 0.0, (left, top, right, bottom), rings[i], look, lines[i]))
    return out


def _look(s: Any, paper: str, border: str) -> Look:
    t = s.style.theme
    path = f"series.{'benchmark.' if s.benchmark else ''}value_label"
    text = s.style.text(path)
    return Look(
        str(t[f"{path}.font"]),
        int(text.font.get_weight()),
        float(text.font.get_size_in_points()),
        str(text.color),
        paper,
        border,
    )


def _lines(ax: Axes, s: Any, d: _Drawing) -> list[tuple[tuple[str, str], ...]]:
    """Each point's readout lines."""
    r, gt = d.drawn.roles, d.gt
    n = len(s.x)
    columns = []
    for name in ("x", "y"):
        base = name == r.base
        values = np.asarray(s.x if base else s.stack.value, dtype=object)
        title = _axis_title(gt, name, r.base_column if base else s.listed.column)
        columns.append((title, _values(ax, s, d, name, base, values)))
    columns += _styling(s, d)
    return [tuple((title, values[i]) for title, values in columns) for i in range(n)]


def _axis_title(gt: dict[str, Any], name: str, column: str) -> str:
    given = gt[f"axis.{name}.title"]
    return html.escape(column) if unset(given) or given == COLUMN_NAME else to_html(str(given))


def _values(ax: Axes, s: Any, d: _Drawing, name: str, base: bool, values: Any) -> list[str]:
    """Each point's value along axis name, as its readout writes it."""
    gt, kind = d.gt, d.drawn.kinds[name]
    if kind == "categorical":
        cats = d.drawn.categories[name]
        return [html.escape(str(cats[round(float(v))])) if _finite(v) else "" for v in values]
    axis = ax.xaxis if name == "x" else ax.yaxis
    if base:
        given, path = "auto", f"axis.{name}.tick.label.format"
    else:
        given, path = s.listed.values["value_label.format"], s.listed.path("value_label.format")
    if kind == "date":
        if given == "auto" and gt[f"axis.{name}.tick.label.format"] == "auto":
            write = _date
        else:
            write = number_text(gt, name, axis, given, path, kind=kind)
        return [html.escape(write(v)) if _finite(v) else "" for v in values]
    write = number_text(gt, name, axis, given, path, extra=1, kind=kind)
    lower, upper, words = s.errors.get(name, (None, None, None))
    out = []
    for i, v in enumerate(values):
        if not _finite(v):
            out.append("")
        elif lower is not None and upper is not None and (lower[i] > 0 or upper[i] > 0):
            out.append(html.escape(with_error(float(v), float(lower[i]), float(upper[i]), words)))
        else:
            out.append(html.escape(write(v)))
    return out


def _date(v: Any) -> str:
    when = num2date(float(v)).replace(tzinfo=None)
    return when.strftime("%Y-%m-%d" if when.time() == when.min.time() else "%Y-%m-%d %H:%M")


def _finite(v: Any) -> bool:
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def with_error(value: float, lower: float, upper: float, words: str | None) -> str:
    """A value with its error bar's distances: each distance to one significant figure, and
    the value to the finer of their last digits; ± where they're the same. 7.985, 0.426 ->
    8.0 ± 0.4."""
    lo, lo_places = _one_figure(lower)
    hi, hi_places = _one_figure(upper)
    places = max(p for p in (lo_places, hi_places) if p is not None)
    rounded = round(value, places)
    text = _fixed(rounded, places)
    if lo == hi:
        text += f" ± {_fixed(lo, places)}"
    else:
        text += f" {MINUS}{_fixed(lo, lo_places or 0)} / +{_fixed(hi, hi_places or 0)}"
    return text if words is None else f"{text} ({words})"


def _one_figure(distance: float) -> tuple[float, int | None]:
    """A distance to one significant figure, and the decimal places that leaves (negative
    for tens and above); None for 0."""
    if distance <= 0 or not math.isfinite(distance):
        return 0.0, None
    places = -math.floor(math.log10(distance))
    rounded = round(distance, places)
    if rounded >= 10 ** (1 - places):  # 0.96 -> 1.0: one figure is now a place further left
        places -= 1
        rounded = round(distance, places)
    return rounded, places


def _fixed(value: float, places: int) -> str:
    return f"{round(value, places):.{max(places, 0)}f}".replace("-", MINUS)


def _styling(s: Any, d: _Drawing) -> list[tuple[str, list[str]]]:
    """The lines for the series' color, marker shape and line style, each where it varies:
    a column, or the series when there's more than one."""
    gt, listed = d.gt, d.drawn.listed
    n = len(s.x)
    seen: set[str] = set()
    out = []
    for by in STYLED:
        column = s.listed.by.get(by)
        if column is None or column in seen or (column == SERIES and len(listed) < 2):
            continue
        seen.add(column)
        numeric = by == "color" and s.values is not None
        key = gt["legend.color_bar.title.text" if numeric else "legend.key.title.text"]
        if column == SERIES:
            title = None if unset(key) or key == COLUMN_NAME else to_html(str(key))
            values = [html.escape(str(s.listed.name))] * n
        else:
            title = html.escape(column) if unset(key) or key == COLUMN_NAME else to_html(str(key))
            if s.values is not None and by == "color":
                values = [f"{float(v):.4g}".replace("-", MINUS) for v in s.values]
            else:
                values = [html.escape(str(s.groups.get(column, "")))] * n
        out.append(("" if title is None else title, values))
    return out


__all__ = ["Look", "Mark", "attach", "marks", "with_error"]
