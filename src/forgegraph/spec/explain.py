"""Every value a graph is drawn with, by kind: its GraphSpec's own, its layers', and its graph
type's, theme's and format's, where the GraphSpec's settings replace variable values."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from forgegraph.spec.layers import resolve_layers, with_defaults
from forgegraph.spec.parameters import definitions
from forgegraph.spec.registry import Registry, builtin
from forgegraph.spec.resolve import (
    HEADINGS,
    Resolved,
    Values,
    definitions_for,
    named,
    resolve,
)


@dataclass
class Explained:
    """Every value a graph is drawn with, by kind, with whether it's fixed and which file set
    it. `layers` holds each layer by name: its type and every parameter of that type, as
    {"type": ..., path: value}."""

    graphspec: Values
    layers: Values
    graph_type: Values
    theme: Values
    format: Values

    def kinds(self) -> dict[str, Values]:
        """The values by kind, in this order: graphspec, layers, graph_type, theme, format."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def plain(self) -> dict[str, dict[str, Any]]:
        """The values alone, by kind and path."""
        return {kind: values.plain() for kind, values in self.kinds().items()}


def explain(
    doc: dict[str, Any], reg: Registry | None = None, format: Values | None = None
) -> Explained:
    """Every value a graph is drawn with (see Explained). The GraphSpec's settings replace
    variable values. With `format` (a layout's format's values), those are the format's."""
    reg = reg or builtin()
    spec = resolve("graphspec", doc, reg)
    chosen = named("graphspec", doc, reg)
    own = definitions("graphspec")
    layers = Values(
        {
            name: Resolved(with_defaults(r.value), r.fixed, r.origin)
            for name, r in resolve_layers(doc, reg).items()
        }
    )
    out: dict[str, Values] = {}
    for kind, name in chosen.items():
        if kind == "format" and format is not None:
            out[kind] = Values(format)
            continue
        other = reg.docs[kind][name]
        defs = definitions_for(kind, other, reg)
        heading = chosen["graph_type"] if kind in HEADINGS else None
        values = resolve(kind, other, reg, heading)
        values.update({p: r for p, r in spec.items() if p in defs})
        out[kind] = values
    graphspec = Values({p: r for p, r in spec.items() if p in own})
    return Explained(graphspec, layers, out["graph_type"], out["theme"], out["format"])
