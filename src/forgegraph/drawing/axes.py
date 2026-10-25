"""Each axis's data and ticks (graph_types/xy.yaml axis.x.*, axis.y.*; themes axis.tick.*).

- **Type** (data.type): decimal, integer, datetime or categorical. auto takes it from the
  column: dates and times, then numbers (integer for an integer column), otherwise
  categorical. An integer axis's automatic ticks are whole numbers (forgegraph.drawing.ticks).
- **Categories** sit at positions 0, 1, 2 … in data.order: as in the data (a pandas
  Categorical's own order), alphanumeric (natural: Run 2 before Run 10), or by the other
  axis's value (the total at each category), ascending or descending. Every value present is
  a category; each is labelled with its value.
- **Ticks** (tick.algorithm): auto, the theme's algorithm (a categorical axis's positions are
  whole numbers); all, a tick at every value; manual, a tick every tick.step: a number, a
  factor on a log axis (10: 10, 100, 1000), or a count and a unit on a date axis
  ("2 week"). Ticks from all and manual are never thinned. Labels that run together
  are an error with any algorithm (check_fit).
- **Date ticks and labels** are on one calendar unit's boundaries and written at that unit
  (forgegraph.drawing.dates).
- **Labels** (tick.label.format): auto, or a Python format spec for numbers (",.0f") or a
  strftime format for dates ("%b %Y"; see forgegraph.drawing.dates).
- **The theme** rotates x-axis tick labels (axis.tick.label.x_rotation) and lets a label that's
  wider than the space between its neighbours wrap onto up to max_wrap more lines.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from itertools import pairwise
from typing import Any, cast

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, Formatter, Locator, MultipleLocator

from forgegraph.drawing import text as text_module
from forgegraph.drawing.dates import (
    CalendarLabels,
    CalendarTicks,
    DateFormatLabels,
    date_format,
    format_date,
)
from forgegraph.drawing.errors import DrawError
from forgegraph.drawing.markup import literal
from forgegraph.drawing.style import Style
from forgegraph.drawing.ticks import LogStep, LogTicks, NiceTicks
from forgegraph.spec.parameters import STEP


def natural(value: Any) -> tuple:
    """Sort key that reads numbers in text by value: "6 cm2" before "130 cm2"."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return ((0, float(value), ""),)
    parts = re.split(r"(-?\d+(?:\.\d+)?)", str(value))
    return tuple(
        (0, float(p), "") if i % 2 else (1, 0.0, p.casefold()) for i, p in enumerate(parts) if p
    )


def data_type(values: pd.Series, setting: str, path: str, column: str) -> str:
    """The axis's type: data.type, or for auto, the column's."""
    dates = pd.api.types.is_datetime64_any_dtype(values)
    numeric = pd.api.types.is_numeric_dtype(values) and not pd.api.types.is_bool_dtype(values)
    if setting == "auto":
        if dates:
            return "date"
        if numeric:
            return "integer" if pd.api.types.is_integer_dtype(values) else "decimal"
        return "categorical"
    if setting == "categorical":
        return setting
    if setting == "datetime":
        if not dates:
            raise DrawError(f"{path}: datetime, but '{column}' isn't dates or times")
        return "date"
    if dates:
        raise DrawError(
            f"{path}: {setting}, but '{column}' holds dates or times; use auto, datetime or "
            "categorical"
        )
    if not numeric:
        raise DrawError(f"{path}: {setting}, but '{column}' isn't numbers; use auto or categorical")
    if setting == "integer":
        given = np.asarray(pd.to_numeric(values, errors="coerce"), dtype=float)
        given = given[~np.isnan(given)]
        if bool((given != np.round(given)).any()):
            raise DrawError(f"{path}: integer, but '{column}' has values that aren't whole numbers")
    return setting


def reads_as_dates(values: pd.Series) -> bool:
    """Whether a column is text whose every value reads as an ISO 8601 date or time."""
    text = values.dropna()
    if text.empty or not all(isinstance(v, str) for v in text):
        return False
    if not text.str.match(r"^\d{4}-\d{2}(-\d{2})?([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?$").all():
        return False
    parsed = pd.to_datetime(text, format="ISO8601", errors="coerce")
    return bool(parsed.notna().all())


