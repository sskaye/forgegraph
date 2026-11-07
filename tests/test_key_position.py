"""Where a key goes: legend.key.positions, tried in order, inside the plot area or outside it
(legend.key.inside), and the layout that makes room for a key outside."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import forgegraph as fg
from forgegraph.drawing import text
from forgegraph.drawing.key import keys
from forgegraph.drawing.marks import Bars

SHARES = pd.DataFrame(
    {
        "grade": ["D", "D", "E", "E", "F", "F"],
        "cut": ["Fair", "Ideal"] * 3,
        "n": [10.0, 30.0, 12.0, 28.0, 9.0, 33.0],
    }
)
STACKED = {
    "series.bar.show": True,
    "series.line.show": False,
    "series.marker.show": False,
    "arrangement.stacking": "percent",
    "axis.x.tick.algorithm": "all",
    "legend.method": "key",
}


def graph(**parameters) -> fg.Graph:
    return fg.xy(SHARES, "grade", "n", color="cut", title="Shares", parameters=parameters)


def test_keys_go_inside_by_default():
    g = graph(**{**STACKED, "axis.y.max": 160})
    [key] = keys(g.axes)
    assert not key.outside and key.position in ("top_right", "top_left")


def test_positions_are_tried_in_order():
    g = graph(**{**STACKED, "axis.y.max": 160, "legend.key.positions": ["top_left", "top_right"]})
    [key] = keys(g.axes)
    assert key.position == "top_left"


def test_no_clear_position_inside_is_an_error():
    with pytest.raises(fg.SpecError, match=r"legend\.key\.inside: false"):
        graph(**STACKED)  # 100 % stacks leave no corner clear


@pytest.mark.parametrize("position", ["right_center", "top_center", "bottom_center"])
def test_a_key_outside_gets_room_beside_the_plot(position):
    g = graph(**{**STACKED, "legend.key.inside": False, "legend.key.positions": [position]})
    [key] = keys(g.axes)
    box, plot = key.bbox(), g.axes.get_window_extent()
    figure = g.figure.bbox
    assert key.outside and not box.overlaps(plot)
    assert figure.x0 <= box.x0 and box.x1 <= figure.x1 and figure.y0 <= box.y0
    assert box.y1 <= figure.y1
    renderer = g.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    title = text.footprint(g.axes.title, renderer)  # to the letters
    xlabel = text.footprint(g.axes.xaxis.label, renderer)
    if position.startswith("right"):
        assert box.x0 > plot.x1
    elif position.startswith("top"):
        assert plot.y1 < box.y0 and box.y1 < title.y0  # under the title
    else:
        assert box.y1 < xlabel.y0  # below the x-axis title


def test_a_key_outside_leaves_less_room_for_the_bars():
    many = pd.DataFrame(
        {"grade": list("DEFGHIJ") * 2, "cut": ["Fair"] * 7 + ["Ideal"] * 7, "n": [1.0] * 14}
    )
    outside = {**STACKED, "legend.key.inside": False, "legend.key.positions": ["right_center"]}
    above = {**STACKED, "legend.key.inside": False, "legend.key.positions": ["top_center"]}

    def bar_width(params: dict) -> float:
        g = fg.xy(many, "grade", "n", color="cut", parameters=params)
        return max(b.width for b in g.axes.collections if isinstance(b, Bars))

    assert bar_width(outside) < bar_width(above)  # the key beside the plot narrows it


# --- making room for a key inside the plot ----------------------------------------------------


def _low_points(n: int = 170) -> pd.DataFrame:
    """Points along the bottom of the plot, and one at the top left that sets the axis's top."""
    rng = np.random.default_rng(3)
    x, y = rng.uniform(-1, 1, n), np.clip(rng.exponential(0.25, n), 0, 1.2)
    x[0], y[0] = -0.9, 5.0
    return pd.DataFrame(
        {
            "x": x,
            "y": y,
            "Class": [f"Class {i % 7}" for i in range(n)],
            "Kind": [f"K{i % 2}" for i in range(n)],
        }
    )


LIMITS = (("a", -0.45, "Lower limit"), ("b", 0.2, "Upper limit"))


