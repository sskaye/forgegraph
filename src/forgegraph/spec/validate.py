"""Check theme, format, graph type, GraphSpec, layout and schedule files against their
definitions (see parameters.py).

- Every file has exactly the header fields name, version, description, extends,
  fixed_parameters and variable_parameters; the header's ranges come from the definition
  file like any parameter's.
- extends names another file of the same kind, or is None; with None the file must list
  every parameter of its kind.
- A file lists each parameter once, under fixed_parameters or variable_parameters, by
  category. A file that extends another may change any parameter, fixed or variable.
- In a theme or format, a graph type's name may be used as a heading (see resolve.py).
- A GraphSpec may also set any parameter its graph type, theme or format lists
  as variable, under the same category. It may not change a parameter that a GraphSpec it
  extends lists as fixed. Its layers are checked by layers.py, a layout's tabs by layout.py.
- A format's width and height can't both be auto; a graph type's legend.method must be one
  of the theme's legend.methods; the parameters TIES ties (benchmark.data_column and
  benchmark.value) are set together or not at all; with several y columns, axis.y.title
  is text or None; and anything else impossible (no font, nothing drawn, a backwards or
  non-positive log axis) is an error, never a silent substitute.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from typing import Any

from forgegraph.fonts import WEIGHTS, font_available, font_weights
from forgegraph.spec.access import PACK_TYPES, permission_problems, use_fonts
from forgegraph.spec.common import kind_label, suggest
from forgegraph.spec.explain import explain
from forgegraph.spec.layers import layer_problems, resolve_layers, with_defaults
from forgegraph.spec.layout import layout_problems
from forgegraph.spec.parameters import (
    HEADER,
    SECTIONS,
    STEP,
    Parameter,
    as_date,
    categories,
    check_parameter,
    check_value,
    definitions,
    header_definitions,
    is_none,
)
from forgegraph.spec.registry import Registry, builtin
from forgegraph.spec.resolve import (
    HEADINGS,
    chain,
    definitions_for,
    entries,
    named,
    resolve,
)
from forgegraph.spec.schedule import Cadence, CadenceError

# Graph-type parameters set together or not at all; the catalog's cards keep them so too.
TIES = (("benchmark.data_column", "benchmark.value"),)


def validate(kind: str, doc: Any, reg: Registry | None = None) -> list[str]:
    """Every problem with a file of `kind`, as '<location>: <what's wrong>'. Each step runs
    only if the ones before found nothing: the header, each listed parameter, then (with
    extends None) every parameter listed, then the kind's own rules and what the configs
    allow."""
    reg = reg or builtin()
    if not isinstance(doc, dict):
        return ["(document): must be a mapping of fields"]
    errors = _header(kind, doc, reg)
    if errors:
        return errors
    try:
        defs = definitions_for(kind, doc, reg)
    except ValueError as e:
        return [str(e)]
    errors, listed = _entry_problems(kind, doc, reg, defs)
    if errors:
        return errors
    if is_none(doc["extends"]):
        missing = [path for path in defs if path not in listed]
        if missing:
            return [
                "extends: None, so every parameter must be listed; missing: " + ", ".join(missing)
            ]
    rules = _RULES.get(kind)
    errors = rules(doc, reg) if rules else []
    if kind == "graphspec" and errors:  # its layers or values can't be resolved: stop here
        return errors
    errors += permission_problems(kind, doc, reg)
    if kind == "format":
        errors += _format_size(doc, reg)
    return errors


def _entry_problems(
    kind: str, doc: dict[str, Any], reg: Registry, defs: dict[str, Parameter]
) -> tuple[list[str], set[str]]:
    """Each listed parameter's problems (unknown, fixed elsewhere, out of range, listed
    twice), and the paths listed without a graph-type heading."""
    errors: list[str] = []
    names = reg.names()
    others = _settable(kind, doc, reg)
    seen: dict[tuple[str | None, str], str] = {}
    for section, heading, path, value in entries(kind, doc, reg):
        where = f"{section}." + (f"{heading}." if heading else "")
        if path == "":
            errors.append(f"{section}: must be categories of parameters, or None")
            continue
        if (heading, path) in seen:
            errors.append(f"{where}{path}: also listed in {seen[heading, path]}")
            continue
        seen[heading, path] = section
        p = defs.get(path)
        if p is None and path in others:
            p, owner, fixed = others[path]
            if fixed:
                errors.append(f"{where}{path}: fixed by {owner}")
                continue
        if p is None:
            known = [*defs, *others]
            if "." in path:
                errors.append(f"{where}{path}: unknown parameter{suggest(path, known)}")
            else:
                tops = {k.split(".")[0] for k in known}
                errors.append(f"{where}{path}: unknown category{suggest(path, tops)}")
            continue
        unloaded = (
            reg.unloaded(value, bool(reg.owner(kind, doc)))
            if PACK_TYPES.intersection(p.range.types)
            else None
        )
        if unloaded:
            errors.append(f"{where}{path}: {unloaded}")
            continue
        for suffix, message in check_parameter(p, value, names):
            errors.append(f"{where}{path}{suffix}: {message}")
    return errors, {path for (heading, path) in seen if heading is None}


def _header(kind: str, doc: dict[str, Any], reg: Registry) -> list[str]:
    errors = [f"{k}: required" for k in HEADER if k not in doc]
    errors += [
        f"{k}: a category of parameters; it goes under {SECTIONS[1]} or {SECTIONS[0]}"
        if k in categories("graphspec", "theme", "format", "graph_type")
        else f"{k}: unknown field; a file has only {', '.join(HEADER)}"
        for k in doc
        if k not in HEADER
    ]
    if errors:
        return errors
    names = reg.names()
    names[kind] = names[kind] - {doc["name"]}  # a file can't extend itself
    for key, p in header_definitions(kind).items():
        if key == "extends" and not is_none(doc[key]) and doc[key] not in reg.docs[kind]:
            continue  # reported by chain, with a suggestion
        if err := check_value(doc[key], p.range, names):
            errors.append(f"{key}: {err}")
    try:
        chain(kind, doc, reg)
    except ValueError as e:
        errors.append(str(e))
    return errors


def _graphspec_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    errors = layer_problems(doc, reg)
    if errors:
        return errors
    errors = _inherited_fixed(doc, reg)
    return errors or _graphspec_rules(explain(doc, reg).plain())


def _schedule_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    try:
        Cadence.from_values(resolve("schedule", doc, reg).plain())
    except CadenceError as e:
        return [str(e)]
    return []


def _format_size(doc: dict[str, Any], reg: Registry) -> list[str]:
    for gt in [None, *reg.docs["graph_type"]]:
        r = resolve("format", doc, reg, gt)
        if r.value("figure.width") == "auto" and r.value("figure.height") == "auto":
            return ["size: width and height can't both be auto"]
    return []


def _settable(
    kind: str, doc: dict[str, Any], reg: Registry
) -> dict[str, tuple[Parameter, str, bool]]:
    """Parameters of the specs a GraphSpec or layout names (see NAMES), with whether each is
    fixed there: {path: (definition, owner, fixed)}. It can set the variable ones."""
    try:
        chosen = named(kind, doc, reg)
    except ValueError:
        return {}
    out = {}
    for k, name in chosen.items():
        other = reg.docs[k].get(name) if isinstance(name, str) else None
        if other is None:
            continue
        try:
            defs = definitions_for(k, other, reg)
            resolved = resolve(k, other, reg, chosen.get("graph_type") if k in HEADINGS else None)
        except ValueError:
            continue
        for path, p in defs.items():
            out[path] = (p, f"{kind_label(k)} '{name}'", resolved.fixed(path, p.fixed))
    return out


def _inherited_fixed(doc: dict[str, Any], reg: Registry) -> list[str]:
    parent = doc["extends"]
    if is_none(parent):
        return []
    inherited = resolve("graphspec", reg.docs["graphspec"][parent], reg)
    return [
        f"{section}.{path}: fixed by GraphSpec '{parent}'"
        for section, _, path, _ in entries("graphspec", doc, reg)
        if inherited.fixed(path)
    ]


def _graphspec_rules(values: dict[str, dict[str, Any]]) -> list[str]:
    """What a GraphSpec's values, resolved once, may not combine."""
    return _method_allowed(values) + _ties_complete(values) + _graph_rules(values)


