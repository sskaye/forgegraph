"""Dates and times on either axis: every value placed on an axis (the data, stacks, reference
lines, error bars, limits) is drawn at matplotlib's day number for its date, the same on x as
on y; and what can't be drawn on a date axis is an error."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest
from matplotlib.dates import date2num

import forgegraph as fg
from forgegraph.drawing.axes import numbers
from forgegraph.drawing.layers import ERROR_BAR, REFERENCE
from forgegraph.drawing.marks import VALUE_LABEL, Bars

TIMES = [datetime(2000, 1, 1, 21) + timedelta(minutes=20 * i) for i in range(4)]
DATA = pd.DataFrame({"n": [1.0, 2.0, 3.0, 4.0], "t": TIMES, "g": ["a", "a", "b", "b"]})
DAYS = date2num(TIMES)
AXES = ["x", "y"]  # the axis the dates are on


def graph(
    on: str, layers: dict[str, Any] | None = None, df: pd.DataFrame = DATA, /, **settings: Any
) -> fg.Graph:
    """DATA drawn with its times on axis `on` and its numbers on the other."""
    columns = {"axis.x.data.column": "t", "axis.y.data.column": "n"}
    if on == "y":
        columns = {"axis.x.data.column": "n", "axis.y.data.column": "t"}
    d = fg.graphspec("t", "xy", settings={**columns, "encoding.color.column": None, **settings})
    if layers:
        d["variable_parameters"]["layers"] = layers
    return fg.render(d, df)


def along(on: str, xy: Any) -> np.ndarray:
    """The coordinates along axis `on`."""
    return np.asarray(xy, dtype=float)[:, 0 if on == "x" else 1]


def labels(g: fg.Graph, on: str) -> list[str]:
    axis = g.axes.xaxis if on == "x" else g.axes.yaxis
    return [t.get_text() for t in axis.get_ticklabels() if t.get_text()]


def lines(g: fg.Graph, gid: str | None = None) -> list:
    return [ln for ln in g.axes.get_lines() if ln.get_gid() == gid]


# --- the one conversion ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "values",
    [
        pd.Series(TIMES),
        pd.Series(TIMES).dt.tz_localize("Europe/Berlin"),  # at the times its clocks show
        np.array(TIMES, dtype="datetime64[ns]"),
        np.array(TIMES, dtype=object),
        pd.DatetimeIndex(TIMES),
    ],
)
def test_dates_become_day_numbers_however_they_come(values):
    assert numbers(values) == pytest.approx(DAYS)


def test_numbers_stay_numbers_and_what_isnt_one_is_missing():
    assert numbers([1, 2.5]).tolist() == [1.0, 2.5]
    assert np.isnan(numbers(pd.Series(["a", None]))).all()
    assert np.isnan(numbers(pd.Series([TIMES[0], pd.NaT]))[1])


# --- the data -----------------------------------------------------------------------------------


@pytest.mark.parametrize("on", AXES)
def test_dates_are_drawn_at_their_day_numbers_on_either_axis(on):
    g = graph(on)
    [line] = lines(g)
    assert along(on, line.get_xydata()) == pytest.approx(DAYS)
    assert labels(g, on)[:2] == ["21:00\nJan 1, 2000", "21:30"]  # date ticks, as on x


@pytest.mark.parametrize("on", AXES)
def test_a_date_format_on_either_axis_writes_its_ticks(on):
    g = graph(on, **{f"axis.{on}.tick.label.format": "%H:%M"})
    assert labels(g, on)[:3] == ["21:00", "21:30", "22:00"]


@pytest.mark.parametrize("on", AXES)
def test_aggregated_dates_are_drawn_at_their_day_numbers(on):
    """The mean of a place's times, on the value axis."""
    other = "y" if on == "x" else "x"
    g = graph(on, **{"series.base_axis": other, f"axis.{on}.data.aggregation": "mean"})
    [line] = lines(g)
    assert along(on, line.get_xydata()) == pytest.approx(DAYS)


def test_an_aggregated_date_axis_is_drawn_at_the_dates_mean():
    df = pd.DataFrame({"n": [1.0, 1.0], "t": TIMES[:2], "g": ["a", "a"]})
    g = graph("y", None, df, **{"axis.y.data.aggregation": "mean"})
    [line] = lines(g)
    assert along("y", line.get_xydata()) == pytest.approx([DAYS[:2].mean()])


