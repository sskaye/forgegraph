"""Layers (layers/*.yaml): a GraphSpec's named layers, checked and merged through extends, and
the reference lines, error bars and notes they draw."""

from __future__ import annotations

import copy
import re
from typing import Any

import numpy as np
import pandas as pd
import pytest

import forgegraph as fg
from forgegraph.drawing.layers import ERROR_BAR, NOTE, REFERENCE, t_quantile
from forgegraph.spec.explain import explain
from forgegraph.spec.registry import builtin
from forgegraph.spec.validate import drawing_problems, validate

RATES = pd.DataFrame(
    {
        "conc": [1.0, 1.0, 1.0, 2.0, 2.0, 2.0] * 2,
        "rate": [10.0, 12.0, 14.0, 20.0, 22.0, 30.0, 5.0, 6.0, 7.0, 9.0, 11.0, 13.0],
        "state": ["a"] * 6 + ["b"] * 6,
    }
)


def doc(listed: dict[str, Any], **settings: Any) -> dict[str, Any]:
    d = fg.graphspec(
        "t",
        "xy",
        settings={"axis.x.data.column": "conc", "axis.y.data.column": "rate", **settings},
    )
    d["variable_parameters"]["layers"] = listed
    return d


def graph(listed: dict[str, Any], df: pd.DataFrame = RATES, /, **settings: Any) -> fg.Graph:
    return fg.render(doc(listed, **settings), df)


def layer_lines(g: fg.Graph, gid: str) -> list:
    return [ln for ln in g.axes.get_lines() if ln.get_gid() == gid]


def layer_texts(g: fg.Graph, gid: str) -> list[str]:
    return [t.get_text() for t in g.axes.texts if t.get_gid() == gid]


# --- the spec --------------------------------------------------------------------------------


def test_layers_are_checked_against_their_type():
    assert validate("graphspec", doc({"t": {"type": "pie"}})) == [
        "variable_parameters.layers.t.type: unknown layer type 'pie'"
    ]
    assert validate("graphspec", doc({"t": {"type": "note", "txt": "x"}})) == [
        "variable_parameters.layers.t.txt: unknown parameter of note; did you mean 'text'?"
    ]
    assert validate("graphspec", doc({"t": {"axis": "y"}})) == [
        "variable_parameters.layers.t.type: required: one of reference_line, note, error_bar"
    ]
    assert validate("graphspec", doc({"t": {"type": "note", "position": "middle"}}))[0].startswith(
        "variable_parameters.layers.t.position: must be one of: auto, top_left"
    )


def test_a_layer_type_the_graph_type_doesnt_take_is_an_error():
    reg = builtin().copy()
    narrow = copy.deepcopy(reg.docs["graph_type"]["xy"])
    narrow.update(name="narrow", extends="xy", variable_parameters="None")
    narrow["fixed_parameters"] = {"layer": {"types": ["note"]}}
    reg.add("graph_type", narrow)
    d = doc({"t": {"type": "reference_line", "axis": "y", "value": 1}})
    d["variable_parameters"]["specifications"]["graph_type"] = "narrow"
    assert validate("graphspec", d, reg) == [
        "variable_parameters.layers.t.type: graph type 'narrow' takes only note"
    ]


def test_required_layer_parameters_are_drawing_problems():
    assert drawing_problems(doc({"t": {"type": "note"}})) == [
        "layers.t.text: must be set before the graph can be drawn"
    ]


def test_layers_merge_by_name_through_extends():
    reg = builtin().copy()
    parent = doc(
        {
            "target": {
                "type": "reference_line",
                "axis": "y",
                "value": 1.0,
                "label": {"text": "Aim"},
            },
            "conditions": {"type": "note", "text": "60 °C"},
            "gone": {"type": "note", "text": "removed"},
        }
    )
    parent["name"] = "parent"
    reg.add("graphspec", parent)
    child = doc({"target": {"value": 2.0}, "gone": "None", "extra": {"type": "note", "text": "x"}})
    child.update(name="child", extends="parent")
    reg.add("graphspec", child)
    assert validate("graphspec", child, reg) == []
    layers = {name: r.value for name, r in explain(child, reg).layers.items()}
    assert list(layers) == ["target", "conditions", "extra"]
    assert layers["target"]["value"] == 2.0 and layers["target"]["label.text"] == "Aim"


