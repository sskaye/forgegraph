"""The layers a GraphSpec lists (layers/*.yaml), drawn on a graph type's series.

- **reference**: one or two lines, with the fill of a band between two (none if fill.color
  is None). Each is at a value (on a date axis, a date or a day number; text that reads as a
  date is a column only if one has that name), or from a column's drawn values: its
  aggregate times its multiplier, plus its offset (an aggregate too), over all the rows for
  a straight line, or at each place for a line that follows the data; with no aggregation,
  through each row. With per_series, the layer is drawn once per named series, all its
  replicates together, in its color. A date column's aggregate is a date, on a date axis
  only. A line outside the data widens an automatic axis; outside a set limit, it's an
  error. Its label, placed after layout, sits at one end or the middle, beside the line:
  auto takes the first position (LABEL_ORDER) inside the plot and clear of the data and
  other text. A chosen position that covers something is an error; one past the plot's edge
  widens an automatic axis. With label.inside false, the label is beyond the plot area at
  the line's start or end.
- **error_bar**: a bar on each mark along an axis, a number or a column's distance below and
  above it. With the series aggregated (its aggregation), the distances can be an aggregate
  of the rows each mark stands for, times its multiplier: such as their standard deviation,
  its standard error, or half the 95 % confidence interval of their mean (Student's t). The
  default is the standard deviation of the series' own column (data_column). Error bars
  follow side-by-side offsets; on stacked series they're an error.
- **note**: text in a position by the plot area, inside or outside it. auto takes the first
  position, inside, that nothing drawn passes through: lines, markers, bars, keys and other
  text. Notes are placed after keys, which need a corner, while a note has six places.

Every look comes from the theme's layer category, with what a layer sets for itself.
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

from forgegraph.drawing import labels, limits, marks
from forgegraph.drawing.axes import number_text, numbers, on_axis
from forgegraph.drawing.errors import DrawError
from forgegraph.drawing.key import keys
from forgegraph.drawing.markup import markup
from forgegraph.drawing.style import Style, unset
from forgegraph.drawing.text import measure
from forgegraph.spec.layers import look_paths
from forgegraph.spec.parameters import as_date, is_none

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
    "stderr": "Std error",
    "ci": "95 % CI",
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
LINES = ("line_1", "line_2")  # a reference layer's lines


@dataclass
class RefLine:
    """A reference layer's line drawn, and its label to place once the figure is laid out:
    straight, at a value, or following the data, through points (base, value)."""

    name: str  # the layer's
    which: str  # line_1 or line_2
    axis: str
    at: float  # a straight line's value; nan for one that follows the data
    label: str  # the text, or the words before the value; "" for none
    position: str
    inside: bool
    color: Any
    look: Style  # the theme with what the layer sets for itself, for this line
    with_value: bool = False  # the value follows, in label.format (after layout)
    fmt: str = "auto"
    kind: str = "decimal"  # its axis's type
    points: tuple[np.ndarray, np.ndarray] | None = None  # (base, value) of a following line
    placed_outside: bool = False  # its label is beyond the plot area, laid out already

    @property
    def path(self) -> str:
        return f"layers.{self.name}.{self.which}"

    def end(self, along: str) -> tuple[float | None, float]:
        """Where a label at the line's start, center or end is: the place along the base axis
        (None for a straight line, which runs across the plot) and the value."""
        if self.points is None:
            return None, self.at
        base, value = self.points
        i = {"start": 0, "center": len(base) // 2, "end": len(base) - 1}[along]
        return float(base[i]), float(value[i])

    def values(self) -> np.ndarray:
        return np.array([self.at]) if self.points is None else self.points[1]


def look(style: Style, layer: dict[str, Any], line: str = "") -> Style:
    """The style a layer, or one of its lines, is drawn in: the theme with the theme
    parameters it sets for itself (spec/layers.py look_paths)."""
    paths = look_paths(str(layer["type"]))
    own = {
        paths[p]: v
        for p, v in layer.get("look", {}).items()
        if p.startswith(f"{line}.") or not p.startswith(LINES)
    }
    return Style({**style.theme, **own}, style.format, style.fixed) if own else style


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


AGGREGATES = {"mean": np.mean, "median": np.median, "sum": np.sum, "min": np.min, "max": np.max}


def combine(values: np.ndarray, how: str, percentile: float = 50) -> float:
    """Values as one, by an [aggregation style]'s function; nan if none are finite."""
    v = values[np.isfinite(values)]
    if not len(v):
        return float("nan")
    if how in ("stddev", "stderr", "ci"):
        return spread(v, how)
    if how == "percentile":
        return float(np.percentile(v, percentile))
    return float(AGGREGATES[how](v))


