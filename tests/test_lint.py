"""Lint: one deliberately bad graph per check, and a clean one."""

from __future__ import annotations

from typing import Any

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from render_helpers import polarization, render

import forgegraph as fg
from forgegraph.drawing.key import keys
from forgegraph.drawing.lint import MIN_TEXT_PT


def _clean_data() -> pd.DataFrame:
    frame = polarization()
    return frame.dropna(subset=["current_density", "cell_voltage"])


def checks(graph) -> list[str]:
    return [i.check for i in graph.issues]


def test_a_clean_graph_has_no_issues():
    assert render(data=_clean_data()).issues == []


def test_overlapping_text():
    g = render(data=_clean_data(), title="Polarization")
    title = g.axes.title
    g.axes.text(*title.get_position(), "Polarization", transform=title.get_transform())  # on it
    g.check()
    assert "overlapping-text" in checks(g)


def test_clipped_text():
    g = render(data=_clean_data())
    g.figure.text(0.98, 0.5, "A note running off the edge")
    g.check()
    assert "clipped-text" in checks(g)


def test_key_over_data():
    g = render({"legend.method": "key"}, data=_clean_data())
    assert "key-over-data" not in checks(g)  # placed clear of the data
    [key] = keys(g.axes)
    box = key.bbox().transformed(g.axes.transData.inverted())
    g.axes.plot([box.x0, box.x1], [box.y0, box.y1])  # a line drawn across it afterwards
    g.check()
    assert "key-over-data" in checks(g)


def test_too_many_groups():
    frame = pd.DataFrame(
        {
            "x": np.tile(np.arange(5.0), 12),
            "y": np.repeat(np.arange(12.0) * 3, 5),
            "g": np.repeat(list("abcdefghijkl"), 5),
        }
    )
    g = render(
        {
            "axis.x.data.column": "x",
            "axis.y.data.column": "y",
            "encoding.color.column": "g",
            "encoding.detail.column": "None",
            "benchmark.data_column": "None",
            "benchmark.value": "None",
            "legend.method": "none",
        },
        theme={"legend.methods": ["auto", "direct", "key", "none"]},
        data=frame,
    )
    [issue] = [i for i in g.issues if i.check == "too-many-groups"]
    assert "12 groups but 7 colors" in issue.message


def test_log_axis_values():
    g = render({"axis.y.scale": "log"}, data=_clean_data())
    assert "log-axis-values" not in checks(g)
    g.axes.plot([10, 20], [-1, 1.2])  # drawn on afterwards
    g.check()
    assert "log-axis-values" in checks(g)


def test_outside_limits():
    g = render({"axis.x.max": 50}, data=_clean_data())
    [issue] = [i for i in g.issues if i.check == "outside-limits"]
    assert "above axis.x.max" in issue.message


def test_small_text():
    g = render(format={"figure.base_size": 5}, data=_clean_data())
    [issue] = [i for i in g.issues if i.check == "small-text"]
    assert f"smaller than {MIN_TEXT_PT:g} pt" in issue.message


def test_font_fallback():
    g = render(data=_clean_data(), title="Polarization ✈")  # not a letter Roboto has
    [issue] = [i for i in g.issues if i.check == "font-fallback"]
    assert "✈" in issue.message


def test_dropped_rows():
    g = render()  # the example data has one missing reading
    [issue] = [i for i in g.issues if i.check == "dropped-rows"]
    assert issue.message == "1 row left out: missing x or y"


