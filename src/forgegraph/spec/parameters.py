"""Parameter definitions, read from the specification files.

Each kind is defined by one file. Graph types and layer types are ForgeGraph's code, each
defined by its own file (graph_types/xy.yaml, layers/note.yaml); the other kinds by the base
pack's complete specs (packs/forgegraph_base/: themes/base_theme.yaml,
formats/base_format.yaml, layouts/layout_example.yaml, schedules/base_schedule.yaml) and its
reference GraphSpec (graphspecs/graphspec_example.yaml). A layer file has
only a name, version and description, and its parameters. A GraphSpec's layers and a
layout's tabs are collections keyed by name, checked by spec/layers.py and spec/layout.py,
so they aren't parameters here; a tab's parameters come from the base layout's one tab
(tab_definitions). Every line of those files, header included, is
`name: value          # [RANGE]; DESCRIPTION`.
RANGE lists the alternatives a value may take, separated by commas:

- a number range `min-max`, inclusive;
- a type word: text, int ≥ 0 (a whole number, 0 or more), int > 0, float, float ≥ 0,
  float > 0, date (a date, or a date and time: YAML's own, or ISO 8601 text; see as_date),
  hex color, hex colors (a list of one or more), two hex colors, column, columns, graph type,
  theme, format, graphspec, layer type, layer types, layout, schedule, texts (a list of
  text), floats > 0 (a list of them), text grid (a list of rows, each a list of text);
- any other word is a literal value (None, true, auto, linear, ...).

A parameter whose value in the definition is a list takes a list of one or more items, each
within RANGE, or None where RANGE includes None. A parameter defined as None whose RANGE
doesn't include None has no default: a GraphSpec must set it before the graph can be drawn.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from ruamel.yaml import YAML
from ruamel.yaml.comments import TaggedScalar

from forgegraph.spec.tags import FIX, UNSET, VAR, loader

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
    "graphspec": "graphspec_example",
    "layer": "reference_line",
    "layout": "layout_example",
    "schedule": "base_schedule",
}
CORE_KINDS = ("graph_type", "layer")  # ForgeGraph's code; every other kind comes from packs
BASE = "forgegraph_base"  # the pack whose specs define every kind but the CORE_KINDS
PARAMETERS = "parameters"  # the tree of a file's parameters, tagged !var or !fix (see tags.py)
HEADER = ("name", "version", "description", "extends", PARAMETERS)
LAYER_HEADER = ("name", "version", "description", "parameters")
COLLECTIONS = {"graphspec": ("layers",), "layout": ("tabs",)}  # categories keyed by chosen names
NAMES = {"graphspec": ("graph_type", "theme", "format"), "layout": ("format",)}  # specs it names
NONE = "None"
STEP = re.compile(r"^\s*(\d+)\s+(sec|min|hour|day|week|month|year)\s*$")  # a date tick step
TYPE_WORDS = (
    "text", "int ≥ 0", "int > 0", "float", "float ≥ 0", "float > 0", "date", "hex color",
    "hex colors", "two hex colors",
    "column", "columns", "graph type", "theme", "format", "graphspec", "layer type",
    "layer types", "layout", "schedule", "texts", "floats > 0", "text grid",
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
    "floats > 0",
    "text grid",
)  # take a list even where the definition has one value
WHOLE_LISTS = ("text grid",)  # a list checked as a whole, even where the definition is a list
# A category marked with a style has the parameters of the category named here (its members),
# each taking that parameter's value unless the category, or a file nearer in the extends
# chain, sets its own.
STYLES = {"text style": "text", "line style": "line", "series style": "series"}
# The members a style's category can't use, so they aren't its parameters (setting one is an
# error): what it draws has no use for them.
EXCLUDED = {
    "axis.tick": ("style", "cap", "join"),  # tick marks are markers
    "axis.tick.minor": ("style", "cap", "join"),
    "plot_area.border": ("join",),  # four straight sides, drawn apart
    "grid": ("cap", "join"),  # straight lines, clipped at the plot area's edges
    "series.line": ("style", "color"),  # series.line.styles and series.colors set them
    "series.marker.edge": ("cap", "join"),  # a closed outline; its corners are its shape's
    "series.bar.edge": ("cap",),
    "legend.key.border": ("cap",),
    "layer.error_bar": ("cap", "join"),  # straight lines, their ends under its caps (cap.*)
    "layer.reference_line.line": ("cap", "join"),  # a straight line, clipped at the edges
    "series.value_label": ("alignment",),  # one line: a number
    "legend.label": ("alignment", "color"),  # one line, in its series' color
    "legend.key.label": ("gap",),  # legend.key.sample.gap spaces a name from its sample
    "layer.reference_line.label": ("alignment",),  # placed by its position
    "layer.note": ("alignment",),  # its lines line up on its position's side
    "watermark": ("size", "gap", "alignment"),  # one line, spanning the plot area
    "series.benchmark": ("bar.gap",),  # one gap for all the bars side by side
}
# A style's member whose range isn't its general parameter's.
RANGES = {
    "series.marker.edge.style": "None, solid",  # a marker's outline can't be dashed
    "layer.reference_line.label.color": "line, hex color",  # line: the line's color
}

_INTERVAL = re.compile(r"^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
_ISO_DATE = re.compile(
    r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}(:?\d{2})?)?)?$"
)
_COMMENT = re.compile(r"^#\s*\[(?P<range>[^\]]*)\];\s*(?P<description>.*)$")
_TYPE_TEXT = {
    "text": "text",
    "int ≥ 0": "a whole number, 0 or more",
    "int > 0": "a whole number above 0",
    "float": "a number",
    "float ≥ 0": "a number, 0 or more",
    "float > 0": "a number above 0",
    "date": 'a date, e.g. 2025-08-25 or "2025-08-25T06:00"',
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
    "floats > 0": "a list of numbers above 0",
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
    fixed: bool  # tagged !fix in the definition file
    inherits: str | None = None  # a style's member: the parameter it takes its value from
    lists: bool | None = None  # a style's member: whether its general parameter takes a list

    @property
    def takes_list(self) -> bool:
        """A list whose items are each checked against the range."""
        if self.lists is not None:
            return self.lists
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


def as_date(value: Any) -> datetime | None:
    """A value of the date type as the date and time it stands for: a date, or a date and time
    (as YAML reads 2025-08-25 or 2025-08-25 06:00:00), or ISO 8601 text of one ("2025-08-25",
    "2025-08-25T06:00"); None for anything else. A time with a zone is at the time its clock
    shows, as the data's are."""
    if isinstance(value, str) and _ISO_DATE.match(value.strip()):
        try:
            value = datetime.fromisoformat(value.strip())
        except ValueError:  # e.g. 2025-02-30
            return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return None


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
        case "int ≥ 0":
            return _is_int(value) and value >= 0
        case "int > 0":
            return _is_int(value) and value > 0
        case "float":
            return _is_number(value)
        case "float ≥ 0":
            return _is_number(value) and value >= 0
        case "float > 0":
            return _is_number(value) and value > 0
        case "date":
            return as_date(value) is not None
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
        case "floats > 0":
            return (
                isinstance(value, list)
                and bool(value)
                and all(_type_ok("float > 0", v, names) for v in value)
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


def _tag(node: Any) -> bool | None:
    """Whether a round-trip YAML node is tagged !fix (True) or !var (False); None if neither."""
    tag = getattr(getattr(node, "tag", None), "value", None)
    return {FIX: True, VAR: False}.get(tag) if isinstance(tag, str) else None


def _parse(path: str, value: Any, comment: str | None, fixed: bool, where: Path) -> Parameter:
    m = _COMMENT.match(comment or "")
    if not m:
        raise ValueError(f"{where.name}: {path} needs '# [RANGE]; DESCRIPTION'")
    return Parameter(path, _plain(value), parse_range(m["range"]), m["description"], fixed)


@dataclass(frozen=True)
class _Style:
    """A category marked with a style, where it is in the file."""

    path: str
    word: str  # "text style", "line style" or "series style"
    fixed: bool | None


@dataclass(frozen=True)
class _Bare:
    """A style's member that its category sets without a comment: the range and description
    are its general parameter's."""

    path: str
    value: Any
    fixed: bool


def _walk(
    prefix: str,
    node: Any,
    fixed: bool | None,
    where: Path,
    in_style: bool = False,
    skip: tuple[str, ...] = (),
) -> list[Parameter | _Style | _Bare]:
    """The parameters in a category and its sub-categories, in file order, each fixed or not
    by the tag nearest it (fixed: the category's), with a marker where a style's category is;
    in a style's category (in_style), a parameter with no comment is one of its members."""
    out: list[Parameter | _Style | _Bare] = []
    for key in node:
        if key in skip:
            continue  # a collection: see spec/layers.py and spec/layout.py
        value = node[key]
        status = _tag(value)
        status = fixed if status is None else status
        path = f"{prefix}.{key}" if prefix else str(key)
        comment = _comment(node, key)
        m = _COMMENT.match(comment or "")
        if m and m["range"] in STYLES:
            out.append(_Style(path, m["range"], status))
            if hasattr(value, "items"):
                out += _walk(path, value, status, where, in_style=True)
        elif hasattr(value, "items"):
            out += _walk(path, value, status, where, in_style)
        elif in_style and not m:
            empty = isinstance(value, TaggedScalar) and str(value.value) == ""  # a tag alone
            out.append(_Bare(path, UNSET if empty else _plain(value), bool(status)))
        else:
            out.append(_parse(path, value, comment, bool(status), where))
    return out


def _status_at(tree: Any, path: str, root: bool | None) -> bool:
    """The status the definition file's tags give a path: the tag nearest it."""
    found, node = root, tree
    for key in path.split("."):
        if not hasattr(node, "items") or key not in node:
            break
        node = node[key]
        if (s := _tag(node)) is not None:
            found = s
    return bool(found)


def _expand(
    items: list[Parameter | _Style | _Bare],
    words: tuple[str, ...],
    tree: Any,
    where: Path,
    last: bool,
) -> list[Parameter | _Style | _Bare]:
    """Each style's category of these words given its members, where the category is: those
    it sets as it sets them, the rest from their general parameters."""
    params = {i.path: i for i in items if isinstance(i, Parameter)}
    bare = {i.path: i for i in items if isinstance(i, _Bare)}
    root = _tag(tree)
    made: dict[str, list[Parameter]] = {}
    for style in (i for i in items if isinstance(i, _Style) and i.word in words):
        general = STYLES[style.word]
        own: list[Parameter] = []
        excluded = EXCLUDED.get(style.path, ())
        generals = [g for g in params.values() if g.path.startswith(f"{general}.")]
        if not generals:  # a layout's: the theme's, which its first tile's theme sets
            generals = [
                g for g in definitions("theme").values() if g.path.startswith(f"{general}.")
            ]
        for g in generals:
            if not g.path.startswith(f"{general}.") or g.path.startswith(f"{style.path}."):
                continue
            rel = g.path[len(general) + 1 :]
            if rel in excluded or (rel.split(".")[-1] in excluded and "." not in rel):
                continue
            path = f"{style.path}.{rel}"
            rng = parse_range(RANGES[path]) if path in RANGES else g.range
            if path in bare:
                b = bare.pop(path)
                value = g.default if b.value is UNSET else b.value
                params[path] = Parameter(
                    path, value, rng, g.description, b.fixed, g.path, g.takes_list
                )
            elif path in params:
                params[path] = Parameter(
                    **{**params[path].__dict__, "inherits": g.path, "lists": g.takes_list}
                )
            else:
                fixed = _status_at(tree, path, root)
                own.append(
                    Parameter(path, g.default, rng, g.description, fixed, g.path, g.takes_list)
                )
        made[style.path] = own
    out: list[Parameter | _Style | _Bare] = []
    for item in items:
        if isinstance(item, _Style) and item.word in words:
            out += made[item.path]
        elif isinstance(item, Parameter):
            out.append(params[item.path])
        elif isinstance(item, _Bare):
            if item.path not in bare:
                out.append(params[item.path])
            elif last:  # no style it's in has a member of its name
                raise ValueError(f"{where.name}: {item.path} needs '# [RANGE]; DESCRIPTION'")
            else:
                out.append(item)
        else:
            out.append(item)
    return out


def _parameters(items: list[Parameter | _Style | _Bare], tree: Any, where: Path) -> list[Parameter]:
    """The file's parameters, with its styles' members: text and line styles first, since a
    series style's members include theirs."""
    items = _expand(items, ("text style", "line style"), tree, where, last=False)
    items = _expand(items, ("series style",), tree, where, last=True)
    return [i for i in items if isinstance(i, Parameter)]


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
        found = _parameters(_walk("", data[PARAMETERS], False, path), data[PARAMETERS], path)
        return header, {p.path: p for p in found}
    header = {
        k: _parse(k, data[k], _comment(data, k), False, path) for k in HEADER if k != PARAMETERS
    }
    tree = data[PARAMETERS]
    root = _tag(tree)
    for category, entries in tree.items():
        style = _COMMENT.match(_comment(tree, category) or "")
        if not hasattr(entries, "items") and not (style and style["range"] in STYLES):
            raise ValueError(f"{path.name}: {PARAMETERS}.{category} must be a category")
    items = _walk("", tree, root, path, skip=COLLECTIONS.get(kind, ()))
    return header, {p.path: p for p in _parameters(items, tree, path)}


@cache
def tab_definitions() -> tuple[dict[str, Parameter], Parameter]:
    """A layout tab's parameters, from the base layout's one tab: its grid's, by path
    (grid.areas...), and the one each tile takes, a GraphSpec file."""
    path = definition_file("layout")
    data = YAML().load(path.read_text(encoding="utf-8"))
    tabs = data[PARAMETERS]["tabs"]
    tab = tabs[next(iter(tabs))]
    grid = {p.path: p for p in _walk("grid", tab["grid"], False, path) if isinstance(p, Parameter)}
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
    names = graph_type_files()
    others = {path for kind in ("theme", "format") for path in definitions(kind)}
    others |= {path for gt in names for path in definitions("graph_type", gt)}
    return {path: p for path, p in params.items() if path not in others}


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
        data = loader().load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and is_none(data.get("extends")):
            out.append(path.stem)
    return tuple(out)


def _plain(value: Any) -> Any:
    """ruamel's round-trip types -> plain Python values. A tagged scalar is read as it would
    be untagged."""
    if isinstance(value, TaggedScalar):
        text = str(value.value)
        value = YAML(typ="safe", pure=True).load(text) if value.style is None else text
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
