"""Readouts (drawing/readout.py): the values an HTML page shows on each data point, and the
page's script that finds the point under the pointer."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from pack_helpers import needs_node
from render_helpers import with_series

import forgegraph as fg
from forgegraph import graph as graph_module
from forgegraph.drawing.layers import spread_words
from forgegraph.drawing.page import _READOUT_SCRIPT, READOUTS
from forgegraph.drawing.readout import MINUS, marks, with_error

ADDITIVES = pd.DataFrame(
    {
        "Additive": ["MgO"] * 3 + ["TiO2"] * 3,
        "1100 °C": [6.0, 6.4, 6.8, 7.0, 7.2, 7.4],
        "1300 °C": [7.6, 7.8, 8.0, 8.1, 8.2, 8.3],
    }
)


def graph(df: pd.DataFrame, x: str, y: str | list[str], **settings: Any) -> fg.Graph:
    layers = settings.pop("layers", None)
    d = fg.graphspec(
        "t",
        "xy",
        settings=with_series({"axis.x.data.column": x, "axis.y.data.column": y, **settings}),
    )
    if layers:
        d["parameters"]["layers"] = layers
    return fg.render(d, df)


def readouts(g: fg.Graph, folder: Path) -> list[dict[str, Any]]:
    """Every figure's readout data on the graph's HTML page."""
    [page] = g._write(folder / "g", ["html"])
    text = page.read_text(encoding="utf-8")
    return [json.loads(m) for m in re.findall(rf'class="{READOUTS}">(.*?)</script>', text, re.S)]


def lines(data: dict[str, Any]) -> list[list[tuple[str, str]]]:
    """Each mark's lines, its names looked up."""
    names = data["names"]
    return [[(names[n] if n >= 0 else "", v) for n, v in m[6]] for m in data["marks"]]


# --- what a point reads out ------------------------------------------------------------------


def test_each_point_reads_out_its_category_value_error_and_series(tmp_path):
    g = graph(
        ADDITIVES,
        "Additive",
        ["1100 °C", "1300 °C"],
        **{
            "axis.y.title": "Hardness (GPa)",
            "legend.key.title.text": "Fired at",
            "arrangement.offset": "side_by_side",
            "series.aggregation.function": "mean",
            "series.line.show": False,
        },
        layers={"ci": {"type": "error_bar", "value": {"aggregation": {"function": "ci"}}}},
    )
    [data] = readouts(g, tmp_path)
    assert lines(data) == [
        [("Additive", "MgO"), ("Hardness (GPa)", "6 ± 1 (95%CI)"), ("Fired at", "1100 °C")],
        [("Additive", "TiO2"), ("Hardness (GPa)", "7.2 ± 0.5 (95%CI)"), ("Fired at", "1100 °C")],
        [("Additive", "MgO"), ("Hardness (GPa)", "7.8 ± 0.5 (95%CI)"), ("Fired at", "1300 °C")],
        [("Additive", "TiO2"), ("Hardness (GPa)", "8.2 ± 0.2 (95%CI)"), ("Fired at", "1300 °C")],
    ]
    blue, orange = (data["rings"][m[4]] for m in (data["marks"][0], data["marks"][2]))
    assert blue != orange
    first, side = data["marks"][0], data["marks"][2]
    assert first[0] < side[0]  # side by side: the second series is to the right
    assert first[2] > 0 and first[3] is None  # a marker's radius, and no box
    [look] = data["looks"]
    assert look["family"] == "Roboto" and look["weight"] == 400 and look["size"] > 0


def test_a_value_without_an_error_bar_has_a_decimal_more_than_the_tick_labels(
    tmp_path, monkeypatch
):
    df = pd.DataFrame({"t": [0.0, 1.0, 2.0], "v": [0.7234, 0.7111, 0.6987]})
    g = graph(df, "t", "v")
    ticks: list[str] = []

    def saved(fig: Any) -> list[Any]:  # the tick labels as the page's image has them
        ticks.extend(t.get_text() for t in fig.axes[0].get_yticklabels())
        return marks(fig)

    monkeypatch.setattr(graph_module, "marks", saved)
    [data] = readouts(g, tmp_path)
    places = max(len(t.split(".")[1]) for t in ticks if "." in t)
    assert lines(data)[0][1] == ("v", f"{0.7234:.{places + 1}f}")
    assert len(lines(data)) == 3  # a line's points, each once
    assert all(m[2] > 0 for m in data["marks"])  # markers shown by default


