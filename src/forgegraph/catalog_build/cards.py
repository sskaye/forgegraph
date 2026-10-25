"""A catalog panel's cards: what each one changes, where it's placed, and its drawing.

place() lays out a catalog's cards from its catalog file (forgegraph.catalog_build.files),
without drawing; Drawings draws them, each once.
"""

from __future__ import annotations

import io
from collections.abc import Collection
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from PIL import Image

from forgegraph.catalog_build.examples import NONSTANDARD, draw, image
from forgegraph.catalog_build.page import CSS_DPI
from forgegraph.graph import Graph, SpecError
from forgegraph.spec.parameters import NONE, Parameter
from forgegraph.spec.registry import Registry

if TYPE_CHECKING:  # catalog_build.files imports this module, so only to check types
    from forgegraph.catalog_build.files import Catalog

DENSITY = 1.5  # image pixels per CSS pixel: sharp on most screens, small enough to commit
COLORS = 64  # palette size: plenty for a graph's few colors and their anti-aliasing


@dataclass(frozen=True)
class Change:
    path: str  # a parameter's, or for a group, the numbered baseline's name
    value: Any
    parts: tuple[Change, ...] = ()  # a numbered baseline changing several parameters


@dataclass(frozen=True)
class Variation:
    """A parameter's change (with any it needs), from the baseline or a numbered baseline."""

    parameter: Parameter
    changes: tuple[Change, ...]  # the parameter's own first
    base: Change | None = None

    @property
    def change(self) -> Change:
        return self.changes[0]


@dataclass(frozen=True)
class Planned:
    """A card on a panel: its id and heading, the changes it draws besides the catalog's
    `always`, and the changes it must draw differently from (`start`, the card named
    `start_name`). A numbered baseline that is no parameter's card has no start; a
    parameter's card shown as a numbered baseline (`numbered`) keeps its start, though the
    build doesn't check it."""

    id: str
    heading: str
    changes: tuple[Change, ...]
    start: tuple[Change, ...] | None = None
    start_name: str = ""
    numbered: bool = False


def show(value: Any) -> str:
    """A parameter value as the specification files write it."""
    if isinstance(value, list):
        return "[" + ", ".join(show(v) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return NONE
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("\n", "\\n")  # a line break, as YAML writes it in quotes


def _change(c: Change) -> str:
    if c.parts:
        return ", ".join(_change(p) for p in c.parts)
    return "non-standard drawing" if c.path == NONSTANDARD else f"{c.path} = {show(c.value)}"


def _id(change: Change) -> str:
    return change.path.replace(".", "-")


def place(catalog: Catalog, shown: Collection[str]) -> list[Planned]:
    """The cards of a catalog's panel, in order: the baseline, then the card of each
    parameter in shown (by path), each numbered baseline before the first card starting
    from it."""
    first = "Baseline"
    if catalog.always:  # a layer's catalog: say what every card adds to the GraphSpec
        first = " + ".join([f"Baseline: {catalog.baseline}", *(_change(c) for c in catalog.always)])
    cards = [Planned("baseline", first, ())]
    variations = [v for p, v in catalog.variations if v is not None and p.path in shown]
    numbers: dict[str, int] = {}  # each numbered baseline's number, by the change that makes it
    placed: dict[str, int] = {}  # and its place in cards
    for v in variations:
        single = len(v.changes) == 1
        base = () if v.base is None else (v.base,)
        if single and _change(v.change) in numbers:  # already shown, as a numbered baseline
            i = placed[_change(v.change)]
            cards[i] = replace(cards[i], start=base, numbered=True)
            continue
        if v.base is not None and _change(v.base) not in numbers:
            numbers[_change(v.base)] = len(numbers) + 2
            placed[_change(v.base)] = len(cards)
            heading = f"Baseline {numbers[_change(v.base)]}: Baseline + {_change(v.base)}"
            cards.append(Planned(f"baseline-{_id(v.base)}", heading, (v.base,)))
        if single and v.base is None and any(w.base == v.change for w in variations):
            numbers[_change(v.change)] = len(numbers) + 2
            placed[_change(v.change)] = len(cards)
            heading = f"Baseline {numbers[_change(v.change)]}: Baseline + {_change(v.change)}"
            cards.append(
                Planned(f"baseline-{_id(v.change)}", heading, (v.change,), (), numbered=True)
            )
            continue
        start = "Baseline" if v.base is None else f"Baseline {numbers[_change(v.base)]}"
        heading = " + ".join([start, *(_change(c) for c in v.changes)])
        cards.append(Planned(f"card-{_id(v.change)}", heading, (*base, *v.changes), base, start))
    return cards


def _png(graph: Graph) -> bytes:
    raw = image(graph, CSS_DPI * DENSITY).convert("RGB")
    small = raw.quantize(COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    buffer = io.BytesIO()
    small.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def _message_png(text: str, width_in: float) -> bytes:
    """A card that can't be drawn: the problem, in place of its graph."""
    import textwrap

    from matplotlib.figure import Figure

    fig = Figure(figsize=(width_in, width_in * 0.6), dpi=CSS_DPI)
    fig.text(0.05, 0.9, "\n".join(textwrap.wrap(text, 60)), va="top", fontsize=9, color="#57606a")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor="#f6f8fa")
    return buffer.getvalue()


class Drawings:
    """A catalog's cards drawn in a theme and format (None: the baseline's), each once, by
    its changes. A lenient one draws a card that can't be drawn as its problem, in place of
    its graph; otherwise that's a CatalogError. The baseline itself must draw."""

    def __init__(
        self,
        catalog: Catalog,
        reg: Registry,
        theme: str | None = None,
        fmt: str | None = None,
        lenient: bool = False,
    ) -> None:
        self.catalog = catalog
        self.reg = reg
        self.theme = theme
        self.fmt = fmt
        self.lenient = lenient
        self._drawn: dict[str, tuple[Graph | None, bytes]] = {}

    def graph(self, *changes: Change) -> Graph | None:
        """The card's graph; None if it can't be drawn."""
        return self._draw(changes)[0]

    def png(self, *changes: Change) -> bytes:
        """The card's image."""
        return self._draw(changes)[1]

    def _draw(self, changes: tuple[Change, ...]) -> tuple[Graph | None, bytes]:
        key = " + ".join(_change(c) for c in changes)
        if key in self._drawn:
            return self._drawn[key]
        catalog = self.catalog
        try:
            graph = draw(
                *catalog.always,
                *changes,
                spec=catalog.baseline,
                theme=self.theme,
                format=self.fmt,
                reg=self.reg,
            )
        except SpecError as e:
            from forgegraph.catalog_build.files import CatalogError

            card = " + ".join(["Baseline", *(_change(c) for c in changes)])
            if self.lenient and changes:
                baseline = self.graph()
                assert baseline is not None  # the baseline itself must draw
                width = baseline.figure.get_size_inches()[0]
                problem = f"Can't be drawn in this theme and format: {e.problems[0]}"
                self._drawn[key] = None, _message_png(problem, width)
                return self._drawn[key]
            kind = catalog.kind.replace("_", " ")
            raise CatalogError(
                [f"{kind} {catalog.name}: {card}: {p}" for p in e.problems]
            ) from None
        self._drawn[key] = graph, _png(graph)
        return self._drawn[key]
