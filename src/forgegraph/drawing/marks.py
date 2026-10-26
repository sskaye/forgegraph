"""How series at the same place combine, bars, and value labels (graph_types/xy.yaml series.*,
mark.bar; themes series.bar, series.value_label).

- **Aggregation** (series.aggregation): none draws each series as it is; sum stacks the series
  at each place in series order, positive values up from 0 and negative values down; percent
  stacks each series' share of the place's total, to 100. The benchmark's series stack among
  themselves, apart from the others. A series with several rows at one
  place is an error that names axis.*.data.aggregation. Dates on the value axis can't be
  added, so stacking them is an error.
- **Bars** (mark.bar.show) run from 0 (1 on a log axis), or from the stack below, to each
  value; on a date value axis, where 0 is 1970, they're an error. Each series' bars are one
  collection of rectangles (Bars), outlined in the theme's series.bar.edge.color and
  edge.width (the benchmark's, series.benchmark.bar), whose width is the theme's
  series.bar.width in points at any size: they're laid out again at every draw.
- **Side by side** (series.offset) centres the marks at each place on it, in series order:
  bars series.bar.gap apart, markers touching. A place with fewer series has fewer marks,
  still centred. Bars, or side-by-side marks, wider than the space between places are an
  error.
- **Value labels** (series.value_label) write each value by its mark: beyond it, or inside a
  bar's end (auto: inside where it fits); a stacked segment's at its centre; with total, each
  stack's total beyond its end. Labels beyond the plot area grow an automatic value axis;
  against a set limit, or running into each other, they're an error. On a date value axis
  they're dates, so they need a date format.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
from matplotlib.text import Annotation
from matplotlib.transforms import Bbox, IdentityTransform, Transform

from forgegraph.drawing.axes import number_text, numbers
from forgegraph.drawing.errors import DrawError
from forgegraph.drawing.style import Style, unset
from forgegraph.drawing.text import measure

BAR = "forgegraph-bar"  # each series' bars
VALUE_LABEL = "forgegraph-value-label"


@dataclass
class Stacked:
    """A series' values once combined: where each mark starts and ends along the value axis,
    and the value it stands for."""

    bottom: np.ndarray
    top: np.ndarray
    value: np.ndarray


def check(gt: dict[str, Any], value_axis: str, kind: str) -> None:
    """Combinations of series settings that can't be drawn, once the value axis's type (kind)
    is known."""
    how = gt["series.aggregation"]
    if kind == "date":
        dates = f"axis.{value_axis} is dates"
        if how != "none":
            raise DrawError(
                f"series.aggregation: {how} adds the values, but {dates}, which can't be "
                "added; use none"
            )
        if gt["mark.bar.show"]:
            raise DrawError(
                f"mark.bar.show: bars start at 0, which on axis.{value_axis}'s dates is 1970; "
                "draw markers or lines instead"
            )
        if gt["series.value_label.show"] and all(
            gt[p] == "auto"
            for p in ("series.value_label.format", f"axis.{value_axis}.tick.label.format")
        ):
            raise DrawError(
                f"series.value_label.show: {dates}, so the labels need a date format; set "
                f'series.value_label.format or axis.{value_axis}.tick.label.format, e.g. "%H:%M"'
            )
    if how != "none" and gt["series.offset"] == "side_by_side":
        raise DrawError(
            f"series.offset: side_by_side, but series.aggregation {how} stacks series at each "
            "place; use one or the other"
        )
    if how != "none" and gt[f"axis.{value_axis}.scale"] == "log":
        raise DrawError(
            f"series.aggregation: {how} stacks values, which a log axis can't show; use linear"
        )
    labels = gt["series.value_label.show"]
    position = gt["series.value_label.position"]
    if labels and position == "inside" and not gt["mark.bar.show"]:
        raise DrawError("series.value_label.position: inside needs bars (mark.bar.show)")
    if labels and how != "none" and position == "outside":
        raise DrawError(
            "series.value_label.position: outside, but stacked segments are labelled inside; "
            "use auto, or series.value_label.total.show for each stack's total"
        )
    if gt["series.value_label.total.show"] and how != "sum":
        raise DrawError("series.value_label.total.show: applies with series.aggregation sum")
    if gt["mark.bar.show"]:
        low = gt[f"axis.{value_axis}.min"]
        base = 1.0 if gt[f"axis.{value_axis}.scale"] == "log" else 0.0
        if not unset(low) and float(low) > base:
            raise DrawError(
                f"axis.{value_axis}.min: bars start at {base:g}, so the axis must include it; "
                "for a narrower range, draw markers instead"
            )


def stack(series: list[Any], how: str, log: bool) -> list[Stacked]:
    """Each series' marks, combined as series.aggregation says; the benchmark's series stack
    among themselves."""
    floor = 1.0 if log else 0.0
    out = []
    up: dict[tuple[bool, float], float] = {}
    down: dict[tuple[bool, float], float] = {}
    totals: dict[tuple[bool, float], float] = {}
    if how != "none":
        for s in series:
            places = [float(p) for p in numbers(s.x)]
            if len(set(places)) < len(places):
                raise DrawError(
                    f"series.aggregation: {how}, but series '{s.label or 'the data'}' has several "
                    "rows at one place; combine them with the value axis's data.aggregation"
                )
            if how == "percent":
                values = numbers(s.y)
                if bool((values < 0).any()):
                    raise DrawError(
                        "series.aggregation: percent, but some values are below 0; a share of a "
                        "total with mixed signs isn't defined"
                    )
                for p, v in zip(places, values, strict=True):
                    if np.isfinite(v):
                        totals[s.benchmark, p] = totals.get((s.benchmark, p), 0.0) + float(v)
    for s in series:
        values = numbers(s.y)
        if how == "none":
            out.append(Stacked(np.full(len(values), floor), values, values))
            continue
        places = numbers(s.x)
        if how == "percent":
            values = np.array(
                [
                    100 * v / totals[s.benchmark, p] if totals.get((s.benchmark, p)) else np.nan
                    for p, v in zip(places, values, strict=True)
                ]
            )
        bottom, top = np.empty(len(values)), np.empty(len(values))
        for i, (p, v) in enumerate(zip(places, values, strict=True)):
            pile = up if not np.isfinite(v) or v >= 0 else down
            start = pile.get((s.benchmark, float(p)), 0.0)
            bottom[i] = start
            top[i] = start + (v if np.isfinite(v) else 0.0)
            pile[s.benchmark, float(p)] = top[i]
            if not np.isfinite(v):
                top[i] = np.nan
        out.append(Stacked(bottom, top, values))
    return out


def key(place: float) -> float:
    """A place as a dictionary key: equal places, computed different ways, compare equal."""
    return round(float(place), 9)


def widths(s: Any, gt: dict[str, Any]) -> float:
    """A series' mark width along the base axis, in points: its bars, or its markers."""
    return s.look.bar_width if gt["mark.bar.show"] else s.look.marker_size