def _with_lines(position: str = "auto", lines=LIMITS, **parameters) -> fg.Graph:
    settings = {
        "axis.x.data.column": "x",
        "legend.method": "key",
        "series": {
            "y": {"color": "Class", "line": {"show": False}, **parameters.pop("series", {})},
        },
        **parameters,
    }
    d = fg.graphspec("t", "xy", settings=settings)
    d["parameters"]["layers"] = {
        name: {
            "type": "reference",
            "axis": "x",
            "line_1": {"value": at, "label": {"text": text, "position": position}},
        }
        for name, at, text in lines
    }
    return fg.render(d, _low_points())


def _label(g: fg.Graph, words: str):
    return next(t for t in g.axes.texts if t.get_text() == words).get_window_extent()


def test_a_key_goes_before_labels_at_auto_which_keep_clear_of_it():
    g = _with_lines()
    [key] = keys(g.axes)
    assert key.position == "top_right"
    for words in ("Lower limit", "Upper limit"):
        assert not key.bbox().overlaps(_label(g, words))


def test_labels_at_chosen_positions_go_first_and_the_error_names_them():
    with pytest.raises(fg.SpecError, match="top_right covers the label 'Upper limit'"):
        _with_lines("end_above")


def test_a_second_key_goes_beside_the_first_when_the_corners_are_used_up():
    g = _with_lines(lines=(), series={"marker": {"shape": "Kind"}})
    first, second = keys(g.axes)
    assert first.position == second.position == "top_right"
    assert not first.bbox().overlaps(second.bbox())
    assert second.bbox().x1 <= first.bbox().x0  # the two are too tall to stack here


def _dots_across_the_top(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(5)
    x, y = rng.uniform(0, 10, n), rng.uniform(0, 10, n)
    return pd.DataFrame({"x": x, "y": y, "g": [f"g{i % 2}" for i in range(n)]})


def _covered(**parameters) -> fg.Graph:
    return fg.xy(
        _dots_across_the_top(),
        "x",
        "y",
        color="g",
        parameters={
            "legend.method": "key",
            "series.line.show": False,
            "legend.key.positions": ["top_right"],
            "axis.max_extension": 0.6,
            **parameters,
        },
    )


def test_the_axis_grows_for_a_key_by_as_little_as_it_takes():
    g = _covered()
    [key] = keys(g.axes)
    _, top = g.axes.get_ylim()
    assert 10 < top < 10 * 1.7
    text.measure(g.figure)
    centres = g.axes.transData.transform(_dots_across_the_top()[["x", "y"]].to_numpy())
    box = key.bbox()
    assert not (
        (box.x0 < centres[:, 0])
        & (centres[:, 0] < box.x1)
        & (box.y0 < centres[:, 1])
        & (centres[:, 1] < box.y1)
    ).any()


def test_a_set_limit_stays_where_it_is_so_the_key_doesnt_fit():
    with pytest.raises(fg.SpecError, match="top_right covers the data"):
        _covered(**{"axis.y.max": 10.0})


def test_no_extension_leaves_the_axis_alone():
    with pytest.raises(fg.SpecError, match="top_right covers the data"):
        _covered(**{"axis.max_extension": 0})


def test_direct_labels_go_after_a_lines_label_at_auto():
    df = pd.DataFrame(
        {"x": [0.0, 1.0, 2.0, 3.0], "up": [1.0, 2.0, 3.0, 4.0], "down": [4.0, 3.0, 2.0, 1.0]}
    )
    d = fg.graphspec(
        "t",
        "xy",
        settings={
            "axis.x.data.column": "x",
            "axis.y.title": "v",
            "legend.method": "direct",
            "legend.key.title.text": "None",
            "series": {"up": {}, "down": {}},
        },
    )
    label = {"value": 2.5, "label": {"text": "Limit"}}
    d["parameters"]["layers"] = {"t": {"type": "reference", "axis": "y", "line_1": label}}
    g = fg.render(d, df)
    written = [t.get_text() for t in g.axes.texts if t.get_text()]
    assert written[0] == "Limit"
    assert sorted(written) == ["Limit", "down", "up"]


def test_a_key_and_a_note_keep_clear_of_a_band_and_its_lines_in_a_scatter():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"x": np.arange(60.0), "y": rng.uniform(0, 60, 60)})
    d = fg.graphspec(
        "t",
        "xy",
        settings={
            "axis.x.data.column": "x",
            "axis.max_extension": 1.0,
            "legend.method": "key",
            "legend.key.positions": ["top_left"],
            "series": {
                "y": {"color": "g", "line": {"show": False}},
            },
        },
    )
    df["g"] = np.where(df["x"] < 30, "a", "b")
    d["parameters"]["layers"] = {
        "band": {
            "type": "reference",
            "axis": "y",
            "line_1": {"value": 59.0},
            "line_2": {"value": 81.0},
        },
        "excluded": {"type": "note", "text": "3 items excluded", "position": "top_right"},
    }
    g = fg.render(d, df)
    [key] = keys(g.axes)
    band_top = g.axes.transData.transform((0, 81.0))[1]
    text.measure(g.figure)
    assert key.bbox().y0 > band_top
    [note] = [t for t in g.axes.texts if t.get_text() == "3 items excluded"]
    assert note.get_window_extent().y0 > band_top


