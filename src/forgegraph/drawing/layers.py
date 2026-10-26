"""The layers a GraphSpec lists (layers/*.yaml), drawn on a graph type's series.

- **reference_line**: a line across the plot at a value, or at multiplier times an aggregate of a
  column's drawn values (with per_series, one per named series, all its replicates
  together, in its color). A line outside the data widens an automatic axis; outside a set
  limit, it's an error. Its label, placed after layout, sits at one end or the middle,
  beside the line: auto takes the first position (LABEL_ORDER) inside the plot and clear
  of the data and other text. A chosen position that covers something is an error; one
  past the plot's edge widens an automatic axis.
- **error_bar**: a bar on each mark along an axis, a number or a column's distance below and
  above it. With the value axis aggregated (data.aggregation), the distances can be
  multiplier times the spread of the rows each mark stands for: their standard deviation, its
  standard error, or half the 95 % confidence interval of their mean (Student's t). The
  default is the standard deviation of the axis's own data column (data_column). Error bars
  follow side-by-side offsets; on stacked series they're an error.
- **note**: text in a position by the plot area, inside or outside it. auto takes the first
  position, inside, that nothing drawn passes through: lines, markers, bars, keys and other
  text. Notes are placed after keys, which need a corner, while a note has six places.

Every look comes from the theme's layer category.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any, cast

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.text import Annotation
from matplotlib.transforms import Bbox

from forgegraph.drawing import labels, marks
from forgegraph.drawing.axes import number_text
from forgegraph.drawing.errors import DrawError
from forgegraph.drawing.markup import markup
from forgegraph.drawing.style import LINE_STYLES, Style, unset
from forgegraph.drawing.text import measure

NOTE = "forgegraph-note"
REFERENCE = "forgegraph-reference-line"
ERROR_BAR = "forgegraph-error-bar"
GIDS = (REFERENCE, ERROR_BAR, NOTE)  # every artist a layer draws has one of these
NAMES = {
    "mean": "Mean",
    "median": "Median",
    "sum": "Sum",
    "min": "Min",
    "max": "Max",
    "stddev": "Std dev",
}
POSITIONS = ["top_left", "top_center", "top_right", "bottom_left", "bottom_center", "bottom_right"]
LABEL_ORDER = [
    "end_above",
    "end_below",
    "start_above",
    "start_below",
    "center_above",
    "center_below",
]


@dataclass
class RefLine:
    """A reference line drawn, and its label to place once the figure is laid out."""

    name: str
    axis: str
    at: float
    label: str  # the text, or the words before the value; "" for none
    position: str
    color: Any
    with_value: bool = False  # the value follows, in label.format (after layout)
    fmt: str = "auto"


def t_quantile(p: float, df: int) -> float:
    """Student's t quantile: exact for 1 and 2 degrees of freedom, a four-term Cornish-Fisher
    expansion beyond (Abramowitz & Stegun 26.7.5)."""
    if df == 1:
        return math.tan(math.pi * (p - 0.5))
    if df == 2:
        return (2 * p - 1) / math.sqrt(2 * p * (1 - p))
    z = NormalDist().inv_cdf(p)
    g1 = (z**3 + z) / 4
    g2 = (5 * z**5 + 16 * z**3 + 3 * z) / 96
    g3 = (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / 384
    g4 = (79 * z**9 + 776 * z**7 + 1482 * z**5 - 1920 * z**3 - 945 * z) / 92160
    return z + g1 / df + g2 / df**2 + g3 / df**3 + g4 / df**4


def spread(values: np.ndarray, how: str) -> float:
    """The standard deviation of values, its standard error, or half the 95 % CI of their
    mean."""
    v = values[np.isfinite(values)]
    if len(v) < 2:
        return float("nan")
    sd = float(np.std(v, ddof=1))
    if how == "stddev":
        return sd
    se = sd / math.sqrt(len(v))
    return se if how == "stderr" else t_quantile(0.975, len(v) - 1) * se


def _aggregate(values: np.ndarray, how: str) -> float:
    v = values[np.isfinite(values)]
    if not len(v):
        raise DrawError(f"aggregation.function: {how}, but the column has no values drawn")
    return {
        "mean": np.mean,
        "median": np.median,
        "sum": np.sum,
        "min": np.min,
        "max": np.max,
        "stddev": lambda a: np.std(a, ddof=1) if len(a) > 1 else np.nan,
    }[how](v)


ROW = "__forgegraph_row__"  # the long-form frame's column of each row's data row
Y_VALUE = "__forgegraph_y__"  # the long-form frame's column of values along the value axis


def _each_row_once(frame: pd.DataFrame, column: str) -> np.ndarray:
    """A column's values, one per data row: the long form repeats each row once per value
    column it draws."""
    rows = frame.drop_duplicates(ROW)
    return np.asarray(pd.to_numeric(rows[column], errors="coerce"), dtype=float)


def reference_lines(
    ax: Axes,
    layers: dict[str, dict[str, Any]],
    series: list[Any],
    frame: pd.DataFrame,
    style: Style,
    kinds: dict[str, str],
) -> list[RefLine]:
    """Draw each reference_line; return each line drawn, its label to place after layout."""
    t = style.theme
    drawn = []
    for name, layer in layers.items():
        if layer["type"] != "reference_line":
            continue
        where = f"layers.{name}"
        axis = layer["axis"]
        if kinds.get(axis) == "categorical":
            raise DrawError(f"{where}.axis: {axis} is categorical, so a line can't mark a value")
        value, how = layer["value"], layer["aggregation.function"]
        multiplier = float(layer["aggregation.multiplier"])
        groups: list[tuple[float, str]] = []
        if isinstance(value, str):
            if unset(how):
                raise DrawError(
                    f"{where}.value: a column, so set aggregation.function to say which of its "
                    "values the line marks"
                )
            if value not in frame.columns:
                raise DrawError(f"{where}.value: no column '{value}' in the data")
            if layer["per_series"]:  # each named series, with all its replicates
                named: dict[tuple[bool, Any], list[Any]] = {}
                for s in series:
                    if s.rows is not None:
                        named.setdefault((s.benchmark, s.label), []).append(s)
                for members in named.values():
                    rows = frame.loc[np.concatenate([m.rows for m in members])]
                    at = _aggregate(_each_row_once(rows, value), how)
                    groups.append((multiplier * at, members[0].color))
            else:
                groups.append((multiplier * _aggregate(_each_row_once(frame, value), how), ""))
        else:
            if not unset(how):
                raise DrawError(
                    f"{where}.aggregation.function: applies only when value is a column"
                )
            groups.append((float(value), ""))
        ink = style.color("layer.reference_line.color")
        for at, color in groups:
            line_color = color or ink
            draw_line = ax.axhline if axis == "y" else ax.axvline
            draw_line(
                at,
                color=line_color,
                linewidth=style.pt("layer.reference_line.line.width"),
                linestyle=LINE_STYLES[t["layer.reference_line.line.style"]],
                zorder=1.5,
                gid=REFERENCE,
            )
            label, with_value = _line_label(layer, how, multiplier)
            drawn.append(
                RefLine(
                    name,
                    axis,
                    at,
                    label,
                    layer["label.position"],
                    line_color,
                    with_value,
                    str(layer["label.format"]),
                )
            )
    return drawn


def _line_label(layer: dict[str, Any], how: Any, multiplier: float) -> tuple[str, bool]:
    """The label's words, and whether its value follows them."""
    text = layer["label.text"]
    if unset(text):
        return "", False
    if text in ("aggregation", "aggregation_value"):
        if unset(how):
            raise DrawError(f"label.text: {text}, but the line's value isn't an aggregate")
        name = NAMES[str(how)]
        name = name if multiplier == 1 else f"{multiplier:g} × {name.lower()}"  # noqa: RUF001
        return (name, False) if text == "aggregation" else (f"{name}: ", True)
    if text == "value":
        return "", True
    return markup(str(text)), False