def _present(series: list[Any]) -> dict[float, list[int]]:
    """The series with a mark at each place (by key), by their positions in series."""
    at: dict[float, list[int]] = {}
    for i, s in enumerate(series):
        for p, v in zip(numbers(s.x), numbers(s.y), strict=True):
            if np.isfinite(p) and np.isfinite(v):
                at.setdefault(key(p), []).append(i)
    return at


def slots(series: list[Any], gt: dict[str, Any], style: Style) -> list[dict[float, float]]:
    """Each series' offset along the base axis at each of its places, in points: the marks at
    a place centred on it, in series order, bars series.bar.gap apart."""
    if gt["series.offset"] != "side_by_side":
        return [{} for _ in series]
    gap = style.pt("series.bar.gap") if gt["mark.bar.show"] else 0.0
    out: list[dict[float, float]] = [{} for _ in series]
    for place, present in _present(series).items():
        each = [widths(series[i], gt) for i in present]
        start = -(sum(each) + gap * (len(each) - 1)) / 2
        for i, w in zip(present, each, strict=True):
            out[i][place] = start + w / 2
            start += w + gap
    return out


class PlaceShift(Transform):
    """Data coordinates to display px, moved along the base axis by each place's offset in
    points (slots): side-by-side marks, wherever they're drawn."""

    input_dims = output_dims = 2  # type: ignore[assignment]  # matplotlib declares them so
    pass_through = True  # it keeps no cache of its own, so it always passes a change on

    def __init__(self, ax: Axes, base_axis: str, shifts: dict[float, float]) -> None:
        super().__init__(shorthand_name="place shift")
        self.ax, self.k, self.shifts = ax, 0 if base_axis == "x" else 1, shifts
        self.set_children(ax.transData)  # redone whenever the data transform changes

    def transform_non_affine(self, values: Any) -> np.ndarray:
        points = np.asarray(values, dtype=float)
        flat = points.reshape(-1, 2)
        out = np.array(self.ax.transData.transform(flat), dtype=float)
        px = self.ax.figure.dpi / 72  # type: ignore[union-attr]
        places, which = np.unique(flat[:, self.k], return_inverse=True)  # few places, many points
        moves = [self.shifts.get(key(p), 0.0) * px if np.isfinite(p) else 0.0 for p in places]
        out[:, self.k] += np.asarray(moves, dtype=float)[which]
        return out.reshape(points.shape)

    def _invalidate_internal(self, level: int, invalidating_node: Any) -> None:
        # Its non-affine part reads the data transform's affine part, so any change to that is
        # a full change here: lines drawn through it then redo their paths (#2).
        super()._invalidate_internal(Transform._INVALID_FULL, invalidating_node)  # type: ignore[attr-defined]

    def inverted(self) -> Transform:  # for picking only: the place, without its shift
        return self.ax.transData.inverted()


