"""Catalog files: the rules a catalog file follows, what reading one gives, and the rule
choosing each card's value and baseline."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest
from pack_helpers import write_pack

from forgegraph.catalog_build.cards import (
    SAMPLE_COLOR,
    SAMPLE_TEXT,
    Change,
    Scene,
    candidates,
    card,
    gets_card,
    place,
    placed,
    tied,
)
from forgegraph.catalog_build.files import Catalog, CatalogError, read
from forgegraph.packs import read_pack
from forgegraph.spec.parameters import definitions, series_definitions
from forgegraph.spec.registry import builtin

HEADER = (
    "name: {name}\nversion: 0\ndescription: Test.\nextends: {extends}\n"
    "baseline: forgegraph_base/graphspec_example\n"
)
XY = {
    **definitions("graph_type", "xy"),
    **{f"series.{p}": replace(q, path=f"series.{p}") for p, q in series_definitions().items()},
}
THEME = definitions("theme")
# A GraphSpec's data and values: x and y use two of its four columns.
SCENE = Scene(
    pd.DataFrame(
        {"Cell": ["A", "B", "A"], "x": [1.0, 2.0, 9.0], "y": [3.0, 5.0, 4.0], "t": [10, 20, 30]}
    ),
    {"axis.x.data.column": "x", "axis.y.data.column": None, "series.column": "y"}
    | {"layers.line.axis": "y"},
    frozenset({"x", "y"}),
)


def catalog_project(tmp_path, catalog: str, kind_folder: str = "formats", name: str = "plain"):
    """A pack, house, with a format (or theme) extending the base one, and its catalog."""
    folder = write_pack(tmp_path)
    kind = "format" if kind_folder == "formats" else "theme"
    (folder / kind_folder).mkdir()
    (folder / kind_folder / f"{name}.yaml").write_text(
        f"name: {name}\nversion: 0\ndescription: Test.\nextends: forgegraph_base/base_{kind}\n"
        "parameters: None\n"
    )
    (folder / "catalogs" / kind_folder).mkdir(parents=True)
    (folder / "catalogs" / kind_folder / f"{name}.yaml").write_text(catalog)
    reg = builtin().add_pack(read_pack(folder, "folder"))
    reg.allowed = frozenset({"forgegraph_base", "house"})
    return reg


def _problems(tmp_path, catalog: str, **kw) -> list[str]:
    reg = catalog_project(tmp_path, catalog, **kw)
    with pytest.raises(CatalogError) as e:
        read(
            "format" if kw.get("kind_folder", "formats") == "formats" else "theme",
            f"house/{kw.get('name', 'plain')}",
            reg,
        )
    return e.value.problems


# --- reading a catalog file ---------------------------------------------------------------


def test_a_catalog_extending_another_adds_its_baselines_after_the_ones_it_inherits(tmp_path):
    catalog = HEADER.format(name="plain", extends="forgegraph_base/base_theme") + (
        "baselines:\n    wide: {figure.width: 200}\n"
    )
    reg = catalog_project(tmp_path, catalog, kind_folder="themes")
    names = [b.path for b in read("theme", "house/plain", reg).baselines]
    inherited = [b.path for b in read("theme", "forgegraph_base/base_theme", builtin()).baselines]
    assert names == [*inherited, "figure.width"]


def test_every_file_needs_a_catalog(tmp_path):
    reg = catalog_project(tmp_path, "")
    (tmp_path / "house" / "catalogs" / "formats" / "plain.yaml").unlink()
    with pytest.raises(CatalogError, match="missing; every format needs a catalog"):
        read("format", "house/plain", reg)


def test_catalog_rules_are_errors(tmp_path):
    catalog = HEADER.format(name="plain", extends="None") + (
        "baselines:\n"
        "    two: [90, 80]\n"
        "    unknown: {figure.depth: 3}\n"
        "    wrong: {figure.width: -5}\n"
        "variations: None\n"
    )
    problems = _problems(tmp_path / "1", catalog)
    assert any("variations: unknown field" in p for p in problems)
    problems = _problems(tmp_path / "2", catalog.replace("variations: None\n", ""))
    assert any("baselines.two: must be parameters and their values" in p for p in problems)
    assert any("baselines.unknown: unknown parameter 'figure.depth'" in p for p in problems)
    assert any("baselines.wrong.figure.width: must be" in p for p in problems)


def test_builtin_catalogs_follow_the_rules():
    for kind, names in (("theme", builtin().docs["theme"]), ("format", builtin().docs["format"])):
        for name in names:
            read(kind, name, builtin())
    read("graph_type", "xy", builtin())
    for name in builtin().docs["layer"]:
        read("layer", name, builtin())


def test_a_numbered_baseline_can_change_several_parameters():
    catalog = read("graph_type", "xy", builtin())
    overlaid = next(b for b in catalog.baselines if b.path == "overlaid")
    parts = {c.path: c.value for c in overlaid.parts}
    [entry] = parts["series"].values()
    assert entry["color"] == "Run" and entry["bar"]["show"] is True
    assert parts["axis.x.data.column"] == "Cell"


def test_a_layer_catalog_draws_its_layer_on_every_card():
    catalog = read("layer", "note", builtin())
    always = {c.path: c.value for c in catalog.always}
    assert always["layers.note.type"] == "note"
    assert always["layers.note.position"] == "bottom_left"
    paths = [options[0][0].path for _, options in catalog.cards]
    assert paths == ["layers.note.text", "layers.note.position", "layers.note.inside"]


def test_a_layer_catalogs_settings_are_on_every_card():
    always = {c.path: c.value for c in read("layer", "error_bar", builtin()).always}
    assert always["series.aggregation.function"] == "mean"
    assert always["layers.error_bar.type"] == "error_bar"


def test_every_parameter_gets_a_card_and_the_page_shows_the_variable_ones():
    catalog = read("theme", "forgegraph_base/base_theme", builtin())
    carded = {p.path for p, _ in catalog.cards}
    assert carded == {p.path for p in catalog.parameters}
    assert "grid.x.show" in catalog.variable and "text.font" not in catalog.variable
    shown = [c.changes[-1].path for c in place(catalog, lambda s, c: True)[1:]]
    assert set(shown) == catalog.variable
    fixed = card(catalog, "text.font", lambda s, c: True)  # placed alone, as any card
    assert fixed.change.value == "IBM Plex Serif" and fixed.base is None


def test_a_formats_output_and_provenance_get_no_card():
    assert not gets_card("format", definitions("format")["output.file_types"])
    assert not gets_card("format", definitions("format")["provenance.level"])
    assert not gets_card("graph_type", XY["layer.types"])  # it permits; it never draws
    assert gets_card("theme", THEME["grid.x.show"])
    assert gets_card("format", definitions("format")["figure.width"])
    paths = [p.path for p, _ in read("format", "forgegraph_base/base_format", builtin()).cards]
    assert paths == ["figure.width", "figure.height", "figure.base_size"]


def test_candidates_outside_the_range_are_dropped():
    catalog = read("layer", "reference_line", builtin())
    options = next(o for p, o in catalog.cards if p.path == "value")
    assert all(changes[0].value != "None" for changes in options)  # d itself: not a value


# --- the rule: each card's candidate values, by range ---------------------------------------


def test_true_or_false_is_the_other():
    assert candidates(XY["series.line.show"], True, SCENE) == [False, True]


def test_an_axis_column_is_each_unused_column_of_numbers():
    assert candidates(XY["axis.x.data.column"], None, SCENE) == ["t", "None"]


def test_a_series_column_is_each_unused_column_then_the_words():
    p = XY["series.color"]
    assert candidates(p, "series", SCENE) == ["Cell", "t", SAMPLE_COLOR, "series"]


def test_a_format_is_a_number_format_then_a_date_format():
    assert candidates(XY["axis.x.tick.label.format"], "auto", SCENE) == [".3f", "%b %-d", "auto"]


def test_other_text_is_the_sample_then_the_words():
    p = XY["axis.x.title"]
    assert candidates(p, "column_name", SCENE) == [SAMPLE_TEXT, "None", "column_name"]


def test_a_hex_color_is_the_sample_color():
    p = THEME["legend.key.background"]
    assert candidates(p, "None", SCENE) == [SAMPLE_COLOR, "None"]


def test_a_number_is_doubled_then_halved_within_its_interval():
    assert candidates(THEME["series.bar.gap"], 0.1, SCENE) == [0.2, 0.05, 0.1]
    p = THEME["legend.direct.max_relative_distance"]  # 0-1
    assert candidates(p, 0.8, SCENE) == [1.0, 0.4, 0.8]
    assert candidates(THEME["axis.tick.minor.count"], 0, SCENE) == [1, 0]
    assert candidates(THEME["axis.tick.label.max_wrap"], 1, SCENE) == [2, 0, 1]  # whole


def test_a_figure_size_defaulting_to_auto_is_the_other_size():
    scene = Scene(SCENE.data, {"figure.width": 150}, SCENE.used)
    assert candidates(definitions("format")["figure.height"], "auto", scene) == [150, "auto"]


def test_a_font_is_each_bundled_family_but_its_own():
    found = candidates(THEME["text.font"], "Roboto", SCENE)
    assert found == ["IBM Plex Serif", "Source Sans 3", SAMPLE_TEXT, "Roboto"]


def test_a_number_defaulting_to_none_comes_from_its_axis_column():
    assert candidates(XY["axis.x.min"], None, SCENE) == [2.0, "None"]  # the median
    assert candidates(XY["axis.y.max"], None, SCENE) == [4.0, "None"]
    step = candidates(XY["axis.x.tick.step"], None, SCENE)
    assert step == [SAMPLE_TEXT, 2.0, "None"]  # a quarter of 1-9, to one figure
    value = definitions("layer", "reference_line")["value"]
    assert candidates(value, None, SCENE, "line") == ["t", 4.0, "None"]  # the layer's axis


def test_words_follow_the_default_round_the_range():
    assert candidates(XY["legend.method"], "auto", SCENE) == ["direct", "key", "none", "auto"]
    assert candidates(XY["arrangement.base_axis"], "y", SCENE) == ["x", "y"]


def test_a_list_takes_each_word_after_its_first_as_a_list():
    p = XY["legend.key.positions"]
    d = ["top_right", "top_left"]
    found = candidates(p, d, SCENE)
    assert found[:2] == [["bottom_left"], ["bottom_center"]]
    assert found[-3:] == [["top_center"], ["top_left", "top_right"], d]  # then d reversed
    assert ["top_right"] not in found


def test_a_mixed_range_takes_its_types_before_its_words():
    p = THEME["legend.color_bar.colors"]
    found = candidates(p, "viridis", SCENE)
    assert found[:3] == [SAMPLE_COLOR, "cividis", "plasma"] and found[-1] == "viridis"


def test_setting_one_of_a_tie_to_none_sets_the_other_too():
    assert tied("benchmark.data_column", "None") == (
        Change("benchmark.data_column", "None"),
        Change("benchmark.value", "None"),
    )
    assert tied("benchmark.value", "None")[1] == Change("benchmark.data_column", "None")
    assert tied("benchmark.data_column", "Cell") == (Change("benchmark.data_column", "Cell"),)
    assert tied("series.line.show", "None") == (Change("series.line.show", "None"),)


# --- placing the cards -----------------------------------------------------------------------

B2, B3 = Change("legend.method", "key"), Change("grid.y.show", True)
ONE, TWO = (Change("series.line.width", 1),), (Change("series.line.width", 2),)
P = THEME["series.line.width"]


def _catalog(*options: tuple[Change, ...]) -> Catalog:
    cards, variable = ((P, options),), frozenset({P.path})
    return Catalog(
        "theme", "t", "forgegraph_base/graphspec_example", (P,), cards, variable, (B2, B3)
    )


def test_a_card_is_its_first_candidate_on_the_first_baseline_it_changes():
    tried = []

    def differs(start, changes):
        tried.append((start, changes))
        return start == (B3,) or changes == TWO

    [v] = placed(_catalog(ONE, TWO), differs)
    assert v.changes == ONE and v.base == B3  # the first candidate, though TWO differs sooner
    assert tried == [((), ONE), ((B2,), ONE), ((B3,), ONE)]


def test_a_card_on_a_numbered_baseline_is_drawn_after_it():
    cards = place(_catalog(ONE), lambda start, changes: start == (B2,))
    assert [c.heading for c in cards] == [
        "Baseline",
        "Baseline 2: Baseline + legend.method = key",
        "Baseline 2 + series.line.width = 1",
    ]
    assert cards[2].start == (B2,) and cards[2].changes == (B2, *ONE)


def test_a_parameter_no_candidate_shows_is_an_error():
    with pytest.raises(CatalogError) as e:
        placed(_catalog(ONE, TWO), lambda start, changes: False)
    assert e.value.problems == [
        "theme t: series.line.width: no candidate changes the drawing on any baseline; "
        "add a baseline that shows it"
    ]


def test_a_packs_card_its_looks_cant_show_is_placed_as_forgegraphs_is():
    [v] = placed(_catalog(ONE, TWO), lambda s, c: False, lambda s, c: c == TWO and s == (B2,))
    assert v.changes == TWO and v.base == B2
