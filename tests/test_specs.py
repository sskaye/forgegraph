"""The specifications and the code that reads them.

Every parameter of every kind is exercised at the edges of its range, through the same
path a real file takes: a file that extends the definition file and lists the parameter.
"""

from __future__ import annotations

import copy
import re
from datetime import date, datetime

import pandas as pd
import pytest
from pack_helpers import doc

import forgegraph as fg
from forgegraph.spec.parameters import (
    BASE,
    CORE_KINDS,
    HEADER,
    KINDS,
    NONE,
    REFERENCE,
    Parameter,
    _read,
    _type_ok,
    definition_file,
    definitions,
    parse_range,
    tree_set,
)
from forgegraph.spec.registry import Registry, builtin
from forgegraph.spec.resolve import resolve
from forgegraph.spec.tags import fix, var
from forgegraph.spec.validate import drawing_problems, validate


def reference_name(kind: str) -> str:
    """The name of the file that specifies a kind: ForgeGraph's own, or the base pack's."""
    return REFERENCE[kind] if kind in CORE_KINDS else f"{BASE}/{REFERENCE[kind]}"


DOCUMENT_KINDS = [k for k in KINDS if k != "layer"]  # files people write; layers aren't
LAYER_TYPES = sorted(builtin().docs["layer"])
ALL = [(kind, p) for kind in DOCUMENT_KINDS for p in definitions(kind).values()]
ALL += [(f"layer:{t}", p) for t in LAYER_TYPES for p in definitions("layer", t).values()]
IDS = [f"{kind}:{p.path}" for kind, p in ALL]
NUMERIC = {"int ≥ 0", "int > 0", "float", "float ≥ 0", "float > 0"}


def reg_with(*docs: tuple[str, dict]) -> Registry:
    reg = builtin().copy()
    for kind, document in docs:
        reg.add(kind, document)
    return reg


def child(
    kind: str, tag: str | None = None, params: dict | None = None, name: str = "child"
) -> dict:
    """A file extending the definition file that lists the given parameters, tagged "fix"
    or "var", or untagged so each keeps the status it inherits."""
    listed = {{"fix": "fixed", "var": "variable", None: "untagged"}[tag]: params}
    return doc(reference_name(kind), name, description="A test file.", version=1, **listed)


# Values another parameter must have for this one to be valid at all.
CONTEXT = {"figure.width": {"figure.height": 140}, "cadence.interval.unit": {"cadence.at": None}}
# Parameters whose valid values depend on others', checked together in test_schedule.py.
CHECKED_TOGETHER = {"cadence.interval.count", "cadence.at"}


# What a layer's other required parameters are set to while one parameter is checked.
LAYER_REQUIRED = {
    "axis": "y",
    "value": 1.0,
    "text": "A note.",
    "value.lower": 0.1,
    "value.upper": 0.1,
}


def check(kind: str, p: Parameter, value) -> list[str]:
    """Problems with a file that sets p to value: one extending the definition file, or for a
    layer type's parameter, a GraphSpec with that layer, named t."""
    if kind.startswith("layer:"):
        layer_type = kind.split(":", 1)[1]
        entry: dict = {"type": layer_type}
        for q in definitions("layer", layer_type).values():
            if q.required and q.path != p.path:
                tree_set(entry, q.path, LAYER_REQUIRED[q.path])
        tree_set(entry, p.path, value)
        doc = child("graphspec", params={"layers": {"t": entry}})
        return validate("graphspec", doc, reg_with(("graphspec", doc)))
    doc = child(kind, None, {**CONTEXT.get(p.path, {}), p.path: value})
    return validate(kind, doc, reg_with((kind, doc)))


def wrap(p: Parameter, value):
    return [value] if p.takes_list else value


def where(p: Parameter, kind: str = "") -> str:
    return ("layers.t." if kind.startswith("layer:") else "") + p.path


# --- the definition files -------------------------------------------------------------


@pytest.mark.parametrize("kind", DOCUMENT_KINDS)
def test_definition_file_is_valid(kind):
    assert validate(kind, builtin().docs[kind][reference_name(kind)]) == []