def _label_line(
    ax: Axes, axis: str, at: float, text: str, position: str, color: Any, style: Style
) -> Annotation:
    along, side = position.split("_")
    fraction = {"start": 0.0, "center": 0.5, "end": 1.0}[along]
    gap = style.pt("layer.reference_line.label.gap")
    sign = 1 if side == "above" else -1
    inset = {"start": gap, "center": 0.0, "end": -gap}[along]  # clear of the plot's frame
    if axis == "y":  # a horizontal line: the label above or below it
        xy, coords = (fraction, at), ax.get_yaxis_transform()
        offset = (inset, sign * gap)
        ha = {"start": "left", "center": "center", "end": "right"}[along]
        va = "bottom" if sign > 0 else "top"
    else:  # a vertical line: above is to its right, below to its left
        xy, coords = (at, fraction), ax.get_xaxis_transform()
        offset = (sign * gap, inset)
        ha = "left" if sign > 0 else "right"
        va = {"start": "bottom", "center": "center", "end": "top"}[along]
    return ax.annotate(
        text,
        xy,
        xycoords=coords,
        xytext=offset,
        textcoords="offset points",
        ha=ha,
        va=va,
        fontsize=style.pt("layer.reference_line.label.size"),
        color=color,
        annotation_clip=False,
        gid=REFERENCE,
        zorder=4,
    )