def test_a_fixed_layer_cant_be_changed():
    reg = builtin().copy()
    parent = doc({})
    parent["variable_parameters"].pop("layers")
    parent.update(
        name="parent",
        fixed_parameters={
            "layers": {"target": {"type": "reference_line", "axis": "y", "value": 1.0}}
        },
    )
    reg.add("graphspec", parent)
    child = doc({"target": {"value": 2.0}})
    child.update(name="child", extends="parent")
    reg.add("graphspec", child)
    assert validate("graphspec", child, reg) == [
        "variable_parameters.layers.target: fixed by GraphSpec 'parent'"
    ]


# --- reference lines -------------------------------------------------------------------------


def test_a_reference_line_at_a_value_with_its_label():
    g = graph({"t": {"type": "reference_line", "axis": "y", "value": 15, "label": {"text": "Aim"}}})
    [line] = layer_lines(g, REFERENCE)
    assert np.asarray(line.get_ydata()).tolist() == [15, 15]
    assert layer_texts(g, REFERENCE) == ["Aim"]


def test_a_line_outside_the_data_widens_the_axis_or_is_an_error():
    g = graph({"t": {"type": "reference_line", "axis": "y", "value": 50}})
    assert g.axes.get_ylim()[1] > 50
    with pytest.raises(fg.SpecError, match=re.escape("the line at 50 is outside axis.y.max")):
        graph({"t": {"type": "reference_line", "axis": "y", "value": 50}}, **{"axis.y.max": 40})


def test_a_line_at_a_limit_but_for_float_noise_is_at_it():
    at_most: dict[str, Any] = {"type": "reference_line", "axis": "y", "value": "rate"}
    at_most["aggregation"] = {"function": "max", "multiplier": 1.1}
    tall = RATES.assign(rate=RATES["rate"] * 100 / 30)  # max 100; 1.1 * 100 is 110.00000000000001
    g = graph({"t": at_most}, tall, **{"axis.y.max": 110})
    assert g.axes.get_ylim()[1] == 110
    with pytest.raises(fg.SpecError, match=re.escape("is outside axis.y.max")):
        graph({"t": at_most}, tall, **{"axis.y.max": 109.99})


def test_a_line_at_an_aggregate():
    g = graph(
        {
            "t": {
                "type": "reference_line",
                "axis": "y",
                "value": "rate",
                "aggregation": {"function": "mean"},
                "label": {"text": "aggregation"},
            }
        },
        **{"mark.line.show": False},  # the lines between the two concentrations cross it
    )
    [line] = layer_lines(g, REFERENCE)
    assert line.get_ydata()[0] == pytest.approx(RATES["rate"].mean())
    assert layer_texts(g, REFERENCE) == ["Mean"]
    g = graph(
        {
            "t": {
                "type": "reference_line",
                "axis": "y",
                "value": "rate",
                "aggregation": {"function": "stddev", "multiplier": 2},
                "label": {"text": "aggregation"},
            }
        },
        **{"mark.line.show": False},  # the lines between the two concentrations cross it
    )
    assert layer_texts(g, REFERENCE) == ["2 × std dev"]  # noqa: RUF001


def test_a_line_per_named_series_takes_in_its_replicates():
    df = RATES.assign(run=[1, 2] * 6)
    g = graph(
        {
            "t": {
                "type": "reference_line",
                "axis": "y",
                "value": "rate",
                "aggregation": {"function": "max"},
                "per_series": True,
            }
        },
        df,
        **{"encoding.color.column": "state", "encoding.detail.column": "run"},
    )
    assert sorted(ln.get_ydata()[0] for ln in layer_lines(g, REFERENCE)) == [13.0, 30.0]


def test_a_line_per_series_in_its_color():
    g = graph(
        {
            "t": {
                "type": "reference_line",
                "axis": "y",
                "value": "rate",
                "aggregation": {"function": "max"},
                "per_series": True,
            }
        },
        **{"encoding.color.column": "state"},
    )
    lines = layer_lines(g, REFERENCE)
    assert sorted(ln.get_ydata()[0] for ln in lines) == [13.0, 30.0]
    assert len({ln.get_color() for ln in lines}) == 2


