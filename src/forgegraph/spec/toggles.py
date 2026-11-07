"""Toggles: the series and layers a reader can show or hide on an HTML page.

A toggle layer (layer_toggle.yaml) lists its items: `series` for every series, `layers` for
every layer but the choice and toggle layers, or series and layers by name. `hidden` names
the items hidden when the page opens, and in png, pdf and svg files. A GraphSpec has at most
one toggle layer.

The figure is drawn once, with everything shown, so its axes, keys and labels are placed as
usual (drawing/toggles.py). A hidden series loses its marks, error bars, value labels and
direct label, and a hidden layer its lines, fill and label; a key's entries stay. In a
layout, the items of the same name in tiles with toggle layers share one checkbox.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forgegraph.spec.layers import CONTROLS, resolve_layers, with_defaults
from forgegraph.spec.parameters import is_none
from forgegraph.spec.registry import Registry
from forgegraph.spec.series import resolve_series

KINDS = {"series": "series", "layers": "layer"}  # an items word, and its items' kind


@dataclass(frozen=True)
class Toggles:
    """A toggle layer's items, each its name and its kind (series or layer, as its artists'
    owners name it: drawing/owners.py), and the names of those hidden when the page opens."""

    name: str  # the layer's
    items: tuple[tuple[str, str], ...]
    hidden: tuple[str, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.items)


def toggles(doc: dict[str, Any], reg: Registry) -> Toggles | None:
    """The GraphSpec's toggle layer, or None; its problems are toggle_problems'."""
    found, _ = _resolved(doc, reg)
    return found


def toggle_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems with the GraphSpec's toggle layers: what they name."""
    return _resolved(doc, reg)[1]


def _resolved(doc: dict[str, Any], reg: Registry) -> tuple[Toggles | None, list[str]]:
    layers = resolve_layers(doc, reg)
    listed = [(n, r.value) for n, r in layers.items() if r.value.get("type") == "toggle"]
    if not listed:
        return None, []
    if len(listed) > 1:
        names = ", ".join(n for n, _ in listed)
        return None, [f"layers: {names} are toggle layers; a GraphSpec has at most one"]
    name, entry = listed[0]
    values = with_defaults(entry)
    where = f"layers.{name}"
    owned = {
        "series": list(resolve_series(doc, reg)),
        "layer": [n for n, r in layers.items() if r.value.get("type") not in CONTROLS],
    }
    items: dict[str, str] = {}
    problems = []
    for i, word in enumerate(values["items"]):
        kinds = [k for k, names in owned.items() if word in names]
        if word in KINDS:
            items.update({n: KINDS[word] for n in owned[KINDS[word]]})
        elif len(kinds) == 1:
            items[word] = kinds[0]
        elif kinds:
            problems.append(f"{where}.items[{i}]: '{word}' names both a series and a layer")
        else:
            problems.append(
                f"{where}.items[{i}]: '{word}' is no series or layer of the GraphSpec; the series "
                f"are {', '.join(owned['series']) or 'none'}, and the layers "
                f"{', '.join(owned['layer']) or 'none'}"
            )
    hidden = [] if is_none(values["hidden"]) else list(values["hidden"])
    for i, h in enumerate(hidden):
        if h not in items:
            problems.append(
                f"{where}.hidden[{i}]: '{h}' isn't one of the items: {', '.join(items) or 'none'}"
            )
    if problems:
        return None, problems
    return Toggles(name, tuple(items.items()), tuple(hidden)), []
