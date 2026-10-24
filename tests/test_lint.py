"""Lint: one deliberately bad graph per check, and a clean one."""

from __future__ import annotations

import numpy as np
import pandas as pd
from render_helpers import polarization, render

from forgegraph.render.key import keys
from forgegraph.render.lint import MIN_TEXT_PT


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
            "encoding.color": "g",
            "encoding.detail": "None",
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