@pytest.mark.parametrize("kind", DOCUMENT_KINDS)
def test_definition_file_header(kind):
    doc = builtin().docs[kind][reference_name(kind)]
    assert list(doc) == list(HEADER)
    assert doc["version"] == 0 and doc["extends"] == NONE
    header, _ = _read(kind, REFERENCE[kind])
    assert set(header) == {"name", "version", "description", "extends"}


@pytest.mark.parametrize("name", LAYER_TYPES)
def test_layer_file_header(name):
    """A layer type's file is its name, version and description, then its parameters."""
    doc = builtin().docs["layer"][name]
    assert list(doc) == ["name", "version", "description", "parameters"]
    assert doc["name"] == name and doc["version"] == 0
    header, params = _read("layer", name)
    assert set(header) == {"name", "version", "description"} and params


@pytest.mark.parametrize(
    ("kind", "name"), [(k, None) for k in DOCUMENT_KINDS] + [("layer", t) for t in LAYER_TYPES]
)
def test_definition_file_layout(kind, name):
    """Four-space steps, and comments ten spaces after the text."""
    text = definition_file(kind, name).read_text(encoding="utf-8")
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        assert indent % 4 == 0, f"line {n}: indent of {indent}"
        if " #" in line:
            assert re.search(r"\S {10}# ", line), (
                f"line {n}: comment must sit ten spaces after the text"
            )


@pytest.mark.parametrize(("kind", "p"), ALL, ids=IDS)
def test_definition_value_is_in_range(kind, p):
    assert check(kind, p, p.default) == []


def test_parameter_paths_are_unique_across_kinds():
    """A GraphSpec sets other kinds' parameters by path, so no two kinds share one, and no
    path is also a sub-category of another."""
    owners: dict[str, str] = {}
    for kind in DOCUMENT_KINDS:  # a layer's parameters sit under its name, not at the top
        if kind == "layout":
            continue  # a layout's parameters are its own; a GraphSpec never sets them
        for path in definitions(kind):
            assert owners.setdefault(path, kind) == kind, path
    for path in owners:
        assert not any(other.startswith(path + ".") for other in owners), path


def test_required_parameters():
    required = [p.path for p in definitions("graph_type").values() if p.required]
    assert required == ["axis.x.data.column", "axis.y.data.column"]


# --- ranges at their edges ------------------------------------------------------------


@pytest.mark.parametrize(("kind", "p"), ALL, ids=IDS)
def test_number_ranges_at_their_edges(kind, p):
    for i in p.range.intervals:
        assert check(kind, p, wrap(p, i.low)) == []
        assert check(kind, p, wrap(p, i.high)) == []
        assert check(kind, p, wrap(p, i.low - 0.001)) != []
        assert check(kind, p, wrap(p, i.high + 0.001)) != []


@pytest.mark.parametrize(("kind", "p"), ALL, ids=IDS)
def test_every_listed_value_is_accepted(kind, p):
    for literal in p.range.literals:
        value = {"true": True, "false": False}.get(literal, literal)
        if p.takes_list and literal == NONE:
            assert check(kind, p, NONE) == []  # the whole list is None
            assert check(kind, p, [NONE]) == [f"{where(p, kind)}[0]: None can't be a list item"]
            continue
        assert check(kind, p, wrap(p, value)) == []


@pytest.mark.parametrize(("kind", "p"), ALL, ids=IDS)
def test_values_outside_the_range_are_rejected(kind, p):
    if not {"text", "column", "columns"} & set(p.range.types):
        [err] = check(kind, p, wrap(p, "not-a-value"))
        assert "must be" in err
    if not p.range.intervals and not NUMERIC & set(p.range.types):
        assert check(kind, p, wrap(p, 12345)) != []
    if "true" not in p.range.literals:
        assert check(kind, p, wrap(p, True)) != []