def shifted(ax: Axes, base_axis: str, shifts: dict[float, float]) -> Any:
    """Data coordinates moved along the base axis by each place's offset."""
    if not any(shifts.values()):
        return ax.transData
    return PlaceShift(ax, base_axis, shifts)


class Bars(PolyCollection):
    """One series' bars: a rectangle from each bottom to each top, width points wide across
    the base axis and moved by its place's offset. The rectangles are laid out in display px
    again at every draw, so their width stays exact at any size or resolution.

    A raster renderer (Agg) rounds every tick mark to the pixel grid, so there each bar is
    placed from where its place's tick is drawn, its edges whole pixels the same distance
    either side: side-by-side bars stay centred on their tick, to the pixel."""

    def __init__(
        self,
        ax: Axes,
        places: np.ndarray,
        stacked: Stacked,
        base_axis: str,
        shifts: dict[float, float],
        width: float,
        color: Any,
        edge: str,
        edge_width: float,
        zorder: float,
    ) -> None:
        super().__init__(
            [],
            # Two of each, so matplotlib never draws a lone bar by its single-path shortcut,
            # which Agg places half a pixel from where it places a collection.
            facecolors=[color] * 2,
            edgecolors=[edge] * 2 if edge != "none" else ["none"] * 2,
            linewidths=[edge_width if edge != "none" else 0.0] * 2,
            zorder=zorder,
        )
        self.set_transform(IdentityTransform())
        self.set_snap(False)  # placed on the pixel grid here, when it's raster
        self.set_gid(BAR)
        self.ax, self.base_axis, self.shifts = ax, base_axis, shifts
        self.places = np.asarray(places, dtype=float)
        self.bottom, self.top = np.asarray(stacked.bottom), np.asarray(stacked.top)
        self.width, self.color, self.edge, self.edge_width = width, color, edge, edge_width

    def rectangles(self, raster: float | None = None) -> list[Bbox]:
        """Each bar's rectangle in display px, as the axes are now; raster (the canvas's
        height in whole px): on the pixel grid, from where Agg draws each tick."""
        px = self.ax.figure.dpi / 72  # type: ignore[union-attr]
        half = self.width * px / 2
        vertical = self.base_axis == "x"
        k = 0 if vertical else 1  # across the bar
        tick = None if raster is None else _tick_snap(self.ax, self.base_axis, raster)
        out = []
        for p, lo, hi in zip(self.places, self.bottom, self.top, strict=True):
            if not (np.isfinite(p) and np.isfinite(lo) and np.isfinite(hi)):
                continue
            a = self.ax.transData.transform((p, lo) if vertical else (lo, p))
            b = self.ax.transData.transform((p, hi) if vertical else (hi, p))
            shift = self.shifts.get(key(p), 0.0) * px
            start, end = sorted((a[1 - k], b[1 - k]))
            if tick is None:
                near, far = a[k] + shift - half, a[k] + shift + half
            else:
                centre = tick(a[k])
                near, far = (
                    centre + _whole(shift - half, centre),
                    centre + _whole(shift + half, centre),
                )
                start, end = round(start), round(end)
            if vertical:
                out.append(Bbox.from_extents(near, start, far, end))
            else:
                out.append(Bbox.from_extents(start, near, end, far))
        return out

    def _lay_out(self, raster: float | None = None) -> None:
        self.set_verts(
            [
                [(b.x0, b.y0), (b.x1, b.y0), (b.x1, b.y1), (b.x0, b.y1)]
                for b in self.rectangles(raster)
            ]
        )

    def draw(self, renderer: Any) -> None:
        self._lay_out(renderer.height if isinstance(renderer, RendererAgg) else None)
        super().draw(renderer)

    def get_window_extent(self, renderer: Any = None) -> Bbox:
        self._lay_out()
        return super().get_window_extent(renderer)


