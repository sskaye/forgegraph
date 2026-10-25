"""A date axis's ticks and labels (axis.*.tick in graph_types/xy.yaml; the theme's date_order).

- **Date ticks** are on one calendar unit's boundaries (CalendarTicks): auto takes the finest
  step of CALENDAR_STEPS (d3's list, with 2 weeks, 6 months and longer runs of years) whose
  labels fit, and never one finer than the data's own spacing. Weeks start on Mondays (ISO
  8601), months count from January, and years are those divisible by the step.
- **Date labels** (CalendarLabels) are at the ticks' unit: 2026; Jul; Jul 6; 06:30; 06:30:15.
  The next unit up (the year, or for times the date) goes on a second line, under the first
  tick and wherever it changes; there's no offset text beside the axis. The theme's
  axis.tick.label.date_order writes days as Jul 6 or 6 Jul.
- **A date format** (tick.label.format) is a strftime format, from directives that behave
  the same on every platform (date_format), with English month and day names whatever the
  computer's locale (format_date).
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from itertools import pairwise
from typing import Any, cast

from matplotlib.axis import XAxis
from matplotlib.dates import date2num, num2date
from matplotlib.ticker import Formatter, Locator

from forgegraph.drawing import text
from forgegraph.drawing.errors import DrawError
from forgegraph.drawing.ticks import target

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
# strftime directives that mean the same on every platform; names are written in English.
DATE_DIRECTIVES = set("aAwdbBmyYHIpMSfzZjUWGuV%")
UNPADDED = set("dmH")  # %-d, %-m and %-H: written without a leading zero, on every platform
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip


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
        prop, dpi = sample.get_fontproperties(), ax.figure.dpi
        labels = calendar_labels(ticks, unit, self.order)
        gap = self.gap * ax.figure.dpi / 72
        across = isinstance(axis, XAxis)
        k = 0 if across else 1
        at = [ax.transData.transform((t, t))[k] for t in ticks]
        if across:
            extents = [text.extent(label, prop, dpi)[0] for label in labels]
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


class DateFormatLabels(Formatter):
    def __init__(self, fmt: str) -> None:
        self.fmt = fmt

    def __call__(self, x: float, pos: int | None = None) -> str:
        return format_date(num2date(x).replace(tzinfo=None), self.fmt)