def categories(
    values: pd.Series, method: str, direction: str, by: pd.Series | None = None
) -> list[Any]:
    """The categories present in values, in order. by: the other axis's values, row for row,
    for method value."""
    present = list(dict.fromkeys(values.dropna().tolist()))
    if method == "source":
        if isinstance(values.dtype, pd.CategoricalDtype):
            shown = set(present)
            present = [c for c in values.cat.categories if c in shown]
        out = present
    elif method == "alphanumeric":
        out = sorted(present, key=natural)
    else:
        assert by is not None
        numbers = pd.Series(np.asarray(pd.to_numeric(by, errors="coerce"), dtype=float))
        sums = cast(pd.Series, numbers.groupby(values.reset_index(drop=True)).sum()).to_dict()
        out = sorted(present, key=lambda c: float(sums.get(c, 0.0)))
    return out[::-1] if direction == "descending" else out


def positions(values: pd.Series, cats: list[Any]) -> pd.Series:
    """Each value's category position, as a float; missing values stay missing."""
    index = {c: float(i) for i, c in enumerate(cats)}
    return values.map(index).astype(float)


def parse_step(step: Any, kind: str, path: str) -> tuple[int, str] | float:
    """A tick step: (count, unit) on a date axis, a number otherwise."""
    if kind == "date":
        m = STEP.match(str(step)) if isinstance(step, str) else None
        if m is None:
            raise DrawError(
                f'{path}: a date axis\'s step is a count and a unit, e.g. "2 week" '
                "(units: sec, min, hour, day, week, month, year)"
            )
        return int(m[1]), m[2]
    if isinstance(step, str):
        raise DrawError(f"{path}: '{step}' is a date step, but this axis isn't dates")
    return float(step)


class LogLabels(Formatter):
    """Plain numbers when every tick on the axis is from 0.001 to 99999; otherwise powers of
    ten, so one axis never mixes the two."""

    ticks: tuple[float, ...] = ()

    def set_locs(self, locs: Any) -> None:
        self.ticks = tuple(float(v) for v in locs)

    def __call__(self, x: float, pos: int | None = None) -> str:
        assert self.axis is not None
        lo, hi = sorted(self.axis.get_view_interval())
        shown = [v for v in self.ticks if lo <= v <= hi] or [x]
        if all(1e-3 <= v < 1e5 for v in shown):
            return f"{x:g}"
        exponent = math.floor(math.log10(x) + 1e-9)
        mantissa = x / 10.0**exponent
        if math.isclose(mantissa, 1.0):
            return f"$10^{{{exponent}}}$"
        return f"${mantissa:g}\\times10^{{{exponent}}}$"


def number_format(fmt: str, path: str) -> str:
    """A Python format spec, checked: it must format numbers and not depend on the locale."""
    if fmt.rstrip().endswith("n"):
        raise DrawError(f"{path}: the n type depends on the computer's locale; use , or _")
    for sample in (1234.5, 1234):
        try:
            format(sample, fmt)
            return fmt
        except (ValueError, TypeError):
            continue
    raise DrawError(f'{path}: \'{fmt}\' isn\'t a Python number format, e.g. ",.0f" or ".1%"')


def format_number(value: float, fmt: str) -> str:
    if fmt.rstrip()[-1:] in "bcdoxX" and float(value).is_integer():
        return format(round(value), fmt)
    return format(value, fmt)


def number_text(
    gt: dict[str, Any], name: str, axis: Any, given: Any, path: str, extra: int = 0
) -> Any:
    """How a label writes a value on axis name: in its own format; auto, in the axis's tick
    label format if that's set, otherwise with as many decimals as the tick labels show,
    plus extra."""
    if given == "auto":
        given, path = gt[f"axis.{name}.tick.label.format"], f"axis.{name}.tick.label.format"
    if given != "auto":
        checked = number_format(str(given), path)
        return lambda v: format_number(float(v), checked)
    places = _tick_decimals(axis) + extra
    return lambda v: f"{float(v):.{places}f}"


def _tick_decimals(axis: Any) -> int:
    """The most decimal places the axis's tick labels show."""
    shown = [t.get_text().replace("\u2212", "-") for t in axis.get_ticklabels()]
    decimals = [len(t.split(".")[1]) for t in shown if re.fullmatch(r"-?\d+\.\d+", t)]
    return max(decimals, default=0)


class NumberLabels(Formatter):
    def __init__(self, fmt: str) -> None:
        self.fmt = fmt

    def __call__(self, x: float, pos: int | None = None) -> str:
        return format_number(x, self.fmt)