ROW = "__forgegraph_row__"  # the long-form frame's column of each row's data row
Y_VALUE = "__forgegraph_y__"  # the long-form frame's column of values along the value axis


def _each_row_once(frame: pd.DataFrame) -> pd.DataFrame:
    """The rows of the long form, one per data row: it repeats each row once per series."""
    return cast(pd.DataFrame, frame.drop_duplicates(ROW))


DATE_AGGREGATES = ("mean", "median", "min", "max", "percentile")  # those of dates that are dates


def _check_column(where: str, layer: dict[str, Any], column: pd.Series, kind: str) -> None:
    """A date column's aggregate marks a date: on a date axis, as mean, median, min, max or a
    percentile, at multiplier 1."""
    if not pd.api.types.is_datetime64_any_dtype(column):
        return
    axis, how = layer["axis"], layer[f"{where}.aggregation.function"]
    path = f"layers.{layer['name']}.{where}"
    if kind != "date":
        raise DrawError(
            f"{path}.value: '{column.name}' is dates, but axis.{axis} is {kind}; use a column "
            "of numbers"
        )
    if not unset(how) and how not in DATE_AGGREGATES:
        raise DrawError(
            f"{path}.aggregation.function: {how} of dates isn't a date; use "
            f"{', '.join(DATE_AGGREGATES)}"
        )
    multiplier = float(layer[f"{where}.aggregation.multiplier"])
    if multiplier != 1:
        raise DrawError(
            f"{path}.aggregation.multiplier: {multiplier:g} times a date isn't a date; use 1"
        )


def _style_value(layer: dict[str, Any], prefix: str, part: str) -> tuple[Any, float, float]:
    """An [aggregation style] of a line (part: aggregation or offset): its function, or None,
    multiplier and percentile."""
    how = layer[f"{prefix}.{part}.function"]
    return (
        None if unset(how) else str(how),
        float(layer[f"{prefix}.{part}.multiplier"]),
        float(layer[f"{prefix}.{part}.percentile"]),
    )


def _line_values(
    layer: dict[str, Any],
    which: str,
    rows: pd.DataFrame,
    roles: Any,
    kinds: dict[str, str],
) -> tuple[float, tuple[np.ndarray, np.ndarray] | None]:
    """A line's value, or for a line that follows the data, its points (base, value): its
    value's aggregate over all the rows, or at each place (scope), plus its offset."""
    path = f"layers.{layer['name']}.{which}"
    axis, value = layer["axis"], layer[f"{which}.value"]
    how, multiplier, percentile = _style_value(layer, which, "aggregation")
    off, off_multiplier, off_percentile = _style_value(layer, which, "offset")
    # text is a column, unless it reads as a date and no column has that name
    if not (isinstance(value, str) and (value in rows.columns or as_date(value) is None)):
        for part, given in (("aggregation", how), ("offset", off)):
            if given is not None:
                raise DrawError(f"{path}.{part}.function: applies only when value is a column")
        return on_axis(value, axis, kinds[axis], f"{path}.value"), None
    if value not in rows.columns:
        raise DrawError(f"{path}.value: no column '{value}' in the data")
    _check_column(which, layer, cast(pd.Series, rows[value]), kinds[axis])
    follows = how is None or layer[f"{which}.scope"] == "each"
    if follows and axis != roles.value:
        raise DrawError(
            f"{path}: a line that follows the data runs along the base axis, so axis must be "
            f"{roles.value}; or aggregate the column over all its rows (scope all)"
        )
    values = numbers(rows[value])
    base = numbers(rows[roles.base_column])
    if not follows:
        assert how is not None
        at = multiplier * combine(values, how, percentile)
        if off is not None:
            at += off_multiplier * combine(values, off, off_percentile)
        return at, None
    keep = np.isfinite(values) & np.isfinite(base)
    base, values = base[keep], values[keep]
    if how is None:  # through each row, in order along the base axis
        order = np.argsort(base, kind="stable")
        places, line = base[order], values[order]
    else:
        places = np.unique(base)
        line = np.array([multiplier * combine(values[base == p], how, percentile) for p in places])
    if off is not None:
        at_each = np.unique(base) if how is None else places
        spreads = {
            marks.key(p): off_multiplier * combine(values[base == p], off, off_percentile)
            for p in at_each
        }
        if how is None or layer[f"{which}.scope"] == "each":
            line = line + np.array([spreads[marks.key(p)] for p in places])
    return float("nan"), (places, line)


