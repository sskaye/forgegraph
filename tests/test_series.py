"""The series a GraphSpec lists (graphtype_xy.yaml series): each drawn from its own column,
with its own settings, and its own look, the theme with what it sets for itself."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_hex
from matplotlib.lines import Line2D

import forgegraph as fg
from forgegraph.drawing.key import KEY, keys
from forgegraph.drawing.marks import VALUE_LABEL, Bars
from forgegraph.drawing.style import Style

TWO = pd.DataFrame(
    {
        "t": [1.0, 2.0, 3.0, 4.0],
        "a": [1.0, 3.0, 2.0, 4.0],
        "b": [6.0, 5.0, 7.0, 6.0],
        "g": ["p", "p", "q", "q"],
    }
)


def graph(series: dict[str, Any], df: pd.DataFrame = TWO, /, **settings: Any) -> fg.Graph:
    """df drawn along t, with these series, each by name."""
    titled = {"axis.y.title": "Value", "legend.key.title.text": "None"}
    doc = fg.graphspec(
        "t", "xy", settings={"axis.x.data.column": "t", "series": series, **titled, **settings}
    )
    return fg.render(doc, df)


def drawn(g: fg.Graph) -> list[Line2D]:
    return [ln for ln in g.axes.get_lines() if ln.get_gid() != KEY]


# --- what each series draws -----------------------------------------------------------------


def test_a_series_draws_its_named_column_or_the_column_it_sets():
    g = graph({"a": {}, "Second": {"column": "b"}}, **{"legend.method": "key"})
    first, second = drawn(g)
    assert np.asarray(first.get_ydata()).tolist() == [1.0, 3.0, 2.0, 4.0]
    assert np.asarray(second.get_ydata()).tolist() == [6.0, 5.0, 7.0, 6.0]
    [key] = keys(g.axes)
    assert [e.name for e in key.entries] == ["a", "Second"]  # each under its own name


def test_a_series_with_no_column_of_its_name_is_an_error():
    message = "series.c.column: no column 'c' in the data (column: name, the series' name)"
    with pytest.raises(fg.SpecError, match=re.escape(message)):
        graph({"c": {}})


def test_series_take_the_palettes_colors_in_order_or_their_own():
    g = graph({"a": {}, "b": {"color": "#123456"}})
    palette = Style(g.values["theme"], g.values["format"]).series_colors()
    assert [to_hex(ln.get_color()) for ln in drawn(g)] == [palette[0].lower(), "#123456"]
    g = graph({"b": {}, "a": {}})  # listed the other way round
    assert [to_hex(ln.get_color()) for ln in drawn(g)] == [p.lower() for p in palette[:2]]


def test_a_named_line_style_shape_and_fill_apply_to_the_series():
    g = graph({"a": {"line": {"style": "dashed"}, "marker": {"shape": "square", "fill": "open"}}})
    [line] = drawn(g)
    assert line.get_linestyle() == "--" and line.get_marker() == "s"
    assert line.get_markerfacecolor() == "none"


def test_line_styles_by_series_with_colors_from_a_column_get_a_style_key():
    g = graph(
        {"a": {"color": "g", "line": {"style": "series"}}, "b": {"color": "g"}},
        **{"legend.method": "key", "legend.key.title.text": "column_name"},
    )
    style_keys = [k for k in keys(g.axes) if k.title is None]  # the series have no column
    [series_key] = style_keys
    assert [e.name for e in series_key.entries] == ["a"]
    assert g.style_keys == ["series"]


def test_each_series_shows_its_own_marks():
    shown = {"a": {"bar": {"show": True}, "line": {"show": False}}, "b": {}}
    g = graph(shown, **{"legend.key.inside": False})
    [bars] = [c for c in g.axes.collections if isinstance(c, Bars)]
    assert bars.top.tolist() == [1.0, 3.0, 2.0, 4.0]  # a's bars only
    a, b = drawn(g)
    assert a.get_linestyle() == "None" and b.get_linestyle() == "-"


def test_each_series_writes_its_own_value_labels():
    g = graph({"a": {"value_label": {"show": True, "format": ".1f"}}, "b": {}})
    written = sorted(t.get_text() for t in g.axes.texts if t.get_gid() == VALUE_LABEL)
    assert written == ["1.0", "2.0", "3.0", "4.0"]


def test_a_series_split_by_a_column_draws_a_line_per_value():
    g = graph({"a": {"split": "g"}, "b": {}})
    assert [len(np.asarray(ln.get_xdata())) for ln in drawn(g)] == [2, 2, 4]


def test_missing_values_break_only_the_series_that_asks():
    df = TWO.assign(a=[1.0, np.nan, 2.0, 4.0], b=[6.0, np.nan, 7.0, 6.0])
    g = graph({"a": {"line": {"missing_values": "gap"}}, "b": {}}, df)
    a, b = drawn(g)
    assert np.isnan(np.asarray(a.get_ydata(), dtype=float)).sum() == 1  # the line breaks there
    assert len(np.asarray(b.get_ydata())) == 3  # joined across it


def test_colors_on_two_scales_are_an_error():
    df = TWO.assign(n=[1, 2, 3, 4], m=[4, 3, 2, 1])
    with pytest.raises(fg.SpecError, match="a graph has one color bar"):
        graph({"a": {"color": "n"}, "b": {"color": "m"}}, df)


# --- aggregation ----------------------------------------------------------------------------

ROWS = pd.DataFrame({"t": [1.0, 1.0, 1.0, 2.0, 2.0, 2.0], "a": [1.0, 2.0, 6.0, 4.0, 4.0, 10.0]})


@pytest.mark.parametrize(
    ("aggregation", "expected"),
    [
        ({"function": "mean"}, [3.0, 6.0]),
        ({"function": "median", "multiplier": 2}, [4.0, 8.0]),
        ({"function": "percentile", "percentile": 100}, [6.0, 10.0]),
        (
            {"function": "stddev"},
            [float(np.std([1, 2, 6], ddof=1)), float(np.std([4, 4, 10], ddof=1))],
        ),
        ({"function": "sum"}, [9.0, 18.0]),
    ],
)
def test_a_series_aggregation_combines_the_rows_at_each_place(aggregation, expected):
    [line] = drawn(graph({"a": {"aggregation": aggregation}}, ROWS))
    assert np.asarray(line.get_ydata()).tolist() == pytest.approx(expected)


def test_each_series_aggregates_its_own_way():
    df = ROWS.assign(b=ROWS["a"])
    g = graph(
        {"a": {"aggregation": {"function": "max"}}, "b": {"aggregation": {"function": "min"}}}, df
    )
    assert [np.asarray(ln.get_ydata()).tolist() for ln in drawn(g)] == [[6.0, 10.0], [1.0, 4.0]]


# --- interpolation --------------------------------------------------------------------------


def _vertices(how: str) -> tuple[list[float], list[float], Line2D]:
    [line] = drawn(graph({"a": {"line": {"interpolate": how}}}))
    xs = np.asarray(line.get_xdata(), dtype=float).tolist()
    ys = np.asarray(line.get_ydata(), dtype=float).tolist()
    return xs, ys, line


def test_step_after_holds_each_value_until_the_next_point():
    xs, ys, line = _vertices("step_after")
    assert xs == [1, 2, 2, 3, 3, 4, 4] and ys == [1, 1, 3, 3, 2, 2, 4]
    assert line.get_markevery() == [0, 2, 4, 6]  # markers only at the points


def test_step_before_takes_the_next_value_at_once():
    xs, ys, _ = _vertices("step_before")
    assert xs == [1, 1, 2, 2, 3, 3, 4] and ys == [1, 3, 3, 2, 2, 4, 4]


def test_step_center_steps_midway():
    xs, ys, _ = _vertices("step_center")
    assert xs == [1, 1.5, 1.5, 2, 2.5, 2.5, 3, 3.5, 3.5, 4]
    assert ys == [1, 1, 3, 3, 3, 2, 2, 2, 4, 4]


def test_a_smooth_line_runs_through_the_points_without_overshooting():
    xs, ys, line = _vertices("smooth")
    marked = line.get_markevery()
    assert isinstance(marked, list)
    assert [xs[i] for i in marked] == [1, 2, 3, 4] and [ys[i] for i in marked] == [1, 3, 2, 4]
    assert len(xs) > 4 and min(ys) >= 1 and max(ys) <= 4  # within the points' values


def test_steps_follow_the_base_axis_when_it_is_y():
    df = pd.DataFrame({"depth": [0.0, 1.0, 2.0], "temp": [20.0, 18.0, 15.0]})
    doc = fg.graphspec(
        "t",
        "xy",
        settings={
            "arrangement.base_axis": "y",
            "axis.y.data.column": "depth",
            "series": {"temp": {"line": {"interpolate": "step_after"}}},
        },
    )
    [line] = drawn(fg.render(doc, df))
    assert np.asarray(line.get_ydata()).tolist() == [0, 1, 1, 2, 2]  # steps along depth
    assert np.asarray(line.get_xdata()).tolist() == [20, 20, 18, 18, 15]


def test_a_smooth_line_needs_its_points_in_order():
    df = TWO.assign(t=[1.0, 3.0, 2.0, 4.0])
    series = {"a": {"line": {"interpolate": "smooth", "connect_order": "data"}}}
    with pytest.raises(fg.SpecError, match=re.escape("series.a.line.interpolate: smooth needs")):
        graph(series, df)


# --- each series' look ------------------------------------------------------------------------


def test_a_series_sets_the_themes_variable_look_for_itself():
    g = graph({"a": {"marker": {"size": 0.9}, "opacity": 0.5}, "b": {}})
    a, b = drawn(g)
    base = Style(g.values["theme"], g.values["format"])
    assert a.get_markersize() == pytest.approx(0.9 * base.base)
    assert b.get_markersize() == pytest.approx(base.pt("series.marker.size"))
    assert a.get_alpha() == 0.5 and b.get_alpha() == 1
    message = "series.a.line.width: fixed by theme 'forgegraph_default/light_theme'"
    with pytest.raises(fg.SpecError, match=re.escape(message)):
        graph({"a": {"line": {"width": 0.5}}})


def test_a_series_cant_set_what_the_theme_fixes():
    doc = fg.graphspec(
        "t", "xy", settings={"axis.x.data.column": "t", "series": {"a": {"colors": "tol_bright"}}}
    )
    with pytest.raises(fg.SpecError, match=re.escape("series.a.colors: unknown parameter")):
        fg.render(doc, TWO)


# --- the benchmark as a series ----------------------------------------------------------------


def test_a_series_can_be_the_benchmark():
    g = graph({"a": {}, "b": {}}, **{"benchmark.data_column": "series", "benchmark.value": "b"})
    a, b = drawn(g)
    theme = Style(g.values["theme"], g.values["format"])
    assert to_hex(b.get_color()) == to_hex(theme.palette("series.benchmark.colors")[0])
    assert b.get_zorder() > a.get_zorder()  # on top
    with pytest.raises(fg.SpecError, match="no series is named 'c'"):
        graph({"a": {}, "b": {}}, **{"benchmark.data_column": "series", "benchmark.value": "c"})


# --- side by side ---------------------------------------------------------------------------


def test_bars_and_markers_side_by_side_are_centred_together():
    df = pd.DataFrame({"t": ["x", "y"], "a": [1.0, 2.0], "b": [2.0, 3.0]})
    bars = {"bar": {"show": True}, "line": {"show": False}, "marker": {"show": False}}
    g = graph(
        {"a": bars, "b": {"line": {"show": False}}},
        df,
        **{"arrangement.offset": "side_by_side", "axis.x.tick.algorithm": "all"},
    )
    g.figure.canvas.draw()
    [b_bars] = [c for c in g.axes.collections if isinstance(c, Bars)]
    rect = sorted(b_bars.rectangles(), key=lambda r: r.x0)[0]
    [markers] = drawn(g)[1:]
    px = markers.get_transform().transform(markers.get_xydata())[0][0]
    assert rect.x1 <= px  # a's bar first, b's marker beside it
    centre = g.axes.transData.transform((0.0, 0.0))[0]
    assert rect.x0 < centre < px  # the two centred on the place


# --- the Python API ---------------------------------------------------------------------------


def test_xy_sets_a_series_parameter_on_every_series():
    titled = {"axis.y.title": "V", "legend.key.title.text": None}
    g = fg.xy(TWO, "t", ["a", "b"], parameters={"series.line.show": False, **titled})
    assert [ln.get_linestyle() for ln in drawn(g)] == ["None", "None"]


def test_xy_reports_a_series_path_no_series_has():
    with pytest.raises(fg.SpecError, match=re.escape("series.nope: must be a series")):
        fg.xy(TWO, "t", "a", parameters={"series.nope": 1})
