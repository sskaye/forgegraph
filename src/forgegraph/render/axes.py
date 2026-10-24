"""Each axis's data and ticks (graph_types/xy.yaml axis.x.*, axis.y.*; themes axis.tick.*).

- **Type** (data.type): decimal, integer, datetime or categorical. auto takes it from the
  column: dates and times, then numbers (integer for an integer column), otherwise
  categorical. An integer axis's automatic ticks are whole numbers (forgegraph.render.ticks).
- **Categories** sit at positions 0, 1, 2 … in data.order: as in the data (a pandas
  Categorical's own order), alphanumeric (natural: Run 2 before Run 10), or by the other
  axis's value (the total at each category), ascending or descending. Every value present is
  a category; each is labelled with its value.
- **Ticks** (tick.algorithm): auto, the theme's algorithm (a categorical axis's positions are
  whole numbers); all, a tick at every value; manual, a tick every tick.step: a number, a
  factor on a log axis (10: 10, 100, 1000), or a count and a unit on a date axis
  ("2 week"). Ticks from all and manual are never thinned. Labels that run together
  are an error with any algorithm (check_fit).
- **Date ticks** are on one calendar unit's boundaries (CalendarTicks): auto takes the finest
  step of CALENDAR_STEPS (d3's list, with 2 weeks, 6 months and longer runs of years) whose
  labels fit, and never one finer than the data's own spacing. Weeks start on Mondays (ISO
  8601), months count from January, and years are those divisible by the step.
- **Date labels** (CalendarLabels) are at the ticks' unit: 2026; Jul; Jul 6; 06:30; 06:30:15.
  The next unit up (the year, or for times the date) goes on a second line, under the first
  tick and wherever it changes; there's no offset text beside the axis. The theme's
  axis.tick.label.date_order writes days as Jul 6 or 6 Jul.
- **Labels** (tick.label.format): auto, or a Python format spec for numbers (",.0f") or a
  strftime format for dates ("%b %Y"), from directives that behave the same on every
  platform, with English month and day names whatever the computer's locale.
- **The theme** rotates x-axis tick labels (axis.tick.label.x_rotation) and lets a label that's
  wider than the space between its neighbours wrap onto up to max_wrap more lines.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from itertools import pairwise
from typing import Any, cast

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.axis import XAxis
from matplotlib.dates import date2num, num2date
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, Formatter, Locator, MultipleLocator

from forgegraph.render.markup import literal
from forgegraph.render.style import Style
from forgegraph.render.ticks import LogTicks, NiceTicks, target


class DrawError(ValueError):
    """A GraphSpec whose data can't be drawn as asked."""


TYPES = ("decimal", "integer", "date", "categorical")
# Steps for automatic date ticks, finest first: d3's, with 2 weeks, 6 months and longer runs
# of years. Each step's unit divides the next unit up, so its ticks are calendar boundaries.
CALENDAR_STEPS = [
    *((n, "sec") for n in (1, 5, 15, 30)),
    *((n, "min") for n in (1, 5, 15, 30)),
    *((n, "hour") for n in (1, 3, 6, 12)),
    (1, "day"), (2, "day"), (1, "week"), (2, "week"),
    (1, "month"), (3, "month"), (6, "month"),
    *((n, "year") for n in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)),
]  # fmt: skip
UNIT_DAYS = {  # each unit's shortest length, in days
    "sec": 1 / 86400,
    "min": 1 / 1440,
    "hour": 1 / 24,
    "day": 1.0,
    "week": 7.0,
    "month": 28.0,
    "year": 365.0,
}
STEP = re.compile(r"^\s*(\d+)\s+(sec|min|hour|day|week|month|year)\s*$")
# strftime directives that mean the same on every platform; names are written in English.
DATE_DIRECTIVES = set("aAwdbBmyYHIpMSfzZjUWGuV%")
UNPADDED = set("dmH")  # %-d, %-m and %-H: written without a leading zero, on every platform
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip


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


class LogStep(Locator):
    """Ticks a factor apart on a log axis, counted from the first power of ten at or above
    its low end: a step of 100 from 10 gives 10, 1000, 100000."""

    def __init__(self, factor: float) -> None:
        if factor <= 1:
            raise DrawError(f"tick.step: {factor:g} on a log axis must be a factor above 1")
        self.factor = factor

    def __call__(self) -> Any:
        lo, hi = sorted(cast(Any, self.axis).get_view_interval())
        return self.tick_values(lo, hi)

    def tick_values(self, vmin: float, vmax: float) -> Any:
        lo, hi = sorted((vmin, vmax))
        anchor = 10.0 ** math.ceil(math.log10(lo) - 1e-9)
        first = math.floor(math.log(lo / anchor) / math.log(self.factor))
        last = math.ceil(math.log(hi / anchor) / math.log(self.factor))
        ticks = (anchor * self.factor**k for k in range(first, last + 1))
        return [float(f"{t:.12g}") for t in ticks if lo * (1 - 1e-9) <= t <= hi * (1 + 1e-9)]