FONTS = (["Source Sans 3"], ["No Such Font"])
SAMPLES = {
    "text": (["Any text"], [7]),
    "int ≥ 0": ([0, 12], [-1, 1.5, True]),
    "int > 0": ([1, 300], [0, -2, 2.5]),
    "float": ([-3.5, 0], ["3"]),
    "float ≥ 0": ([0, 0.001, 40], [-0.1, "1"]),
    "float > 0": ([0.001, 1.15, 40], [0, -0.1, "1"]),
    "floats > 0": ([[1, 2.5]], [[0], [], 1]),
    "date": (
        [date(2025, 8, 25), datetime(2025, 8, 25, 6), "2025-08-25", "2025-08-25T06:00"],
        ["25/08/2025", "2025-02-30", "2025-08-25T6:00", 20325, True],
    ),
    "hex color": (["#4C78A8", "#4C78A880"], ["blue", "#4C78A"]),
    "hex colors": ([["#4C78A8"], ["#4C78A8", "#000000"]], ["#4C78A8", [], ["#4C78A8", "blue"]]),
    "two hex colors": ([["#FFFFFF", "#000000"]], [["#FFFFFF"], ["#FFFFFF", "#000000", "#111111"]]),
    "column": (["current_density"], [""]),
    "columns": ([["a", "b"], "a"], [[]]),
    "graph type": (["xy"], ["pie"]),
    "theme": (["forgegraph_base/base_theme"], ["loud", "base_theme"]),
    "format": (["forgegraph_base/base_format"], ["poster"]),
    "graphspec": (["forgegraph_base/graphspec_example"], ["none-such"]),
    "layer type": (["note"], ["pie"]),
    "layer types": ([["note", "error_bar"], "note"], [[], ["pie"]]),
    "texts": ([["a.yaml"], ["prog", "-x"]], [[], [7], "a.yaml"]),
}


@pytest.mark.parametrize(("kind", "p"), ALL, ids=IDS)
def test_type_words(kind, p):
    if p.path in CHECKED_TOGETHER:
        pytest.skip("its values depend on the cadence's other parameters")
    others = set(p.range.types)
    for t in p.range.types:
        good, bad = FONTS if p.path.endswith("font") else SAMPLES[t]
        for value in good:
            assert check(kind, p, wrap(p, value)) == [], value
        for value in bad:
            if any(_type_ok(o, value, builtin().names()) for o in others - {t}):
                continue  # accepted through another alternative
            if t in NUMERIC and p.range.intervals:
                continue
            assert check(kind, p, wrap(p, value)) != [], value


@pytest.mark.parametrize(("kind", "p"), [x for x in ALL if x[1].takes_list], ids=lambda x: str(x))
def test_list_parameters(kind, p):
    assert check(kind, p, []) == [f"{where(p, kind)}: must have at least one item"]
    assert check(kind, p, p.default[0])[0].startswith(f"{where(p, kind)}: must be a list")
    bad = 12345 if {"text", "column"} & set(p.range.types) else "not-a-value"
    errors = check(kind, p, [*p.default, bad])
    assert errors[0].startswith(f"{where(p, kind)}[{len(p.default)}]:")


def test_a_single_value_parameter_refuses_a_list():
    x, y = (
        definitions("graph_type")["axis.x.data.column"],
        definitions("graph_type")["axis.y.data.column"],
    )
    assert check("graph_type", x, ["a", "b"]) == [
        "axis.x.data.column: must be a single value: a column name"
    ]
    assert check("graph_type", y, ["a", "b"]) == []


def test_range_parsing():
    r = parse_range("auto, 10-2000, hex color")
    assert r.literals == ("auto",) and r.types == ("hex color",)
    assert (r.intervals[0].low, r.intervals[0].high) == (10, 2000)
    assert parse_range("-1-1").intervals[0].low == -1
    assert parse_range("None, float > 0").types == ("float > 0",)
    assert parse_range("int ≥ 0, float ≥ 0").types == ("int ≥ 0", "float ≥ 0")
    with pytest.raises(ValueError):
        parse_range("5-1")
    with pytest.raises(ValueError):
        parse_range("a,,b")


def test_messages():
    assert check("format", definitions("format")["figure.width"], 0) == [
        "figure.width: must be auto or a number above 0"
    ]
    assert check("theme", definitions("theme")["axis.tick.direction"], "up") == [
        "axis.tick.direction: must be one of: in, out, both"
    ]