def _tick_snap(ax: Axes, base_axis: str, height: float) -> Any:
    """Where Agg draws a tick mark at a display coordinate along the base axis: its position
    rounded to a whole pixel (in Agg's coordinates, y down from the top of a canvas height
    whole px tall), then its line snapped to a pixel's centre when it's an odd number of
    pixels wide (matplotlib's draw_markers and PathSnapper)."""
    axis = ax.xaxis if base_axis == "x" else ax.yaxis
    ticks = axis.get_major_ticks()
    width = ticks[0].tick1line.get_markeredgewidth() if ticks else 0.0
    odd = int(np.floor(width * ax.figure.dpi / 72 + 0.5)) % 2 == 1  # type: ignore[union-attr]
    snap = 0.5 if odd else 0.0
    if base_axis == "x":
        return lambda v: np.floor(v + 0.5) + snap
    return lambda v: height - (np.floor(height - v + 0.5) + snap)


def _whole(distance: float, centre: float) -> float:
    """A distance from a drawn tick to a bar edge, rounded the same either side so the edge
    lands on a pixel boundary: symmetric bars stay symmetric."""
    base = centre % 1.0  # 0.5 when the tick is on a pixel's centre
    size = abs(distance) - base
    return float(np.sign(distance) * (np.floor(size + 0.5) + base))


def bars(ax: Axes, s: Any, base_axis: str, color: Any) -> Bars:
    """One series' bars, from its stack, at its shifts, in its look's bar width, edge and
    z-order."""
    look = s.look
    collection = Bars(
        ax,
        numbers(s.x),
        s.stack,
        base_axis,
        s.shifts,
        look.bar_width,
        color,
        look.bar_edge,
        look.bar_edge_width,
        look.bar_z,
    )
    ax.add_collection(collection, autolim=False)
    ends = [
        (p, v) if base_axis == "x" else (v, p)
        for p, lo, hi in zip(collection.places, collection.bottom, collection.top, strict=True)
        for v in (lo, hi)
        if np.isfinite(p) and np.isfinite(v)
    ]
    if ends:
        ax.update_datalim(ends)
    return collection


def check_room(
    ax: Axes, series: list[Any], gt: dict[str, Any], style: Style, base_axis: str
) -> None:
    """Bars, or side-by-side marks, must fit between neighbouring places."""
    side = gt["series.offset"] == "side_by_side"
    if not (gt["mark.bar.show"] or side):
        return
    gap = style.pt("series.bar.gap") if gt["mark.bar.show"] else 0.0
    at = {p: [widths(series[i], gt) for i in present] for p, present in _present(series).items()}
    places = sorted(at)
    if len(places) < 2:
        return
    k = 0 if base_axis == "x" else 1
    px = [ax.transData.transform((p, 1.0) if base_axis == "x" else (1.0, p))[k] for p in places]
    room = min(abs(b - a) for a, b in pairwise(px)) * 72 / ax.figure.dpi  # type: ignore[union-attr]
    need = max((sum(each) + gap * (len(each) - 1)) if side else max(each) for each in at.values())
    count = max(len(each) for each in at.values()) if side else 1
    if need > room:
        what = f"{count} side by side" if count > 1 else "each bar"
        now = f"{float(style.theme['series.bar.width']):g}"
        narrow = (
            "narrow the bars in the theme"
            if "series.bar.width" in style.fixed
            else f"set a smaller series.bar.width in the GraphSpec (now {now})"
        )
        raise DrawError(
            f"series.bar.width: {what} {'need' if count > 1 else 'needs'} {need:.1f} pt at each "
            f"place, but places are {room:.1f} pt apart; {narrow}, widen the format, or show "
            "fewer places or series"
        )


