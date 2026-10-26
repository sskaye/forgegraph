"""Resolving a file of any kind: the files it extends, what each lists, and the value each
parameter ends up with, whether it's fixed, and which file set it.

The nearest file in the extends chain that lists a parameter decides it. In a theme or
format, a graph type's name may be used as a heading; parameters under it apply to that
graph type only and beat the general ones in the same file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forgegraph.spec.common import kind_label, suggest
from forgegraph.spec.parameters import (
    COLLECTIONS,
    NAMES,
    SECTIONS,
    Parameter,
    definitions,
    flatten,
    graph_type_files,
    is_none,
)
from forgegraph.spec.registry import Registry

HEADINGS = ("theme", "format")  # kinds that may use graph-type headings


def entries(
    kind: str, doc: dict[str, Any], reg: Registry
) -> list[tuple[str, str | None, str, Any]]:
    """(section, graph-type heading or None, parameter path, value) for every listed value.
    Anything not shaped as category.parameter is kept as written, to be reported."""
    out: list[tuple[str, str | None, str, Any]] = []
    for section in SECTIONS:
        tree = doc.get(section)
        if is_none(tree):
            continue
        if not isinstance(tree, dict):
            out.append((section, None, "", tree))
            continue
        for category, params in tree.items():
            if category in COLLECTIONS.get(kind, ()):
                continue  # layers and tabs: see layer_problems and spec/layout.py
            if kind in HEADINGS and category in reg.docs["graph_type"] and isinstance(params, dict):
                for sub, sub_params in params.items():
                    out += _category(section, str(category), str(sub), sub_params)
            else:
                out += _category(section, None, str(category), params)
    return out


def _category(section: str, heading: str | None, category: str, params: Any) -> list:
    if not isinstance(params, dict):
        return [(section, heading, category, params)]
    return [
        (section, heading, path, value) for path, value in flatten(params, f"{category}.").items()
    ]


def chain(kind: str, doc: dict[str, Any], reg: Registry) -> list[dict[str, Any]]:
    """The document, then each file it extends, nearest first."""
    chain = [doc]
    seen = [doc.get("name")]
    parent = doc.get("extends")
    while not is_none(parent):
        if parent in seen:
            raise ValueError(
                f"extends: '{parent}' extends itself, through {' → '.join(map(str, seen))}"
            )
        nxt = reg.docs[kind].get(parent)
        if nxt is None:
            unloaded = reg.unloaded(str(parent), bool(reg.owner(kind, chain[-1])))
            if unloaded:
                raise ValueError(f"extends: {unloaded}")
            raise ValueError(
                f"extends: unknown {kind_label(kind)} '{parent}'{suggest(parent, reg.docs[kind])}"
            )
        chain.append(nxt)
        seen.append(parent)
        parent = nxt.get("extends")
    return chain


def definitions_for(kind: str, doc: dict[str, Any], reg: Registry) -> dict[str, Parameter]:
    """A graph type's parameters are those of the graph type at the root of its chain."""
    if kind != "graph_type":
        return definitions(kind)
    root = chain(kind, doc, reg)[-1]["name"]
    if root not in graph_type_files():
        defined = ", ".join(graph_type_files())
        raise ValueError(
            f"extends: None, but only ForgeGraph defines graph types; extend one of: {defined}"
        )
    return definitions("graph_type", root)


@dataclass(frozen=True)
class Resolved:
    """A parameter's value as resolved: whether it's fixed, and which file set it."""

    value: Any
    fixed: bool
    origin: str  # e.g. "theme 'journal'", or "theme 'journal', under xy"


class Values(dict[str, Resolved]):
    """Resolved values by parameter path, each with whether it's fixed and which file set
    it."""

    def value(self, path: str, default: Any = None) -> Any:
        """A parameter's value, or default if it isn't listed."""
        r = self.get(path)
        return default if r is None else r.value

    def fixed(self, path: str, default: bool = False) -> bool:
        """Whether a parameter is fixed, or default if it isn't listed."""
        r = self.get(path)
        return default if r is None else r.fixed

    def plain(self) -> dict[str, Any]:
        """The values alone, by path."""
        return {p: r.value for p, r in self.items()}


def resolve(kind: str, doc: dict[str, Any], reg: Registry, graph_type: str | None = None) -> Values:
    """Every listed parameter's value, whether it's fixed, and which file set it. The nearest
    file that lists a parameter decides it; within one file, an entry under the graph type's
    heading beats the general one."""
    out = Values()
    for d in chain(kind, doc, reg):
        own: dict[str, tuple[int, Resolved]] = {}
        label = f"{kind_label(kind)} '{d.get('name')}'"
        for section, heading, path, value in entries(kind, d, reg):
            if heading not in (None, graph_type):
                continue
            rank = 0 if heading else 1
            origin = f"{label}, under {heading}" if heading else label
            if path not in own or rank < own[path][0]:
                own[path] = (rank, Resolved(value, section == SECTIONS[0], origin))
        for path, (_, r) in own.items():
            out.setdefault(path, r)
    return out


def setter(kind: str, doc: dict[str, Any], reg: Registry, path: str) -> dict[str, Any] | None:
    """The file in doc's extends chain that sets a parameter, nearest first; None if none of
    them lists it."""
    for d in chain(kind, doc, reg):
        if any(p == path for _, _, p, _ in entries(kind, d, reg)):
            return d
    return None


def named(kind: str, doc: dict[str, Any], reg: Registry) -> dict[str, Any]:
    """The specs a file names under specifications, by kind (see NAMES): a GraphSpec's graph
    type, theme and format, and a layout's format; None where unset."""
    if kind not in NAMES:
        return {}
    values = resolve(kind, doc, reg)
    return {k: values.value(f"specifications.{k}") for k in NAMES[kind]}