def category_label(value: Any, fmt: str | None) -> str:
    """A category's label: its value as written, or formatted (numbers and dates only)."""
    if isinstance(value, pd.Timestamp | datetime | np.datetime64):
        stamp = cast(datetime, pd.Timestamp(value).to_pydatetime())
        return format_date(stamp, fmt) if fmt else stamp.strftime("%Y-%m-%d")
    if isinstance(value, int | float | np.number) and not isinstance(value, bool):
        return format_number(float(value), fmt) if fmt else f"{value:g}"
    return literal(str(value))


class CategoryLabels(Formatter):
    """Each position's category, as its label."""

    def __init__(self, cats: list[Any], fmt: str | None) -> None:
        self.labels = [category_label(c, fmt) for c in cats]

    def __call__(self, x: float, pos: int | None = None) -> str:
        i = round(x)
        return self.labels[i] if 0 <= i < len(self.labels) and abs(x - i) < 1e-9 else ""


class Wrapped(Formatter):
    """Another formatter's labels, each wrapped at its spaces onto up to max_wrap more lines
    when it's wider than the space between its tick and the nearest other."""

    def __init__(self, inner: Formatter, max_wrap: int, gap: float) -> None:
        self.inner, self.max_wrap, self.gap = inner, max_wrap, gap  # gap in points

    def set_axis(self, axis: Any) -> None:
        super().set_axis(axis)
        self.inner.set_axis(axis)

    def set_locs(self, locs: Any) -> None:
        self.inner.set_locs(locs)

    def get_offset(self) -> str:
        return self.inner.get_offset()

    def __call__(self, x: float, pos: int | None = None) -> str:
        return self.inner(x, pos)

    def format_ticks(self, values: Any) -> list[str]:
        labels = self.inner.format_ticks(values)
        axis = cast(Any, self.axis)
        if self.max_wrap <= 0 or axis is None or len(values) < 2:
            return labels
        ax = axis.axes
        at = [ax.transData.transform((v, 0.0))[0] for v in values]
        room = min(abs(b - a) for a, b in pairwise(at)) - self.gap * ax.figure.dpi / 72
        sample = axis.get_major_ticks(1)[0].label1
        return [self._wrap(text, room, sample, ax) for text in labels]

    def _wrap(self, text: str, room: float, sample: Text, ax: Axes) -> str:
        width = _measure(sample, ax)
        if " " not in text or width(text) <= room:
            return text
        lines: list[str] = []
        for word in text.split(" "):
            if lines and width(f"{lines[-1]} {word}") <= room:
                lines[-1] = f"{lines[-1]} {word}"
            else:
                lines.append(word)
        return "\n".join(lines) if len(lines) <= self.max_wrap + 1 else text


def _measure(sample: Text, ax: Axes) -> Any:
    prop, dpi = sample.get_fontproperties(), ax.figure.dpi  # type: ignore[union-attr]
    return lambda label: text_module.extent(label, prop, dpi)[0]


