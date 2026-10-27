"""Resolving a file of any kind: the files it extends, what each lists, and the value each
parameter ends up with, whether it's fixed, and which file set it.

The nearest file in the extends chain that lists a parameter's value decides it, and the
nearest file that tags it, or a category above it, decides whether it's fixed (see tags.py).
In a theme or format, a graph type's name may be used as a heading; parameters under it
apply to that graph type only and beat the general ones in the same file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forgegraph.spec.common import kind_label, suggest
from forgegraph.spec.parameters import (
    COLLECTIONS,
    NAMES,
    NONE,
    PARAMETERS,
    Parameter,
    definitions,
    flatten,
    graph_type_files,
    is_none,
)
from forgegraph.spec.registry import Registry
from forgegraph.spec.tags import UNSET, status_at, untag

HEADINGS = ("theme", "format")  # kinds that may use graph-type headings


def entries(kind: str, doc: dict[str, Any], reg: Registry) -> list[tuple[str | None, str, Any]]:
    """(graph-type heading or None, parameter path, value) for every listed value, without its
    tag; a tag with no value is listed as UNSET. Anything not shaped as category.parameter is
    kept as written, to be reported."""
    out: list[tuple[str | None, str, Any]] = []
    tree = untag(doc.get(PARAMETERS))
    if is_none(tree):
        return out
    if not isinstance(tree, dict):
        return [(None, "", tree)]
    for category, params in tree.items():
        if category in COLLECTIONS.get(kind, ()):
            continue  # layers and tabs: see layer_problems and spec/layout.py
        if kind in HEADINGS and category in reg.docs["graph_type"] and isinstance(params, dict):
            for sub, sub_params in params.items():
                out += _category(str(category), str(sub), sub_params)
        else:
            out += _category(None, str(category), params)
    return out


def _category(heading: str | None, category: str, params: Any) -> list:
    if not isinstance(params, dict):
        return [(heading, category, untag(params))]
    return [
        (heading, path, untag(value)) for path, value in flatten(params, f"{category}.").items()
    ]


def tag_status(
    kind: str, doc: dict[str, Any], path: str, graph_type: str | None = None
) -> bool | None:
    """Whether one file's tags make a parameter fixed: the tag nearest it, under the graph
    type's heading first; None if the file doesn't tag it."""
    tree = doc.get(PARAMETERS)
    if not isinstance(untag(tree), dict):
        return None
    if kind in HEADINGS and graph_type is not None:
        under = untag(tree).get(graph_type)
        if isinstance(under, dict) and (s := status_at(under, path)) is not None:
            return s
    return status_at(tree, path)


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
    via: str | None = None  # a style's member no file sets: the parameter its value is from


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
    file that lists a value decides it, and the nearest that tags it whether it's fixed;
    within one file, an entry under the graph type's heading beats the general one."""
    docs = chain(kind, doc, reg)
    values: dict[str, tuple[Any, str]] = {}
    for d in docs:
        own: dict[str, tuple[int, Any, str]] = {}
        label = f"{kind_label(kind)} '{d.get('name')}'"
        for heading, path, value in entries(kind, d, reg):
            if heading not in (None, graph_type) or value is UNSET:
                continue
            rank = 0 if heading else 1
            origin = f"{label}, under {heading}" if heading else label
            if path not in own or rank < own[path][0]:
                own[path] = (rank, value, origin)
        for path, (_, value, origin) in own.items():
            values.setdefault(path, (value, origin))

    def status(path: str) -> bool:
        return next(
            (s for d in docs if (s := tag_status(kind, d, path, graph_type)) is not None), False
        )

    out = Values()
    for path, (value, origin) in values.items():
        out[path] = Resolved(value, status(path), origin)
    for p in _members(kind, doc, reg):
        if p.path not in out and p.inherits is not None and p.inherits in out:
            source = out[p.inherits]
            out[p.path] = Resolved(source.value, status(p.path), source.origin, p.inherits)
    root = f"{kind_label(kind)} '{docs[-1].get('name')}'"
    for p in _copies(kind, doc, reg):  # with the same defaults as the parameters they copy
        if p.path not in out:
            out[p.path] = Resolved(NONE if p.default is None else p.default, status(p.path), root)
    return out


def _copies(kind: str, doc: dict[str, Any], reg: Registry) -> list[Parameter]:
    """A kind's parameters in a category with a sibling's parameters (`[same as x]`): no file
    need list them."""
    if kind != "graph_type":
        return []
    return [p for p in definitions_for(kind, doc, reg).values() if p.same is not None]


def _members(kind: str, doc: dict[str, Any], reg: Registry) -> list[Parameter]:
    """A kind's styles' members, in definition order: each after the parameter it takes its
    value from."""
    if kind not in ("theme",):
        return []
    return [p for p in definitions_for(kind, doc, reg).values() if p.inherits is not None]


def inherit(values: Values, defs: dict[str, Parameter]) -> None:
    """After a GraphSpec's settings are put in values: each member no file set takes the
    value of the parameter it inherits from again, in case a setting changed it."""
    for p in defs.values():
        r = values.get(p.path)
        if p.inherits is not None and r is not None and r.via is not None and p.inherits in values:
            source = values[p.inherits]
            values[p.path] = Resolved(source.value, r.fixed, source.origin, p.inherits)


def setter(kind: str, doc: dict[str, Any], reg: Registry, path: str) -> dict[str, Any] | None:
    """The file in doc's extends chain that sets a parameter, nearest first; None if none of
    them lists it."""
    for d in chain(kind, doc, reg):
        if any(p == path and v is not UNSET for _, p, v in entries(kind, d, reg)):
            return d
    return None


def named(kind: str, doc: dict[str, Any], reg: Registry) -> dict[str, Any]:
    """The specs a file names under specifications, by kind (see NAMES): a GraphSpec's graph
    type, theme and format, and a layout's format; None where unset."""
    if kind not in NAMES:
        return {}
    values = resolve(kind, doc, reg)
    return {k: values.value(f"specifications.{k}") for k in NAMES[kind]}
