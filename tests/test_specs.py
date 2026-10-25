"""The specifications and the code that reads them.

Every parameter of every kind is exercised at the edges of its range, through the same
path a real file takes: a file that extends the definition file and lists the parameter.
"""

from __future__ import annotations

import copy
import re

import pytest

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
from forgegraph.spec.validate import drawing_problems, validate


def reference_name(kind: str) -> str:
    """The name of the file that specifies a kind: ForgeGraph's own, or the base pack's."""
    return REFERENCE[kind] if kind in CORE_KINDS else f"{BASE}/{REFERENCE[kind]}"


DOCUMENT_KINDS = [k for k in KINDS if k != "layer"]  # files people write; layers aren't
LAYER_TYPES = sorted(builtin().docs["layer"])
ALL = [(kind, p) for kind in DOCUMENT_KINDS for p in definitions(kind).values()]
ALL += [(f"layer:{t}", p) for t in LAYER_TYPES for p in definitions("layer", t).values()]
IDS = [f"{kind}:{p.path}" for kind, p in ALL]
NUMERIC = {"int", "positive int", "float", "positive float"}


def reg_with(*docs: tuple[str, dict]) -> Registry:
    reg = builtin().copy()
    for kind, doc in docs:
        reg.add(kind, doc)
    return reg


def child(
    kind: str, section: str = "variable_parameters", params: dict | None = None, name: str = "child"
) -> dict:
    """A file extending the definition file that lists the given parameters."""
    tree: dict = {}
    for path, value in (params or {}).items():
        tree_set(tree, path, value)
    doc = {
        "name": name,
        "version": 1,
        "description": "A test file.",
        "extends": reference_name(kind),
        "fixed_parameters": NONE,
        "variable_parameters": NONE,
    }
    doc[section] = tree or NONE
    return doc


# Values another parameter must have for this one to be valid at all.
CONTEXT = {"figure.width": {"figure.height": 140}, "cadence.interval_unit": {"cadence.at": None}}
# Parameters whose valid values depend on others', checked together in test_schedule.py.
CHECKED_TOGETHER = {"cadence.interval", "cadence.at"}


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
    section = "fixed_parameters" if p.fixed else "variable_parameters"
    doc = child(kind, section, {**CONTEXT.get(p.path, {}), p.path: value})
    return validate(kind, doc, reg_with((kind, doc)))


def wrap(p: Parameter, value):
    return [value] if p.takes_list else value


def where(p: Parameter, kind: str = "") -> str:
    if kind.startswith("layer:"):
        return "variable_parameters.layers.t." + p.path
    return ("fixed_parameters." if p.fixed else "variable_parameters.") + p.path


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
    "int": ([0, 12], [-1, 1.5, True]),
    "positive int": ([1, 300], [0, -2, 2.5]),
    "float": ([-3.5, 0], ["3"]),
    "positive float": ([0.001, 1.15, 40], [0, -0.1, "1"]),
    "hex color": (["#4C78A8", "#4C78A880"], ["blue", "#4C78A"]),
    "hex colors": ([["#4C78A8"], ["#4C78A8", "#000000"]], ["#4C78A8", [], ["#4C78A8", "blue"]]),
    "two hex colors": ([["#FFFFFF", "#000000"]], [["#FFFFFF"], ["#FFFFFF", "#000000", "#111111"]]),
    "column": (["current_density"], [""]),
    "columns": ([["a", "b"], "a"], [[]]),
    "graph type": (["xy"], ["pie"]),
    "theme": (["forgegraph_base/base_theme"], ["loud", "base_theme"]),
    "format": (["forgegraph_base/base_format"], ["poster"]),
    "graphspec": (["forgegraph_base/polarization"], ["none-such"]),
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
        good, bad = FONTS if p.path == "font.family" else SAMPLES[t]
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
        "variable_parameters.axis.x.data.column: must be a single value: a column name"
    ]
    assert check("graph_type", y, ["a", "b"]) == []


def test_range_parsing():
    r = parse_range("auto, 10-2000, hex color")
    assert r.literals == ("auto",) and r.types == ("hex color",)
    assert (r.intervals[0].low, r.intervals[0].high) == (10, 2000)
    assert parse_range("-1-1").intervals[0].low == -1
    assert parse_range("None, positive float").types == ("positive float",)
    with pytest.raises(ValueError):
        parse_range("5-1")
    with pytest.raises(ValueError):
        parse_range("a,,b")


