"""Views (spec/views.py): a choice layer's alternatives, each the GraphSpec with some of its
parameters changed, all drawn ahead of time, and the page's controls that switch them."""

from __future__ import annotations

import io
import re
from typing import Any

import pytest
from pack_helpers import dump, graphspec_file
from PIL import Image
from render_helpers import BASE, polarization, with_series

import forgegraph as fg
from forgegraph.drawing.page import READOUTS
from forgegraph.spec.registry import builtin
from forgegraph.spec.tags import Tagged
from forgegraph.spec.validate import validate
from forgegraph.spec.views import applied, changes, combinations, controls

POWER = {"series.cell_voltage.column": "power_density", "axis.y.title": "Power density"}


def metric(control: str = "dropdown", **views: Any) -> dict[str, Any]:
    """A choice layer between voltage and power density, or the views given."""
    listed = views or {"Voltage": {}, "Power": POWER}
    return {"type": "choice", "label": "Metric", "control": control, "views": listed}


def doc(layers: dict[str, Any], **settings: Any) -> dict[str, Any]:
    d = fg.graphspec("t", "xy", settings=with_series({**BASE, **settings}))
    d["parameters"]["layers"] = layers
    return d


def problems(layers: dict[str, Any]) -> list[str]:
    d = doc(layers)
    reg = builtin().copy()
    reg.add("graphspec", d)
    return validate("graphspec", d, reg)


# --- the spec --------------------------------------------------------------------------------


def test_a_view_is_checked_as_the_graphspec_it_makes():
    assert problems({"m": metric(A={}, B={"axis.y.scal": "log"})}) == [
        "layers.m.views.B: axis.y.scal: unknown parameter; did you mean 'axis.y.scale'?"
    ]
    assert problems({"m": metric(A={}, B={"axis": {"y": {"scale": "lin"}}})}) == [
        "layers.m.views.B: axis.y.scale: must be one of: linear, log"
    ]


def test_a_view_cant_set_what_the_data_and_files_come_from():
    assert problems({"m": metric(A={}, B={"data.file": "x.parquet", "output": {"dpi": 3}})}) == [
        "layers.m.views.B.data.file: a view can't set data",
        "layers.m.views.B.output.dpi: a view can't set output",
    ]


def test_a_choice_layer_lists_two_or_more_views():
    assert problems({"m": metric(A={})}) == ["layers.m.views: must list two or more views"]
    assert problems({"m": {"type": "choice"}}) == ["layers.m.views: must list two or more views"]
    assert problems({"m": {"type": "choice", "views": ["A", "B"]}}) == [
        "layers.m.views: must be views keyed by name, each a mapping of parameters and values"
    ]
    assert problems({"m": metric(A={}, B=3)}) == [
        "layers.m.views.B: must be parameters and their values, or {}"
    ]


def test_two_choice_layers_cant_set_the_same_parameter_or_each_other():
    found = problems(
        {
            "m": metric(A={}, B={"axis.x.scale": "log"}),
            "n": metric(C={"axis.x.scale": "linear"}, D={}),
        }
    )
    assert found == [
        "layers.n.views: sets axis.x.scale, which layers.m's views also set; two choice "
        "layers can't set the same parameter"
    ]
    assert problems({"m": metric(A={}, B={"layers.n.label": "x"}), "n": metric()}) == [
        "layers.m.views.B.layers.n.label: a view can't set a choice or toggle layer"
    ]


def test_a_views_changes_are_dotted_paths_or_categories_and_keep_their_tags():
    assert changes({"axis": {"y": {"scale": "log"}}}) == {"axis.y.scale": "log"}
    assert changes({"axis.y.scale": "log"}) == {"axis.y.scale": "log"}
    assert changes({}) == changes(None) == {}
    d = doc({})
    d["parameters"]["axis"]["x"]["scale"] = Tagged("linear", True)
    out = applied(d, {"axis.x.scale": "log", "legend.method": "key"})
    assert out["parameters"]["axis"]["x"]["scale"].value == "log"
    assert out["parameters"]["axis"]["x"]["scale"].fixed
    assert out["parameters"]["legend"]["method"] == "key"
    assert d["parameters"]["axis"]["x"]["scale"].value == "linear"  # the GraphSpec is unchanged