def _line_text(ax: Axes, gt: dict[str, Any], line: RefLine) -> str:
    """A reference line's value in its label, written as axes.number_text says; with auto
    and no tick label format, one decimal place more than the tick labels show (a single
    value is read more closely than the scale)."""
    axis = ax.xaxis if line.axis == "x" else ax.yaxis
    path = f"layers.{line.name}.label.format"
    return number_text(gt, line.axis, axis, line.fmt, path, extra=1)(line.at)


def label_lines(ax: Axes, lines: list[RefLine], gt: dict[str, Any], style: Style) -> bool:
    """Place each line's label once the figure is laid out (again on every pass): clear of
    what's drawn, or, at a chosen position past the plot's edge, with an automatic axis
    widened to take it. Returns True if an axis was widened, so the figure must be laid out
    again."""
    for a in [t for t in ax.texts if t.get_gid() == REFERENCE]:
        a.remove()
    with_lines = bool(gt["mark.line.show"])  # whether lines are obstacles: labels.Obstacles.of
    gap = style.pt("layer.reference_line.label.gap") * ax.figure.dpi / 72  # type: ignore[union-attr]
    widened = False
    for line in lines:
        if not (line.label or line.with_value):
            continue
        words = line.label + (_line_text(ax, gt, line) if line.with_value else "")
        auto = line.position == "auto"
        for position in LABEL_ORDER if auto else [line.position]:
            a = _label_line(ax, line.axis, line.at, words, position, line.color, style)
            measure(ax.figure)
            box, plot = a.get_window_extent(), ax.get_window_extent()
            inside = (
                box.x0 >= plot.x0 - 0.5
                and box.x1 <= plot.x1 + 0.5
                and box.y0 >= plot.y0 - 0.5
                and box.y1 <= plot.y1 + 0.5
            )
            if inside and labels.box_clear(ax, box, with_lines):
                break
            if not auto and not inside:  # past the plot's edge: widen, then place again
                what = f"layers.{line.name}: its label"
                widened |= marks.grow_to_fit(ax, [box], gt, line.axis, gap, what)
                break
            a.remove()
            if not auto:
                others = ", ".join(p for p in LABEL_ORDER if p != position)
                raise DrawError(
                    f"layers.{line.name}.label.position: {position}, but the label covers "
                    f"what's drawn; use auto, or one of {others}"
                )
        else:
            raise DrawError(
                f"layers.{line.name}.label.position: auto, but no position beside the line is "
                "clear of what's drawn; choose one and widen the axis, shorten the label, or "
                "widen the format"
            )
    return widened


def include(ax: Axes, lines: list[RefLine], gt: dict[str, Any]) -> None:
    """Widen automatic limits to every reference line; outside a set limit, an error."""
    for line in lines:
        name, axis, at = line.name, line.axis, line.at
        get = ax.get_ylim if axis == "y" else ax.get_xlim
        put = ax.set_ylim if axis == "y" else ax.set_xlim
        lo, hi = get()
        if lo <= at <= hi:
            continue
        end = "min" if at < lo else "max"
        if not unset(gt[f"axis.{axis}.{end}"]):
            raise DrawError(
                f"layers.{name}: the line at {at:g} is outside axis.{axis}.{end}; move the line "
                "or the limit"
            )
        margin = (hi - lo) * 0.05 if hi > lo else abs(at) * 0.05 or 1.0
        put(min(lo, at - margin), max(hi, at + margin))