def ticks_and_labels(
    ax: Axes,
    name: str,
    kind: str,
    gt: dict[str, Any],
    style: Style,
    cats: list[Any] | None,
    values: np.ndarray,
) -> None:
    """Set the axis's locator and formatter, and the theme's rotation and wrapping (x)."""
    axis = ax.xaxis if name == "x" else ax.yaxis
    prefix = f"axis.{name}"
    algorithm = gt[f"{prefix}.tick.algorithm"]
    step = gt[f"{prefix}.tick.step"]
    fmt = gt[f"{prefix}.tick.label.format"]
    log = axis.get_scale() == "log"
    if kind == "categorical" and log:
        raise DrawError(f"{prefix}.scale: log, but the axis is categorical")
    t = style.theme
    order = str(t["axis.tick.label.date_order"])
    gap = style.pt("axis.tick.label.gap")
    locator: Locator
    if algorithm == "all":
        locator = FixedLocator(sorted(set(float(v) for v in values if not np.isnan(v))))
    elif algorithm == "manual":
        parsed = parse_step(step, kind, f"{prefix}.tick.step")
        if isinstance(parsed, tuple):
            locator = CalendarTicks(order, gap, step=parsed)
        else:
            locator = LogStep(parsed) if log else MultipleLocator(parsed)
    elif log:
        locator = LogTicks(
            str(t["axis.tick.log_algorithm"]),
            str(t["axis.tick.algorithm"]),
            style.pt("axis.tick.label.gap"),
            integer=kind == "integer",
        )
    elif kind == "date":
        locator = CalendarTicks(order, gap, spacing=_spacing(values))
    else:
        locator = NiceTicks(
            str(t["axis.tick.algorithm"]), integer=kind in ("integer", "categorical")
        )
    axis.set_major_locator(locator)

    given = None if fmt == "auto" else str(fmt)
    formatter: Formatter | None
    if kind == "categorical":
        assert cats is not None
        if given is not None and all(isinstance(c, str) for c in cats):
            raise DrawError(f"{prefix}.tick.label.format: the categories are text, not numbers")
        if given is not None:
            given = (
                date_format(given, f"{prefix}.tick.label.format")
                if any(isinstance(c, pd.Timestamp | datetime) for c in cats)
                else number_format(given, f"{prefix}.tick.label.format")
            )
        formatter = CategoryLabels(cats, given)
    elif given is not None:
        formatter = (
            DateFormatLabels(date_format(given, f"{prefix}.tick.label.format"))
            if kind == "date"
            else NumberLabels(number_format(given, f"{prefix}.tick.label.format"))
        )
    elif log:
        formatter = LogLabels()
    elif kind == "date":
        formatter = CalendarLabels(locator, order)
    else:
        formatter = None  # matplotlib's
    if name == "x" and int(t["axis.tick.label.max_wrap"]) > 0 and kind != "date":
        formatter = Wrapped(
            formatter or axis.get_major_formatter(),
            int(t["axis.tick.label.max_wrap"]),
            style.pt("axis.tick.label.gap"),
        )
    if formatter is not None:
        axis.set_major_formatter(formatter)
    rotation = float(t["axis.tick.label.x_rotation"])
    if name == "x" and rotation:
        ax.tick_params(axis="x", labelrotation=rotation, labelrotation_mode="xtick")


def _spacing(values: np.ndarray) -> float | None:
    """The smallest gap between distinct values, or None with fewer than two."""
    distinct = np.unique(values[~np.isnan(values)])
    return float(np.diff(distinct).min()) if len(distinct) > 1 else None


def check_fit(ax: Axes, gt: dict[str, Any], style: Style) -> None:
    """Tick labels that run together, or come within the theme's axis.tick.label.gap of each
    other, are an error: all and manual are never thinned, and auto's algorithms count
    labels by their height, not their width, so long labels can still meet."""
    gap = style.pt("axis.tick.label.gap") * ax.figure.dpi / 72
    for name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
        algorithm = gt[f"axis.{name}.tick.algorithm"]
        # get_majorticklabels updates the ticks first: before a draw they're stale
        if _run_together([t for t in axis.get_majorticklabels() if t.get_text()], gap):
            what = {
                "all": "a tick at every value",
                "manual": "a tick every tick.step",
                "auto": "ticks from the theme's algorithm",
            }[algorithm]
            raise DrawError(
                f"axis.{name}.tick.algorithm: {algorithm} gives {what}, but their labels run "
                "together; use a larger tick.step, a shorter tick.label.format, fewer values, "
                "a wider format, or the theme's tick label rotation or wrapping"
            )


def _run_together(labels: list[Text], gap: float) -> bool:
    """Whether any two labels come within gap (pixels) of each other. An axis's labels share
    one rotation, so each is a rectangle along that direction: two are clear when they're
    apart along their text or across it. Upright boxes around rotated labels would overlap
    even when the labels don't."""
    if len(labels) < 2:
        return False
    angle = math.radians(labels[0].get_rotation())
    along = np.array([math.cos(angle), math.sin(angle)])
    across = np.array([-math.sin(angle), math.cos(angle)])
    shapes = []
    for label in labels:
        box = label.get_window_extent()  # the rotated label's box: centred on it
        rotation = label.get_rotation()
        label.set_rotation(0)
        flat = label.get_window_extent()
        label.set_rotation(rotation)
        centre = np.array([(box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2])
        shapes.append((centre, flat.width, flat.height))
    for i, (c1, w1, h1) in enumerate(shapes):
        for c2, w2, h2 in shapes[i + 1 :]:
            d = c2 - c1
            if abs(d @ along) < (w1 + w2) / 2 + gap and abs(d @ across) < (h1 + h2) / 2 + gap:
                return True
    return False