def _contrast(a: str, b: str) -> float:
    def lum(c: str) -> float:
        rgb = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in to_rgb(c)]
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def value_labels(
    ax: Axes, series: list[Any], gt: dict[str, Any], style: Style, base_axis: str, kind: str
) -> bool:
    """Write the values (series.value_label) after layout, in series.value_label.format (see
    axes.number_text; kind: the value axis's type). Returns True if the value axis was
    widened to fit them, so the figure must be laid out again."""
    value_axis = "y" if base_axis == "x" else "x"
    for a in [a for a in ax.texts if a.get_gid() == VALUE_LABEL]:
        a.remove()
    show, total = bool(gt["series.value_label.show"]), bool(gt["series.value_label.total.show"])
    if not (show or total):
        return False  # nothing is written, so no format is checked
    fmt = gt["series.value_label.format"]
    axis = ax.yaxis if value_axis == "y" else ax.xaxis
    text_of = number_text(gt, value_axis, axis, fmt, "series.value_label.format", kind=kind)
    fig = ax.figure
    size = style.pt("series.value_label.size")
    gap = style.pt("series.value_label.gap")
    ink = style.color("font.color")
    paper = style.color("background.color")
    paper = "#FFFFFF" if paper == "none" else paper
    how = gt["series.aggregation"]
    has_bars = bool(gt["mark.bar.show"])
    position = gt["series.value_label.position"]
    vertical = base_axis == "x"  # values run up the y axis
    made: list[Annotation] = []

    def put(
        place: float, at: float, text: str, offset: float, where: str, color: str, sign: float
    ) -> Annotation:
        """where: beyond (past at, away from 0), inside (back from at), centre."""
        xy = (place, at) if vertical else (at, place)
        push = {"beyond": gap, "inside": -gap, "centre": 0.0}[where] * (1 if sign >= 0 else -1)
        dx, dy = (offset, push) if vertical else (push, offset)
        if vertical:
            va = {"beyond": "bottom", "inside": "top", "centre": "center"}[where]
            if sign < 0 and where != "centre":
                va = {"bottom": "top", "top": "bottom"}[va]
            ha = "center"
        else:
            ha = {"beyond": "left", "inside": "right", "centre": "center"}[where]
            if sign < 0 and where != "centre":
                ha = {"left": "right", "right": "left"}[ha]
            va = "center"
        a = ax.annotate(
            text,
            xy,
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=size,
            color=color,
            gid=VALUE_LABEL,
            annotation_clip=False,
            zorder=4,
        )
        made.append(a)
        return a

    for s in series:
        if not show:
            break
        st, shifts = s.stack, s.shifts
        width = widths(s, gt)
        for place, bottom, top, value in zip(
            numbers(s.x), st.bottom, st.top, st.value, strict=True
        ):
            if not (np.isfinite(value) and np.isfinite(top)):
                continue
            off = shifts.get(key(place), 0.0)
            text = text_of(value)
            sign = 1.0 if value >= 0 else -1.0
            if how != "none":
                put(
                    place,
                    (bottom + top) / 2,
                    text,
                    off,
                    "centre",
                    _inside_ink(s.color, ink, paper) if has_bars else ink,
                    sign,
                )
                continue
            inside = has_bars and position in ("inside", "auto")
            if inside:
                a = put(place, top, text, off, "inside", _inside_ink(s.color, ink, paper), sign)
                if _fits_bar(ax, a, place, bottom, top, style, vertical, width):
                    continue
                a.remove()
                made.remove(a)
                if position == "inside":
                    raise DrawError(
                        f"series.value_label.position: inside, but {text} doesn't fit inside "
                        "its bar; use auto or outside, or widen the bars in the theme"
                    )
            put(place, top, text, off, "beyond", ink, sign)
    if total:
        ends: dict[tuple[bool, float], tuple[float, float]] = {}
        sums: dict[tuple[bool, float], float] = {}
        for s in series:
            for place, top, value in zip(numbers(s.x), s.stack.top, s.stack.value, strict=True):
                if np.isfinite(top) and np.isfinite(value):
                    pile = (s.benchmark, float(place))
                    lo, hi = ends.get(pile, (0.0, 0.0))
                    ends[pile] = (min(lo, top), max(hi, top))
                    sums[pile] = sums.get(pile, 0.0) + float(value)
        for pile, t in sums.items():
            lo, hi = ends[pile]
            place = pile[1]
            put(
                place, hi if t >= 0 else lo, text_of(t), 0.0, "beyond", ink, 1.0 if t >= 0 else -1.0
            )

    measure(fig)
    boxes = [a.get_window_extent() for a in made]
    for (i, a), (j, b) in (
        (p, q) for p in enumerate(boxes) for q in enumerate(boxes) if p[0] < q[0]
    ):
        if a.overlaps(b):
            raise DrawError(
                f"series.value_label: '{made[i].get_text()}' and '{made[j].get_text()}' run "
                "together; widen the format, narrow the theme's series.value_label.size, or "
                "show fewer labels"
            )
    gap_px = gap * fig.dpi / 72  # type: ignore[union-attr]
    if has_bars:
        _clear_of_bars(ax, made, boxes, gap_px, vertical)
    return grow_to_fit(ax, boxes, gt, "y" if vertical else "x", gap_px)