def test_a_set_value_label_format_is_used_as_it_is(tmp_path):
    df = pd.DataFrame({"t": [0.0, 1.0], "v": [0.72345, 0.7111]})
    g = graph(df, "t", "v", **{"series.value_label.format": ".3f"})
    [data] = readouts(g, tmp_path)
    assert lines(data)[0][1] == ("v", "0.723")


def test_a_line_without_markers_reads_out_its_points(tmp_path):
    df = pd.DataFrame({"t": [0.0, 1.0, 2.0], "v": [1.0, 2.0, 1.5]})
    g = graph(df, "t", "v", **{"series.marker.show": False})
    [data] = readouts(g, tmp_path)
    assert len(data["marks"]) == 3
    assert all(m[2] == 0 for m in data["marks"])


def test_stacked_bars_read_out_their_own_value_in_their_box(tmp_path):
    df = pd.DataFrame({"week": ["w1", "w2"], "a": [3.0, 4.0], "b": [5.0, 6.0]})
    g = graph(
        df,
        "week",
        ["a", "b"],
        **{
            "arrangement.stacking": "sum",
            "series.bar.show": True,
            "series.line.show": False,
            "series.marker.show": False,
            "series.value_label.format": ".0f",
            "legend.key.title.text": None,
            "axis.y.title": "Count",
        },
    )
    [data] = readouts(g, tmp_path)
    assert [m[6][1][1] for m in data["marks"]] == ["3", "4", "5", "6"]  # not the stacks' tops
    assert [line[2] for line in lines(data)] == [("", "a"), ("", "a"), ("", "b"), ("", "b")]
    for m in data["marks"]:
        left, top, right, bottom = m[3]
        assert 0 <= left < right <= 1 and 0 <= top < bottom <= 1
        assert left < m[0] < right and top < m[1] < bottom


def test_a_color_column_reads_out_under_the_keys_title_or_its_name(tmp_path):
    df = pd.DataFrame(
        {"t": [0.0, 1.0, 0.0, 1.0], "v": [1.0, 2.0, 3.0, 4.0], "cell": ["A", "A", "B", "B"]}
    )
    g = graph(df, "t", "v", **{"series.color": "cell", "series.marker.shape": "cell"})
    [data] = readouts(g, tmp_path)
    assert [line[2:] for line in lines(data)] == [[("cell", "A")]] * 2 + [[("cell", "B")]] * 2
    titled = graph(df, "t", "v", **{"series.color": "cell", "legend.key.title.text": "Cell"})
    assert lines(readouts(titled, tmp_path)[0])[0][2] == ("Cell", "A")


def test_one_series_has_no_series_line(tmp_path):
    df = pd.DataFrame({"t": [0.0, 1.0], "v": [1.0, 2.0]})
    assert [len(line) for line in lines(readouts(graph(df, "t", "v"), tmp_path)[0])] == [2, 2]


def test_titles_are_html_with_their_markup(tmp_path):
    df = pd.DataFrame({"t": [0.0, 1.0], "v <x>": [1.0, 2.0]})
    g = graph(df, "t", "v <x>", **{"axis.x.title": "H_{2} flow (m^3)"})
    [data] = readouts(g, tmp_path)
    assert lines(data)[0][0][0] == "H<sub>2</sub> flow (m<sup>3</sup>)"
    assert lines(data)[0][1][0] == "v &lt;x&gt;"


def test_dates_read_out_in_the_axis_format_or_as_iso_dates(tmp_path):
    df = pd.DataFrame({"day": pd.to_datetime(["2026-01-05", "2026-01-06"]), "v": [1.0, 2.0]})
    g = graph(df, "day", "v")
    assert lines(readouts(g, tmp_path)[0])[0][0] == ("day", "2026-01-05")
    g = graph(df, "day", "v", **{"axis.x.tick.label.format": "%b %-d"})
    assert lines(readouts(g, tmp_path)[0])[0][0] == ("day", "Jan 5")


def test_a_page_embeds_the_readouts_font_and_script(tmp_path):
    df = pd.DataFrame({"t": [0.0, 1.0], "v": [1.0, 2.0]})
    [page] = graph(df, "t", "v")._write(tmp_path / "g", ["html"])
    text = page.read_text(encoding="utf-8")
    assert '@font-face { font-family: "Roboto"; font-weight: 400;' in text
    assert '<div class="figure"><img' in text
    assert "function hit(marks, found" in text


