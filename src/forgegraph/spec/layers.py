"""A GraphSpec's layers: what's drawn on top of the graph.

A GraphSpec's layers are keyed by names it chooses; each has a type, one of its graph type's
layer.types, and that layer type's parameters. Through extends, layers merge by name: a
GraphSpec changes an inherited layer's parameters by naming it, replaces it by giving another
type, and removes it with None; it can't change a layer tagged !fix, itself or through the
layers category. A tag goes on a layer or on layers, never inside a layer.

A layer type's category whose look comes from the theme (`[look from layer.note]` in its
brackets) takes the theme category's parameters, and a layer may set, for itself alone,
those the theme leaves variable (look_paths).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from forgegraph.spec.common import suggest
from forgegraph.spec.parameters import (
    PARAMETERS,
    Notes,
    category_notes,
    check_parameter,
    definition_file,
    definitions,
    flatten,
    is_none,
    styles_in,
)
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import Resolved, chain, named, resolve
from forgegraph.spec.tags import Tagged, TaggedMap, status_at, untag


@cache
def look_paths(kind: str) -> dict[str, str]:
    """The theme parameters a layer type's entry may set for itself, by their path in the
    entry (see looks_in)."""
    return looks_in(definition_file("layer", kind))


def looks_in(path: Path) -> dict[str, str]:
    """The theme parameters an entry of the layer type defined at path may set for itself, by
    their path in the entry: those of the theme category each of its categories takes its
    look from (look from), which must have the category's style; a copy of a category (same
    as) takes the same."""
    data = YAML().load(path.read_text(encoding="utf-8"))
    theme, styles = definitions("theme"), styles_in("theme")
    looks: dict[str, str] = {}  # each category's path in the entry ("" for all of it): its theme's

    def take(prefix: str, found: Notes | None) -> None:
        if found is None or found.look is None:
            return
        where = f"{path.name}: {prefix or PARAMETERS}: look from {found.look}"
        if not any(t.startswith(f"{found.look}.") for t in theme):
            raise ValueError(f"{where}: no theme category")
        if styles.get(found.look) != found.style:
            raise ValueError(f"{where}: {_a(styles.get(found.look))}, not {_a(found.style)}")
        looks[prefix] = found.look

    def walk(node: Any, prefix: str) -> None:
        for key in node if hasattr(node, "items") else []:
            here = f"{prefix}.{key}" if prefix else str(key)
            found = category_notes(node, key, f"{path.name}: {here}")
            if found is not None and found.same is not None:  # a sibling's, under its own name
                source = f"{prefix}.{found.same}" if prefix else found.same
                for k, v in dict(looks).items():
                    if k == source or k.startswith(f"{source}."):
                        looks[here + k[len(source) :]] = v
            take(here, found)
            walk(node[key], here)

    take("", category_notes(data, PARAMETERS, f"{path.name}: {PARAMETERS}"))
    walk(data[PARAMETERS], "")
    out = {}
    for prefix, category in looks.items():
        for t in theme:
            if t.startswith(f"{category}."):
                member = t[len(category) + 1 :]
                out[f"{prefix}.{member}" if prefix else member] = t
    return out


def _a(style: str | None) -> str:
    return f"a {style}" if style else "no style"


def _layers_in(d: dict[str, Any]) -> list[tuple[bool, str, Any]]:
    """(fixed, name, entry) for each layer a file lists, in order: fixed if the file tags the
    layer, or layers, !fix. The entry is without its own tag."""
    tree = untag(d.get(PARAMETERS))
    layers = untag(tree.get("layers")) if isinstance(tree, dict) else None
    if isinstance(layers, dict):
        return [
            (bool(status_at(d[PARAMETERS], f"layers.{name}")), str(name), untag(entry))
            for name, entry in layers.items()
        ]
    return [] if layers is None else [(False, "", layers)]


def _tag_inside(entry: dict[str, Any], prefix: str = "") -> str | None:
    """The path of the first tag inside a layer's entry, or None."""
    for key, value in entry.items():
        if isinstance(value, Tagged | TaggedMap):
            return f"{prefix}{key}"
        if isinstance(value, dict) and (found := _tag_inside(value, f"{prefix}{key}.")):
            return found
    return None


