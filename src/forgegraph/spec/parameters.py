"""Parameter definitions, read from the specification files.

Each kind is defined by one file. Graph types and layer types are ForgeGraph's code, each
defined by its own file (graph_types/xy.yaml, layers/note.yaml); the other kinds by the base
pack's complete specs (packs/forgegraph_base/: themes/base_theme.yaml,
formats/base_format.yaml, layouts/base_layout.yaml, schedules/base_schedule.yaml) and its
reference GraphSpec (graphspecs/polarization.yaml). A layer file has
only a name, version and description, and its parameters. A GraphSpec's layers and a
layout's tabs are collections keyed by name, checked by spec/layers.py and spec/layout.py,
so they aren't parameters here; a tab's parameters come from the base layout's one tab
(tab_definitions). Every line of those files, header included, is
`name: value          # [RANGE]; DESCRIPTION`.
RANGE lists the alternatives a value may take, separated by commas:

- a number range `min-max`, inclusive;
- a type word: text, int (a whole number, 0 or more), positive int, float, positive float,
  hex color, hex colors (a list of one or more), two hex colors, column, columns, graph type,
  theme, format, graphspec, layer type, layer types, layout, schedule, texts (a list of text),
  positive floats (a list of them), text grid (a list of rows, each a list of text);
- any other word is a literal value (None, true, auto, linear, ...).

A parameter whose value in the definition is a list takes a list of one or more items, each
within RANGE, or None where RANGE includes None. A parameter defined as None whose RANGE
doesn't include None has no default: a GraphSpec must set it before the graph can be drawn.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from ruamel.yaml import YAML

if TYPE_CHECKING:  # typing.TypeIs is Python 3.13's
    from typing_extensions import TypeIs

KINDS = {
    "theme": "themes",
    "format": "formats",
    "graph_type": "graph_types",
    "graphspec": "graphspecs",
    "layer": "layers",
    "layout": "layouts",
    "schedule": "schedules",
}
REFERENCE = {
    "theme": "base_theme",
    "format": "base_format",
    "graph_type": "xy",
    "graphspec": "polarization",
    "layer": "reference_line",
    "layout": "base_layout",
    "schedule": "base_schedule",
}
CORE_KINDS = ("graph_type", "layer")  # ForgeGraph's code; every other kind comes from packs
BASE = "forgegraph_base"  # the pack whose specs define every kind but the CORE_KINDS
HEADER = ("name", "version", "description", "extends", "fixed_parameters", "variable_parameters")
LAYER_HEADER = ("name", "version", "description", "parameters")
COLLECTIONS = {"graphspec": ("layers",), "layout": ("tabs",)}  # categories keyed by chosen names
NAMES = {"graphspec": ("graph_type", "theme", "format"), "layout": ("format",)}  # specs it names
SECTIONS = ("fixed_parameters", "variable_parameters")
NONE = "None"
STEP = re.compile(r"^\s*(\d+)\s+(sec|min|hour|day|week|month|year)\s*$")  # a date tick step
TYPE_WORDS = (
    "text", "int", "positive int", "float", "positive float", "hex color", "hex colors",
    "two hex colors",
    "column", "columns", "graph type", "theme", "format", "graphspec", "layer type",
    "layer types", "layout", "schedule", "texts", "positive floats", "text grid",
)  # fmt: skip
NAME_TYPES = {
    "graph type": "graph_type",
    "theme": "theme",
    "format": "format",
    "graphspec": "graphspec",
    "layer type": "layer",
    "layout": "layout",
    "schedule": "schedule",
}
LIST_TYPES = (
    "columns",
    "hex colors",
    "two hex colors",
    "layer types",
    "texts",
    "positive floats",
    "text grid",
)  # take a list even where the definition has one value
WHOLE_LISTS = ("text grid",)  # a list checked as a whole, even where the definition is a list

_INTERVAL = re.compile(r"^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
_COMMENT = re.compile(r"^#\s*\[(?P<range>[^\]]*)\];\s*(?P<description>.*)$")
_TYPE_TEXT = {
    "text": "text",
    "int": "a whole number, 0 or more",
    "positive int": "a whole number above 0",
    "float": "a number",
    "positive float": "a number above 0",
    "hex color": "a hex color code such as #4C78A8",
    "hex colors": "a list of hex color codes",
    "two hex colors": "a list of two hex color codes",
    "column": "a column name",
    "columns": "a column name or a list of column names",
    "graph type": "the name of a graph type",
    "theme": "the name of a theme",
    "format": "the name of a format",
    "graphspec": "the name of a GraphSpec",
    "layer type": "the name of a layer type",
    "layer types": "a list of layer type names",
    "layout": "the name of a layout",
    "schedule": "the name of a schedule",
    "texts": "a list of text",
    "positive floats": "a list of numbers above 0",
    "text grid": "a list of rows, each a list of text",
}


@dataclass(frozen=True)
class Interval:
    low: float
    high: float

    def describe(self) -> str:
        return f"a number from {_num(self.low)} to {_num(self.high)}"


@dataclass(frozen=True)
class Range:
    literals: tuple[str, ...]
    intervals: tuple[Interval, ...]
    types: tuple[str, ...]

    def describe(self) -> str:
        if not self.intervals and not self.types:
            return "one of: " + ", ".join(self.literals)
        parts = [*self.literals, *(i.describe() for i in self.intervals)]
        parts += [_TYPE_TEXT[t] for t in self.types]
        return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " or " + parts[-1]


@dataclass(frozen=True)
class Parameter:
    path: str  # e.g. "axis.tick.length"
    default: Any
    range: Range
    description: str
    fixed: bool  # in fixed_parameters of the definition file

    @property
    def takes_list(self) -> bool:
        """A list whose items are each checked against the range."""
        return isinstance(self.default, list) and not set(WHOLE_LISTS) & set(self.range.types)

    @property
    def required(self) -> bool:
        """Defined as None with no None in its range: a GraphSpec must set it."""
        return self.default is None and NONE not in self.range.literals


def is_none(value: Any) -> TypeIs[Literal["None"] | None]:
    """Whether a spec's value is None: the word None, or YAML's null (null, ~ or nothing)."""
    return value is None or value == NONE


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def parse_range(text: str) -> Range:
    """'auto, 10-2000, hex color' -> literals ('auto',), one interval, types ('hex color',)."""
    literals, intervals, types = [], [], []
    for item in (s.strip() for s in text.split(",")):
        if not item:
            raise ValueError(f"empty item in range [{text}]")
        m = _INTERVAL.match(item)
        if m:
            low, high = float(m[1]), float(m[2])
            if low > high:
                raise ValueError(f"range {item} runs backwards")
            intervals.append(Interval(low, high))
        elif item in TYPE_WORDS:
            types.append(item)
        else:
            literals.append(item)
    return Range(tuple(literals), tuple(intervals), tuple(types))


def _as_literal(value: Any) -> str | None:
    if value is None:
        return NONE
    if isinstance(value, bool):
        return "true" if value else "false"
    return value if isinstance(value, str) else None


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_value(value: Any, rng: Range, names: dict[str, set[str]] | None = None) -> str | None:
    """Return why `value` is outside `rng`, or None if it's inside."""
    names = names or {}
    lit = _as_literal(value)
    if lit is not None and lit in rng.literals:
        return None
    if _is_number(value) and any(i.low <= value <= i.high for i in rng.intervals):
        return None
    if any(_type_ok(t, value, names) for t in rng.types):
        return None
    return f"must be {rng.describe()}"


