"""A GraphSpec's series: what it draws, each under its name in the legend.

A GraphSpec lists its series by name; each takes its graph type's series parameters
(series_definitions: its column, aggregation, color, line, marker, bars...), and may also set,
for itself alone, any of the theme's series parameters the theme leaves variable (its
opacity, line width, marker size, value labels' look...), but not a palette or style list,
which the series' own color, line.style, marker.shape and marker.fill choose from. Through
extends, series merge by name, as layers do: a GraphSpec changes an inherited series by
naming it and removes it with None; it can't change one tagged !fix. A tag goes on a series
or on series, never inside one.
"""

from __future__ import annotations

from typing import Any

from forgegraph.spec.common import suggest
from forgegraph.spec.parameters import (
    PARAMETERS,
    Parameter,
    check_parameter,
    definitions,
    flatten,
    is_none,
    series_definitions,
)
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import Resolved, Values, chain, inherit, named, resolve
from forgegraph.spec.tags import Tagged, TaggedMap, status_at, untag

# The theme's series parameters a series can't set for itself: the lists each series chooses
# from, and the benchmark's own style.
NOT_PER_SERIES = ("colors", "line.styles", "marker.shapes", "marker.fills")


def look_definitions() -> dict[str, Parameter]:
    """The theme's series parameters a series may set for itself, by path within a series."""
    out = {}
    for path, p in definitions("theme").items():
        if not path.startswith("series.") or path.startswith("series.benchmark."):
            continue
        rel = path.removeprefix("series.")
        if rel not in NOT_PER_SERIES:
            out[rel] = p
    return out


def _series_in(d: dict[str, Any]) -> list[tuple[bool, str, Any]]:
    """(fixed, name, entry) for each series a file lists, in order: fixed if the file tags
    the series, or series, !fix. The entry is without its own tag."""
    tree = untag(d.get(PARAMETERS))
    listed = untag(tree.get("series")) if isinstance(tree, dict) else None
    if isinstance(listed, dict):
        return [
            (bool(status_at(d[PARAMETERS], f"series.{name}")), str(name), untag(entry))
            for name, entry in listed.items()
        ]
    return [] if listed is None else [(False, "", listed)]


def _merge(base: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in change.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def resolve_series(doc: dict[str, Any], reg: Registry) -> dict[str, Resolved]:
    """The GraphSpec's series by name, in drawing order: those it inherits first, then its
    own, each merged by name down the extends chain."""
    out: dict[str, Resolved] = {}
    for d in reversed(chain("graphspec", doc, reg)):
        label = f"GraphSpec '{d.get('name')}'"
        for fixed, name, entry in _series_in(d):
            if is_none(entry):
                out.pop(name, None)
                continue
            if not isinstance(entry, dict):
                entry = {}  # a series named, with every parameter as its graph type has it
            old = out.get(name)
            value = _merge(old.value, entry) if old is not None else dict(entry)
            out[name] = Resolved(value, fixed, label)
    return out


def with_defaults(entry: dict[str, Any]) -> dict[str, Any]:
    """A series as {path: value}: every parameter its graph type defines, each as the series
    sets it or its default, and the theme parameters it sets for itself, under "look"."""
    listed = flatten(entry)
    own = series_definitions()
    out: dict[str, Any] = {p: listed.get(p, d.default) for p, d in own.items()}
    out["look"] = {p: v for p, v in listed.items() if p not in own}
    return out


def theme_for(theme: Values, look: dict[str, Any]) -> dict[str, Any]:
    """The theme's values as a series is drawn with them: with the theme parameters it sets
    for itself (look, by path within a series), and the members that take their value from
    them."""
    values = Values(theme)
    for path, value in look.items():
        values[f"series.{path}"] = Resolved(value, False, "the series")
    inherit(values, definitions("theme"))
    return values.plain()


def _tag_inside(entry: dict[str, Any], prefix: str = "") -> str | None:
    """The path of the first tag inside a series' entry, or None."""
    for key, value in entry.items():
        if isinstance(value, Tagged | TaggedMap):
            return f"{prefix}{key}"
        if isinstance(value, dict) and (found := _tag_inside(value, f"{prefix}{key}.")):
            return found
    return None


def series_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems with the series a GraphSpec lists: unknown or out-of-range parameters, theme
    parameters the theme fixes, and series an extended GraphSpec fixes."""
    errors: list[str] = []
    parent = doc.get("extends")
    inherited = (
        resolve_series(reg.docs["graphspec"][parent], reg)
        if not is_none(parent) and parent in reg.docs["graphspec"]
        else {}
    )
    try:
        theme_name = named("graphspec", doc, reg)["theme"]
        theme = resolve("theme", reg.docs["theme"][theme_name], reg)
    except (ValueError, KeyError):
        return []
    own, look = series_definitions(), look_definitions()
    names = reg.names()
    for _, name, entry in _series_in(doc):
        where = "series"
        if name == "":
            errors.append(f"{where}: must be series keyed by name, or None")
            continue
        where = f"{where}.{name}"
        if name in inherited and inherited[name].fixed:
            errors.append(f"{where}: fixed by {inherited[name].origin}")
            continue
        if is_none(entry) or entry == {}:
            continue
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be a series: its parameters, by category")
            continue
        if inside := _tag_inside(entry):
            errors.append(f"{where}.{inside}: a tag goes on the series or on series, not inside")
            continue
        for path, value in flatten(entry).items():
            p = own.get(path) or look.get(path)
            if p is None:
                known = [*own, *look]
                if any(k.startswith(f"{path}.") for k in known) and is_none(value):
                    continue  # an empty category
                errors.append(
                    f"{where}.{path}: unknown parameter of a series{suggest(path, known)}"
                )
                continue
            if path in look and theme.fixed(f"series.{path}", p.fixed):
                errors.append(f"{where}.{path}: fixed by theme '{theme_name}'")
                continue
            for suffix, message in check_parameter(p, value, names):
                errors.append(f"{where}.{path}{suffix}: {message}")
    return errors
