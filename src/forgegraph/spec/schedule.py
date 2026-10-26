"""A schedule's cadence: when a scheduled job runs (docs/specs/schedule/base_schedule.md).

cadence.interval.count counts cadence.interval.unit (minute, hour, day, week, month or year), and
cadence.at says when in each unit the job runs, as one time or a list:

| interval.unit | at | e.g. | None means |
| --- | --- | --- | --- |
| minute | None | | each minute's start |
| hour | :MM | ":30" | :00 |
| day | HH:MM | "06:00" | 00:00 |
| week | day HH:MM | "mon 06:00" | Monday 00:00 |
| month | day of month (1-28), HH:MM | "1 06:00" | the 1st, 00:00 |
| year | month and day, HH:MM | "Jan 1 06:00" | 1 January, 00:00 |

The time is optional for week, month and year. interval.count divides the next unit up (60 for
minutes, 24 for hours, 12 for months), and is 1 for days, weeks and years, so that every run
lands on the same clock positions, as cron and launchd need. Times are the machine's local
time. Everything here is checked: a cadence that can't be run exactly is an error.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from typing import Any

from forgegraph.spec.parameters import is_none

UNITS = ("minute", "hour", "day", "week", "month", "year")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
DIVIDES = {"minute": 60, "hour": 24, "month": 12}  # interval must divide these
FORMS = {
    "minute": "None",
    "hour": '":MM", e.g. ":30"',
    "day": '"HH:MM", e.g. "06:00"',
    "week": 'a day and a time, e.g. "mon 06:00"',
    "month": 'a day of the month from 1 to 28 and a time, e.g. "1 06:00"',
    "year": 'a month and day and a time, e.g. "Jan 1 06:00"',
}
_TIME = r"(?P<hour>\d{1,2}):(?P<minute>\d{2})"


class CadenceError(ValueError):
    """A cadence that can't be run; the message says where and why."""


