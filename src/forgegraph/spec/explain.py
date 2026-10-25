"""Every value a graph is drawn with, by kind: its GraphSpec's own, its layers', and its graph
type's, theme's and format's, where the GraphSpec's settings replace variable values."""

from __future__ import annotations

from typing import Any

from forgegraph.spec.layers import resolve_layers, with_defaults
from forgegraph.spec.parameters import definitions
from forgegraph.spec.registry import Registry, builtin
from forgegraph.spec.resolve import (
    HEADINGS,
    OTHER_KINDS,
    Resolved,
    choices,
    definitions_for,
    resolve_detailed,
)


def explain(doc: dict[str, Any], reg: Registry | None = None) -> dict[str, dict[str, Resolved]]:
    """Every value a graph is drawn with, by kind, with whether it's fixed and which file set
    it: {"graphspec": {...}, "graph_type": {...}, "theme": {...}, "format": {...}}. The
    GraphSpec's settings replace variable values. "layers" holds each layer by name: its type
    and every parameter of that type, as {"type": ..., path: value}."""
    reg = reg or builtin()
    spec = resolve_detailed("graphspec", doc, reg)
    chosen = choices(doc, reg)
    own = definitions("graphspec")
    out = {"graphspec": {p: r for p, r in spec.items() if p in own}}
    out["layers"] = {
        name: Resolved(with_defaults(r.value), r.fixed, r.origin)
        for name, r in resolve_layers(doc, reg).items()
    }
    for kind in OTHER_KINDS:
        other = reg.docs[kind][chosen[kind]]
        defs = definitions_for(kind, other, reg)
        heading = chosen["graph_type"] if kind in HEADINGS else None
        values = resolve_detailed(kind, other, reg, heading)
        values.update({p: r for p, r in spec.items() if p in defs})
        out[kind] = values
    return out


def resolve_graphspec(
    doc: dict[str, Any], reg: Registry | None = None
) -> dict[str, dict[str, Any]]:
    """The values a graph is drawn with, by kind (see explain)."""
    return {
        kind: {p: r.value for p, r in values.items()} for kind, values in explain(doc, reg).items()
    }