def test_messages():
    assert check("format", definitions("format")["figure.width"], 0) == [
        "fixed_parameters.figure.width: must be auto or a number above 0"
    ]
    assert check("theme", definitions("theme")["axis.tick.direction"], "up") == [
        "fixed_parameters.axis.tick.direction: must be one of: in, out, both"
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
        "axis: a category of parameters; it goes under variable_parameters or fixed_parameters"
    ]
    assert validate("theme", {**child("theme"), "version": -1}) == [
        "version: must be a whole number, 0 or more"
    ]
    assert validate("theme", {**child("theme"), "description": 3}) == ["description: must be text"]


def test_unknown_parameter_and_category():
    doc = child("theme", "fixed_parameters", {"axis.tick.length_mul": 0.3})
    doc["fixed_parameters"]["axes"] = 3
    assert validate("theme", doc) == [
        "fixed_parameters.axis.tick.length_mul: unknown parameter; "
        "did you mean 'axis.tick.length'?",
        "fixed_parameters.axes: unknown category; did you mean 'axis'?",
    ]


def test_a_parameter_is_listed_once():
    doc = child("theme", "fixed_parameters", {"grid.show": True})
    doc["variable_parameters"] = {"grid": {"show": False}}
    assert validate("theme", doc) == [
        "variable_parameters.grid.show: also listed in fixed_parameters"
    ]


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


@pytest.mark.parametrize("kind", DOCUMENT_KINDS)
def test_extending_none_requires_every_parameter(kind):
    doc = copy.deepcopy(builtin().docs[kind][reference_name(kind)])
    if kind == "graph_type":
        pytest.skip("a graph type extending None is its own definition")
    doc["name"] = "copy"
    p = list(definitions(kind).values())[-1]
    *parents, name = p.path.split(".")
    section = doc["fixed_parameters" if p.fixed else "variable_parameters"]
    for key in parents:
        section = section[key]
    del section[name]
    [err] = validate(kind, doc, reg_with((kind, doc)))
    assert err == f"extends: None, so every parameter must be listed; missing: {p.path}"


def test_inheritance_keeps_values_and_lets_a_file_move_a_parameter():
    theme = child("theme", "fixed_parameters", {"axis.tick.direction": "in"})
    theme["variable_parameters"] = {"series": {"line": {"width": 0.12}}}
    reg = reg_with(("theme", theme))
    assert validate("theme", theme, reg) == []
    r = resolve("theme", theme, reg)
    assert r["axis.tick.direction"] == ("in", True)
    assert r["series.line.width"] == (0.12, False)  # fixed in default, variable here
    assert r["axis.tick.length"] == (0.3, True)  # inherited
    assert r["grid.show"] == (False, False)


def test_graph_type_heading_in_a_theme():
    theme = child("theme")
    left, bottom = {"tick": {"sides": ["left"]}}, {"tick": {"sides": ["bottom"]}}
    theme["fixed_parameters"] = {"axis": left, "xy": {"axis": bottom}}
    reg = reg_with(("theme", theme))
    assert validate("theme", theme, reg) == []
    assert resolve("theme", theme, reg)["axis.tick.sides"][0] == ["left"]
    assert resolve("theme", theme, reg, "xy")["axis.tick.sides"][0] == ["bottom"]


def test_graph_type_heading_only_in_themes_and_formats():
    gt = child("graph_type")
    gt["variable_parameters"] = {"xy": {"marks": {"mode": "lines"}}}
    [err] = validate("graph_type", gt, reg_with(("graph_type", gt)))
    assert "unknown" in err


def test_format_width_and_height_cant_both_be_auto():
    fmt = child("format", "fixed_parameters", {"figure.width": "auto", "figure.height": "auto"})
    assert validate("format", fmt, reg_with(("format", fmt))) == [
        "size: width and height can't both be auto"
    ]
    fmt = child("format", "fixed_parameters", {"figure.width": "auto", "figure.height": 140})
    assert validate("format", fmt, reg_with(("format", fmt))) == []


# --- GraphSpecs -----------------------------------------------------------------------


def spec(params: dict | None = None) -> dict:
    return child("graphspec", params=params, name="graph")


def test_the_reference_graphspec_sets_every_parameter_with_its_owners_description():
    _, listed = _read("graphspec", "polarization")
    for kind in ("graph_type", "theme", "format"):
        for path, p in definitions(kind).items():
            if p.fixed:
                assert path not in listed, path
                continue
            assert path in listed, f"polarization.yaml doesn't set {path}"
            own = p.description.replace(" A GraphSpec must set it.", "")
            assert (listed[path].range, listed[path].description) == (p.range, own), path


def test_a_graphspec_sets_what_its_graph_type_theme_and_format_leave_variable():
    doc = spec(
        {
            "grid.show": True,
            "axis.x.min": 0,
            "mark.line.show": False,
            "provenance.level": "minimal",
        }
    )
    assert validate("graphspec", doc) == []