@dataclass(frozen=True)
class When:
    """One time in each unit: the parts the unit needs, from the largest."""

    month: int = 1  # year
    day: int = 1  # month, year
    weekday: int = 0  # week; 0 is Monday
    hour: int = 0  # day, week, month, year
    minute: int = 0  # hour, day, week, month, year

    def clock(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"


@dataclass(frozen=True)
class Cadence:
    interval: int
    unit: str
    times: tuple[When, ...]

    @classmethod
    def from_values(cls, values: dict[str, Any]) -> Cadence:
        """The cadence a schedule's resolved values describe, checked."""
        interval = values["cadence.interval.count"]
        unit = values["cadence.interval.unit"]
        at = values["cadence.at"]
        if unit in DIVIDES:
            if DIVIDES[unit] % interval:
                raise CadenceError(
                    f"cadence.interval.count: {interval} doesn't divide {DIVIDES[unit]}, so runs "
                    f"wouldn't land on the same clock positions every {_next_up(unit)}"
                )
        elif interval != 1:
            raise CadenceError(
                f"cadence.interval.count: must be 1 for {unit}s; cron and launchd can't run every "
                f"{interval} {unit}s exactly"
            )
        listed = at if isinstance(at, list) else [at]
        if unit == "minute" and not (len(listed) == 1 and is_none(listed[0])):
            raise CadenceError("cadence.at: must be None for minute, the finest unit")
        times = tuple(_parse(item, unit) for item in listed)
        if len(set(times)) != len(times):
            raise CadenceError("cadence.at: lists the same time twice")
        return cls(int(interval), str(unit), tuple(sorted(times, key=_order)))

    def describe(self) -> str:
        """In words, for the footnote and the status file: e.g. "Mon to Fri at 06:00", with an en
        dash for "to"."""
        n = self.interval
        if self.unit == "minute":
            return "every minute" if n == 1 else f"every {n} minutes"
        if self.unit == "hour":
            at = " and ".join(f":{t.minute:02d}" for t in self.times)
            return f"{'every hour' if n == 1 else f'every {n} hours'} at {at}"
        if self.unit == "day":
            return "daily at " + " and ".join(t.clock() for t in self.times)
        if self.unit == "week":
            by_clock: dict[str, list[int]] = {}
            for t in self.times:
                by_clock.setdefault(t.clock(), []).append(t.weekday)
            return "; ".join(f"{_days(days)} at {clock}" for clock, days in by_clock.items())
        if self.unit == "month":
            every = "monthly" if n == 1 else f"every {n} months"
            days = " and ".join(f"the {_ordinal(t.day)} at {t.clock()}" for t in self.times)
            return f"{every} on {days}"
        days = " and ".join(f"{MONTHS[t.month - 1]} {t.day} at {t.clock()}" for t in self.times)
        return f"yearly on {days}"

    def runs(self, start: datetime, end: datetime) -> Iterator[datetime]:
        """Every run from start to end, in order."""
        n = self.interval
        if self.unit in ("minute", "hour"):
            step = timedelta(minutes=n) if self.unit == "minute" else timedelta(hours=n)
            day = start.replace(hour=0, minute=0, second=0, microsecond=0)
            while day <= end:
                offsets = sorted(
                    timedelta(minutes=t.minute) + k * step
                    for t in self.times
                    for k in range(int(timedelta(days=1) / step))
                )
                for offset in offsets:
                    if start <= day + offset <= end:
                        yield day + offset
                day += timedelta(days=1)
            return
        day = start.replace(hour=0, minute=0, second=0, microsecond=0)
        while day <= end:
            for t in self.times:
                if self._on(day, t):
                    when = day.replace(hour=t.hour, minute=t.minute)
                    if start <= when <= end:
                        yield when
            day += timedelta(days=1)

    def _on(self, day: datetime, t: When) -> bool:
        if self.unit == "day":
            return True
        if self.unit == "week":
            return day.weekday() == t.weekday
        if self.unit == "month":
            return day.day == t.day and (day.month - 1) % self.interval == 0
        return day.month == t.month and day.day == t.day

    def period(self) -> timedelta:
        """The longest time between two runs, over a span long enough to see every gap."""
        start = datetime(2024, 1, 1)  # a Monday, in a leap year
        span = {"minute": 2, "hour": 3, "day": 3, "week": 21, "month": 800, "year": 2200}
        runs = list(self.runs(start, start + timedelta(days=span[self.unit])))
        return max(b - a for a, b in pairwise(runs))


def _next_up(unit: str) -> str:
    return {"minute": "hour", "hour": "day", "month": "year"}[unit]


def _order(t: When) -> tuple[int, ...]:
    return (t.month, t.day, t.weekday, t.hour, t.minute)


def _parse(item: Any, unit: str) -> When:
    """One of cadence.at's times, for the unit."""
    if is_none(item):
        return When()
    if not isinstance(item, str):
        raise CadenceError(f"cadence.at: {item!r} isn't text; write it in quotes: {FORMS[unit]}")
    text = item.strip()
    where = f"cadence.at: '{item}'"
    forms = {
        "hour": r"^:(?P<minute>\d{2})$",
        "day": rf"^{_TIME}$",
        "week": rf"^(?P<weekday>[A-Za-z]{{3}})(?:\s+{_TIME})?$",
        "month": rf"^(?P<day>\d{{1,2}})(?:\s+{_TIME})?$",
        "year": rf"^(?P<month>[A-Za-z]{{3}})\s+(?P<day>\d{{1,2}})(?:\s+{_TIME})?$",
    }
    m = re.match(forms[unit], text) if unit in forms else None
    if m is None:
        raise CadenceError(f"{where} isn't one of {unit}'s times: {FORMS[unit]}")
    parts = m.groupdict()
    when: dict[str, int] = {
        "hour": int(parts.get("hour") or 0),
        "minute": int(parts.get("minute") or 0),
    }
    if when["hour"] > 23 or when["minute"] > 59:
        raise CadenceError(f"{where}: no such time of day")
    if unit == "week":
        name = str(parts["weekday"]).lower()
        if name not in DAYS:
            raise CadenceError(f"{where}: days are {', '.join(DAYS)}")
        when["weekday"] = DAYS.index(name)
    if unit == "month":
        when["day"] = int(parts["day"])
        if not 1 <= when["day"] <= 28:
            raise CadenceError(
                f"{where}: the day of the month is 1 to 28, so it falls in every month"
            )
    if unit == "year":
        name = str(parts["month"]).title()
        if name not in MONTHS:
            raise CadenceError(f"{where}: months are {', '.join(MONTHS)}")
        when["month"] = MONTHS.index(name) + 1
        when["day"] = int(parts["day"])
        if not 1 <= when["day"] <= (28 if when["month"] == 2 else _LENGTHS[when["month"] - 1]):
            raise CadenceError(f"{where}: no such day in {name}, every year")
    return When(**when)


_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _days(days: list[int]) -> str:
    names = [DAYS[d].title() for d in days]
    if len(days) > 2 and days == list(range(days[0], days[-1] + 1)):
        return f"{names[0]}\u2013{names[-1]}"  # an en dash
    return ", ".join(names)


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
