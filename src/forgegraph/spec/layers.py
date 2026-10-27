"""A GraphSpec's layers: what's drawn on top of the graph.

A GraphSpec's layers are keyed by names it chooses; each has a type, one of its graph type's
layer.types, and that layer type's parameters. Through extends, layers merge by name: a
GraphSpec changes an inherited layer's parameters by naming it, replaces it by giving another
type, and removes it with None; it can't change a layer tagged !fix, itself or through the
layers category. A tag goes on a layer or on layers, never inside a layer.
"""

from __future__ import annotations

from typing import Any

from forgegraph.spec.common import suggest
from forgegraph.spec.parameters import (
    PARAMETERS,
    check_parameter,
    definitions,
    flatten,
    is_none,
)
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import Resolved, chain, named, resolve
from forgegraph.spec.tags import Tagged, TaggedMap, status_at, untag


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
    """A layer as {"type": ..., path: value}, with every parameter its type defines."""
    kind = layer["type"]
    listed = flatten({k: v for k, v in layer.items() if k != "type"})
    return {
        "type": kind,
        **{p: listed.get(p, d.default) for p, d in definitions("layer", kind).items()},
    }


def layer_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems with the layers a GraphSpec lists, and with the layers it ends up with."""
    errors = []
    try:
        gt_name = named("graphspec", doc, reg)["graph_type"]
        gt = resolve("graph_type", reg.docs["graph_type"][gt_name], reg)
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
        defs = definitions("layer", str(kind))
        for path, value in flatten({k: v for k, v in entry.items() if k != "type"}).items():
            p = defs.get(path)
            if p is None:
                errors.append(f"{where}.{path}: unknown parameter of {kind}{suggest(path, defs)}")
                continue
            for suffix, message in check_parameter(p, value, names):
                errors.append(f"{where}.{path}{suffix}: {message}")
    return errors