def test_every_combination_is_drawn_the_first_view_of_each_first():
    d = doc({"m": metric(), "s": metric("radio", Linear={}, Log={"axis.x.scale": "log"})})
    listed = controls(d, builtin())
    assert [(c.name, c.label, c.kind, c.names) for c in listed] == [
        ("m", "Metric", "dropdown", ("Voltage", "Power")),
        ("s", "Metric", "radio", ("Linear", "Log")),
    ]
    assert [names for names, _ in combinations(listed)] == [
        ("Voltage", "Linear"),
        ("Voltage", "Log"),
        ("Power", "Linear"),
        ("Power", "Log"),
    ]
    assert combinations(listed)[3][1] == {**POWER, "axis.x.scale": "log"}


# --- drawing ---------------------------------------------------------------------------------


def test_the_graph_is_its_first_view_and_holds_the_others():
    g = fg.render(doc({"m": metric(Power=POWER, Voltage={})}), polarization())
    assert g.axes.get_ylabel() == "Power density"  # Power is listed first
    assert list(g.views) == [("Power",), ("Voltage",)]
    assert g.views[("Power",)] is g
    assert g.views[("Voltage",)].axes.get_ylabel() == "cell_voltage"


def test_every_view_has_the_same_figure_and_plot_box():
    wide = {"series.cell_voltage.column": "power_density", "axis.y.title": "Power density"}
    df = polarization().assign(power_density=lambda d: d["power_density"] * 1000)
    g = fg.render(doc({"m": metric(Voltage={}, Power=wide)}), df)
    boxes = {v.axes.get_position().bounds for v in g.views.values()}
    sizes = {tuple(v.figure.get_size_inches()) for v in g.views.values()}
    assert len(boxes) == 1 and len(sizes) == 1  # though the power ticks are wider


def test_lint_names_each_view():
    g = fg.render(doc({"m": metric()}), polarization())
    assert g.warnings  # a row left out, in each view drawn with it
    assert all(w.startswith(("view 'Voltage': ", "view 'Power': ")) for w in g.warnings)
    assert [i.message for i in g.check()] == g.warnings  # checking again finds the same


def test_a_view_that_cant_be_drawn_is_named():
    bad = metric(A={}, B={"series.cell_voltage.column": "nothing"})
    with pytest.raises(fg.SpecError) as e:
        fg.render(doc({"m": bad}), polarization())
    assert e.value.problems[0].startswith("view 'B': ")


def test_the_choice_layer_draws_nothing_in_the_figure():
    plain = fg.render(doc({}), polarization())
    chosen = fg.render(doc({"m": metric(A={}, B={})}), polarization())
    assert _pixels(plain) == _pixels(chosen)


def _pixels(g: fg.Graph) -> bytes:
    return Image.open(io.BytesIO(g._repr_png_())).tobytes()


# --- the page --------------------------------------------------------------------------------


def test_a_page_has_a_control_for_each_choice_layer_and_an_image_for_each_view(tmp_path):
    d = doc({"m": metric(), "s": metric("radio", Linear={}, Log={"axis.x.scale": "log"})})
    [path] = fg.render(d, polarization()).save(tmp_path / "g.html")
    page = path.read_text()
    assert '<label for="view0">Metric</label>\n<select id="view0">' in page
    assert (
        '<option value="0">Voltage</option>' in page and '<option value="1">Power</option>' in page
    )
    assert '<input type="radio" name="view1" id="view1-0" value="0" checked>Linear</label>' in page
    keys = re.findall(r'class="figure view" data-view="([^"]+)"( data-first)?', page)
    assert keys == [("0-0 1-0", " data-first"), ("0-0 1-1", ""), ("0-1 1-0", ""), ("0-1 1-1", "")]
    assert page.count(f'class="{READOUTS}"') == 4  # each view's own readouts
    chosen = ':has(#view0 option[value="1"]:checked):has(#view1-1:checked)'
    assert f'main{chosen} .view[data-view="0-1 1-1"] {{ display: block; }}' in page
    assert 'alt="t (Power, Log)"' in page