TWO_Y = pd.DataFrame(
    {"x": [1.0, 2.0, 3.0, 4.0, 5.0], "a": [10.0, 100, 1000, 300, 50], "b": [20.0, 40, 60, 80, 100]}
)
AGGREGATES = {
    "mean": np.mean,
    "median": np.median,
    "sum": np.sum,
    "min": np.min,
    "max": np.max,
    "stddev": lambda v: np.std(v, ddof=1),
}


@pytest.mark.parametrize("how", sorted(AGGREGATES))
@pytest.mark.parametrize("y", [["a"], ["a", "b"], ["b", "a"]])
def test_a_line_at_an_aggregate_counts_each_row_once(how, y):
    """However many y columns are drawn, a column's aggregate is of its rows, each once."""
    g = graph(
        {
            "t": {
                "type": "reference_line",
                "axis": "y",
                "value": "b",
                "aggregation": {"function": how},
            }
        },
        TWO_Y,
        **{
            "axis.x.data.column": "x",
            "axis.y.data.column": y,
            "axis.y.title": "v",
            "legend.method": "key",
            "legend.key.inside": False,
            "legend.key.title.text": "None",
        },
    )
    [line] = layer_lines(g, REFERENCE)
    assert line.get_ydata()[0] == pytest.approx(AGGREGATES[how](TWO_Y["b"]))


def test_a_line_per_series_at_an_aggregate_counts_each_row_once():
    df = pd.concat([TWO_Y.assign(g="p"), TWO_Y.assign(g="q", b=TWO_Y["b"] * 2)])
    g = graph(
        {
            "t": {
                "type": "reference_line",
                "axis": "y",
                "value": "b",
                "per_series": True,
                "aggregation": {"function": "sum"},
            }
        },
        df,
        **{
            "axis.x.data.column": "x",
            "axis.y.data.column": ["b"],
            "encoding.color.column": "g",
            "legend.method": "key",
            "legend.key.inside": False,
            "legend.key.title.text": "None",
        },
    )
    assert sorted(ln.get_ydata()[0] for ln in layer_lines(g, REFERENCE)) == pytest.approx(
        [300.0, 600.0]
    )


@pytest.mark.parametrize(
    ("layer", "message"),
    [
        ({"value": "rate"}, "value: a column, so set aggregation.function"),
        ({"value": 3, "aggregation": {"function": "mean"}}, "applies only when value is a column"),
        ({"value": "nope", "aggregation": {"function": "mean"}}, "no column 'nope'"),
    ],
)
def test_reference_line_errors(layer, message):
    with pytest.raises(fg.SpecError, match=re.escape(message)):
        graph({"t": {"type": "reference_line", "axis": "y", **layer}})


# --- error bars ------------------------------------------------------------------------------


def test_t_quantiles_match_published_tables():
    published = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 10: 2.228, 30: 2.042}
    for df, t in published.items():
        assert t_quantile(0.975, df) == pytest.approx(t, abs=0.005)


def test_error_bars_of_a_constant_and_of_a_column():
    g = graph(
        {
            "e": {
                "type": "error_bar",
                "value": {"lower": 1, "upper": 2, "aggregation": {"function": "None"}},
            }
        },
        **{"axis.y.data.aggregation": "mean", "encoding.color.column": "state"},
    )
    stems = [ln for ln in layer_lines(g, ERROR_BAR) if ln.get_linestyle() != "None"]
    y = np.asarray(stems[0].get_ydata(), dtype=float)
    assert (y[1] - y[0]) == pytest.approx(3)
    df = RATES.assign(sd=0.5)
    g = graph(
        {
            "e": {
                "type": "error_bar",
                "value": {"lower": "sd", "upper": "sd", "aggregation": {"function": "None"}},
            }
        },
        df,
    )
    assert layer_lines(g, ERROR_BAR)