def _bar_boxes(ax: Axes) -> list[Bbox]:
    """Every bar's rectangle, in display px."""
    return [b for c in ax.collections if isinstance(c, Bars) for b in c.rectangles()]


def _clear_of_bars(
    ax: Axes, made: list[Annotation], boxes: list[Bbox], gap: float, vertical: bool
) -> None:
    """A value label keeps gap px from every bar but those in its own column (its bar, or its
    stack's segments)."""
    for label, box in zip(made, boxes, strict=True):
        cx, cy = box.get_points().mean(axis=0)
        near = box.padded(gap)
        for bar in _bar_boxes(ax):
            own = bar.x0 <= cx <= bar.x1 if vertical else bar.y0 <= cy <= bar.y1
            if not own and near.overlaps(bar):
                raise DrawError(
                    f"series.value_label: '{label.get_text()}' runs into a neighbouring bar; "
                    "widen the bars in the theme (series.bar.width), narrow "
                    "series.value_label.size, or put the labels inside"
                )


def _inside_ink(bar: str, ink: str, paper: str) -> str:
    """The text color, of the theme's two, that stands out more on the bar."""
    return ink if _contrast(bar, ink) >= _contrast(bar, paper) else paper


def _fits_bar(
    ax: Axes,
    a: Annotation,
    place: float,
    bottom: float,
    top: float,
    style: Style,
    vertical: bool,
    bar_width: float,
) -> bool:
    """Whether a label inside a bar's end fits within the bar (bar_width points across), gap
    clear of its ends."""
    measure(ax.figure)
    box = a.get_window_extent()
    k = 1 if vertical else 0
    ends = sorted(
        ax.transData.transform((place, v) if vertical else (v, place))[k] for v in (bottom, top)
    )
    gap = style.pt("series.value_label.gap") * ax.figure.dpi / 72  # type: ignore[union-attr]
    width = bar_width * ax.figure.dpi / 72  # type: ignore[union-attr]
    along = box.height if vertical else box.width
    across = box.width if vertical else box.height
    return along + 2 * gap <= ends[1] - ends[0] and across <= width


def grow_to_fit(
    ax: Axes,
    boxes: list[Bbox],
    gt: dict[str, Any],
    value_axis: str,
    gap: float,
    what: str = "value labels",
) -> bool:
    """Widen an automatic axis until every box (what: the labels they are, for an error) is
    inside the plot area, gap px clear of its edges. True if it changed."""
    if not boxes:
        return False
    plot = ax.get_window_extent()
    k = 1 if value_axis == "y" else 0
    lo_px = min(b.y0 if k else b.x0 for b in boxes)
    hi_px = max(b.y1 if k else b.x1 for b in boxes)
    low, high = (plot.y0, plot.y1) if k else (plot.x0, plot.x1)
    low, high = low + gap, high - gap
    if lo_px >= low - 0.5 and hi_px <= high + 0.5:
        return False
    get = ax.get_ylim if k else ax.get_xlim
    put = ax.set_ylim if k else ax.set_xlim
    lo, hi = get()
    inv = ax.transData.inverted()

    def data(px: float) -> float:
        return float(inv.transform((0.0, px) if k else (px, 0.0))[k])

    if (ax.get_yscale() if k else ax.get_xscale()) == "log":  # by the factor they overrun
        new_lo = lo if lo_px >= low - 0.5 else lo * data(lo_px) / data(low)
        new_hi = hi if hi_px <= high + 0.5 else hi * data(hi_px) / data(high)
    else:
        new_lo = lo if lo_px >= low - 0.5 else lo - (data(low) - data(lo_px))
        new_hi = hi if hi_px <= high + 0.5 else hi + (data(hi_px) - data(high))
    for end, old, new in (("min", lo, new_lo), ("max", hi, new_hi)):
        if new != old and not unset(gt[f"axis.{value_axis}.{end}"]):
            raise DrawError(
                f"axis.{value_axis}.{end}: {what} reach past it; widen the axis, or leave its "
                "limit automatic"
            )
    put(new_lo, new_hi)
    return True