def _method_allowed(values: dict[str, dict[str, Any]]) -> list[str]:
    method = values["graph_type"].get("legend.method")
    methods = values["theme"]["legend.methods"]
    if method is None or method in methods:
        return []
    theme = values["graphspec"]["specifications.theme"]
    return [f"legend.method: theme '{theme}' allows only {', '.join(methods)}"]


def _ties_complete(values: dict[str, dict[str, Any]]) -> list[str]:
    gt = values["graph_type"]
    errors = []
    for tie in TIES:
        if len({is_none(gt.get(path)) for path in tie}) > 1:
            category = tie[0].rsplit(".", 1)[0]
            names = " and ".join(path.rsplit(".", 1)[1] for path in tie)
            errors.append(f"{category}: set {names} together, or neither")
    return errors


def _graph_rules(values: dict[str, dict[str, Any]]) -> list[str]:
    """Combinations of graph-type values that ask for something impossible."""
    v = values["graph_type"]
    errors = []
    columns = v.get("axis.y.data.column")
    several = isinstance(columns, list) and len(columns) > 1
    if several and v.get("axis.y.title") == "column_name":
        errors.append("axis.y.title: several y columns have no single name; set a title, or None")
    if (
        several
        and v.get("encoding.color.column") == "column_name"
        and v.get("legend.key.title.text") == "column_name"
    ):
        errors.append(
            "legend.key.title.text: encoding.color.column is column_name, which has no single "
            "name; set a title, or None"
        )
    if all(v.get(f"mark.{m}.show") is False for m in ("line", "marker", "bar")):
        errors.append(
            "mark.line.show, mark.marker.show, mark.bar.show: all false, so nothing would be drawn"
        )
    for axis in ("axis.x", "axis.y"):
        algorithm, step = v.get(f"{axis}.tick.algorithm"), v.get(f"{axis}.tick.step")
        if algorithm == "manual" and is_none(step):
            errors.append(f"{axis}.tick.algorithm: manual needs tick.step")
        if algorithm != "manual" and not is_none(step):
            errors.append(f"{axis}.tick.step: applies only with tick.algorithm manual")
        if isinstance(step, str) and not is_none(step) and not STEP.match(step):
            errors.append(
                f"{axis}.tick.step: '{step}' isn't a count and a unit, e.g. \"2 week\" "
                "(units: sec, min, hour, day, week, month, year)"
            )
        lo, hi = v.get(f"{axis}.min"), v.get(f"{axis}.max")
        numbers = [x for x in (lo, hi) if isinstance(x, int | float) and not isinstance(x, bool)]
        ends = [x for x in (lo, hi) if x in numbers or as_date(x) is not None]
        if len(ends) == 2:
            from forgegraph.drawing.axes import value_number  # as drawn: dates as day numbers

            if value_number(lo) >= value_number(hi):
                errors.append(f"{axis}.min: must be below {axis}.max ({lo} is not below {hi})")
        if v.get(f"{axis}.scale") == "log":
            for end, value in (("min", lo), ("max", hi)):
                if value in numbers and value <= 0:
                    errors.append(f"{axis}.{end}: a log axis needs values above 0, not {value}")
    return errors


