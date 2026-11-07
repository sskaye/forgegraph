"""Toggles (spec/toggles.py, drawing/toggles.py): series and layers a reader can show or hide
on an HTML page, the figure cut into images stacked in the order it draws."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any

import pandas as pd
import pytest
from pack_helpers import needs_node
from test_views import _layout, _tile, metric, problems

import forgegraph as fg
from forgegraph.drawing import owners
from forgegraph.drawing.page import _READOUT_SCRIPT, READOUTS
from forgegraph.drawing.toggles import drawn, member_of, slices

LINES = pd.DataFrame(
    {"x": [0.0, 1.0, 2.0, 3.0], "up": [1.0, 1.2, 1.4, 1.6], "down": [1.6, 1.4, 1.2, 1.0]}
)
BAND = {
    "type": "reference",
    "axis": "y",
    "line_1": {"value": 1.25, "label": {"text": "None"}},
    "line_2": {"value": 1.35, "label": {"text": "None"}},
}


def doc(**toggle: Any) -> dict[str, Any]:
    d = fg.graphspec(
        "t",
        "xy",
        settings={
            "axis.x.data.column": "x",
            "axis.y.title": "v",
            "legend.method": "key",
            "legend.key.inside": False,
            "legend.key.positions": ["right_top"],
            "legend.key.title.text": "None",
            "series": {"up": {}, "down": {}},
        },
    )
    d["parameters"]["layers"] = {"band": BAND, "t": {"type": "toggle", **toggle}}
    return d


def owned_by(g: fg.Graph, name: str) -> list[Any]:
    return [a for a in drawn(g.figure) if name in owners.of(a)]


# --- the spec --------------------------------------------------------------------------------


def test_a_toggle_layer_names_the_graphspecs_series_and_layers():
    assert problems({"t": {"type": "toggle", "items": ["series", "nope"], "hidden": ["x"]}}) == [
        "layers.t.items[1]: 'nope' is no series or layer of the GraphSpec; the series are "
        "cell_voltage, and the layers none",
        "layers.t.hidden[0]: 'x' isn't one of the items: cell_voltage",
    ]
    assert problems({"t": {"type": "toggle"}, "u": {"type": "toggle"}}) == [
        "layers: t, u are toggle layers; a GraphSpec has at most one"
    ]


def test_items_are_every_series_every_layer_or_those_named():
    from forgegraph.spec.registry import builtin
    from forgegraph.spec.toggles import toggles

    found = toggles(doc(items=["series", "layers"], hidden=["band"]), builtin())
    assert found is not None
    assert found.items == (("up", "series"), ("down", "series"), ("band", "layer"))
    assert found.hidden == ("band",)
    named = toggles(doc(items=["band"]), builtin())
    assert named is not None and named.items == (("band", "layer"),)


# --- drawing ---------------------------------------------------------------------------------


def test_hidden_items_are_hidden_in_the_figure_and_the_rest_drawn_as_usual():
    shown = fg.render(doc(items=["series", "band"]), LINES)
    hidden = fg.render(doc(items=["series", "band"], hidden=["band", "down"]), LINES)
    assert all(a.get_visible() for a in owned_by(shown, "layer-band"))
    assert not any(a.get_visible() for a in owned_by(hidden, "layer-band"))
    assert not any(a.get_visible() for a in owned_by(hidden, "series-down"))
    assert any(a.get_visible() for a in owned_by(hidden, "series-up"))
    assert hidden.axes.get_ylim() == shown.axes.get_ylim()  # laid out with everything shown
    assert not hidden.nonstandard


def test_the_figure_is_cut_in_the_order_it_draws():
    g = fg.render(doc(items=["series", "band"], hidden=["band"]), LINES)
    owned = {g.axes: {"series-up": "up", "series-down": "down", "layer-band": "band"}}
    with g.inspected_once():
        cut = slices(g.figure, member_of(owned), 72)
    order = [sorted(s.items) for s in cut]
    assert order[0] == []  # the background, and what's under everything
    assert order.index(["band"]) < order.index(["up"]) < order.index(["down"])  # by zorder
    assert all(not s.items or len(s.items) == 1 for s in cut)
    assert not any(a.get_visible() for a in owned_by(g, "layer-band"))  # hidden again
    assert not g.nonstandard


def test_error_bars_belong_to_their_series_and_their_layer():
    df = pd.DataFrame({"x": [1.0, 1.0, 2.0, 2.0], "y": [1.0, 2.0, 3.0, 4.0]})
    d = fg.graphspec(
        "t",
        "xy",
        settings={
            "axis.x.data.column": "x",
            "series": {"y": {"aggregation": {"function": "mean"}}},
        },
    )
    d["parameters"]["layers"] = {
        "spread": {"type": "error_bar"},
        "t": {"type": "toggle", "items": ["series", "spread"], "hidden": ["spread"]},
    }
    g = fg.render(d, df)
    bars = [a for a in drawn(g.figure) if "layer-spread" in owners.of(a)]
    assert bars and all(owners.of(a) == ("series-y", "layer-spread") for a in bars)
    assert not any(a.get_visible() for a in bars)


# --- the page --------------------------------------------------------------------------------


def test_a_page_has_a_button_for_each_item_and_hides_its_images(tmp_path):
    g = fg.render(doc(items=["series", "band"], hidden=["band"]), LINES)
    [path] = g.save(tmp_path / "g.html")
    page = path.read_text()
    button = '<label class="toggle" data-toggle="0"><input type="checkbox" id="toggle0" checked>'
    assert f"{button}up</label>" in page
    assert '<input type="checkbox" id="toggle2">band</label>' in page  # hidden at first
    items = re.findall(r'<img class="slice" alt=""( data-items="[^"]*")?( data-hidden)?', page)
    assert (' data-items="2"', " data-hidden") in items
    assert (' data-items="0"', "") in items and (' data-items="1"', "") in items
    rule = 'main:has(#toggle1:not(:checked)) .slice[data-items~="1"] { display: none; }'
    assert rule in page
    [data] = [
        json.loads(m)
        for m in re.findall(
            rf'<script type="application/json" class="{READOUTS}">(.*?)</script>', page
        )
    ]
    assert {m[7] for m in data["marks"]} == {0, 1}  # each point's series' button


def test_each_view_has_its_own_images(tmp_path):
    d = doc(items=["series"])
    d["parameters"]["layers"]["s"] = metric("radio", Linear={}, Log={"axis.y.scale": "log"})
    [path] = fg.render(d, LINES).save(tmp_path / "g.html")
    page = path.read_text()
    views = re.findall(r'<div class="figure stack view" data-view="[^"]+"', page)
    assert len(views) == 2
    assert page.count('data-items="0"') == page.count('data-items="1"') >= 2


@needs_node
def test_the_script_skips_the_points_of_a_series_switched_off():
    functions = _READOUT_SCRIPT.split("(function ()")[0]
    marks = [[0.5, 0.5, 0.01, None, 0, 0, [], 0], [0.51, 0.5, 0.01, None, 0, 0, [], 1]]
    calls = (
        f"var marks = {json.dumps(marks)}, found = index(marks);"
        "console.log(JSON.stringify([hit(marks, found, 0.5, 0.5, 500, 400),"
        "hit(marks, found, 0.5, 0.5, 500, 400, function (m) { return m[7] !== 0; })]));"
    )
    node = shutil.which("node")
    assert node is not None
    done = subprocess.run([node], input=functions + calls, capture_output=True, text=True)
    assert json.loads(done.stdout) == [0, 1]


# --- layouts ---------------------------------------------------------------------------------


def test_items_of_the_same_name_in_a_layout_share_one_button(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _tile(tmp_path, "a", {"t": {"type": "toggle"}})
    _tile(tmp_path, "b", {"t": {"type": "toggle"}})
    _tile(tmp_path, "c", {})
    tabs = {
        "Both": {"grid": {"areas": [["a", "b"]]}, "tiles": {"a": "a.yaml", "b": "b.yaml"}},
        "Plain": {"grid": {"areas": [["c"]]}, "tiles": {"c": "c.yaml"}},
    }
    layout = fg.layout(_layout(tmp_path, tabs))
    assert [t.name for t in layout.toggles] == ["cell_voltage"]
    [path] = layout.save(tmp_path / "fig.html")
    page = path.read_text()
    assert page.count('class="toggle"') == 1
    both = re.search(r'<section id="both".*?</section>', page, re.S)
    plain = re.search(r'<section id="plain".*?</section>', page, re.S)
    assert both and plain
    assert both[0].count('data-items="0"') >= 2  # each tile's series
    assert "slice" not in plain[0]  # a tile without a toggle layer isn't cut


def test_items_sharing_a_button_start_hidden_in_every_tile_or_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _tile(tmp_path, "a", {"t": {"type": "toggle", "hidden": ["cell_voltage"]}})
    _tile(tmp_path, "b", {"t": {"type": "toggle"}})
    tabs = {"Both": {"grid": {"areas": [["a", "b"]]}, "tiles": {"a": "a.yaml", "b": "b.yaml"}}}
    with pytest.raises(fg.SpecError) as e:
        fg.layout(_layout(tmp_path, tabs))
    assert e.value.problems == [
        "tabs.Both.tiles.b (b.yaml): layers.t: 'cell_voltage' is shown at first, and not in "
        "tabs.Both.tiles.a (a.yaml); items of the same name share one button, so they start "
        "hidden in every tile or in none"
    ]