def _type_ok(t: str, value: Any, names: dict[str, set[str]]) -> bool:
    match t:
        case "text":
            return isinstance(value, str) and not is_none(value)
        case "int":
            return _is_int(value) and value >= 0
        case "positive int":
            return _is_int(value) and value > 0
        case "float":
            return _is_number(value)
        case "positive float":
            return _is_number(value) and value > 0
        case "hex color":
            return isinstance(value, str) and bool(_HEX.match(value))
        case "hex colors":
            return (
                isinstance(value, list)
                and bool(value)
                and all(_type_ok("hex color", v, names) for v in value)
            )
        case "two hex colors":
            return (
                isinstance(value, list)
                and len(value) == 2
                and all(_type_ok("hex color", v, names) for v in value)
            )
        case "column":
            return isinstance(value, str) and value.strip() != "" and not is_none(value)
        case "columns":
            items = value if isinstance(value, list) else [value]
            return bool(items) and all(_type_ok("column", v, names) for v in items)
        case "layer types":
            items = value if isinstance(value, list) else [value]
            return bool(items) and all(_type_ok("layer type", v, names) for v in items)
        case "texts":
            return (
                isinstance(value, list)
                and bool(value)
                and all(_type_ok("text", v, names) for v in value)
            )
        case "positive floats":
            return (
                isinstance(value, list)
                and bool(value)
                and all(_type_ok("positive float", v, names) for v in value)
            )
        case "text grid":
            return (
                isinstance(value, list)
                and bool(value)
                and all(_type_ok("texts", row, names) for row in value)
            )
    if t in NAME_TYPES:
        return isinstance(value, str) and value in names.get(NAME_TYPES[t], set())
    raise AssertionError(t)


