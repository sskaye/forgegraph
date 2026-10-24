"""Where a key goes: legend.key.positions, tried in order, inside the plot area or outside it
(legend.key.inside), and the layout that makes room for a key outside."""

from __future__ import annotations

import pandas as pd
import pytest

import forgegraph as fg
from forgegraph.render import text
from forgegraph.render.key import keys

SHARES = pd.DataFrame(
    {
        "grade": ["D", "D", "E", "E", "F", "F"],
        "cut": ["Fair", "Ideal"] * 3,
        "n": [10.0, 30.0, 12.0, 28.0, 9.0, 33.0],
    }
)
STACKED = {
    "mark.bar.show": True,
    "mark.line.show": False,
    "mark.marker.show": False,
    "series.aggregation": "percent",
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
    params = {**STACKED, "legend.key.inside": False, "legend.key.positions": ["right_center"]}
    with pytest.raises(fg.SpecError, match=r"series\.bar\.width"):
        fg.xy(many, "grade", "n", color="cut", parameters=params)