def test_a_key_over_markers_is_found_without_testing_points_one_by_one(monkeypatch):
    """The key-over-data check tests a line's markers against the key all at once."""
    from matplotlib.transforms import BboxBase

    from forgegraph.drawing import lint

    g = render({"legend.method": "key"}, data=_clean_data())
    [key] = keys(g.axes)
    box = key.bbox()
    to_data = g.axes.transData.inverted()

    def marker_at(x: float, y: float):
        ((px, py),) = to_data.transform([(x, y)])
        return g.axes.plot([px], [py], linestyle="none", marker="o")[0]

    tested = []
    contains = BboxBase.contains
    monkeypatch.setattr(
        BboxBase, "contains", lambda self, x, y: tested.append(1) or contains(self, x, y)
    )
    covered = marker_at((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
    assert [i.check for i in lint._key_over_data(g.axes)] == ["key-over-data"]
    covered.remove()
    marker_at(box.x1 + 3 * box.width, box.y1 + 3 * box.height)
    assert lint._key_over_data(g.axes) == []
    assert tested == []


# --- outside-limits: what counts as a point --------------------------------------------------

POINTS = pd.DataFrame({"x": [10, 20, 30, 40], "y": [1, 3, 2, 4]})
ACROSS = {"t": {"type": "reference_line", "axis": "y", "value": 3.5}}


def _layered(listed: dict[str, Any], data: pd.DataFrame = POINTS, /, **settings: Any) -> fg.Graph:
    doc = fg.graphspec(
        "t", "xy", settings={"axis.x.data.column": "x", "axis.y.data.column": "y", **settings}
    )
    doc["parameters"]["layers"] = listed
    return fg.render(doc, data)


def _outside(g: fg.Graph) -> list[str]:
    return [i.message for i in g.issues if i.check == "outside-limits"]


def test_a_reference_lines_ends_arent_points():
    assert _outside(_layered(ACROSS, **{"axis.x.min": 5, "axis.x.max": 45})) == []
    down = {"t": {"type": "reference_line", "axis": "x", "value": 25}}
    assert _outside(_layered(down, **{"axis.y.min": 1.5, "axis.y.max": 5})) == [
        "1 below axis.y.min: those points aren't drawn"
    ]


def test_a_reference_line_on_a_date_axis_isnt_points():
    days = POINTS.assign(x=pd.date_range("2025-08-25", periods=4, freq="D"))
    start, end = (float(mdates.date2num(pd.Timestamp(d))) for d in ("2025-08-24", "2025-08-29"))
    assert _outside(_layered(ACROSS, days, **{"axis.x.min": start, "axis.x.max": end})) == []


def test_an_error_bar_past_a_limit_isnt_points():
    one = {"lower": 1, "upper": 1, "aggregation": {"function": "None"}}
    bars = {"e": {"type": "error_bar", "value": one}}
    assert _outside(_layered(bars, **{"axis.y.min": 0.5, "axis.y.max": 4.5})) == []


def test_a_reference_lines_ends_arent_values_on_a_log_axis():
    assert "log-axis-values" not in checks(_layered(ACROSS, **{"axis.x.scale": "log"}))


def test_a_stack_that_totals_a_limit_but_for_float_noise_isnt_past_it():
    counts, n = [3, 30, 156, 8, 4], 201
    shares = [100 * c / n for c in counts]
    assert np.cumsum(shares)[-1] > 100  # 100.00000000000001
    frame = pd.DataFrame({"week": ["a"] * 5, "band": list("ABCDE"), "pct": shares})
    settings = {
        "axis.x.data.column": "week",
        "axis.y.data.column": "pct",
        "axis.y.min": 0,
        "axis.y.max": 100,
        "encoding.color.column": "band",
        "encoding.order": "data",
        "series.aggregation": "sum",
        "legend.method": "key",
        "legend.key.inside": False,
        "legend.key.positions": ["right_top"],
        "mark.bar.show": True,
        "mark.line.show": False,
        "mark.marker.show": False,
    }
    assert _outside(fg.render(fg.graphspec("t", "xy", settings=settings), frame)) == []


def test_a_point_just_past_a_limit_is_outside_it():
    assert _outside(_layered({}, **{"axis.y.max": 3.999})) == [
        "1 above axis.y.max: those points aren't drawn"
    ]
    assert _outside(_layered({}, **{"axis.y.scale": "log", "axis.y.min": 1.001})) == [
        "1 below axis.y.min: those points aren't drawn"
    ]
