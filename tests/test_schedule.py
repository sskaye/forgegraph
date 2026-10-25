"""A schedule's cadence (spec/schedule.py): every form, its description, its longest gap
between runs, and the errors for cadences that can't be run exactly."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from pack_helpers import doc

from forgegraph.spec.documents import builtin, validate
from forgegraph.spec.schedule import Cadence, CadenceError

EN_DASH = chr(0x2013)
WEEKDAYS = ["mon 06:00", "tue 06:00", "wed 06:00", "thu 06:00", "fri 06:00"]


def cadence(interval: int, unit: str, at: object) -> Cadence:
    return Cadence.from_values(
        {"cadence.interval": interval, "cadence.interval_unit": unit, "cadence.at": at}
    )


@pytest.mark.parametrize(
    ("interval", "unit", "at", "words", "period"),
    [
        (15, "minute", None, "every 15 minutes", timedelta(minutes=15)),
        (2, "hour", ":30", "every 2 hours at :30", timedelta(hours=2)),
        (1, "day", "06:00", "daily at 06:00", timedelta(days=1)),
        (1, "day", ["06:00", "18:00"], "daily at 06:00 and 18:00", timedelta(hours=12)),
        (1, "week", WEEKDAYS, f"Mon{EN_DASH}Fri at 06:00", timedelta(days=3)),
        (1, "week", "mon", "Mon at 00:00", timedelta(days=7)),
        (3, "month", "1 06:00", "every 3 months on the 1st at 06:00", timedelta(days=92)),
        (1, "year", "Jan 1", "yearly on Jan 1 at 00:00", timedelta(days=366)),
    ],
)
def test_cadences(interval, unit, at, words, period):
    c = cadence(interval, unit, at)
    assert c.describe() == words
    assert c.period() == period


def test_runs_land_on_their_times():
    c = cadence(1, "week", WEEKDAYS)
    runs = list(c.runs(datetime(2026, 10, 19), datetime(2026, 10, 26, 23, 59)))
    assert [r.strftime("%a %H:%M") for r in runs] == [
        "Mon 06:00", "Tue 06:00", "Wed 06:00", "Thu 06:00", "Fri 06:00", "Mon 06:00"
    ]  # fmt: skip
    monthly = cadence(3, "month", "15 09:30")
    starts = list(monthly.runs(datetime(2026, 1, 1), datetime(2026, 12, 31)))
    assert [r.month for r in starts] == [1, 4, 7, 10] and {r.day for r in starts} == {15}


@pytest.mark.parametrize(
    ("interval", "unit", "at", "message"),
    [
        (7, "minute", None, "7 doesn't divide 60"),
        (5, "hour", ":00", "5 doesn't divide 24"),
        (2, "week", "mon", "must be 1 for weeks"),
        (1, "minute", ":30", "must be None for minute"),
        (1, "day", "25:00", "no such time of day"),
        (1, "day", 600, "isn't text; write it in quotes"),
        (1, "week", "someday", "isn't one of week's times"),
        (1, "week", "xyz 06:00", "days are mon, tue"),
        (1, "month", "30", "1 to 28"),
        (1, "year", "Feb 29", "no such day in Feb, every year"),
        (1, "day", ["06:00", "06:00"], "the same time twice"),
    ],
)
def test_cadences_that_cant_run_exactly_are_errors(interval, unit, at, message):
    with pytest.raises(CadenceError, match=message):
        cadence(interval, unit, at)


def test_a_schedules_cadence_is_checked_with_the_file():
    schedule = doc(
        "forgegraph_base/base_schedule",
        variable={"cadence.interval": 2, "cadence.interval_unit": "day"},
    )
    assert validate("schedule", schedule, builtin()) == [
        "cadence.interval: must be 1 for days; cron and launchd can't run every 2 days exactly"
    ]