def test_a_bands_labels_may_sit_on_its_fill_and_direct_labels_on_any_fill():
    x = np.arange(0.0, 10.0)
    df = pd.DataFrame({"x": x, "up": 1.0 + 0.1 * x, "down": 1.6 - 0.1 * x})
    d = fg.graphspec(
        "t",
        "xy",
        settings={
            "axis.x.data.column": "x",
            "axis.y.title": "v",
            "legend.method": "direct",
            "legend.key.title.text": "None",
            "series": {"up": {}, "down": {}},
        },
    )
    lines = {
        "line_1": {"value": 1.0, "label": {"text": "Low", "position": "end_above"}},
        "line_2": {"value": 1.6, "label": {"text": "High", "position": "end_below"}},
    }
    d["parameters"]["layers"] = {"band": {"type": "reference", "axis": "y", **lines}}
    g = fg.render(d, df)  # the band fills the plot: its labels and the series' are on it
    assert sorted(t.get_text() for t in g.axes.texts if t.get_text()) == [
        "High",
        "Low",
        "down",
        "up",
    ]


def test_ticks_continue_into_the_part_of_an_axis_extended_for_a_key():
    g = _covered()
    ticks = [float(v) for v in g.axes.get_yticks() if v <= g.axes.get_ylim()[1]]
    assert max(ticks) > 10  # the axis grew past the data's 10, and its ticks go on
    steps = np.diff(ticks)
    assert np.allclose(steps, steps[0])


def test_an_axis_grown_a_long_way_chooses_its_ticks_again_and_is_laid_out_around_them():
    rng = np.random.default_rng(2)
    df = pd.DataFrame(
        {
            "x": rng.uniform(0, 10, 300),
            "y": rng.uniform(0, 95, 300),
            "g": [f"g{i % 3}" for i in range(300)],
        }
    )
    g = fg.xy(
        df,
        "x",
        "y",
        color="g",
        parameters={
            "legend.method": "key",
            "series.line.show": False,
            "legend.key.positions": ["top_right"],
            "axis.max_extension": 0.6,
            "axis.y.title": "A rather long y-axis title",
        },
    )
    ticks = [float(v) for v in g.axes.get_yticks() if v <= g.axes.get_ylim()[1]]
    assert ticks[-1] > 100 and np.allclose(np.diff(ticks), ticks[1] - ticks[0])
    assert not [i for i in g.issues if i.check == "clipped-text"]


def test_a_key_keeps_clear_of_a_markers_edge_not_only_its_centre():
    for seed in (4, 5, 8):  # each put its key over a marker's edge when centres alone counted
        rng = np.random.default_rng(seed)
        df = pd.DataFrame(
            {
                "x": rng.uniform(0, 10, 40),
                "y": rng.uniform(0, 10, 40),
                "g": [f"g{i % 2}" for i in range(40)],
            }
        )
        g = fg.xy(
            df,
            "x",
            "y",
            color="g",
            parameters={
                "legend.method": "key",
                "series.line.show": False,
                "series.marker.size": 1.5,
            },
        )
        assert not [i for i in g.issues if i.check == "key-over-data"], seed


def test_a_box_runs_into_a_marker_at_its_edge():
    from forgegraph.drawing import labels

    obstacles = labels.Obstacles(centres=[np.array([[0.0, 0.0]])], radii=[6.0])
    near = labels.Bbox.from_extents(4.0, -1.0, 20.0, 1.0)  # 4 px from the centre: on the edge
    assert obstacles.hits(near) == ["the data"]
    assert obstacles.hits(labels.Bbox.from_extents(7.0, -1.0, 20.0, 1.0)) == []