@pytest.mark.parametrize("on", AXES)
def test_stacks_at_dates_add_up_on_either_base_axis(on):
    """Dates as the places series stack at, along x or y."""
    df = pd.DataFrame({"n": [1.0, 2.0, 3.0, 4.0], "t": TIMES[:2] * 2, "g": ["a", "a", "b", "b"]})
    stacked = {"series.base_axis": on, "series.aggregation": "sum", "encoding.color.column": "g"}
    g = graph(on, None, df, **stacked)
    tops = sorted(along("y" if on == "x" else "x", ln.get_xydata()).tolist() for ln in lines(g))
    assert tops == [[1.0, 2.0], [4.0, 6.0]]
    assert sorted(along(on, lines(g)[0].get_xydata())) == pytest.approx(DAYS[:2])


@pytest.mark.parametrize("fmt", [",.0f", "at noon"])
def test_a_date_axis_takes_only_a_date_format(fmt):
    with pytest.raises(
        fg.SpecError, match=re.escape(f"axis.y.tick.label.format: '{fmt}' isn't a date format")
    ):
        graph("y", **{"axis.y.tick.label.format": fmt})


# --- what a date value axis can't draw ----------------------------------------------------------


@pytest.mark.parametrize("how", ["sum", "percent"])
def test_stacking_dates_is_an_error(how):
    with pytest.raises(
        fg.SpecError, match=re.escape(f"series.aggregation: {how} adds the values, but axis.y is")
    ):
        graph("y", **{"series.aggregation": how})


def test_adding_up_dates_is_an_error():
    with pytest.raises(
        fg.SpecError, match=re.escape("axis.y.data.aggregation: sum adds the values, but axis.y is")
    ):
        graph("y", **{"axis.y.data.aggregation": "sum"})


def test_bars_on_a_date_value_axis_are_an_error():
    with pytest.raises(fg.SpecError, match=re.escape("mark.bar.show: bars start at 0, which")):
        graph("y", **{"mark.bar.show": True})


def test_bars_at_dates_stand_on_their_places():
    g = graph("x", **{"mark.bar.show": True})
    [bars] = [c for c in g.axes.collections if isinstance(c, Bars)]
    assert bars.places == pytest.approx(DAYS)


def test_value_labels_on_a_date_axis_need_a_date_format():
    with pytest.raises(
        fg.SpecError,
        match=re.escape("series.value_label.show: axis.y is dates, so the labels need a date"),
    ):
        graph("y", **{"series.value_label.show": True})


@pytest.mark.parametrize(
    "settings",
    [{"series.value_label.format": "%H:%M"}, {"axis.y.tick.label.format": "%H:%M"}],
)
def test_value_labels_on_a_date_axis_write_dates(settings):
    g = graph("y", **{"series.value_label.show": True, **settings})
    written = [t.get_text() for t in g.axes.texts if t.get_gid() == VALUE_LABEL]
    assert written == ["21:00", "21:20", "21:40", "22:00"]


def test_value_labels_in_a_number_format_on_a_date_axis_are_an_error():
    with pytest.raises(fg.SpecError, match=re.escape("series.value_label.format: '.1f'")):
        graph("y", **{"series.value_label.show": True, "series.value_label.format": ".1f"})


def test_a_date_format_with_value_labels_off_isnt_checked_as_a_number_format():
    """With no value label shown, nothing is written in the value axis's format."""
    graph("y", **{"axis.y.tick.label.format": "%H:%M", "series.value_label.show": False})


# --- reference lines and error bars ----------------------------------------------------------


def _line_at(g: fg.Graph, on: str) -> float:
    [line] = lines(g, REFERENCE)
    [at] = set(along(on, line.get_xydata()).tolist())
    return at


@pytest.mark.parametrize("on", AXES)
@pytest.mark.parametrize(("how", "expected"), [("max", DAYS[-1]), ("mean", DAYS.mean())])
def test_a_reference_line_at_a_date_columns_aggregate(on, how, expected):
    layer = {"type": "reference_line", "axis": on, "value": "t", "aggregation": {"function": how}}
    g = graph(on, {"r": layer})
    assert _line_at(g, on) == pytest.approx(expected)
    low, high = g.axes.get_xlim() if on == "x" else g.axes.get_ylim()
    assert high - low < 1  # the data isn't crushed


@pytest.mark.parametrize("on", AXES)
def test_a_reference_line_at_a_day_number(on):
    g = graph(on, {"r": {"type": "reference_line", "axis": on, "value": float(DAYS[1])}})
    assert _line_at(g, on) == pytest.approx(DAYS[1])