def test_files_show_the_first_view():
    g = fg.render(doc({"m": metric(Power=POWER, Voltage={})}), polarization())
    alone = fg.render(doc({}, **POWER), polarization())
    assert _pixels(g) == _pixels(alone)


def test_a_graph_without_choice_layers_has_no_controls(tmp_path):
    [path] = fg.render(doc({}), polarization()).save(tmp_path / "g.html")
    page = path.read_text()
    assert 'class="controls"' not in page and "data-view" not in page


# --- layouts ---------------------------------------------------------------------------------


def _tile(folder, name: str, layers: dict[str, Any]) -> None:
    path = graphspec_file(folder, name)
    from ruamel.yaml import YAML

    from forgegraph.spec.tags import with_tags

    d = with_tags(YAML()).load(path.read_text(encoding="utf-8"))
    d["parameters"]["layers"] = layers
    dump(d, path)


def _layout(folder, tabs: dict[str, Any]) -> Any:
    d = {
        "name": "fig",
        "version": 0,
        "description": "test",
        "extends": "forgegraph_default/layout",
        "parameters": {"output": {"file_types": ["html"]}, "tabs": tabs},
    }
    return dump(d, folder / "fig.layout.yaml")


def test_choice_layers_of_the_same_name_in_a_layout_share_one_control(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _tile(tmp_path, "a", {"metric": metric("radio")})
    _tile(tmp_path, "b", {"metric": metric()})
    _tile(tmp_path, "c", {})
    tabs = {
        "Both": {"grid": {"areas": [["a", "b"]]}, "tiles": {"a": "a.yaml", "b": "b.yaml"}},
        "Plain": {"grid": {"areas": [["c"]]}, "tiles": {"c": "c.yaml"}},
    }
    layout = fg.layout(_layout(tmp_path, tabs))
    assert [c.name for c in layout.controls] == ["metric"]
    both, plain = layout.tabs
    assert list(both.views) == [("Voltage",), ("Power",)] and not plain.views
    power = both.views[("Power",)]
    assert [t.axes.get_ylabel() for t in power.tiles.values()] == ["Power density"] * 2
    [path] = layout.save(tmp_path / "fig.html")
    page = path.read_text()
    assert page.count('class="control"') == 1 and 'id="view0-1"' in page  # radio: a's
    shown = '.tabs:not(:has(#tab1-plain:checked)) .control[data-control="0"]'  # on Both only
    assert f"{shown} {{ display: inline-flex; }}" in page
    assert "  .controls .control { display: none; }" in page


def test_choice_layers_sharing_a_control_need_the_same_views(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _tile(tmp_path, "a", {"metric": metric()})
    _tile(tmp_path, "b", {"metric": metric(Power=POWER, Voltage={})})
    tabs = {"Both": {"grid": {"areas": [["a", "b"]]}, "tiles": {"a": "a.yaml", "b": "b.yaml"}}}
    with pytest.raises(fg.SpecError) as e:
        fg.layout(_layout(tmp_path, tabs))
    assert e.value.problems == [
        "tabs.Both.tiles.b (b.yaml): layers.metric: its views (Power, Voltage) aren't those of "
        "the choice layer of that name in tabs.Both.tiles.a (a.yaml) (Voltage, Power); choice "
        "layers of the same name share one control, so their views need the same names in the "
        "same order"
    ]