def check_parameter(
    p: Parameter, value: Any, names: dict[str, set[str]] | None = None
) -> list[tuple[str, str]]:
    """Problems as (suffix, message); suffix is '' or '[i]' for a list item."""
    if p.required and is_none(value):
        return []  # unset; drawing needs it, see validate.drawing_problems
    if p.takes_list:
        if is_none(value) and NONE in p.range.literals:
            return []  # a list parameter whose range allows None, e.g. no tick sides
        if not isinstance(value, list):
            return [("", f"must be a list of one or more items, each {p.range.describe()}")]
        if not value:
            return [("", "must have at least one item")]
        problems = []
        for i, item in enumerate(value):
            if is_none(item):
                problems.append((f"[{i}]", "None can't be a list item"))
            elif err := check_value(item, p.range, names):
                problems.append((f"[{i}]", err))
        return problems
    if isinstance(value, list) and not set(LIST_TYPES) & set(p.range.types):
        return [("", f"must be a single value: {p.range.describe()}")]
    err = check_value(value, p.range, names)
    return [("", err)] if err else []


def flatten(tree: Any, prefix: str = "") -> dict[str, Any]:
    """A category tree as {dotted path: value}. Parameter values are never mappings, so every
    mapping inside a category is a sub-category."""
    out: dict[str, Any] = {}
    for key, value in tree.items():
        path = f"{prefix}{key}"
        if hasattr(value, "items"):
            out.update(flatten(value, f"{path}."))
        else:
            out[path] = value
    return out


def tree_get(tree: Any, path: str, default: Any = None) -> Any:
    """The value at a dotted path in a category tree, or default."""
    node = tree
    for key in path.split("."):
        if not hasattr(node, "items") or key not in node:
            return default
        node = node[key]
    return node


def tree_set(tree: dict[str, Any], path: str, value: Any) -> None:
    """Set the value at a dotted path, making sub-categories as needed."""
    *parents, leaf = path.split(".")
    node = tree
    for key in parents:
        node = node.setdefault(key, {})
    node[leaf] = value


def tree_has(tree: Any, path: str) -> bool:
    marker = object()
    return tree_get(tree, path, marker) is not marker


def base_folder() -> Path:
    """The base pack's folder, in this package."""
    return Path(str(files("forgegraph") / "packs" / BASE))


def definition_file(kind: str, name: str | None = None) -> Path:
    """A graph type's or layer type's own file, or the base pack's file defining a kind."""
    root = Path(str(files("forgegraph"))) if kind in CORE_KINDS else base_folder()
    return root / KINDS[kind] / f"{name or REFERENCE[kind]}.yaml"


def _comment(node: Any, key: str) -> str | None:
    entry = node.ca.items.get(key)
    for part in entry or []:
        for c in part if isinstance(part, list) else [part]:
            if c is not None and hasattr(c, "value"):
                return c.value.strip().split("\n")[0].strip()
    return None


def _parse(path: str, value: Any, comment: str | None, fixed: bool, where: Path) -> Parameter:
    m = _COMMENT.match(comment or "")
    if not m:
        raise ValueError(f"{where.name}: {path} needs '# [RANGE]; DESCRIPTION'")
    return Parameter(path, _plain(value), parse_range(m["range"]), m["description"], fixed)