def reference_lines(
    ax: Axes,
    layers: dict[str, dict[str, Any]],
    series: list[Any],
    frame: pd.DataFrame,
    style: Style,
    kinds: dict[str, str],
    roles: Any,
) -> list[RefLine]:
    """Draw each reference layer: its lines, and between two the fill of a band, once for
    the whole graph or per series; return each line drawn, its label to place after
    layout."""
    drawn = []
    for name, entry in layers.items():
        if entry["type"] != "reference":
            continue
        layer = {**entry, "name": name}
        where = f"layers.{name}"
        axis = layer["axis"]
        if kinds.get(axis) == "categorical":
            raise DrawError(f"{where}.axis: {axis} is categorical, so a line can't mark a value")
        groups: list[tuple[pd.DataFrame, str]] = []
        if layer["per_series"]:  # each named series, with all its replicates
            named: dict[tuple[bool, Any], list[Any]] = {}
            for s in series:
                if s.rows is not None:
                    named.setdefault((s.benchmark, s.label), []).append(s)
            for members in named.values():
                rows = frame.loc[np.concatenate([m.rows for m in members])]
                groups.append((_each_row_once(cast(pd.DataFrame, rows)), members[0].color))
        else:
            groups.append((_each_row_once(frame), ""))
        listed = [w for w in LINES if not unset(layer[f"{w}.value"])]
        if not listed:
            raise DrawError(f"{where}: set line_1.value, line_2.value, or both")
        for rows, color in groups:
            found = {w: _line_values(layer, w, rows, roles, kinds) for w in listed}
            if len(found) == 2:
                _band(ax, layer, found, color, style, roles)
            for w, (at, points) in found.items():
                own = look(style, layer, w)
                line = own.line("layer.reference.line")
                line_color = color or line.color
                if points is None:
                    draw_line = ax.axhline if axis == "y" else ax.axvline
                    draw_line(at, color=line_color, linewidth=line.width, linestyle=line.style,
                              zorder=1.5, gid=REFERENCE)  # fmt: skip
                else:
                    xs, ys = points if roles.base == "x" else points[::-1]
                    ax.plot(xs, ys, color=line_color, linewidth=line.width, linestyle=line.style,
                            zorder=1.5, gid=REFERENCE)  # fmt: skip
                label, with_value = _line_label(layer, w)
                drawn.append(
                    RefLine(
                        name,
                        w,
                        axis,
                        at,
                        label,
                        layer[f"{w}.label.position"],
                        bool(layer[f"{w}.label.inside"]),
                        line_color,
                        own,
                        with_value,
                        str(layer[f"{w}.label.format"]),
                        kinds[axis],
                        points,
                    )
                )
    return drawn