# --- the numbers -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "lower", "upper", "words", "written"),
    [
        (7.985, 0.426, 0.426, "95%CI", "8.0 ± 0.4 (95%CI)"),
        (1234.0, 31.0, 31.0, None, "1230 ± 30"),
        (5.0, 0.96, 0.96, None, "5 ± 1"),
        (-2.5, 0.12, 0.12, None, f"{MINUS}2.5 ± 0.1"),
        (0.0123, 0.00049, 0.0021, "SD", f"0.0123 {MINUS}0.0005 / +0.002 (SD)"),
        (3.0, 0.0, 0.26, None, f"3.0 {MINUS}0 / +0.3"),
    ],
)
def test_a_value_is_rounded_to_its_errors_significant_digit(value, lower, upper, words, written):
    assert with_error(value, lower, upper, words) == written


@pytest.mark.parametrize(
    ("how", "multiplier", "percentile", "words"),
    [
        ("ci", 1.0, 50.0, "95%CI"),
        ("stddev", 2.0, 50.0, "2 × SD"),  # noqa: RUF001
        ("stderr", 1.0, 50.0, "SE"),
        ("percentile", 1.0, 90.0, "90th percentile"),
        ("percentile", 1.0, 1.0, "1st percentile"),
        ("percentile", 1.0, 12.0, "12th percentile"),
        ("percentile", 1.0, 2.5, "2.5th percentile"),
        ("max", 1.0, 50.0, "max"),
    ],
)
def test_an_aggregation_is_written_in_a_readers_words(how, multiplier, percentile, words):
    assert spread_words(how, multiplier, percentile) == words


# --- the page's script -----------------------------------------------------------------------


def _hits(marks: list[list[Any]], pointers: list[tuple[float, float]], size=(500, 400)) -> list:
    """What the page's own hit finds at each pointer, in fractions of a size px image."""
    functions = _READOUT_SCRIPT.split("(function ()")[0]
    calls = (
        f"var marks = {json.dumps(marks)}, found = index(marks);"
        f"console.log(JSON.stringify({json.dumps(pointers)}.map(function (p) {{"
        f"return hit(marks, found, p[0], p[1], {size[0]}, {size[1]}); }})));"
    )
    node = shutil.which("node")
    assert node is not None
    done = subprocess.run(
        [node, "-e", functions + calls], capture_output=True, text=True, check=True
    )
    return json.loads(done.stdout)


@needs_node
def test_the_script_finds_the_nearest_point_within_reach_then_a_bar():
    r = 4 / 500  # a 4 px marker
    marks = [
        [0.2, 0.5, r, None, 0, 0, []],
        [0.21, 0.5, r, None, 0, 0, []],
        [0.6, 0.5, 0, None, 0, 0, []],  # a line's point, without a marker
        [0.8, 0.6, 0, [0.75, 0.3, 0.85, 0.9], 0, 0, []],  # a bar
        [0.8, 0.3, r, None, 0, 0, []],  # a marker on the bar's top
    ]
    px = 1 / 500
    assert _hits(
        marks,
        [
            (0.2, 0.5),  # on the first
            (0.209, 0.5),  # nearer the second
            (0.2 - 6.9 * px, 0.5),  # its 4 px marker and 3 px: 7 px
            (0.2 - 8 * px, 0.5),  # out of reach
            (0.6 + 5 * px, 0.5),  # a line's point: 6 px
            (0.6 + 7 * px, 0.5),
            (0.8, 0.8),  # on the bar
            (0.8, 0.3),  # the marker beats its bar
            (0.5, 0.95),  # nothing
        ],
    ) == [0, 1, 0, -1, 2, -1, 3, 4, -1]


@needs_node
def test_the_script_finds_points_quickly_among_many():
    rng = np.random.default_rng(0)
    points = rng.random((20000, 2)).round(4)
    marks = [[float(x), float(y), 0.004, None, 0, 0, []] for x, y in points]
    pointers = [(m[0], m[1]) for m in marks[:50]]
    found = _hits(marks, pointers)
    assert all(marks[k][:2] == list(p) for k, p in zip(found, pointers, strict=True))