def test_error_bars_by_default_are_the_data_columns_standard_deviation():
    g = graph({"e": {"type": "error_bar"}}, **{"axis.y.data.aggregation": "mean"})
    stem = next(ln for ln in layer_lines(g, ERROR_BAR) if ln.get_linestyle() != "None")
    y = np.asarray(stem.get_ydata(), dtype=float)
    assert (y[1] - y[0]) / 2 == pytest.approx(np.std([10, 12, 14, 5, 6, 7], ddof=1))  # conc 1


def test_error_bars_of_the_spread_of_aggregated_rows():
    for how, factor in (("stddev", 1.0), ("stderr", 1 / np.sqrt(3)), ("ci", 4.303 / np.sqrt(3))):
        g = graph(
            {
                "e": {
                    "type": "error_bar",
                    "value": {"lower": "rate", "upper": "rate", "aggregation": {"function": how}},
                }
            },
            **{"axis.y.data.aggregation": "mean", "encoding.color.column": "state"},
        )
        stem = next(ln for ln in layer_lines(g, ERROR_BAR) if ln.get_linestyle() != "None")
        y = np.asarray(stem.get_ydata(), dtype=float)
        assert (y[1] - y[0]) / 2 == pytest.approx(2.0 * factor, abs=0.01)  # sd of 10, 12, 14


DAYS = pd.DataFrame(
    {
        "day": pd.to_datetime(["2026-03-01", "2026-03-02", "2026-03-03"] * 3),
        "rate": [10.0, 20.0, 30.0, 12.0, 22.0, 33.0, 14.0, 24.0, 36.0],
        "sd": [1.0, 2.0, 3.0] * 3,
    }
)


def _stems(g: fg.Graph) -> list:
    return [ln for ln in layer_lines(g, ERROR_BAR) if ln.get_linestyle() != "None"]


def _ends(stem) -> list[tuple[float, float, float]]:
    """Each bar of a stem line as (place, low, high)."""
    xy = np.asarray(stem.get_xydata(), dtype=float)
    return [(a[0], a[1], b[1]) for a, b in zip(xy[0::3], xy[1::3], strict=True)]


def test_error_bars_on_a_date_axis_stand_on_their_points():
    rows = DAYS.iloc[:3]
    g = graph(
        {
            "e": {
                "type": "error_bar",
                "value": {"lower": "sd", "upper": "sd", "aggregation": {"function": "None"}},
            }
        },
        rows,
        **{"axis.x.data.column": "day"},
    )
    [line] = [ln for ln in g.axes.get_lines() if ln.get_gid() not in (ERROR_BAR,)]
    points = np.asarray(line.get_xydata(), dtype=float)
    [stem] = _stems(g)
    assert [e[0] for e in _ends(stem)] == pytest.approx(points[:, 0])
    assert [(e[1], e[2]) for e in _ends(stem)] == pytest.approx([(9, 11), (18, 22), (27, 33)])
    low, high = g.axes.get_xlim()
    assert low <= points[0, 0] and points[-1, 0] <= high <= points[-1, 0] + 1  # not stretched


def test_error_bars_of_aggregated_rows_on_a_date_axis():
    g = graph(
        {
            "e": {
                "type": "error_bar",
                "value": {"lower": "rate", "upper": "rate", "aggregation": {"function": "stddev"}},
            }
        },
        DAYS,
        **{"axis.x.data.column": "day", "axis.y.data.aggregation": "mean"},
    )
    [line] = [ln for ln in g.axes.get_lines() if ln.get_gid() not in (ERROR_BAR,)]
    points = np.asarray(line.get_xydata(), dtype=float)
    [stem] = _stems(g)
    ends = _ends(stem)
    assert [e[0] for e in ends] == pytest.approx(points[:, 0])
    spreads = [np.std(DAYS.rate[DAYS.day == d], ddof=1) for d in DAYS.day.unique()]
    assert [(e[2] - e[1]) / 2 for e in ends] == pytest.approx(spreads)