def _band(
    ax: Axes,
    layer: dict[str, Any],
    found: dict[str, tuple[float, tuple[np.ndarray, np.ndarray] | None]],
    color: str,
    style: Style,
    roles: Any,
) -> None:
    """The fill between a band's two lines, in fill.color (series: the series') and
    fill.opacity; none if fill.color is None."""
    own = look(style, layer)
    fill = own.theme["layer.reference.fill.color"]
    if is_none(fill):
        return
    if fill == "series" and not color:
        raise DrawError(
            f"layers.{layer['name']}.fill.color: series, but the band isn't drawn per series; "
            "set per_series, or give a color"
        )
    face = color if fill == "series" else fill
    alpha = float(own.theme["layer.reference.fill.opacity"])
    (a, pa), (b, pb) = found["line_1"], found["line_2"]
    if pa is None and pb is None:
        span = ax.axhspan if layer["axis"] == "y" else ax.axvspan
        span(min(a, b), max(a, b), facecolor=face, alpha=alpha, linewidth=0, zorder=1.4,
             gid=REFERENCE)  # fmt: skip
        return
    places = pa[0] if pa is not None else cast(Any, pb)[0]
    lo = np.full(len(places), a) if pa is None else pa[1]
    hi = np.full(len(places), b) if pb is None else np.interp(places, pb[0], pb[1])
    between = ax.fill_between if roles.base == "x" else ax.fill_betweenx
    between(places, lo, hi, facecolor=face, alpha=alpha, linewidth=0, zorder=1.4,
            gid=REFERENCE)  # fmt: skip


def _named(how: str, multiplier: float, percentile: float) -> str:
    name = f"P{percentile:g}" if how == "percentile" else NAMES[how]
    return name if multiplier == 1 else f"{multiplier:g} × {name.lower()}"  # noqa: RUF001


def _line_label(layer: dict[str, Any], which: str) -> tuple[str, bool]:
    """A line's label's words, and whether its value follows them."""
    text = layer[f"{which}.label.text"]
    if unset(text):
        return "", False
    how, multiplier, percentile = _style_value(layer, which, "aggregation")
    if text in ("aggregation", "aggregation_value"):
        if how is None:
            raise DrawError(
                f"layers.{layer['name']}.{which}.label.text: {text}, but the line's value isn't "
                "an aggregate"
            )
        name = _named(how, multiplier, percentile)
        off, off_multiplier, off_percentile = _style_value(layer, which, "offset")
        if off is not None:
            sign = "−" if off_multiplier < 0 else "+"  # noqa: RUF001
            name += f" {sign} {_named(off, abs(off_multiplier), off_percentile).lower()}"
        return (name, False) if text == "aggregation" else (f"{name}: ", True)
    if text == "value":
        return "", True
    return markup(str(text)), False


def _label_line(ax: Axes, line: RefLine, text: str, position: str) -> Annotation:
    """A line's label at a position: inside the plot area beside the line, or with inside
    false, beyond the plot area at the line's start or end."""
    along, side = position.split("_")
    style = line.look.text("layer.reference.label")
    gap = style.gap or 0.0
    sign = 1 if side == "above" else -1
    place, at = line.end(along)
    fraction = {"start": 0.0, "center": 0.5, "end": 1.0}[along]
    if line.inside:  # clear of the plot's frame, or of the point it starts or ends at
        inset = {"start": gap, "center": 0.0, "end": -gap}[along]
    else:  # beyond the plot area
        inset = {"start": -gap, "center": 0.0, "end": gap}[along]
    if line.axis == "y":  # along x: the label above or below it
        xy, coords = ((fraction, at), ax.get_yaxis_transform())
        if place is not None:
            xy, coords = (place, at), "data"
        offset = (inset, sign * gap)
        ha = {"start": "left", "center": "center", "end": "right"}[along]
        if not line.inside:
            ha = {"start": "right", "center": "center", "end": "left"}[along]
        va = "bottom" if sign > 0 else "top"
    else:  # along y: above is to its right, below to its left
        xy, coords = ((at, fraction), ax.get_xaxis_transform())
        if place is not None:
            xy, coords = (at, place), "data"
        offset = (sign * gap, inset)
        ha = "left" if sign > 0 else "right"
        va = {"start": "bottom", "center": "center", "end": "top"}[along]
        if not line.inside:
            va = {"start": "top", "center": "center", "end": "bottom"}[along]
    colored = line.look.theme["layer.reference.label.color"] == "line"
    return ax.annotate(
        text,
        xy,
        xycoords=coords,
        xytext=offset,
        textcoords="offset points",
        ha=ha,
        va=va,
        fontproperties=style.font,
        color=line.color if colored else style.color,
        annotation_clip=False,
        gid=REFERENCE,
        zorder=4,
    )