def error_bars(
    ax: Axes,
    layers: dict[str, dict[str, Any]],
    series: list[Any],
    frame: pd.DataFrame,
    gt: dict[str, Any],
    style: Style,
    roles: Any,
) -> None:
    """Draw each error_bar layer on every series, moved by its side-by-side offsets."""
    t = style.theme
    for name, layer in layers.items():
        if layer["type"] != "error_bar":
            continue
        where = f"layers.{name}"
        if gt["series.aggregation"] != "none":
            raise DrawError(
                f"{where}: error bars on stacked series aren't defined (a segment's uncertainty "
                "isn't the stack's); draw the series unstacked"
            )
        axis = layer["axis"]
        along_value = axis == roles.value
        how = layer["value.aggregation.function"]
        multiplier = float(layer["value.aggregation.multiplier"])
        aggregated = gt[f"axis.{roles.value}.data.aggregation"] != "none"
        columns = [e for e in ("lower", "upper") if isinstance(layer[f"value.{e}"], str)]
        if not unset(how) and not aggregated and columns:  # the function acts on columns
            raise DrawError(
                f"{where}.value.aggregation.function: {how} is the spread of the rows a mark "
                f"stands for, so set axis.{roles.value}.data.aggregation too"
            )
        log = gt[f"axis.{axis}.scale"] == "log"
        for s in series:
            centres = marks.numbers(s.y if along_value else s.x)
            distances = {}
            for end in ("lower", "upper"):
                given = layer[f"value.{end}"]
                if given == "data_column":
                    if unset(how):
                        raise DrawError(
                            f"{where}.value.{end}: data_column, whose values aren't distances; "
                            "set value.aggregation.function to its spread"
                        )
                    given = Y_VALUE if along_value else s.place_column
                distances[end] = _distances(
                    given,
                    how,
                    multiplier,
                    s,
                    frame,
                    aggregated,
                    f"{where}.value.{end}",
                )
            low = centres - distances["lower"]
            high = centres + distances["upper"]
            if log and bool((low[np.isfinite(low)] <= 0).any()):
                raise DrawError(
                    f"{where}.value.lower: a bar reaches 0 or below on axis.{axis}'s log scale"
                )
            places = marks.numbers(s.x if along_value else s.y)
            shifted = marks.shifted(ax, roles.base, s.shifts)
            _draw_bars(ax, places, low, high, axis, s.color, style, shifted, t)


def _distances(
    given: Any,
    how: Any,
    multiplier: float,
    s: Any,
    frame: pd.DataFrame,
    aggregated: bool,
    path: str,
) -> np.ndarray:
    n = len(s.x)
    if not isinstance(given, str):
        if float(given) < 0:
            raise DrawError(f"{path}: {given} is below 0; it's a distance from each value")
        return np.full(n, float(given))
    if given not in frame.columns:
        raise DrawError(f"{path}: no column '{given}' in the data")
    column = cast(pd.Series, pd.to_numeric(frame[given], errors="coerce"))
    if aggregated:
        if unset(how):
            raise DrawError(
                f"{path}: each mark stands for several rows, so a column's distance needs "
                "value.aggregation.function"
            )
        rows = frame.loc[s.rows]
        groups = rows.groupby(marks.numbers(rows[s.place_column]), sort=False)[given]
        spreads = {
            marks.key(k): spread(
                np.asarray(pd.to_numeric(g, errors="coerce"), dtype=float), str(how)
            )
            for k, g in groups
        }
        out = np.array([multiplier * spreads.get(marks.key(p), np.nan) for p in marks.numbers(s.x)])
    else:
        out = np.asarray(column.loc[s.rows], dtype=float)
    if bool((out[np.isfinite(out)] < 0).any()):
        raise DrawError(f"{path}: '{given}' has values below 0; they're distances from each value")
    return out


def _draw_bars(
    ax: Axes,
    places: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    axis: str,
    color: Any,
    style: Style,
    transform: Any,
    t: dict[str, Any],
) -> None:
    ink = color if t["layer.error_bar.color"] == "series" else style.color("layer.error_bar.color")
    width = style.pt("layer.error_bar.line.width")
    n = len(places)
    along = np.repeat(places, 3)
    span = np.empty(3 * n)
    span[0::3], span[1::3], span[2::3] = low, high, np.nan
    along[2::3] = np.nan
    xs, ys = (along, span) if axis == "y" else (span, along)
    (stem,) = ax.plot(xs, ys, color=ink, linewidth=width, zorder=1.9, gid=ERROR_BAR)
    stem.set_transform(transform)
    cap = "_" if axis == "y" else "|"
    ends_x, ends_y = (
        (np.r_[places, places], np.r_[low, high])
        if axis == "y"
        else (np.r_[low, high], np.r_[places, places])
    )
    (caps,) = ax.plot(
        ends_x,
        ends_y,
        linestyle="none",
        marker=cap,
        markersize=style.pt("layer.error_bar.cap.width"),
        markeredgewidth=width,
        color=ink,
        zorder=1.9,
        gid=ERROR_BAR,
    )
    caps.set_transform(transform)