@pytest.mark.parametrize(
    ("value", "settings", "message"),
    [
        (
            {"lower": "rate", "upper": "rate", "aggregation": {"function": "stddev"}},
            {},
            "set axis.y.data.aggregation too",
        ),
        (
            {"lower": "rate", "upper": "rate", "aggregation": {"function": "None"}},
            {"axis.y.data.aggregation": "mean"},
            "needs value.aggregation.function",
        ),
        (
            {"lower": -1, "upper": 1, "aggregation": {"function": "None"}},
            {},
            "is below 0; it's a distance",
        ),
        (
            {"lower": 100, "upper": 1, "aggregation": {"function": "None"}},
            {"axis.y.scale": "log"},
            "reaches 0 or below",
        ),
        ({"aggregation": {"function": "None"}}, {}, "data_column, whose values aren't distances"),
    ],
)
def test_error_bar_errors(value, settings, message):
    with pytest.raises(fg.SpecError, match=re.escape(message)):
        graph({"e": {"type": "error_bar", "value": value}}, **settings)


def test_error_bars_on_stacked_series_are_an_error():
    with pytest.raises(fg.SpecError, match="error bars on stacked series aren't defined"):
        graph(
            {"e": {"type": "error_bar", "value": {"lower": 1, "upper": 1}}},
            **{
                "axis.y.data.aggregation": "mean",
                "encoding.color.column": "state",
                "series.aggregation": "sum",
            },
        )


# --- notes -----------------------------------------------------------------------------------


def test_a_note_finds_a_clear_corner_and_keys_avoid_it():
    g = graph(
        {"n": {"type": "note", "text": "60 °C"}},
        **{
            "encoding.color.column": "state",
            "legend.method": "key",
            "axis.y.data.aggregation": "mean",
        },
    )
    [note] = [t for t in g.axes.texts if t.get_gid() == NOTE]
    box = note.get_window_extent()
    assert g.axes.get_window_extent().contains(*box.get_points().mean(axis=0))
    from forgegraph.drawing.key import keys

    assert all(not k.bbox().overlaps(box) for k in keys(g.axes))


def test_a_note_outside_sits_below_the_x_axis_title():
    g = graph(
        {
            "n": {
                "type": "note",
                "text": "Source: notebook 12",
                "inside": False,
                "position": "bottom_left",
            }
        }
    )
    [note] = [t for t in g.axes.texts if t.get_gid() == NOTE]
    assert note.get_window_extent().y1 < g.axes.xaxis.label.get_window_extent().y0


def test_an_outside_note_needs_a_position():
    with pytest.raises(fg.SpecError, match="outside it, choose a position"):
        graph({"n": {"type": "note", "text": "x", "inside": False}})


def test_a_note_that_fits_nowhere_is_an_error():
    long = " ".join(["word"] * 60)
    with pytest.raises(fg.SpecError, match="the note doesn't fit any position"):
        graph({"n": {"type": "note", "text": long}})


def _label_box(g: fg.Graph):
    [label] = [t for t in g.axes.texts if t.get_gid() == REFERENCE]
    return label, label.get_window_extent()


def test_an_auto_label_is_clear_of_the_data_and_inside_the_plot():
    from forgegraph.drawing.labels import box_clear

    top = 30.0  # the highest rate
    g = graph(
        {"t": {"type": "reference_line", "axis": "y", "value": top, "label": {"text": "Max"}}},
        **{"mark.line.show": False},
    )
    _, box = _label_box(g)
    plot = g.axes.get_window_extent()
    assert plot.y0 <= box.y0 and box.y1 <= plot.y1  # the line is at the top: label below
    assert box_clear(g.axes, box, lines=False)


def test_a_chosen_label_position_that_covers_the_data_is_an_error():
    with pytest.raises(fg.SpecError, match=r"label.position: start_above, but the label covers"):
        graph(  # the line at conc 1 runs from 5 to 14, through the label
            {
                "t": {
                    "type": "reference_line",
                    "axis": "y",
                    "value": 8,
                    "label": {"text": "Limit", "position": "start_above"},
                }
            }
        )