def test_a_graphspec_cannot_change_fixed_parameters():
    doc = spec({"axis.tick.length": 0.5, "figure.width": 100})
    assert validate("graphspec", doc) == [
        "variable_parameters.axis.tick.length: fixed by theme 'forgegraph_base/base_theme'",
        "variable_parameters.figure.width: fixed by format 'forgegraph_base/base_format'",
    ]
    lines_only = child("graph_type", "fixed_parameters", {"mark.line.show": True}, name="line")
    doc = spec({"specifications.graph_type": "line", "mark.line.show": False})
    assert validate("graphspec", doc, reg_with(("graph_type", lines_only))) == [
        "variable_parameters.mark.line.show: fixed by graph type 'line'"
    ]


def test_settings_are_checked_against_their_own_range():
    assert validate("graphspec", spec({"axis.x.scale": "logarithmic"})) == [
        "variable_parameters.axis.x.scale: must be one of: linear, log"
    ]


def test_a_graphspec_names_existing_files():
    assert validate("graphspec", spec({"specifications.theme": "loud"})) == [
        "variable_parameters.specifications.theme: must be the name of a theme"
    ]


def test_a_graphspec_respects_fixed_values_of_the_graphspec_it_extends():
    base = child("graphspec", "fixed_parameters", {"mark.line.show": True}, name="base")
    doc = {**spec({"mark.line.show": False}), "extends": "base"}
    reg = reg_with(("graphspec", base), ("graphspec", doc))
    assert validate("graphspec", base, reg) == []
    assert validate("graphspec", doc, reg) == [
        "variable_parameters.mark.line.show: fixed by GraphSpec 'base'"
    ]


def test_naming_method_is_limited_to_the_themes_methods():
    theme = child("theme", "fixed_parameters", {"legend.methods": ["key"]}, name="plain")
    reg = reg_with(("theme", theme))
    doc = spec({"specifications.theme": "plain"})
    assert validate("graphspec", doc, reg) == ["legend.method: theme 'plain' allows only key"]
    doc = spec({"specifications.theme": "plain", "legend.method": "key"})
    assert validate("graphspec", doc, reg) == []


def test_drawing_needs_the_required_columns():
    assert drawing_problems(builtin().docs["graphspec"]["forgegraph_base/polarization"]) == []
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
    theme = child("theme", "fixed_parameters", {"font.family": "Comic Nonexistent"}, name="odd")
    assert validate("theme", theme, reg_with(("theme", theme))) == [
        "fixed_parameters.font.family: no font 'Comic Nonexistent' is bundled or installed"
    ]
    bold = {p: "bold" for p in ("title.weight", "axis.title.weight", "legend.label.weight")}
    theme = child("theme", "fixed_parameters", {"font.family": "DejaVu Sans", **bold}, name="odd")
    assert validate("theme", theme, reg_with(("theme", theme))) == [
        "legend.key.title.weight: DejaVu Sans has no semibold weight; it has regular, bold"
    ]
    tree_set(theme["fixed_parameters"], "legend.key.title.weight", "bold")
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
    from forgegraph.spec import explain as explaining
    from forgegraph.spec.registry import builtin
    from forgegraph.spec.validate import validate

    doc = builtin().docs["graphspec"]["forgegraph_base/polarization"]
    calls = []
    explain = explaining.explain
    monkeypatch.setattr(explaining, "explain", lambda *a, **k: calls.append(1) or explain(*a, **k))
    assert validate("graphspec", doc) == []
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

    from forgegraph.spec.registry import builtin, load_document

    doc = {**builtin().docs["graphspec"]["forgegraph_base/polarization"], "name": "mine"}
    path = tmp_path / "mine.yaml"
    with path.open("w", encoding="utf-8") as f:  # its descriptions hold subscripts
        YAML().dump(doc, f)
    loaded, reg, folder = load_document("graphspec", path)
    assert loaded["name"] == "mine" and reg.paths["graphspec"]["mine"] == path
    assert folder == tmp_path

    given = builtin()
    loaded, reg, folder = load_document("graphspec", doc, given)
    assert reg.docs["graphspec"]["mine"] is doc and "mine" not in given.docs["graphspec"]
    monkeypatch.chdir(tmp_path)
    assert load_document("graphspec", doc)[2] == tmp_path

    named = builtin().docs["graphspec"]["forgegraph_base/polarization"]
    stranger = {**named, "description": "a document of a name the registry holds"}
    _, reg, _ = load_document("graphspec", stranger, builtin())
    assert reg.docs["graphspec"]["forgegraph_base/polarization"] is not stranger