# --- files: header, listing, inheritance ----------------------------------------------


def test_header_fields():
    doc = child("theme")
    del doc["version"]
    doc["colour"] = 1
    assert validate("theme", doc) == [
        "version: required",
        "colour: unknown field; a file has only " + ", ".join(HEADER),
    ]
    doc = child("graphspec")
    doc["axis"] = {"x": {"data_column": "a"}}
    assert validate("graphspec", doc) == [
        "axis: a category of parameters; it goes under parameters"
    ]
    assert validate("theme", {**child("theme"), "version": -1}) == [
        "version: must be a whole number, 0 or more"
    ]
    assert validate("theme", {**child("theme"), "description": 3}) == ["description: must be text"]


def test_unknown_parameter_and_category():
    doc = child("theme", "fix", {"axis.tick.length_mul": 0.3})
    doc["parameters"]["axes"] = 3
    assert validate("theme", doc) == [
        "axis.tick.length_mul: unknown parameter; did you mean 'axis.tick.length'?",
        "axes: unknown category; did you mean 'axis'?",
    ]


@pytest.mark.parametrize(
    ("kind", "old", "value", "new"),
    [
        ("theme", "grid.line_width", 0.05, "grid.width"),
        ("theme", "axis.tick.minor.num", 4, "axis.tick.minor.count"),
        ("theme", "series.bar.edge_color", "#000000", "series.bar.edge.color"),
        ("graphspec", "encoding.marker_shape", "Cell", "encoding.marker.shape.column"),
        ("schedule", "freshness.stamp", False, "freshness.stamp.show"),
    ],
)
def test_a_renamed_parameter_suggests_its_new_name(kind, old, value, new):
    assert validate(kind, child(kind, "var", {old: value})) == [
        f"{old}: unknown parameter; did you mean '{new}'?"
    ]


@pytest.mark.parametrize(
    ("kind", "old", "value", "new"),
    [
        ("graphspec", "encoding.color", "Cell", "'encoding.color.column' or 'encoding.color.type'"),
        ("schedule", "cadence.interval", 1, "'cadence.interval.count' or 'cadence.interval.unit'"),
        (
            "theme",
            "legend.key.gap",
            0.5,
            "'legend.key.gap.inner' or 'legend.key.gap.outer' or 'legend.key.gap.row'",
        ),
        ("layout", "separators.line.border", True, None),
    ],
)
def test_a_name_that_is_now_a_category_suggests_its_parameters(kind, old, value, new):
    """A renamed parameter whose old name is now a category: its own parameters, not the
    sibling whose name is spelled closest."""
    [problem] = validate(kind, child(kind, "var", {old: value}))
    if new is not None:
        assert problem == f"{old}: unknown parameter; did you mean {new}?"
    else:  # not a category: the closest name, as before
        assert problem.startswith(f"{old}: unknown parameter; did you mean")


def test_a_parameter_written_twice_is_an_error(tmp_path):
    """One tree holds every parameter, so a parameter can be listed only once: YAML refuses a
    key written twice."""
    from ruamel.yaml.constructor import DuplicateKeyError

    from forgegraph.spec import registry

    path = tmp_path / "t.yaml"
    path.write_text("parameters:\n    grid:\n        show: true\n        show: false\n")
    with pytest.raises(DuplicateKeyError):
        registry.load_yaml(path)


def test_extends_must_exist_and_not_loop():
    assert validate("theme", {**child("theme"), "extends": "forgegraph_base/base_thmee"}) == [
        "extends: unknown theme 'forgegraph_base/base_thmee'; "
        "did you mean 'forgegraph_base/base_theme'?"
    ]
    a = {**child("theme"), "name": "a", "extends": "b"}
    b = {**child("theme"), "name": "b", "extends": "a"}
    [err] = validate("theme", a, reg_with(("theme", a), ("theme", b)))
    assert "extends itself" in err