def _merge(base: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in change.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def resolve_layers(doc: dict[str, Any], reg: Registry) -> dict[str, Resolved]:
    """The GraphSpec's layers by name, in drawing order: those it inherits first, then its
    own. Each value is the layer as listed (type and parameters), merged by name down the
    extends chain."""
    out: dict[str, Resolved] = {}
    for d in reversed(chain("graphspec", doc, reg)):
        label = f"GraphSpec '{d.get('name')}'"
        for fixed, name, entry in _layers_in(d):
            if is_none(entry):
                out.pop(name, None)
                continue
            if not isinstance(entry, dict):
                continue
            old = out.get(name)
            same = old is not None and entry.get("type", old.value.get("type")) == old.value.get(
                "type"
            )
            value = _merge(old.value, entry) if same and old is not None else dict(entry)
            out[name] = Resolved(value, fixed, label)
    return out


def with_defaults(layer: dict[str, Any]) -> dict[str, Any]:
    """A layer as {"type": ..., path: value}, with every parameter its type defines, and
    under "look" the theme parameters it sets for itself, by their path in the layer. One of
    its own parameters whose look comes from the theme is there only if the layer sets it."""
    kind = layer["type"]
    listed = flatten({k: v for k, v in layer.items() if k != "type"})
    looks = look_paths(kind)
    return {
        "type": kind,
        **{
            p: listed.get(p, d.default)
            for p, d in definitions("layer", kind).items()
            if p not in looks
        },
        "look": {p: v for p, v in listed.items() if p in looks},
    }


def layer_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems with the layers a GraphSpec lists, and with the layers it ends up with."""
    errors = []
    try:
        chosen = named("graphspec", doc, reg)
        gt_name, theme_name = chosen["graph_type"], chosen["theme"]
        gt = resolve("graph_type", reg.docs["graph_type"][gt_name], reg)
        theme = resolve("theme", reg.docs["theme"][theme_name], reg, gt_name)
    except (ValueError, KeyError):
        return []
    accepted = gt.value("layer.types", []) or []
    parent = doc.get("extends")
    inherited = (
        resolve_layers(reg.docs["graphspec"][parent], reg)
        if not is_none(parent) and parent in reg.docs["graphspec"]
        else {}
    )
    names = reg.names()
    for _, name, entry in _layers_in(doc):
        where = "layers"
        if name == "":
            errors.append(f"{where}: must be layers keyed by name, or None")
            continue
        where = f"{where}.{name}"
        if name in inherited and inherited[name].fixed:
            errors.append(f"{where}: fixed by {inherited[name].origin}")
            continue
        if is_none(entry):
            continue
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be a layer: its type, then its parameters")
            continue
        if inside := _tag_inside(entry):
            errors.append(f"{where}.{inside}: a tag goes on the layer or on layers, not inside")
            continue
        kind = entry.get("type", inherited[name].value.get("type") if name in inherited else None)
        if is_none(kind):
            errors.append(f"{where}.type: required: one of {', '.join(map(str, accepted))}")
            continue
        if kind not in reg.docs["layer"]:
            errors.append(
                f"{where}.type: unknown layer type '{kind}'{suggest(str(kind), reg.docs['layer'])}"
            )
            continue
        if kind not in accepted:
            errors.append(
                f"{where}.type: graph type '{gt_name}' takes only {', '.join(map(str, accepted))}"
            )
            continue
        defs, looks = definitions("layer", str(kind)), look_paths(str(kind))
        theme_defs = definitions("theme")
        for path, value in flatten({k: v for k, v in entry.items() if k != "type"}).items():
            p = defs.get(path) or (theme_defs[looks[path]] if path in looks else None)
            if p is None:
                known = [*defs, *looks]
                if any(k.startswith(f"{path}.") for k in known) and is_none(value):
                    continue  # an empty category
                errors.append(f"{where}.{path}: unknown parameter of {kind}{suggest(path, known)}")
                continue
            if path in looks and theme.fixed(looks[path], theme_defs[looks[path]].fixed):
                errors.append(f"{where}.{path}: fixed by theme '{theme_name}'")
                continue
            for suffix, message in check_parameter(p, value, names):
                errors.append(f"{where}.{path}{suffix}: {message}")
    return errors