def _line_text(ax: Axes, gt: dict[str, Any], line: RefLine, at: float) -> str:
    """A line's value in its label, written as axes.number_text says; with auto and no tick
    label format, one decimal place more than the tick labels show (a single value is read
    more closely than the scale)."""
    axis = ax.xaxis if line.axis == "x" else ax.yaxis
    path = f"{line.path}.label.format"
    return number_text(gt, line.axis, axis, line.fmt, path, extra=1, kind=line.kind)(at)


def label_lines(
    ax: Axes, lines: list[RefLine], gt: dict[str, Any], style: Style, with_lines: bool
) -> bool:
    """Place each line's label once the figure is laid out (again on every pass): clear of
    what's drawn, or, at a chosen position past the plot's edge, with an automatic axis
    widened to take it; with label.inside false, beyond the plot area, the first time with
    the figure to be laid out again around it. Returns True if the figure must be laid out
    again."""
    for a in [t for t in ax.texts if t.get_gid() == REFERENCE]:
        a.remove()
    widened = False
    most = float(style.theme["axis.max_extension"])
    for line in lines:
        if not (line.label or line.with_value):
            continue
        gap = (line.look.text("layer.reference.label").gap or 0.0) * ax.figure.dpi / 72  # type: ignore[union-attr]
        auto = line.position == "auto"

        def words(position: str, line: RefLine = line) -> str:
            at = line.end(position.split("_")[0])[1]
            return line.label + (_line_text(ax, gt, line, at) if line.with_value else "")

        if not line.inside:
            if auto or line.position.startswith("center"):
                raise DrawError(
                    f"{line.path}.label.position: {line.position}, but label.inside is false, "
                    "so the label goes beyond the line's start or end; choose a start or end "
                    "position"
                )
            _label_line(ax, line, words(line.position), line.position)
            widened |= not line.placed_outside
            line.placed_outside = True
            continue

        def attempt(
            position: str, keep: bool, line: RefLine = line, auto: bool = auto, gap: float = gap
        ) -> str:
            """Place the label: "clear" inside the plot area, "outside" it, or "covers"."""
            a = _label_line(ax, line, words(position), position)
            measure(ax.figure)
            box, plot = a.get_window_extent(), ax.get_window_extent()
            inside = (
                box.x0 >= plot.x0 - 0.5
                and box.x1 <= plot.x1 + 0.5
                and box.y0 >= plot.y0 - 0.5
                and box.y1 <= plot.y1 + 0.5
            )
            found = (
                "clear" if inside and labels.box_clear(ax, box, with_lines) else
                "covers" if inside else "outside"
            )  # fmt: skip
            if found == "outside" and not auto and keep:  # past the plot's edge: widen to it
                nonlocal widened
                what = f"{line.path}: its label"
                widened |= marks.grow_to_fit(ax, [box], gt, line.axis, gap, what)
            elif not (keep and found == "clear"):
                a.remove()
            return found

        def room(position: str, line: RefLine = line) -> bool:
            """Grow the axis along the line at its start or end until the label is clear."""
            along = position.split("_")[0]
            other, end = ("x" if line.axis == "y" else "y"), ("max" if along == "end" else "min")
            if along == "center" or not unset(gt[f"axis.{other}.{end}"]):
                return False
            return labels.grow_until(
                ax, other, end, lambda: attempt(position, False) == "clear", most
            )

        tries = LABEL_ORDER if auto else [line.position]
        if auto:  # the first clear position; past the edge counts as not clear
            found = next((f for p in tries if (f := attempt(p, keep=True)) == "clear"), "covers")
        else:
            found = attempt(line.position, keep=True)
        if found == "covers" and any(room(p) and attempt(p, keep=True) == "clear" for p in tries):
            continue
        if found == "covers" and auto:
            raise DrawError(
                f"{line.path}.label.position: auto, but no position beside the line is clear "
                "of what's drawn; choose one and widen the axis, shorten the label, or widen "
                "the format"
            )
        if found == "covers":
            others = ", ".join(p for p in LABEL_ORDER if p != line.position)
            raise DrawError(
                f"{line.path}.label.position: {line.position}, but the label covers what's "
                f"drawn; use auto, or one of {others}"
            )
    return widened