def test_only_forgegraph_defines_graph_types():
    doc = copy.deepcopy(builtin().docs["graph_type"]["xy"])
    doc["name"] = "pie"
    [err] = validate("graph_type", doc, reg_with(("graph_type", doc)))
    assert err.startswith("extends: None, but only ForgeGraph defines graph types")


@pytest.mark.parametrize("none", [NONE, None], ids=["word", "null"])
@pytest.mark.parametrize("kind", DOCUMENT_KINDS)
def test_extending_none_requires_every_parameter(kind, none):
    doc = copy.deepcopy(builtin().docs[kind][reference_name(kind)])
    if kind == "graph_type":
        pytest.skip("a graph type extending None is its own definition")
    doc["name"] = "copy"
    doc["extends"] = none
    p = [q for q in definitions(kind).values() if q.inherits is None][-1]  # not a member
    *parents, name = p.path.split(".")
    tree = doc["parameters"]
    for key in parents:
        tree = tree[key]
    del tree[name]
    [err] = validate(kind, doc, reg_with((kind, doc)))
    assert err == f"extends: None, so every parameter must be listed; missing: {p.path}"


@pytest.mark.parametrize("null", ["null", "~", ""])
def test_yamls_null_is_none(tmp_path, null):
    """extends takes YAML's null as the word None."""
    pd.DataFrame({"x": [1, 2, 3], "y": [2, 1, 3]}).to_parquet(tmp_path / "d.parquet")
    (tmp_path / "g.yaml").write_text(
        f"""name: g
version: 0
description: YAML's null for None.
extends: {null}
parameters: !var
    specifications:
        graph_type: xy
        theme: forgegraph_base/base_theme
        format: forgegraph_base/base_format
    text: {{title: None}}
    data: {{file: d.parquet, preprocessing: None}}
    axis:
        x: {{data: {{column: x}}}}
        y: {{data: {{column: y}}}}
""",
        encoding="utf-8",
    )
    assert fg.render(tmp_path / "g.yaml").spec["extends"] is None


def test_inheritance_keeps_values_and_lets_a_file_move_a_parameter():
    theme = child("theme", "fix", {"axis.tick.direction": "in"})
    tree_set(theme["parameters"], "series.line.width", var(0.12))
    reg = reg_with(("theme", theme))
    assert validate("theme", theme, reg) == []
    r = {p: (v.value, v.fixed) for p, v in resolve("theme", theme, reg).items()}
    assert r["axis.tick.direction"] == ("in", True)
    assert r["series.line.width"] == (0.12, False)  # fixed in default, variable here
    assert r["axis.tick.length"] == (0.3, True)  # inherited
    assert r["grid.x.show"] == (False, False)
    assert r["title.font"] == ("Roboto", True)  # a member: the general text's font


def test_a_tag_with_no_value_changes_only_the_status():
    """A house theme can make a base parameter variable without restating its value; a
    GraphSpec in that theme may then set it."""
    theme = child("theme", None, {"axis.tick.length": var()}, name="open")
    reg = reg_with(("theme", theme))
    assert validate("theme", theme, reg) == []
    r = resolve("theme", theme, reg)["axis.tick.length"]
    assert (r.value, r.fixed, r.origin) == (0.3, False, "theme 'forgegraph_base/base_theme'")
    graph = spec({"specifications.theme": "open", "axis.tick.length": 0.5})
    assert validate("graphspec", graph, reg) == []


def test_a_category_tag_covers_everything_in_it_and_beats_the_files_it_extends():
    """A tag on a category applies to every parameter in it, unless one has its own; and
    the nearest file to tag a parameter decides, whatever the files it extends say."""
    theme = child("theme", None, {"series.marker.edge.width": fix(0.1)}, name="locked")
    theme["parameters"]["series"]["marker"] = fix(theme["parameters"]["series"]["marker"])
    theme["parameters"]["axis"] = var()  # a tag alone, on a whole category
    reg = reg_with(("theme", theme))
    assert validate("theme", theme, reg) == []
    r = resolve("theme", theme, reg)
    assert r.fixed("series.marker.size")  # variable in the base, fixed by the category here
    assert r.fixed("series.marker.edge.width")
    assert not r.fixed("axis.tick.length")  # fixed in the base, variable through axis here
    assert not r.fixed("axis.tick.label.size")
    assert not r.fixed("series.line.width")  # untouched: the base's