def _walk(prefix: str, node: Any, fixed: bool, where: Path) -> list[Parameter]:
    """The parameters in a category and its sub-categories, in file order."""
    out = []
    for key in node:
        value = node[key]
        if hasattr(value, "items"):
            out += _walk(f"{prefix}.{key}", value, fixed, where)
        else:
            out.append(_parse(f"{prefix}.{key}", value, _comment(node, key), fixed, where))
    return out


@cache
def _read(kind: str, name: str) -> tuple[dict[str, Parameter], dict[str, Parameter]]:
    """(header, parameters) of a definition file."""
    path = definition_file(kind, name)
    data = YAML().load(path.read_text(encoding="utf-8"))
    if kind == "layer":
        header = {
            k: _parse(k, data[k], _comment(data, k), False, path)
            for k in LAYER_HEADER
            if k != "parameters"
        }
        tree = data["parameters"]
        found: list[Parameter] = []
        for key in tree:
            if hasattr(tree[key], "items"):
                found += _walk(str(key), tree[key], False, path)
            else:
                found.append(_parse(str(key), tree[key], _comment(tree, key), False, path))
        return header, {p.path: p for p in found}
    header = {
        k: _parse(k, data[k], _comment(data, k), False, path) for k in HEADER if k not in SECTIONS
    }
    params: dict[str, Parameter] = {}
    for section in SECTIONS:
        tree = data.get(section)
        if is_none(tree):
            continue
        for category, entries in tree.items():
            if category in COLLECTIONS.get(kind, ()):
                continue
            if not hasattr(entries, "items"):
                raise ValueError(f"{path.name}: {section}.{category} must be a category")
            for p in _walk(str(category), entries, section == SECTIONS[0], path):
                if p.path in params:
                    raise ValueError(f"{path.name}: {p.path} is listed twice")
                params[p.path] = p
    return header, params


@cache
def tab_definitions() -> tuple[dict[str, Parameter], Parameter]:
    """A layout tab's parameters, from the base layout's one tab: its grid's, by path
    (grid.areas...), and the one each tile takes, a GraphSpec file."""
    path = definition_file("layout")
    data = YAML().load(path.read_text(encoding="utf-8"))
    tabs = data[SECTIONS[1]]["tabs"]
    tab = tabs[next(iter(tabs))]
    grid = {p.path: p for p in _walk("grid", tab["grid"], False, path)}
    tiles = tab["tiles"]
    first = next(iter(tiles))
    tile = _parse("tile", tiles[first], _comment(tiles, first), False, path)
    return grid, tile


def header_definitions(kind: str) -> dict[str, Parameter]:
    return _read(kind, REFERENCE[kind])[0]


def definitions(kind: str, name: str | None = None) -> dict[str, Parameter]:
    """Every parameter of a kind, by path. A graph type's and a layer type's come from their
    own file (name); a GraphSpec's are those of the reference GraphSpec that no other kind
    defines."""
    if kind == "graphspec":
        return _graphspec_definitions(name or REFERENCE[kind])
    return _read(kind, name or REFERENCE[kind])[1]


@cache
def _graphspec_definitions(name: str) -> dict[str, Parameter]:
    params = _read("graphspec", name)[1]
    others = categories("theme", "format", "graph_type")
    return {path: p for path, p in params.items() if path.split(".")[0] not in others}


@cache
def categories(*kinds: str) -> frozenset[str]:
    """The top-level categories of these kinds' parameters; for graph_type, every graph
    type's."""
    paths = []
    for kind in kinds:
        names = graph_type_files() if kind == "graph_type" else (None,)
        paths += [p for name in names for p in definitions(kind, name)]
    return frozenset(p.split(".")[0] for p in paths)


@cache
def graph_type_files() -> tuple[str, ...]:
    """Graph types with their own definition (extends None)."""
    folder = Path(str(files("forgegraph") / KINDS["graph_type"]))
    out = []
    for path in sorted(folder.glob("*.yaml")):
        data = YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and is_none(data.get("extends")):
            out.append(path.stem)
    return tuple(out)


def _plain(value: Any) -> Any:
    """ruamel's round-trip types -> plain Python values."""
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    s = str(value)
    return None if is_none(s) else s