def test_a_chosen_label_past_the_plots_edge_widens_the_axis():
    top = 30.0  # the highest rate
    g = graph(
        {
            "t": {
                "type": "reference_line",
                "axis": "y",
                "value": top,
                "label": {"text": "Max", "position": "start_above"},
            }
        },
        **{"mark.line.show": False},
    )
    _, box = _label_box(g)
    assert box.y1 <= g.axes.get_window_extent().y1 + 0.5
    with pytest.raises(fg.SpecError, match=r"axis.y.max: layers.t: its label reach"):
        graph(
            {
                "t": {
                    "type": "reference_line",
                    "axis": "y",
                    "value": 30,
                    "label": {"text": "Max", "position": "start_above"},
                }
            },
            **{"mark.line.show": False, "axis.y.max": 30},
        )


def test_a_label_can_give_the_aggregate_and_its_value():
    g = graph(
        {
            "t": {
                "type": "reference_line",
                "axis": "y",
                "value": "rate",
                "aggregation": {"function": "max"},
                "label": {"text": "aggregation_value"},
            }
        },
        **{"mark.line.show": False},
    )
    assert layer_texts(g, REFERENCE) == ["Max: 30.0"]  # one decimal more than the ticks


def test_a_labels_value_takes_its_own_format_or_its_axiss():
    line = {
        "type": "reference_line",
        "axis": "y",
        "value": "rate",
        "aggregation": {"function": "mean"},
        "label": {"text": "value", "format": ".3f"},
    }
    g = graph({"t": line}, **{"mark.line.show": False})
    assert layer_texts(g, REFERENCE) == [f"{RATES['rate'].mean():.3f}"]
    line["label"] = {"text": "value"}
    g = graph({"t": line}, **{"mark.line.show": False, "axis.y.tick.label.format": ".2f"})
    assert layer_texts(g, REFERENCE) == [f"{RATES['rate'].mean():.2f}"]
    vertical = {"type": "reference_line", "axis": "x", "value": 1.5, "label": {"text": "value"}}
    g = graph({"t": vertical}, **{"mark.line.show": False})
    x_decimals = max(
        len(t.get_text().split(".")[1]) for t in g.axes.get_xticklabels() if "." in t.get_text()
    )
    assert layer_texts(g, REFERENCE) == [f"{1.5:.{x_decimals + 1}f}"]  # the x axis's ticks


def test_error_bars_on_side_by_side_bars_are_drawn_on_their_bars():
    """Each series' error bars stay on its own bars, moved by its side-by-side offset: as
    drawn, after layout has changed the axes, not where they were first placed (#2)."""
    from forgegraph.drawing.marks import Bars

    df = pd.DataFrame(
        {
            "kind": ["A"] * 9 + ["B"] * 9,
            "series": (["x"] * 3 + ["y"] * 3 + ["z"] * 3) * 2,
            "value": [30, 32, 34, 20, 22, 26, 40, 45, 50, 25, 27, 29, 15, 18, 21, 35, 37, 42],
        }
    )
    g = graph(
        {"spread": {"type": "error_bar"}},
        df,
        **{
            "axis.x.data.column": "kind",
            "axis.y.data.column": "value",
            "axis.y.data.aggregation": "mean",
            "axis.x.tick.algorithm": "all",
            "encoding.color.column": "series",
            "series.offset": "side_by_side",
            "layer.error_bar.color": "series",
            "legend.key.inside": False,
            "mark.bar.show": True,
            "mark.line.show": False,
            "mark.marker.show": False,
        },
    )
    g.figure.canvas.draw()
    centres = {
        str(b.color): sorted((r.x0 + r.x1) / 2 for r in b.rectangles())
        for b in g.axes.collections
        if isinstance(b, Bars)
    }
    stems = [ln for ln in layer_lines(g, ERROR_BAR) if ln.get_marker() in ("None", "", None)]
    assert len(stems) == 3
    for stem in stems:
        # what the last draw used, which a stale cache would leave where the stem began
        drawn = stem._get_transformed_path().get_fully_transformed_path().vertices
        now = stem.get_transform().transform(stem.get_xydata())
        finite = np.isfinite(now).all(axis=1)
        np.testing.assert_allclose(drawn[finite], now[finite], atol=0.01)
        xs = sorted(set(np.round(drawn[finite][:, 0], 1)))
        np.testing.assert_allclose(xs, centres[str(stem.get_color())], atol=1.0)