def test_a_file_extending_none_tags_every_parameter():
    base = copy.deepcopy(builtin().docs["theme"][reference_name("theme")])
    base["name"] = "bare"
    tree = dict(base["parameters"])  # the same parameters, without the root's !fix
    tree["grid"] = fix(tree["grid"])
    base["parameters"] = tree
    [err] = validate("theme", base, reg_with(("theme", base)))
    assert err.startswith(
        "extends: None, so every parameter needs a !var or !fix tag, on it or a category above "
        "it; untagged: text.font, "
    )
    assert "grid.x.show" not in err


def test_a_tag_goes_on_a_layer_not_inside_it():
    layer = {"type": "note", "text": fix("A note.")}
    doc = child("graphspec", None, {"layers": {"t": layer}})
    assert validate("graphspec", doc, reg_with(("graphspec", doc))) == [
        "layers.t.text: a tag goes on the layer or on layers, not inside"
    ]


def test_graph_type_heading_in_a_theme():
    theme = child("theme")
    left, bottom = {"tick": {"sides": ["left"]}}, {"tick": {"sides": ["bottom"]}}
    theme["parameters"] = {"axis": left, "xy": {"axis": bottom}}
    reg = reg_with(("theme", theme))
    assert validate("theme", theme, reg) == []
    assert resolve("theme", theme, reg).value("axis.tick.sides") == ["left"]
    assert resolve("theme", theme, reg, "xy").value("axis.tick.sides") == ["bottom"]


def test_graph_type_heading_only_in_themes_and_formats():
    gt = child("graph_type")
    gt["parameters"] = {"xy": {"marks": {"mode": "lines"}}}
    [err] = validate("graph_type", gt, reg_with(("graph_type", gt)))
    assert "unknown" in err


def test_format_width_and_height_cant_both_be_auto():
    fmt = child("format", "fix", {"figure.width": "auto", "figure.height": "auto"})
    assert validate("format", fmt, reg_with(("format", fmt))) == [
        "size: width and height can't both be auto"
    ]
    fmt = child("format", "fix", {"figure.width": "auto", "figure.height": 140})
    assert validate("format", fmt, reg_with(("format", fmt))) == []


# --- GraphSpecs -----------------------------------------------------------------------


def spec(params: dict | None = None) -> dict:
    return child("graphspec", params=params, name="graph")


def test_the_reference_graphspec_sets_every_parameter_with_its_owners_description():
    _, listed = _read("graphspec", "graphspec_example")
    for kind in ("graph_type", "theme", "format"):
        for path, p in definitions(kind).items():
            if p.fixed:
                assert path not in listed, path
                continue
            assert path in listed, f"graphspec_example.yaml doesn't set {path}"
            own = p.description.replace(" A GraphSpec must set it.", "")
            assert (listed[path].range, listed[path].description) == (p.range, own), path


def test_a_graphspec_sets_what_its_graph_type_theme_and_format_leave_variable():
    doc = spec(
        {
            "grid.y.show": True,
            "axis.x.min": 0,
            "mark.line.show": False,
            "provenance.level": "minimal",
        }
    )
    assert validate("graphspec", doc) == []


def test_a_graphspec_cannot_change_fixed_parameters():
    doc = spec({"axis.tick.length": 0.5, "figure.width": 100})
    assert validate("graphspec", doc) == [
        "axis.tick.length: fixed by theme 'forgegraph_base/base_theme'",
        "figure.width: fixed by format 'forgegraph_base/base_format'",
    ]
    lines_only = child("graph_type", "fix", {"mark.line.show": True}, name="line")
    doc = spec({"specifications.graph_type": "line", "mark.line.show": False})
    assert validate("graphspec", doc, reg_with(("graph_type", lines_only))) == [
        "mark.line.show: fixed by graph type 'line'"
    ]