def include(ax: Axes, lines: list[RefLine], gt: dict[str, Any]) -> None:
    """Widen automatic limits to every reference line; outside a set limit, an error."""
    for line in lines:
        axis = line.axis
        values = line.values()
        values = values[np.isfinite(values)]
        if not len(values):
            continue
        get = ax.get_ylim if axis == "y" else ax.get_xlim
        put = ax.set_ylim if axis == "y" else ax.set_xlim
        lo, hi = get()
        low, high = float(values.min()), float(values.max())
        log = (ax.get_yscale() if axis == "y" else ax.get_xscale()) == "log"
        below = limits.outside(low, lo, hi, log)[0]
        above = limits.outside(high, lo, hi, log)[1]
        if not (below or above):
            continue
        end = "min" if below else "max"
        if not unset(gt[f"axis.{axis}.{end}"]):
            at = low if below else high
            raise DrawError(
                f"{line.path}: the line at {at:g} is outside axis.{axis}.{end}; move the line "
                "or the limit"
            )
        margin = (hi - lo) * 0.05 if hi > lo else abs(low) * 0.05 or 1.0
        put(min(lo, low - margin), max(hi, high + margin))


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
        if gt["arrangement.stacking"] != "none":
            raise DrawError(
                f"{where}: error bars on stacked series aren't defined (a segment's uncertainty "
                "isn't the stack's); draw the series unstacked"
            )
        axis = layer["axis"]
        along_value = axis == roles.value
        how = layer["value.aggregation.function"]
        multiplier = float(layer["value.aggregation.multiplier"])
        percentile = float(layer["value.aggregation.percentile"])
        columns = [e for e in ("lower", "upper") if isinstance(layer[f"value.{e}"], str)]
        log = gt[f"axis.{axis}.scale"] == "log"
        for s in series:
            aggregated = s.listed.aggregation is not None
            if not unset(how) and not aggregated and columns:  # the function acts on columns
                raise DrawError(
                    f"{where}.value.aggregation.function: {how} is the spread of the rows a "
                    f"mark stands for, so set {s.listed.path('aggregation')} too"
                )
            centres = numbers(s.y if along_value else s.x)
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
                    (how, multiplier, percentile),
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
            places = numbers(s.x if along_value else s.y)
            shifted = marks.shifted(ax, roles.base, s.shifts, s.spacing)
            _draw_bars(ax, places, low, high, axis, s.color, style, shifted, t)


def _distances(
    given: Any,
    aggregation: tuple[Any, float, float],
    s: Any,
    frame: pd.DataFrame,
    aggregated: bool,
    path: str,
) -> np.ndarray:
    n = len(s.x)
    how, multiplier, percentile = aggregation
    if not isinstance(given, str):
        if float(given) < 0:
            raise DrawError(f"{path}: {given} is below 0; it's a distance from each value")
        return np.full(n, float(given))
    if given not in frame.columns:
        raise DrawError(f"{path}: no column '{given}' in the data")
    column = pd.Series(numbers(frame[given]), index=frame.index)
    if aggregated:
        if unset(how):
            raise DrawError(
                f"{path}: each mark stands for several rows, so a column's distance needs "
                "value.aggregation.function"
            )
        rows = frame.loc[s.rows]
        groups = rows.groupby(numbers(rows[s.place_column]), sort=False)[given]
        spreads = {marks.key(k): combine(numbers(g), str(how), percentile) for k, g in groups}
        out = np.array([multiplier * spreads.get(marks.key(p), np.nan) for p in numbers(s.x)])
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
    look = style.line("layer.error_bar")
    ink, width = look.color, look.width
    n = len(places)
    along = np.repeat(places, 3)
    span = np.empty(3 * n)
    span[0::3], span[1::3], span[2::3] = low, high, np.nan
    along[2::3] = np.nan
    xs, ys = (along, span) if axis == "y" else (span, along)
    (stem,) = ax.plot(
        xs,
        ys,
        color=ink,
        linewidth=width,
        linestyle=look.style,
        zorder=1.9,
        gid=ERROR_BAR,
    )
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


TOP_NOTE = "_forgegraph_top_note"  # on a note above the plot box: its gap, in points