def notes_outside(ax: Axes, layers: dict[str, dict[str, Any]], style: Style) -> None:
    """Notes outside the plot area: above the title, or below the x-axis title. Drawn before
    layout, which makes room for them."""
    for name, layer in layers.items():
        if layer["type"] != "note" or layer["inside"]:
            continue
        position = layer["position"]
        if position == "auto":
            raise DrawError(
                f"layers.{name}.position: auto finds a clear place inside the plot area; outside "
                "it, choose a position"
            )
        vertical, horizontal = position.split("_")
        fraction = {"left": 0.0, "center": 0.5, "right": 1.0}[horizontal]
        gap = style.pt("layer.note.inset")
        top = vertical == "top"
        anchor = ax.title if top else ax.xaxis.label

        def edge(renderer: Any, anchor: Any = anchor, top: bool = top) -> Bbox:
            plot = ax.get_window_extent(renderer)
            if anchor.get_text():
                box = anchor.get_window_extent(renderer)
            elif top:
                box = plot
            else:
                box = ax.xaxis.get_tightbbox(renderer) or plot
            return Bbox.from_extents(plot.x0, box.y0, plot.x1, box.y1)

        _note(
            ax,
            layer["text"],
            (fraction, 1.0 if top else 0.0),
            edge,
            (0.0, gap if top else -gap),
            {"left": "left", "center": "center", "right": "right"}[horizontal],
            "bottom" if top else "top",
            style,
        )


def _note(
    ax: Axes,
    text: str,
    xy: tuple[float, float],
    coords: Any,
    offset: tuple[float, float],
    ha: str,
    va: str,
    style: Style,
) -> Annotation:
    return ax.annotate(
        markup(str(text)),
        xy,
        xycoords=coords,
        xytext=offset,
        textcoords="offset points",
        ha=ha,
        va=va,
        fontsize=style.pt("layer.note.size"),
        color=style.color("layer.note.color"),
        annotation_clip=False,
        gid=NOTE,
        zorder=5,
    )


def unplace_notes(ax: Axes) -> None:
    """Take away the notes inside the plot area (placed in axes fraction, where notes outside
    follow a title), to place them again."""
    for t in list(ax.texts):
        if t.get_gid() == NOTE and getattr(t, "xycoords", None) == "axes fraction":
            t.remove()


def notes_inside(
    ax: Axes, layers: dict[str, dict[str, Any]], gt: dict[str, Any], style: Style
) -> list[Bbox]:
    """Notes inside the plot area, after layout and keys, each clear of everything drawn,
    the keys and the other notes; return their boxes."""
    with_lines = bool(gt["mark.line.show"])  # whether lines are obstacles: labels.Obstacles.of
    placed: list[Bbox] = []
    inset = style.pt("layer.note.inset")
    for name, layer in layers.items():
        if layer["type"] != "note" or not layer["inside"]:
            continue
        tries = POSITIONS if layer["position"] == "auto" else [layer["position"]]
        for position in tries:
            vertical, horizontal = position.split("_")
            fraction = {"left": 0.0, "center": 0.5, "right": 1.0}[horizontal]
            dx = {"left": inset, "center": 0.0, "right": -inset}[horizontal]
            top = vertical == "top"
            a = _note(
                ax,
                layer["text"],
                (fraction, 1.0 if top else 0.0),
                "axes fraction",
                (dx, -inset if top else inset),
                horizontal,
                "top" if top else "bottom",
                style,
            )
            measure(ax.figure)
            box = a.get_window_extent()
            clear = labels.box_clear(ax, box, with_lines, keys=True)
            if clear and not any(box.overlaps(p) for p in placed):
                placed.append(box)
                break
            a.remove()
        else:
            what = "any position" if layer["position"] == "auto" else layer["position"]
            raise DrawError(
                f"layers.{name}: the note doesn't fit {what} inside the plot area without "
                "covering what's drawn; put it outside (inside: false), shorten it, or widen "
                "the format"
            )
    return placed