def test_settings_are_checked_against_their_own_range():
    assert validate("graphspec", spec({"axis.x.scale": "logarithmic"})) == [
        "axis.x.scale: must be one of: linear, log"
    ]


def test_a_graphspec_names_existing_files():
    assert validate("graphspec", spec({"specifications.theme": "loud"})) == [
        "specifications.theme: must be the name of a theme"
    ]
    theme = "forgegraph_base/base_theme"
    assert validate("graphspec", spec({"specifications.theme": [theme]})) == [
        "specifications.theme: must be a single value: the name of a theme"
    ]


def test_a_graphspec_respects_fixed_values_of_the_graphspec_it_extends():
    base = child("graphspec", "fix", {"mark.line.show": True}, name="base")
    doc = {**spec({"mark.line.show": False}), "extends": "base"}
    reg = reg_with(("graphspec", base), ("graphspec", doc))
    assert validate("graphspec", base, reg) == []
    assert validate("graphspec", doc, reg) == ["mark.line.show: fixed by GraphSpec 'base'"]


def test_naming_method_is_limited_to_the_themes_methods():
    theme = child("theme", "fix", {"legend.methods": ["key"]}, name="plain")
    reg = reg_with(("theme", theme))
    doc = spec({"specifications.theme": "plain"})
    assert validate("graphspec", doc, reg) == ["legend.method: theme 'plain' allows only key"]
    doc = spec({"specifications.theme": "plain", "legend.method": "key"})
    assert validate("graphspec", doc, reg) == []


def test_drawing_needs_the_required_columns():
    assert drawing_problems(builtin().docs["graphspec"]["forgegraph_base/graphspec_example"]) == []
    doc = spec({"axis.x.data.column": NONE})
    assert validate("graphspec", doc) == []
    assert drawing_problems(doc) == [
        "axis.x.data.column: must be set before the graph can be drawn"
    ]


def test_benchmark_column_and_value_go_together():
    assert validate("graphspec", spec({"benchmark.value": NONE})) == [
        "benchmark: set data_column and value together, or neither"
    ]
    both_unset = spec({"benchmark.data_column": NONE, "benchmark.value": NONE})
    assert validate("graphspec", both_unset) == []


def test_a_graphspec_without_a_data_file_is_drawn_from_a_dataframe():
    doc = spec({"data.file": NONE})
    assert validate("graphspec", doc) == [] and drawing_problems(doc) == []


def test_several_y_columns_need_a_title_or_none():
    two = ["cell_voltage", "temperature"]
    assert validate(
        "graphspec", spec({"axis.y.data.column": two, "axis.y.title": "column_name"})
    ) == ["axis.y.title: several y columns have no single name; set a title, or None"]
    assert validate("graphspec", spec({"axis.y.data.column": two, "axis.y.title": NONE})) == []
    assert (
        validate("graphspec", spec({"axis.y.data.column": two, "axis.y.title": "Voltage (V)"}))
        == []
    )
    assert (
        validate(
            "graphspec", spec({"axis.y.data.column": "cell_voltage", "axis.y.title": "column_name"})
        )
        == []
    )


def test_impossible_requests_are_errors():
    assert validate("graphspec", spec({"mark.line.show": False, "mark.marker.show": False})) == [
        "mark.line.show, mark.marker.show, mark.bar.show: all false, so nothing would be drawn"
    ]
    assert (
        validate(
            "graphspec",
            spec({"mark.line.show": False, "mark.marker.show": False, "mark.bar.show": True}),
        )
        == []
    )
    assert validate("graphspec", spec({"axis.x.min": 5.0, "axis.x.max": 5.0})) == [
        "axis.x.min: must be below axis.x.max (5.0 is not below 5.0)"
    ]
    assert validate("graphspec", spec({"axis.y.scale": "log", "axis.y.min": 0})) == [
        "axis.y.min: a log axis needs values above 0, not 0"
    ]
    theme = child("theme", "fix", {"text.font": "Comic Nonexistent"}, name="odd")
    assert validate("theme", theme, reg_with(("theme", theme))) == [
        "text.font: no font 'Comic Nonexistent' is bundled or installed"
    ]
    bold = {
        f"{p}.weight": "bold"
        for p in ("title", "axis.title", "legend.label", "legend.color_bar.title")
    }
    theme = child("theme", "fix", {"text.font": "DejaVu Sans", **bold}, name="odd")
    assert validate("theme", theme, reg_with(("theme", theme))) == [
        "legend.key.title.weight: DejaVu Sans has no semibold weight; it has regular, bold"
    ]
    tree_set(theme["parameters"], "legend.key.title.weight", "bold")
    assert validate("theme", theme, reg_with(("theme", theme))) == []