def _when(x: float) -> datetime:
    return num2date(x).replace(tzinfo=None)


def calendar_ticks(lo: float, hi: float, count: int, unit: str) -> list[float]:
    """The boundaries of a calendar step from lo to hi (matplotlib date numbers): every count
    seconds, minutes or hours from midnight; days counted from 1 January 1970; weeks of
    Mondays from 5 January 1970; months from January 1970; years divisible by count."""
    start, end = _when(lo), _when(hi)
    out: list[datetime] = []
    if unit in ("sec", "min", "hour"):
        size = {"sec": 1, "min": 60, "hour": 3600}[unit] * count
        day = start.replace(hour=0, minute=0, second=0, microsecond=0)
        t = day + timedelta(seconds=math.ceil((start - day).total_seconds() / size) * size)
        while t <= end:
            out.append(t)
            t += timedelta(seconds=size)
            if t.date() != (t - timedelta(seconds=size)).date():  # each day starts at midnight
                t = t.replace(hour=0, minute=0, second=0)
    elif unit in ("day", "week"):
        epoch = datetime(1970, 1, 5) if unit == "week" else datetime(1970, 1, 1)
        days = 7 * count if unit == "week" else count
        first = math.ceil((start - epoch) / timedelta(days=days))
        t = epoch + timedelta(days=first * days)
        while t <= end:
            out.append(t)
            t += timedelta(days=days)
    elif unit == "month":
        index = start.year * 12 + start.month - 1  # months since year 0
        if datetime(start.year, start.month, 1) < start:
            index += 1
        index += -index % count
        while (t := datetime(index // 12, index % 12 + 1, 1)) <= end:
            out.append(t)
            index += count
    else:
        year = start.year + (-start.year % count)
        if datetime(year, 1, 1) < start:
            year += count
        while year <= end.year:
            out.append(datetime(year, 1, 1))
            year += count
    return [float(date2num(t)) for t in out]


def _day(when: datetime, order: str) -> str:
    month = MONTHS[when.month - 1][:3]
    return f"{when.day} {month}" if order == "day_month" else f"{month} {when.day}"


def _label(when: datetime, unit: str, order: str) -> str:
    if unit == "year":
        return str(when.year)
    if unit == "month":
        return MONTHS[when.month - 1][:3]
    if unit in ("week", "day"):
        return _day(when, order)
    return when.strftime("%H:%M:%S" if unit == "sec" else "%H:%M")


def calendar_labels(values: list[float], unit: str, order: str) -> list[str]:
    """Labels at a calendar unit, with the next unit up on a second line under the first tick
    and wherever it changes: the year under months, weeks and days; the date (with its year
    on the first tick and where the year changes) under times."""
    out = []
    before: datetime | None = None
    for x in values:
        when = _when(x)
        label = _label(when, unit, order)
        if unit in ("month", "week", "day"):
            if before is None or before.year != when.year:
                label += f"\n{when.year}"
        elif unit != "year" and (before is None or before.date() != when.date()):
            date = _day(when, order)
            if before is None or before.year != when.year:
                date += f" {when.year}" if order == "day_month" else f", {when.year}"
            label += f"\n{date}"
        out.append(label)
        before = when
    return out


def unit_of(values: list[float]) -> str:
    """The coarsest calendar unit every value is a boundary of: for a tick at every value."""
    times = [_when(x) for x in values]
    if not times:
        return "day"
    midnight = all(t.hour == t.minute == t.second == 0 for t in times)
    if midnight and all(t.month == 1 and t.day == 1 for t in times):
        return "year"
    if midnight and all(t.day == 1 for t in times):
        return "month"
    if midnight:
        return "day"
    return "min" if all(t.second == 0 for t in times) else "sec"


class CalendarTicks(Locator):
    """Date ticks on one calendar unit's boundaries: a manual step's, or the finest of
    CALENDAR_STEPS that's no finer than the data's spacing (in days) and whose labels fit,
    with gap points between them."""

    def __init__(
        self,
        order: str,
        gap: float,
        spacing: float | None = None,
        step: tuple[int, str] | None = None,
    ) -> None:
        self.order, self.gap, self.spacing, self.fixed = order, gap, spacing, step
        self.step: tuple[int, str] = step or CALENDAR_STEPS[0]

    def __call__(self) -> Any:
        lo, hi = sorted(cast(Any, self.axis).get_view_interval())
        return self.tick_values(lo, hi)

    def tick_values(self, vmin: float, vmax: float) -> Any:
        lo, hi = sorted((vmin, vmax))
        if self.fixed is not None:
            return calendar_ticks(lo, hi, *self.fixed)
        room = target(self.axis)
        ticks: list[float] = []
        for count, unit in CALENDAR_STEPS:
            days = count * UNIT_DAYS[unit]
            if self.spacing is not None and days < self.spacing * (1 - 1e-9):
                continue  # finer than the data
            if (hi - lo) / days > 4 * room + 4:
                continue  # far too many to try
            self.step = (count, unit)
            ticks = calendar_ticks(lo, hi, count, unit)
            if len(ticks) <= room and self._fit(ticks, unit):
                break
        return ticks

    def _fit(self, ticks: list[float], unit: str) -> bool:
        """Whether the ticks' labels clear each other by the gap, along the axis."""
        axis = cast(Any, self.axis)
        if axis is None or len(ticks) < 2:
            return True
        ax = axis.axes
        sample = axis.get_major_ticks(1)[0].label1
        size = _measure(sample, ax)
        labels = calendar_labels(ticks, unit, self.order)
        gap = self.gap * ax.figure.dpi / 72
        across = isinstance(axis, XAxis)
        k = 0 if across else 1
        at = [ax.transData.transform((t, t))[k] for t in ticks]
        if across:
            extents = [size(label) for label in labels]
        else:
            line = sample.get_fontsize() * 1.2 * ax.figure.dpi / 72
            extents = [line * (label.count("\n") + 1) for label in labels]
        return all(
            abs(b - a) >= (ea + eb) / 2 + gap
            for (a, ea), (b, eb) in pairwise(zip(at, extents, strict=True))
        )


class CalendarLabels(Formatter):
    """Labels at the ticks' calendar unit (calendar_labels): the locator's step, or for a
    tick at every value, the coarsest unit the values all fall on."""

    def __init__(self, locator: Locator, order: str) -> None:
        self.locator, self.order = locator, order

    def _unit(self, values: list[float]) -> str:
        if isinstance(self.locator, CalendarTicks):
            return self.locator.step[1]
        return unit_of(values)

    def format_ticks(self, values: Any) -> list[str]:
        values = [float(v) for v in values]
        return calendar_labels(values, self._unit(values), self.order)

    def __call__(self, x: float, pos: int | None = None) -> str:
        return _label(_when(x), self._unit([x]), self.order)


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


def date_format(fmt: str, path: str) -> str:
    """A strftime format, checked: only directives that behave the same on every platform, and
    %-d, %-m and %-H, which ForgeGraph writes itself."""
    for m in re.finditer(r"%(-?.)", fmt):
        if m[1] not in DATE_DIRECTIVES and not (m[1][0] == "-" and m[1][1:] in UNPADDED):
            raise DrawError(
                f"{path}: %{m[1]} isn't one of the date directives ForgeGraph takes "
                "(those that mean the same on every computer, e.g. %d %b %Y %H:%M, and %-d, "
                "%-m and %-H for no leading zero)"
            )
    return fmt


def format_number(value: float, fmt: str) -> str:
    if fmt.rstrip()[-1:] in "bcdoxX" and float(value).is_integer():
        return format(round(value), fmt)
    return format(value, fmt)


def format_date(when: datetime, fmt: str) -> str:
    """strftime with English names for %a %A %b %B %p, and %-d %-m %-H without a leading
    zero."""
    english = {
        "%a": DAYS[when.weekday()][:3],
        "%A": DAYS[when.weekday()],
        "%b": MONTHS[when.month - 1][:3],
        "%B": MONTHS[when.month - 1],
        "%p": "AM" if when.hour < 12 else "PM",
        "%%": "%",
        "%-d": str(when.day),
        "%-m": str(when.month),
        "%-H": str(when.hour),
    }
    parts = re.split(r"(%-?.)", fmt)
    return "".join(
        english[p] if p in english else (when.strftime(p) if p.startswith("%") else p)
        for p in parts
    )


class NumberLabels(Formatter):
    def __init__(self, fmt: str) -> None:
        self.fmt = fmt

    def __call__(self, x: float, pos: int | None = None) -> str:
        return format_number(x, self.fmt)


class DateFormatLabels(Formatter):
    def __init__(self, fmt: str) -> None:
        self.fmt = fmt

    def __call__(self, x: float, pos: int | None = None) -> str:
        return format_date(num2date(x).replace(tzinfo=None), self.fmt)


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
    figure = ax.figure

    def width(text: str) -> float:
        probe = Text(text=text, fontproperties=sample.get_fontproperties())
        probe.set_figure(figure)
        return probe.get_window_extent().width  # matplotlib finds the renderer, any backend

    return width


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