def _theme_rules(doc: dict[str, Any], reg: Registry) -> list[str]:
    """A theme's fonts are installed (its packs' registered first), its weights are ones its
    family has, and its watermark text draws something."""
    use_fonts("theme", doc, reg)
    errors = []
    for section, heading, path, value in entries("theme", doc, reg):
        if path == "font.family" and isinstance(value, str) and not font_available(value):
            where = f"{section}." + (f"{heading}." if heading else "")
            errors.append(f"{where}font.family: no font '{value}' is bundled or installed")
    if errors:
        return errors
    headings = {h for d in chain("theme", doc, reg) for _, h, _, _ in entries("theme", d, reg)}
    for heading in sorted(headings, key=lambda h: h or ""):
        values = resolve("theme", doc, reg, heading)
        where = f" under {heading}" if heading else ""
        family = str(values["font.family"].value)
        has = font_weights(family)
        for path, value in values.plain().items():
            if path.endswith("weight") and WEIGHTS.get(value) not in has:
                names = ", ".join(n for n, w in WEIGHTS.items() if w in has)
                errors.append(f"{path}{where}: {family} has no {value} weight; it has {names}")
        if "watermark.text" in values and not _visible(str(values["watermark.text"].value)):
            errors.append(
                f"watermark.text{where}: has no letters; the watermark is drawn from its "
                "letters' outlines, so it needs at least one visible character"
            )
    return errors


# Each kind's own rules, after its parameters are each found valid (see validate).
_RULES: dict[str, Callable[[dict[str, Any], Registry], list[str]]] = {
    "graphspec": _graphspec_problems,
    "layout": layout_problems,
    "schedule": _schedule_problems,
    "theme": _theme_rules,
}


def _visible(text: str) -> bool:
    """Whether text has a character that draws something: not a space or a control or
    formatting character."""
    return any(not (c.isspace() or unicodedata.category(c).startswith("C")) for c in text)


def drawing_problems(doc: dict[str, Any], reg: Registry | None = None) -> list[str]:
    """What a valid GraphSpec still lacks before the graph can be drawn: parameters its
    graph type defines with no default."""
    reg = reg or builtin()
    values = explain(doc, reg).graph_type.plain()
    gt = reg.docs["graph_type"][named("graphspec", doc, reg)["graph_type"]]
    problems = [
        f"{path}: must be set before the graph can be drawn"
        for path, p in definitions_for("graph_type", gt, reg).items()
        if p.required and is_none(values.get(path))
    ]
    for name, r in resolve_layers(doc, reg).items():
        layer = with_defaults(r.value)
        problems += [
            f"layers.{name}.{path}: must be set before the graph can be drawn"
            for path, p in definitions("layer", layer["type"]).items()
            if p.required and is_none(layer.get(path))
        ]
    return problems


def named_problems(kind: str, doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems in the specs a GraphSpec or layout names (see NAMES), and the specs they
    extend."""
    problems = []
    for k, name in named(kind, doc, reg).items():
        while not is_none(name):
            spec = reg.docs[k][name]
            problems += [f"{kind_label(k)} '{name}': {p}" for p in validate(k, spec, reg)]
            name = spec.get("extends")
    return problems