@pytest.mark.parametrize(
    ("layer", "message"),
    [
        (
            {"aggregation": {"function": "sum"}},
            "layers.r.aggregation.function: sum of dates isn't a date",
        ),
        (
            {"aggregation": {"function": "max", "multiplier": 2}},
            "layers.r.aggregation.multiplier: 2 times a date isn't a date",
        ),
    ],
)
def test_aggregates_of_dates_that_arent_dates_are_errors(layer, message):
    full = {"type": "reference_line", "axis": "y", "value": "t", **layer}
    with pytest.raises(fg.SpecError, match=re.escape(message)):
        graph("y", {"r": full})


def test_a_date_column_on_a_number_axis_is_an_error():
    layer = {
        "type": "reference_line",
        "axis": "x",
        "value": "t",
        "aggregation": {"function": "max"},
    }
    with pytest.raises(
        fg.SpecError, match=re.escape("layers.r.value: 't' is dates, but axis.x is decimal")
    ):
        graph("y", {"r": layer})


def test_a_reference_lines_value_on_a_date_axis_is_written_as_a_date():
    layer = {
        "type": "reference_line",
        "axis": "y",
        "value": "t",
        "aggregation": {"function": "max"},
        "label": {"text": "value", "format": "%H:%M"},
    }
    g = graph("y", {"r": layer})
    assert [t.get_text() for t in g.axes.texts if t.get_gid() == REFERENCE] == ["22:00"]


def test_a_reference_lines_value_on_a_date_axis_needs_a_date_format():
    layer = {
        "type": "reference_line",
        "axis": "y",
        "value": "t",
        "aggregation": {"function": "max"},
        "label": {"text": "value"},
    }
    with pytest.raises(fg.SpecError, match=re.escape("layers.r.label.format: auto, but axis.y")):
        graph("y", {"r": layer})


def _ends(g: fg.Graph, on: str) -> list[tuple[float, float]]:
    """Each error bar's low and high end along axis `on`."""
    [stem] = [ln for ln in lines(g, ERROR_BAR) if ln.get_linestyle() != "None"]
    ends = along(on, stem.get_xydata())
    return list(zip(ends[0::3], ends[1::3], strict=True))


@pytest.mark.parametrize("on", AXES)
def test_error_bars_along_a_date_axis_are_days_either_side(on):
    other = "y" if on == "x" else "x"
    layer = {
        "type": "error_bar",
        "axis": on,
        "value": {"lower": 0.5, "upper": 0.25, "aggregation": {"function": "None"}},
    }
    g = graph(on, {"e": layer}, **{"series.base_axis": other})
    assert _ends(g, on) == pytest.approx([(d - 0.5, d + 0.25) for d in DAYS])


@pytest.mark.parametrize("on", AXES)
def test_error_bars_of_a_date_columns_spread_are_in_days(on):
    other = "y" if on == "x" else "x"
    df = pd.DataFrame({"n": [1.0, 1.0, 2.0, 2.0], "t": TIMES, "g": ["a"] * 4})
    layer = {"type": "error_bar", "axis": on}
    aggregated = {"series.base_axis": other, f"axis.{on}.data.aggregation": "mean"}
    g = graph(on, {"e": layer}, df, **aggregated)
    spread = float(np.std(DAYS[:2], ddof=1))
    assert [(hi - lo) / 2 for lo, hi in _ends(g, on)] == pytest.approx([spread, spread])


# --- limits ---------------------------------------------------------------------------------


@pytest.mark.parametrize("on", AXES)
def test_day_number_limits_on_either_date_axis(on):
    low, high = float(DAYS[0]) - 0.1, float(DAYS[-1]) + 0.1
    g = graph(on, **{f"axis.{on}.min": low, f"axis.{on}.max": high})
    assert (g.axes.get_xlim() if on == "x" else g.axes.get_ylim()) == pytest.approx((low, high))
    assert not [i for i in g.issues if i.check == "outside-limits"]


@pytest.mark.parametrize("on", AXES)
def test_lint_counts_dates_outside_a_limit_on_either_axis(on):
    g = graph(on, **{f"axis.{on}.max": float(DAYS[1]) + 0.001})
    [issue] = [i for i in g.issues if i.check == "outside-limits"]
    assert issue.message.startswith(f"2 above axis.{on}.max")
