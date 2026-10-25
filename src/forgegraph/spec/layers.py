"""A GraphSpec's layers: what's drawn on top of the graph.

A GraphSpec's layers are keyed by names it chooses; each has a type, one of its graph type's
layer.types, and that layer type's parameters. Through extends, layers merge by name: a
GraphSpec changes an inherited layer's parameters by naming it, replaces it by giving another
type, and removes it with None; it can't change a layer listed as fixed.
"""

from __future__ import annotations

from typing import Any

from forgegraph.spec.common import suggest
from forgegraph.spec.parameters import NONE, SECTIONS, check_parameter, definitions, flatten
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import Resolved, chain, choices, resolve


def _layers_in(d: dict[str, Any]) -> list[tuple[str, str, Any]]:
    """(section, name, entry) for each layer a file lists, in order."""
    out = []
    for section in SECTIONS:
        tree = d.get(section)
        layers = tree.get("layers") if isinstance(tree, dict) else None
        if isinstance(layers, dict):
            out += [(section, str(name), entry) for name, entry in layers.items()]
        elif layers is not None:
            out.append((section, "", layers))
    return out


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
        for section, name, entry in _layers_in(d):
            if entry in (None, NONE):
                out.pop(name, None)
                continue
            if not isinstance(entry, dict):
                continue
            old = out.get(name)
            same = old is not None and entry.get("type", old.value.get("type")) == old.value.get(
                "type"
            )
            value = _merge(old.value, entry) if same and old is not None else dict(entry)
            out[name] = Resolved(value, section == SECTIONS[0], label)
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
        gt_name = choices(doc, reg)["graph_type"]
        gt = resolve("graph_type", reg.docs["graph_type"][gt_name], reg)
    except (ValueError, KeyError):
        return []
    accepted = gt.value("layer.types", []) or []
    parent = doc.get("extends")
    inherited = (
        resolve_layers(reg.docs["graphspec"][parent], reg)
        if parent not in (None, NONE) and parent in reg.docs["graphspec"]
        else {}
    )
    names = reg.names()
    for section, name, entry in _layers_in(doc):
        where = f"{section}.layers"
        if name == "":
            errors.append(f"{where}: must be layers keyed by name, or None")
            continue
        where = f"{where}.{name}"
        if name in inherited and inherited[name].fixed:
            errors.append(f"{where}: fixed by {inherited[name].origin}")
            continue
        if entry in (None, NONE):
            continue
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be a layer: its type, then its parameters")
            continue
        kind = entry.get("type", inherited[name].value.get("type") if name in inherited else None)
        if kind in (None, NONE):
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