# --- reading files ----------------------------------------------------------------------------


def test_an_unchanged_file_is_parsed_once(tmp_path, monkeypatch):
    from forgegraph.spec import registry

    path = tmp_path / "t.yaml"
    path.write_text("a: 1\nb: [x, y]\n")
    parsed = []
    parse = registry._yaml.load
    monkeypatch.setattr(registry._yaml, "load", lambda f: parsed.append(1) or parse(f))
    first = registry.load_yaml(path)
    first["a"] = 99  # a caller changing what it was given
    first["b"].append("z")
    assert registry.load_yaml(path) == {"a": 1, "b": ["x", "y"]}
    assert len(parsed) == 1


def test_an_edited_file_is_parsed_again(tmp_path):
    import os

    from forgegraph.spec import registry

    path = tmp_path / "t.yaml"
    path.write_text("a: 1\n")
    assert registry.load_yaml(path) == {"a": 1}
    path.write_text("a: 2\n")  # the same size: only the time tells
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert registry.load_yaml(path) == {"a": 2}


def test_validating_a_graphspec_resolves_its_values_once(monkeypatch):
    from forgegraph.spec import validate as validation
    from forgegraph.spec.registry import builtin

    doc = builtin().docs["graphspec"]["forgegraph_base/graphspec_example"]
    calls = []
    explain = validation.explain
    monkeypatch.setattr(validation, "explain", lambda *a, **k: calls.append(1) or explain(*a, **k))
    assert validation.validate("graphspec", doc) == []
    assert len(calls) == 1


def test_a_graphspecs_own_parameters_are_worked_out_once(monkeypatch):
    from forgegraph.spec import parameters

    first = parameters.definitions("graphspec")
    calls = []
    files = parameters.graph_type_files
    monkeypatch.setattr(parameters, "graph_type_files", lambda: calls.append(1) or files())
    assert parameters.definitions("graphspec") == first
    assert calls == []


def test_a_document_is_loaded_with_the_registry_it_is_checked_against(tmp_path, monkeypatch):
    """From a file: its folder's registry, holding it; as a document: the given registry or
    the working folder's, holding it unless one of its name is there. The given registry is
    never changed."""
    from ruamel.yaml import YAML

    from forgegraph.spec.loaded import load_document
    from forgegraph.spec.registry import builtin
    from forgegraph.spec.tags import with_tags

    doc = {**builtin().docs["graphspec"]["forgegraph_base/graphspec_example"], "name": "mine"}
    path = tmp_path / "mine.yaml"
    with path.open("w", encoding="utf-8") as f:  # its descriptions hold subscripts
        with_tags(YAML()).dump(doc, f)
    loaded = load_document("graphspec", path)
    assert loaded.doc["name"] == "mine" and loaded.reg.paths["graphspec"]["mine"] == path
    assert loaded.folder == tmp_path

    given = builtin()
    loaded = load_document("graphspec", doc, given)
    assert loaded.reg.docs["graphspec"]["mine"] is doc and "mine" not in given.docs["graphspec"]
    monkeypatch.chdir(tmp_path)
    assert load_document("graphspec", doc).folder == tmp_path

    named = builtin().docs["graphspec"]["forgegraph_base/graphspec_example"]
    stranger = {**named, "description": "a document of a name the registry holds"}
    reg = load_document("graphspec", stranger, builtin()).reg
    assert reg.docs["graphspec"]["forgegraph_base/graphspec_example"] is not stranger
