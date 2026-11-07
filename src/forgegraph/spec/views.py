"""Views: a choice layer's alternatives, each the GraphSpec with some of its parameters changed.

A choice layer (layer_choice.yaml) lists two or more views by name, each a set of GraphSpec
parameters and their values, written as dotted paths (series.Voltage.column) or as nested
categories; {} changes nothing. A view can't set specifications, data, output or provenance,
nor a choice or toggle layer's parameters (VIEW_LIMITS); anything else is checked as the GraphSpec
with the view's changes would be, so a view can set a parameter only where the GraphSpec
could. Two choice layers can't set the same parameter.

ForgeGraph draws every view ahead of time: with several choice layers, every combination
(combinations), the first view of each first. A png, pdf or svg file shows the first; an
HTML page shows a control for each choice layer, which switches between them
(drawing/page.py). In a layout, choice layers of the same name in several tiles share one
control, so their views must have the same names, in the same order.
"""

from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass
from typing import Any

from forgegraph.spec.layers import resolve_layers, with_defaults
from forgegraph.spec.parameters import PARAMETERS, flatten, is_none
from forgegraph.spec.registry import Registry
from forgegraph.spec.tags import Tagged


@dataclass(frozen=True)
class Control:
    """A choice layer, as its page control shows it: the layer's name, the text before the
    control, dropdown or radio, and each view's name and changes ({dotted path: value})."""

    name: str
    label: str | None
    kind: str
    views: tuple[tuple[str, dict[str, Any]], ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.views)


def controls(doc: dict[str, Any], reg: Registry) -> list[Control]:
    """The GraphSpec's choice layers, in drawing order."""
    out = []
    for name, r in resolve_layers(doc, reg).items():
        if r.value.get("type") != "choice":
            continue
        values = with_defaults(r.value)
        views = r.value.get("views")
        label = values["label"]
        out.append(
            Control(
                name,
                None if is_none(label) else str(label),
                str(values["control"]),
                tuple((str(v), changes(c)) for v, c in (views or {}).items()),
            )
        )
    return out


def changes(view: Any) -> dict[str, Any]:
    """A view's changes, by dotted path: {} for {} or None."""
    return flatten(view) if isinstance(view, dict) else {}


def combinations(listed: list[Control]) -> list[tuple[tuple[str, ...], dict[str, Any]]]:
    """Every combination of the controls' views, the first view of each first: the views'
    names, one for each control, and their changes together."""
    out = []
    for picked in itertools.product(*(c.views for c in listed)):
        merged: dict[str, Any] = {}
        for _, change in picked:
            merged.update(change)
        out.append((tuple(name for name, _ in picked), merged))
    return out


def applied(doc: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    """A copy of the GraphSpec with the changes made to its own parameters: through
    extends, each then wins over what it inherits, as a parameter the file lists does."""
    out = copy.deepcopy(doc)
    tree = out.get(PARAMETERS)
    if not isinstance(tree, dict):
        tree = out[PARAMETERS] = {}
    for path, value in change.items():
        *parents, leaf = path.split(".")
        node = tree
        for key in parents:
            if not isinstance(node.get(key), dict):
                node[key] = {}
            node = node[key]
        old = node.get(leaf)
        node[leaf] = Tagged(value, old.fixed) if isinstance(old, Tagged) else value
    return out


def view_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems with the GraphSpec's views: each is checked as the GraphSpec with its
    changes."""
    from forgegraph.spec.validate import validate  # validate checks views with this

    problems = []
    listed = controls(doc, reg)
    for c in listed:
        where = f"layers.{c.name}.views"
        if len(c.views) < 2:
            problems.append(f"{where}: must list two or more views")
            continue
        for name, change in c.views:
            problems += [
                f"{where}.{name}: {p}"
                for p in validate("graphspec", applied(doc, change), reg, views=False)
            ]
    for a, b in itertools.combinations(listed, 2):
        both = sorted({p for _, ch in a.views for p in ch} & {p for _, ch in b.views for p in ch})
        if both:
            problems.append(
                f"layers.{b.name}.views: sets {', '.join(both)}, which layers.{a.name}'s views "
                "also set; two choice layers can't set the same parameter"
            )
    return problems
