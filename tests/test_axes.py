"""Each axis's data and ticks: data types, categories and their order, the tick algorithm per
axis (auto, all, manual with a step), label formats, the theme's label rotation and wrapping,
which axis series are drawn along, and data aggregation (graph_types/xy.yaml axis.*, series.*;
themes axis.tick.label.*)."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import num2date
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator, NullLocator
from pack_helpers import child
from render_helpers import render

import forgegraph as fg
from forgegraph.drawing import spacing
from forgegraph.drawing.axes import LogLabels
from forgegraph.drawing.layout import texts_of, tick_marks
from forgegraph.drawing.limits import inside, outside
from forgegraph.drawing.ticks import ALGORITHMS, _Between
from forgegraph.spec.registry import builtin


def graph(df: pd.DataFrame, x: str, y: str | list[str], **parameters) -> fg.Graph:
    return fg.xy(df, x, y, parameters=parameters)


def ticks(g: fg.Graph, name: str = "x") -> list[float]:
    axis = g.axes.xaxis if name == "x" else g.axes.yaxis
    lo, hi = sorted(axis.get_view_interval())
    return [float(v) for v in axis.get_majorticklocs() if lo - 1e-9 <= v <= hi + 1e-9]


def labels(g: fg.Graph, name: str = "x") -> list[str]:
    axis = g.axes.xaxis if name == "x" else g.axes.yaxis
    lo, hi = sorted(axis.get_view_interval())
    return [
        t.label1.get_text()
        for t in axis.get_major_ticks()
        if lo - 1e-9 <= t.get_loc() <= hi + 1e-9 and t.label1.get_text()
    ]


MONTHS = pd.DataFrame({"month": list(range(1, 13)), "passengers": np.linspace(300, 500, 12)})
SAMPLES = pd.DataFrame(
    {
        "sample": ["Run 10", "Run 2", "Run 1", "Run 2", "Run 10", "Run 1"],
        "rate": [5.0, 7.0, 1.0, 9.0, 3.0, 2.0],
        "state": ["a", "a", "a", "b", "b", "b"],
    }
)


# --- types -------------------------------------------------------------------------------------


def test_an_integer_column_gets_whole_number_ticks():
    g = graph(MONTHS, "month", "passengers")
    assert all(v.is_integer() for v in ticks(g))  # never 2.5, 7.5


def test_a_decimal_column_of_whole_numbers_can_be_made_integer():
    df = MONTHS.assign(month=MONTHS["month"].astype(float))
    assert all(
        v.is_integer()
        for v in ticks(graph(df, "month", "passengers", **{"axis.x.data.type": "integer"}))
    )


def test_integer_on_fractions_is_an_error():
    df = MONTHS.assign(month=MONTHS["month"] + 0.5)
    with pytest.raises(fg.SpecError, match="integer, but 'month' has values that aren't whole"):
        graph(df, "month", "passengers", **{"axis.x.data.type": "integer"})


def test_a_text_column_is_categorical():
    g = graph(SAMPLES, "sample", "rate", **{"mark.line.show": False})
    assert labels(g) == ["Run 10", "Run 2", "Run 1"]  # as first seen
    assert ticks(g) == [0, 1, 2] or ticks(g) == [0, 2]  # the theme's algorithm, whole steps
    assert g.axes.get_xlim() == (-0.5, 2.5)


def test_numbers_can_be_categorical():
    g = graph(
        MONTHS,
        "month",
        "passengers",
        **{"axis.x.data.type": "categorical", "axis.x.tick.algorithm": "all"},
    )
    assert labels(g) == [str(m) for m in range(1, 13)]


def test_category_order():
    def order(method: str, direction: str) -> list[str]:
        return labels(
            graph(
                SAMPLES,
                "sample",
                "rate",
                **{
                    "mark.line.show": False,
                    "axis.x.tick.algorithm": "all",
                    "axis.x.data.order.method": method,
                    "axis.x.data.order.direction": direction,
                },
            )
        )

    assert order("alphanumeric", "ascending") == ["Run 1", "Run 2", "Run 10"]
    assert order("alphanumeric", "descending") == ["Run 10", "Run 2", "Run 1"]
    assert order("source", "descending") == ["Run 1", "Run 2", "Run 10"]
    assert order("value", "ascending") == ["Run 1", "Run 10", "Run 2"]  # totals 3, 8, 16


def test_a_pandas_categorical_keeps_its_own_order():
    df = SAMPLES.assign(
        sample=pd.Categorical(SAMPLES["sample"], ["Run 2", "Run 1", "Run 10", "unused"])
    )
    g = graph(df, "sample", "rate", **{"mark.line.show": False, "axis.x.tick.algorithm": "all"})
    assert labels(g) == ["Run 2", "Run 1", "Run 10"]  # unused levels aren't categories


def test_min_and_max_dont_apply_to_a_categorical_axis():
    with pytest.raises(fg.SpecError, match=re.escape("axis.x.min, max: the axis is categorical")):
        graph(SAMPLES, "sample", "rate", **{"axis.x.min": 0})


# --- ticks -------------------------------------------------------------------------------------


def test_all_puts_a_tick_at_every_value():
    df = pd.DataFrame({"x": [1, 3, 4, 9], "y": [1, 2, 3, 4]})
    assert ticks(graph(df, "x", "y", **{"axis.x.tick.algorithm": "all"})) == [1, 3, 4, 9]


def test_manual_ticks_every_step():
    g = graph(
        MONTHS, "month", "passengers", **{"axis.x.tick.algorithm": "manual", "axis.x.tick.step": 3}
    )
    assert ticks(g) == [3, 6, 9, 12]  # multiples of the step, within the axis


def test_a_log_step_is_a_factor():
    df = pd.DataFrame({"x": [10.0, 50.0, 2000.0, 90000.0], "y": [1, 2, 3, 4]})
    g = graph(
        df,
        "x",
        "y",
        **{"axis.x.scale": "log", "axis.x.tick.algorithm": "manual", "axis.x.tick.step": 100},
    )
    assert ticks(g)[:2] == [10, 1000]


def test_a_date_step_is_a_count_and_a_unit():
    when = pd.date_range("2025-01-01", "2025-12-31", freq="7D")
    df = pd.DataFrame({"when": when, "value": np.arange(len(when))})
    g = graph(
        df,
        "when",
        "value",
        **{
            "axis.x.tick.algorithm": "manual",
            "axis.x.tick.step": "3 month",
            "axis.x.tick.label.format": "%b",
        },
    )
    assert labels(g)[:4] == ["Jan", "Apr", "Jul", "Oct"]  # a format given: no second line


def _dates(start: str, periods: int, freq: str) -> pd.DataFrame:
    when = pd.date_range(start, periods=periods, freq=freq)
    return pd.DataFrame({"when": when, "value": np.arange(periods, dtype=float)})


@pytest.mark.parametrize(
    ("start", "periods", "freq", "expected"),
    [
        ("2026-03-01", 48, "h", ["00:00\nMar 1, 2026", "12:00", "00:00\nMar 2", "12:00"]),
        ("2026-03-01", 40, "D", ["Mar 2\n2026", "Mar 9", "Mar 16", "Mar 23"]),
        ("2026-03-01", 30, "MS", ["Jul\n2026", "Jan\n2027", "Jul", "Jan\n2028"]),
        ("2000-01-01", 30, "YS", ["2000", "2005", "2010", "2015"]),
    ],
)
def test_date_labels_are_at_one_unit_with_the_next_up_where_it_changes(
    start, periods, freq, expected
):
    labels_ = labels(graph(_dates(start, periods, freq), "when", "value"))
    assert labels_[: len(expected)] == expected


def test_date_ticks_are_never_finer_than_the_data():
    df = _dates("2026-07-06", 3, "W-MON")  # three Mondays: room for daily ticks
    assert labels(graph(df, "when", "value")) == ["Jul 6\n2026", "Jul 13", "Jul 20"]


def test_date_ticks_fall_on_calendar_boundaries():
    df = _dates("2026-01-01", 400, "D")
    for v in ticks(graph(df, "when", "value")):
        assert num2date(v).day == 1  # month starts: never the 15th


def test_a_week_step_counts_mondays():
    df = _dates("2026-07-01", 60, "D")
    g = graph(
        df, "when", "value", **{"axis.x.tick.algorithm": "manual", "axis.x.tick.step": "2 week"}
    )
    assert {num2date(v).weekday() for v in ticks(g)} == {0}
    assert labels(g)[:2] == ["Jul 6\n2026", "Jul 20"]


def test_a_tick_at_every_date_is_labelled_at_their_unit():
    df = _dates("2026-01-01", 4, "MS")
    assert labels(graph(df, "when", "value", **{"axis.x.tick.algorithm": "all"})) == [
        "Jan\n2026",
        "Feb",
        "Mar",
        "Apr",
    ]


def test_the_theme_orders_day_and_month():
    df = _dates("2026-03-01", 40, "D")
    reg = builtin().copy()
    order = {"axis.tick.label.date_order": "day_month"}
    theme = child("theme", "forgegraph_base/base_theme", order, name="uk")
    reg.add("theme", theme)
    g = fg.xy(df, "when", "value", theme="uk", registry=reg)
    assert labels(g)[:2] == ["2 Mar\n2026", "9 Mar"]


def test_datetime_is_a_type_for_dates_only():
    df = _dates("2026-03-01", 10, "D")
    assert ticks(graph(df, "when", "value", **{"axis.x.data.type": "datetime"}))
    with pytest.raises(fg.SpecError, match="datetime, but 'value' isn't dates or times"):
        graph(df, "value", "when", **{"axis.x.data.type": "datetime"})
    with pytest.raises(fg.SpecError, match="use auto, datetime or categorical"):
        graph(df, "when", "value", **{"axis.x.data.type": "decimal"})


def test_text_that_reads_as_dates_is_flagged():
    df = pd.DataFrame({"week": ["2026-07-06", "2026-07-13", "2026-07-20"], "n": [1.0, 2, 3]})
    g = graph(df, "week", "n")
    assert [i.check for i in g.issues] == ["dates-as-text"]


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"axis.x.tick.algorithm": "manual"}, "axis.x.tick.algorithm: manual needs tick.step"),
        ({"axis.x.tick.step": 5}, "axis.x.tick.step: applies only with tick.algorithm manual"),
        (
            {"axis.x.tick.algorithm": "manual", "axis.x.tick.step": "3 weeks"},
            "axis.x.tick.step: '3 weeks' isn't a count and a unit",
        ),
    ],
)
def test_tick_step_rules(settings, message):
    with pytest.raises(fg.SpecError, match=re.escape(message)):
        render(settings)


@pytest.mark.parametrize("zone", ["UTC", "Europe/Berlin", "America/New_York"])
def test_times_with_a_time_zone_are_drawn_at_their_own_clock_time(zone):
    """A time zone doesn't move the points: each is drawn at the time its clock shows, as the
    same times without one are."""
    from matplotlib.dates import date2num

    aware = pd.date_range("2026-03-27", periods=72, freq="h", tz=zone)  # Berlin changes on the 29th
    naive = aware.tz_localize(None)  # the times its clocks show
    g = graph(pd.DataFrame({"when": aware, "value": np.arange(72.0)}), "when", "value")
    plain = graph(pd.DataFrame({"when": naive, "value": np.arange(72.0)}), "when", "value")
    [line] = g.axes.get_lines()
    assert np.asarray(line.get_xdata(), dtype=float) == pytest.approx(date2num(naive))
    assert labels(g) == labels(plain)


def test_a_date_step_on_numbers_is_an_error():
    with pytest.raises(fg.SpecError, match="'3 month' is a date step, but this axis isn't dates"):
        render({"axis.x.tick.algorithm": "manual", "axis.x.tick.step": "3 month"})


@pytest.mark.slow
def test_ticks_from_all_are_never_thinned():
    df = pd.DataFrame({"x": np.arange(0, 400, 1.0), "y": np.arange(400.0)})
    with pytest.raises(
        fg.SpecError, match=re.escape("axis.x.tick.algorithm: all gives a tick at every value")
    ):
        graph(df, "x", "y", **{"axis.x.tick.algorithm": "all"})


# --- labels ------------------------------------------------------------------------------------


def test_a_number_format():
    df = pd.DataFrame({"x": [1000, 2000, 3000], "y": [0.1, 0.2, 0.3]})
    g = graph(
        df,
        "x",
        "y",
        **{
            "axis.x.tick.algorithm": "all",
            "axis.x.tick.label.format": ",.0f",
            "axis.y.tick.label.format": ".0%",
        },
    )
    assert labels(g) == ["1,000", "2,000", "3,000"]
    assert all(t.endswith("%") for t in labels(g, "y"))


def test_formats_are_checked():
    with pytest.raises(fg.SpecError, match="'zz' isn't a Python number format"):
        render({"axis.x.tick.label.format": "zz"})
    with pytest.raises(fg.SpecError, match="depends on the computer's locale"):
        render({"axis.x.tick.label.format": ",n"})
    when = pd.date_range("2025-01-01", periods=10, freq="D")
    df = pd.DataFrame({"when": when, "value": np.arange(10)})
    with pytest.raises(fg.SpecError, match="%c isn't one of the date directives"):
        graph(df, "when", "value", **{"axis.x.tick.label.format": "%c"})
    with pytest.raises(fg.SpecError, match="%-M isn't one of the date directives"):
        graph(df, "when", "value", **{"axis.x.tick.label.format": "%-M"})


def test_a_date_format_can_drop_the_leading_zero():
    when = pd.date_range("2025-01-01", periods=10, freq="D")
    df = pd.DataFrame({"when": when, "value": np.arange(10)})
    g = graph(df, "when", "value", **{"axis.x.tick.label.format": "%-m/%-d %-H"})
    assert labels(g) == ["1/2 0", "1/4 0", "1/6 0", "1/8 0", "1/10 0"]  # ticks at midnight


def test_month_names_are_english_whatever_the_locale():
    import locale

    previous = locale.setlocale(locale.LC_TIME)
    try:
        locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")
    except locale.Error:
        pytest.skip("no German locale on this machine")
    try:
        months = pd.date_range("2025-01-01", "2025-12-31", freq="MS")
        df = pd.DataFrame({"when": months, "value": np.arange(len(months))})
        settings = {"axis.x.tick.algorithm": "manual", "axis.x.tick.step": "2 month"}
        g = graph(df, "when", "value", **settings, **{"axis.x.tick.label.format": "%b"})
        assert labels(g) == ["Jan", "Mar", "May", "Jul", "Sep", "Nov"]  # German: Mär, Mai
    finally:
        locale.setlocale(locale.LC_TIME, previous)
    assert locale.setlocale(locale.LC_TIME) == previous


def test_text_categories_take_no_format():
    with pytest.raises(fg.SpecError, match="the categories are text, not numbers"):
        graph(SAMPLES, "sample", "rate", **{"axis.x.tick.label.format": ".1f"})


def test_long_category_labels_wrap():
    names = ["North field", "South field", "East field", "West field", "Upper field", "Lower field"]
    df = pd.DataFrame({"site": names, "value": np.arange(6.0)})
    g = graph(df, "site", "value", **{"mark.line.show": False, "axis.x.tick.algorithm": "all"})
    assert all("\n" in t for t in labels(g))


MEMBRANES = pd.DataFrame(
    {
        "membrane": ["Thick membrane", "Thin membrane", "Reinforced membrane", "Benchmark"],
        "value": np.arange(4.0),
    }
)


def membranes(**theme) -> fg.Graph:
    """Four long category names on a narrow figure, unwrapped."""
    settings = {
        "axis.x.data.column": "membrane",
        "axis.y.data.column": "value",
        "encoding.color.column": None,
        "encoding.detail.column": None,
        "benchmark.data_column": None,
        "benchmark.value": None,
        "mark.line.show": False,
    }
    theme = {"axis.tick.label.max_wrap": 0, **theme}
    return render(settings, theme=theme, format={"figure.width": 90}, data=MEMBRANES)


def test_labels_from_any_algorithm_that_run_together_are_an_error():
    with pytest.raises(fg.SpecError, match="auto gives ticks from the theme's algorithm, but"):
        membranes()


def test_rotated_labels_are_clear_when_they_dont_touch():
    g = membranes(**{"axis.tick.label.x_rotation": 45})  # their upright boxes would overlap
    assert labels(g) == list(MEMBRANES["membrane"])


def test_the_theme_can_rotate_x_tick_labels():
    g = render(theme={"axis.tick.label.x_rotation": 45})
    assert all(t.get_rotation() == 45 for t in g.axes.get_xticklabels() if t.get_text())


# --- series ------------------------------------------------------------------------------------


def test_series_can_be_drawn_along_y():
    df = pd.DataFrame({"depth": [0.0, 1.0, 2.0, 3.0], "temp": [20.0, 18.0, 15.0, 14.0]})
    g = graph(df, "temp", "depth", **{"series.base_axis": "y"})
    [line] = g.axes.get_lines()
    assert np.asarray(line.get_xdata()).tolist() == [
        20.0,
        18.0,
        15.0,
        14.0,
    ]  # joined in depth order
    assert np.asarray(line.get_ydata()).tolist() == [0.0, 1.0, 2.0, 3.0]


def test_the_base_axis_takes_one_column():
    with pytest.raises(
        fg.SpecError, match=re.escape("axis.y.data.column: series are drawn along y")
    ):
        render(
            {
                "series.base_axis": "y",
                "axis.y.data.column": ["cell_voltage", "temperature"],
                "axis.y.title": "Values",
            }
        )


def test_aggregation_draws_one_point_per_place():
    df = pd.DataFrame({"x": [1, 1, 1, 2, 2], "y": [1.0, 2.0, 3.0, 10.0, 20.0]})
    g = graph(df, "x", "y", **{"axis.y.data.aggregation": "mean"})
    [line] = g.axes.get_lines()
    assert np.asarray(line.get_ydata()).tolist() == [2.0, 15.0]


def test_the_base_axis_isnt_aggregated():
    with pytest.raises(
        fg.SpecError, match=re.escape("axis.x.data.aggregation: series are drawn along x")
    ):
        render({"axis.x.data.aggregation": "mean"})


@pytest.mark.parametrize(("side", "at"), [("start", 0), ("end", -1)])
def test_the_benchmark_keeps_its_side_whatever_the_order(side, at):
    for direction in ("ascending", "descending"):
        g = render(
            {
                "axis.x.data.column": "cell",
                "axis.y.data.column": "cell_voltage",
                "axis.y.data.aggregation": "max",
                "axis.x.tick.algorithm": "all",
                "axis.x.data.order.direction": direction,
                "encoding.color.column": None,
                "encoding.detail.column": None,
                "mark.line.show": False,
                "benchmark.side": side,
            }
        )
        assert labels(g)[at] == "Benchmark"


# --- the tick algorithms, remembered -------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ALGORITHMS))
def test_a_tick_algorithm_remembers_what_it_found(name):
    """A render asks for the same ticks many times; the answer is worked out once, and is
    the same as working it out afresh, whatever the caller does with it."""
    algorithm: Any = ALGORITHMS[name]
    algorithm.cache_clear()
    rng = np.random.default_rng(0)
    for _ in range(200):
        lo = float(rng.uniform(-100, 100))
        hi = lo + float(rng.choice([0.01, 0.7, 13.0, 2e5]))
        m, integer = int(rng.integers(2, 11)), bool(rng.integers(0, 2))
        try:
            expected = algorithm.__wrapped__(lo, hi, m, integer=integer)
        except ValueError:  # an algorithm with no answer here has none remembered either
            with pytest.raises(ValueError):
                algorithm(lo, hi, m, integer=integer)
            continue
        first = algorithm(lo, hi, m, integer=integer)
        assert np.array_equal(first, expected)
        first[:] = -1  # a caller changing its copy
        assert np.array_equal(algorithm(lo, hi, m, integer=integer), expected)
    assert algorithm.cache_info().hits >= algorithm.cache_info().currsize > 0
    assert np.array_equal(algorithm(np.float64(0.0), np.float64(1.0), 5), algorithm(0.0, 1.0, 5))


# --- values at an axis's limits, and float noise ------------------------------------------


def test_a_value_is_past_a_limit_only_by_more_than_float_noise():
    below, above = outside([0, -1e-12, -1e-6, 100.00000000000001, 100.001], 0, 100)
    assert below.tolist() == [False, False, True, False, False]
    assert above.tolist() == [False, False, False, False, True]
    assert inside([0, -1e-12, -1e-6, 100.00000000000001, 100.001], 100, 0).tolist() == [
        True,
        True,
        False,
        True,
        False,
    ]
    # on a log axis, measured in powers of ten; 0 and below are below any limit
    below, above = outside(
        [1e-3 * (1 - 1e-15), 0.9e-3, 0, -1, 1e5 * (1 + 1e-15)], 1e-3, 1e5, log=True
    )
    assert below.tolist() == [False, True, True, True, False]
    assert not above.any()


def _bare() -> tuple[Figure, Axes]:
    fig = Figure()
    ax = fig.add_subplot()
    ax.xaxis.set_major_locator(NullLocator())
    return fig, ax


def test_a_tick_at_an_end_but_for_float_noise_is_in_view():
    """matplotlib draws a tick a hair past the end of the view, so layout measures it."""
    fig, ax = _bare()
    ax.set_ylim(0, 0.3)
    ax.yaxis.set_major_locator(FixedLocator([0, 0.1, 0.2, 0.1 + 0.2]))  # 0.30000000000000004
    fig.draw_without_rendering()
    last = ax.yaxis.get_major_ticks()[3]
    assert last.get_loc() > 0.3
    assert len(spacing._in_view(ax.yaxis)) == 4
    assert last.label1 in texts_of(ax)
    assert len(tick_marks(ax, FigureCanvasAgg(fig).get_renderer())) == 4


def test_log_labels_count_a_tick_at_an_end_but_for_float_noise():
    _, ax = _bare()
    ax.set_yscale("log")
    ax.set_ylim(0.1, 1e5 * (1 - 1e-15))
    formatter = LogLabels()
    ax.yaxis.set_major_formatter(formatter)
    formatter.set_locs([0.1, 1, 10, 100, 1e3, 1e4, 1e5])
    assert formatter(10) == "$10^{1}$"  # 1e5 is drawn too, so every label is a power of ten


def test_a_minor_tick_at_an_end_but_for_float_noise_is_kept():
    _, ax = _bare()
    ax.set_ylim(0, 0.15)
    ax.yaxis.set_major_locator(FixedLocator([0, 0.1]))
    between = _Between(1)
    ax.yaxis.set_minor_locator(between)
    assert between() == pytest.approx([0.05, 0.15])  # 0.15000000000000002


def test_a_tick_length_of_0_draws_labels_without_marks():
    from render_helpers import render

    g = render(theme={"axis.tick.length": 0})
    g.figure.canvas.draw()
    tick = g.axes.xaxis.get_major_ticks()[0]
    assert tick.tick1line.get_markersize() == 0
    label = g.axes.xaxis.get_ticklabels()[1].get_window_extent()
    gap = g.style.pt("axis.tick.label.gap") * g.figure.dpi / 72
    letters = label.y1  # the label's box top; its letters sit a little lower
    assert g.axes.bbox.y0 - letters <= gap + 1  # no room kept for a mark
