"""Drawing the catalog's cards: a baseline GraphSpec with changes.

What each card changes comes from the catalog files (forgegraph.catalog_build.files).
"""

from __future__ import annotations

import copy
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from forgegraph.drawing import export
from forgegraph.drawing.style import isolated
from forgegraph.graph import Graph, data_path, render
from forgegraph.spec.layers import resolve_layers
from forgegraph.spec.parameters import NONE, Parameter, definitions, tree_has, tree_set
from forgegraph.spec.registry import Registry, builtin
from forgegraph.spec.resolve import resolve

NONSTANDARD = "non-standard"  # a change that draws on the graph after ForgeGraph finishes
FOOTNOTED = "footnoted"  # a change that draws a footnote, as a scheduled run's stamp
FOOTNOTE = "Data as of Oct 21, 2026, 05:12 \u00b7 rendered daily at 06:00"
SPECIAL = (NONSTANDARD, FOOTNOTED)  # baselines that aren't parameter changes


@dataclass(frozen=True)
class Change:
    path: str  # a parameter's, or for a group, the numbered baseline's name
    value: Any
    parts: tuple[Change, ...] = ()  # a numbered baseline changing several parameters


def _flat(changes: tuple[Change, ...]) -> list[Change]:
    return [p for c in changes for p in (c.parts or (c,))]


def _child(kind: str, parent: str, changes: dict[str, Any]) -> dict[str, Any]:
    defs = definitions(kind)
    sections: dict[str, dict] = {"fixed_parameters": {}, "variable_parameters": {}}
    for path, value in changes.items():
        section = "fixed_parameters" if defs[path].fixed else "variable_parameters"
        tree_set(sections[section], path, value)
    return {
        "name": "catalog",
        "version": 0,
        "description": "",
        "extends": parent,
        **{k: (v or NONE) for k, v in sections.items()},
    }


def draw(
    *changes: Change,
    spec: str,
    theme: str | None = None,
    format: str | None = None,
    reg: Registry | None = None,
) -> Graph:
    """A GraphSpec, in this theme and format if given, with these
    changes. A parameter the GraphSpec lists is changed there; any other in a theme or format
    extending the one it uses."""
    reg = (reg or builtin()).copy()
    doc = copy.deepcopy(reg.docs["graphspec"][spec])
    inherited = list(resolve_layers(doc, reg)) if doc.get("extends") not in (None, NONE) else []
    in_chain = set(resolve("graphspec", doc, reg))  # set by the GraphSpec or one it extends
    listed = doc["variable_parameters"]
    listed.pop("layers", None)  # a card shows one change; layers are shown on their own cards
    if inherited:  # and those it inherits are removed by name
        listed["layers"] = {name: NONE for name in inherited}
    for kind, name in (("theme", theme), ("format", format)):
        if name is not None:
            listed["specifications"][kind] = name
    others: dict[str, dict[str, Any]] = {"theme": {}, "format": {}}
    for c in _flat(changes):
        if c.path in SPECIAL:
            continue
        if c.path in in_chain or tree_has(listed, c.path) or c.path.startswith("layers."):
            tree_set(listed, c.path, c.value)
        elif c.path in definitions("theme"):
            others["theme"][c.path] = c.value
        elif c.path in definitions("format"):
            others["format"][c.path] = c.value
        else:  # the GraphSpec's or its graph type's, inherited by the baseline
            tree_set(listed, c.path, c.value)
    for kind, values in others.items():
        if values:
            reg.add(kind, _child(kind, listed["specifications"][kind], values))
            listed["specifications"][kind] = "catalog"
    home = reg.paths["graphspec"].get(spec)
    where = data_path(doc, reg, home.parent if home is not None else Path.cwd())
    if where is not None:  # the copy is drawn from memory: its data found where the original's is
        tree_set(listed, "data.file", str(where))
    footnoted = any(c.path == FOOTNOTED for c in _flat(changes))
    graph = render(doc, None, reg, footnote=FOOTNOTE if footnoted else None)
    if any(c.path == NONSTANDARD for c in _flat(changes)):
        graph.axes.axvline(60, color="#000000", linewidth=1)  # any addition makes it non-standard
    return graph


def png(graph: Graph, dpi: float) -> bytes:
    """The graph as a PNG with no metadata, so the same drawing gives the same bytes."""
    buffer = io.BytesIO()
    with isolated(graph.style):
        graph.figure.savefig(
            buffer, format="png", dpi=dpi, metadata={"Software": None, export.KEY: None}
        )
    return buffer.getvalue()


def image(graph: Graph, dpi: float) -> Image.Image:
    """The graph drawn at dpi, as the pixels png() would encode: savefig's raw buffer, as
    many pixels across and down as Agg's renderer has (the figure's size, truncated)."""
    buffer = io.BytesIO()
    with isolated(graph.style):
        graph.figure.savefig(buffer, format="raw", dpi=dpi)
    width, height = (int(v * dpi) for v in graph.figure.get_size_inches())
    return Image.frombuffer("RGBA", (width, height), buffer.getvalue(), "raw", "RGBA", 0, 1)


@dataclass(frozen=True)
class Variation:
    """A parameter's change (with any it needs), from the baseline or a numbered baseline."""

    parameter: Parameter
    changes: tuple[Change, ...]  # the parameter's own first
    base: Change | None = None

    @property
    def change(self) -> Change:
        return self.changes[0]