def _under_top_notes(ax: Axes, renderer: Any) -> float:
    """How far above the plot box a note outside at the top starts, in display pixels: past
    the x-axis's tick labels on top, and past a key outside at the top."""
    plot = ax.get_window_extent(renderer)
    reach = 0.0
    if any(t.label2.get_visible() and t.label2.get_text() for t in ax.xaxis.get_major_ticks()):
        box = ax.xaxis.get_tightbbox(renderer)
        reach = max(reach, box.y1 - plot.y1) if box is not None else reach
    for k in keys(ax):
        if k.outside and k.position and k.position.startswith("top"):
            room = k.height + k.style.pt("legend.key.gap.outer")
            reach = max(reach, room * ax.figure.dpi / 72)  # type: ignore[union-attr]
    return reach


def notes_outside(ax: Axes, layers: dict[str, dict[str, Any]], style: Style) -> None:
    """Notes outside the plot area: at the top, between the title and the plot box (above a
    key outside at the top), or below the x-axis title. Drawn before layout, which makes room
    for them; the title moves up over a note at the top."""
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
        own = look(style, layer)
        gap = own.pt("layer.note.gap")
        top = vertical == "top"

        def edge(renderer: Any, top: bool = top) -> Bbox:
            plot = ax.get_window_extent(renderer)
            if top:
                reach = _under_top_notes(ax, renderer)
                return Bbox.from_extents(plot.x0, plot.y0, plot.x1, plot.y1 + reach)
            if ax.xaxis.label.get_text():
                box = ax.xaxis.label.get_window_extent(renderer)
            else:
                box = ax.xaxis.get_tightbbox(renderer) or plot
            return Bbox.from_extents(plot.x0, box.y0, plot.x1, box.y1)

        note = _note(
            ax,
            layer["text"],
            (fraction, 1.0 if top else 0.0),
            edge,
            (0.0, gap if top else -gap),
            {"left": "left", "center": "center", "right": "right"}[horizontal],
            "bottom" if top else "top",
            own,
        )
        if top:
            setattr(note, TOP_NOTE, gap)


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
        fontproperties=style.font("layer.note"),
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
    ax: Axes,
    layers: dict[str, dict[str, Any]],
    gt: dict[str, Any],
    style: Style,
    with_lines: bool,
) -> list[Bbox]:
    """Notes inside the plot area, after layout and keys, each clear of everything drawn,
    the keys and the other notes; return their boxes. When no position is clear, an automatic
    y-axis grows at the note's top or bottom, by up to axis.max_extension, to make room."""
    placed: list[Bbox] = []
    most = float(style.theme["axis.max_extension"])

    def attempt(layer: dict[str, Any], position: str, keep: bool) -> Bbox | None:
        """The note's box at a position if it's clear there (kept, with keep), else None."""
        own = look(style, layer)
        inset = own.pt("layer.note.gap")
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
            own,
        )
        measure(ax.figure)
        box, plot = a.get_window_extent(), ax.get_window_extent()
        inside = box.x0 >= plot.x0 - 0.5 and box.x1 <= plot.x1 + 0.5
        if (
            inside
            and labels.box_clear(ax, box, with_lines, keys=True)
            and not any(box.overlaps(p) for p in placed)
        ):
            if not keep:
                a.remove()
            return box
        a.remove()
        return None

    for name, layer in layers.items():
        if layer["type"] != "note" or not layer["inside"]:
            continue
        tries = POSITIONS if layer["position"] == "auto" else [layer["position"]]
        box = next((b for p in tries if (b := attempt(layer, p, keep=True)) is not None), None)
        for position in tries if box is None else []:  # make room at the top or bottom
            end = "max" if position.startswith("top") else "min"
            if not unset(gt[f"axis.y.{end}"]):
                continue  # a set limit stays where it is

            def fits(layer: dict[str, Any] = layer, position: str = position) -> bool:
                return attempt(layer, position, keep=False) is not None

            if labels.grow_until(ax, "y", end, fits, most):
                box = attempt(layer, position, keep=True)
                break
        if box is not None:
            placed.append(box)
        else:
            what = "any position" if layer["position"] == "auto" else layer["position"]
            raise DrawError(
                f"layers.{name}: the note doesn't fit {what} inside the plot area without "
                "covering what's drawn; put it outside (inside: false), shorten it, or widen "
                "the format"
            )
    return placed
