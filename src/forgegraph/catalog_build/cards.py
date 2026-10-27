"""A catalog panel's cards: what each one changes, where it's placed, and its drawing.

Every parameter of the spec a catalog shows gets one card, chosen by a rule, not by hand;
a format's output.* and provenance.* parameters, which change the saved files, and a graph
type's layer.types, which only permits layers, get none (EXEMPT): they never change a
drawing. A catalog page shows the variable parameters' cards; the perturbation test draws
them all. candidates() lists the values the rule gives a parameter's card, in order, from
the parameter's default d (the value the spec shown gives it: a theme's or format's own, a
graph type's or layer type's definition's), its range and the baseline's data:

1. true or false: not d.
2. A column in the range: each column of the baseline's data, in the data's order, that the
   GraphSpec drawn doesn't already use, and whose type the parameter takes: numbers for an
   axis's column or a layer's, any other.
3. A font family: each bundled family but d. A parameter whose name ends in format, with
   text in its range: FORMATS.
4. Other text in its range: SAMPLE_TEXT.
5. A hex color in its range: SAMPLE_COLOR.
6. A number with a numeric default: 2d, then d/2 (rounded down for a whole number; for
   d = 0, just 1), each within the range's interval. A figure size defaulting to auto: the
   other size.
7. A number with a None default: for an axis's min or max, the median of the axis's column;
   for its tick.step, a quarter of the column's range, to one significant figure; for a
   layer's value, the median of the layer's axis's column.
8. Then the range's words after d, in the range's order and wrapping round, without d; for
   a list default, the one-item list of each word after d's first, then d reversed.
9. Last, d itself, which changes the drawing where the GraphSpec sets another value (the
   base pack's example sets a benchmark).

A value outside the range isn't a candidate. A card setting one of the parameters TIES ties
to None sets the others to None too.

place() puts each card on its first candidate that draws, and differently from the baseline
it's drawn on, on the first such baseline: the catalog's GraphSpec first, then its numbered
baselines in the catalog files' order. Drawings draws the cards, each once.
"""

from __future__ import annotations

import io
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from PIL import Image

from forgegraph.catalog_build.examples import NONSTANDARD, draw, image
from forgegraph.catalog_build.page import CSS_DPI
from forgegraph.fonts import bundled_families
from forgegraph.graph import Graph, SpecError
from forgegraph.spec.parameters import NONE, Parameter, is_none
from forgegraph.spec.registry import Registry
from forgegraph.spec.validate import TIES

if TYPE_CHECKING:  # catalog_build.files imports this module, so only to check types
    from forgegraph.catalog_build.files import Catalog

DENSITY = 1.5  # image pixels per CSS pixel: sharp on most screens, small enough to commit
COLORS = 64  # palette size: plenty for a graph's few colors and their anti-aliasing
# Parameters that can't change a drawing: a format's saved files, and the layer types a
# GraphSpec may list
EXEMPT = {"format": ("output.", "provenance."), "graph_type": ("layer.types",)}
SIZES = {"figure.height": "figure.width", "figure.width": "figure.height"}  # each from the other
FORMATS = (".3f", "%b %-d")  # a format's candidates: for numbers, then for dates
SAMPLE_TEXT = "Sample text"
SAMPLE_COLOR = "#D55E00"
NUMBERS = ("int ≥ 0", "int > 0", "float", "float ≥ 0", "float > 0")


@dataclass(frozen=True)
class Change:
    path: str  # a parameter's, or for a group, the numbered baseline's name
    value: Any
    parts: tuple[Change, ...] = ()  # a numbered baseline changing several parameters


@dataclass(frozen=True)
class Variation:
    """A parameter's card: its change (with its ties'), from the baseline or a numbered
    baseline."""

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
    parameter's card shown as a numbered baseline (`numbered`) keeps its start."""

    id: str
    heading: str
    changes: tuple[Change, ...]
    start: tuple[Change, ...] | None = None
    start_name: str = ""
    numbered: bool = False


@dataclass(frozen=True)
class Scene:
    """What the rule reads of the GraphSpec a catalog draws: its data, its values with the
    catalog's `always` (a layer catalog's layer, with its defaults), and the columns those
    name."""

    data: pd.DataFrame
    values: Mapping[str, Any]
    used: frozenset[str]


def gets_card(kind: str, p: Parameter) -> bool:
    """Whether a parameter of a spec of this kind gets a card."""
    return not p.path.startswith(EXEMPT.get(kind, ()))


def candidates(p: Parameter, d: Any, scene: Scene, layer: str = "") -> list[Any]:
    """The values the rule gives a parameter's card, in order (see the module's docstring),
    before they're checked against its range. d: its default, the value the spec shown gives
    it; layer: the layer type whose parameter it is."""
    rng = p.range
    if set(rng.literals) == {"true", "false"}:
        return [not d, d]
    out: list[Any] = []
    if {"column", "columns"} & set(rng.types):
        numbers = bool(layer) or p.path.startswith("axis.")
        frame = scene.data
        out += [
            c
            for c in frame.columns
            if c not in scene.used and (not numbers or pd.api.types.is_numeric_dtype(frame[c]))
        ]
    if "text" in rng.types and p.path.endswith("family"):  # a font
        out += [f for f in bundled_families() if f != d]
    if "text" in rng.types:
        out += FORMATS if p.path.endswith("format") else (SAMPLE_TEXT,)
    if "hex color" in rng.types:
        out.append(SAMPLE_COLOR)
    if rng.intervals or set(NUMBERS) & set(rng.types):
        whole = not rng.intervals and not {"float", "float ≥ 0", "float > 0"} & set(rng.types)
        if isinstance(d, int | float) and not isinstance(d, bool):
            out += _within(p, d, [1] if d == 0 else [2 * d, d // 2 if whole else d / 2])
        elif is_none(d):
            out += _from_data(p, scene, layer)
        elif p.path in SIZES:  # auto: from the other size
            out.append(scene.values.get(SIZES[p.path]))
    reverse = [list(reversed(d))] if isinstance(d, list) and len(d) > 1 else []
    return [*out, *_words(p, d), *reverse, NONE if d is None else d]


def _within(p: Parameter, d: float, values: list[float]) -> list[float]:
    """Each value, moved into the range's interval that holds d."""
    for i in p.range.intervals:
        if i.low <= d <= i.high:
            return [min(max(v, i.low), i.high) for v in values]
    return values


def _column(scene: Scene, axis: Any) -> pd.Series | None:
    """The numbers of an axis's column (its first, for several), if they are numbers."""
    name = scene.values.get(f"axis.{axis}.data.column")
    name = name[0] if isinstance(name, list) else name
    if name not in scene.data.columns or not pd.api.types.is_numeric_dtype(scene.data[name]):
        return None
    return cast(pd.Series, scene.data[name]).dropna()


def _from_data(p: Parameter, scene: Scene, layer: str) -> list[float]:
    """A number for a parameter defaulting to None, from its axis's column."""
    parts = p.path.split(".")
    if layer and p.path == "value":
        column = _column(scene, scene.values.get(f"layers.{layer}.axis"))
        return [] if column is None else [float(column.median())]
    column = _column(scene, parts[1]) if parts[0] == "axis" and not layer else None
    if column is None:
        return []
    if parts[2:] in (["min"], ["max"]):
        return [float(column.median())]
    if parts[2:] == ["tick", "step"]:
        return [float(f"{(column.max() - column.min()) / 4:.1g}")]
    return []


def _words(p: Parameter, d: Any) -> list[Any]:
    """The range's words after d (for a list, its first), in the range's order and wrapping
    round, without it; for a list, each as a one-item list."""
    words = list(p.range.literals)
    first = d[0] if isinstance(d, list) and d else d
    first = NONE if first is None else first
    i = words.index(first) if first in words else len(words) - 1
    after = [w for w in words[i + 1 :] + words[: i + 1] if w != first]
    return [[w] for w in after] if isinstance(d, list) else after


def tied(path: str, value: Any, prefix: str = "") -> tuple[Change, ...]:
    """A card's changes: its parameter's, and when that's None, None for each parameter TIES
    ties it to. prefix: a layer catalog's layers.<layer>."""
    own = Change(f"{prefix}{path}", value)
    if not is_none(value):
        return (own,)
    others = [q for tie in TIES if path in tie for q in tie if q != path]
    return (own, *(Change(f"{prefix}{q}", NONE) for q in others))


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


# differs(start, changes): whether start with changes draws, and differently from start
Differs = Callable[[tuple[Change, ...], tuple[Change, ...]], bool]


def card(
    catalog: Catalog, path: str, differs: Differs, fallback: Differs | None = None
) -> Variation:
    """A parameter's card: its first candidate that draws differently from a baseline, on the
    first such baseline (the GraphSpec, then the numbered baselines in order). One with none
    is placed by fallback if given (a pack's catalog: as ForgeGraph's places it), else it's a
    CatalogError. No other card changes where it's placed."""
    from forgegraph.catalog_build.files import CatalogError

    p, options = next((p, o) for p, o in catalog.cards if p.path == path)
    bases: list[Change | None] = [None, *catalog.baselines]
    for test in (differs,) if fallback is None else (differs, fallback):
        for changes in options:
            for base in bases:
                if test(() if base is None else (base,), changes):
                    return Variation(p, changes, base)
    raise CatalogError(
        [
            f"{catalog.kind.replace('_', ' ')} {catalog.name}: {path}: no candidate changes "
            "the drawing on any baseline; add a baseline that shows it"
        ]
    )


def placed(catalog: Catalog, differs: Differs, fallback: Differs | None = None) -> list[Variation]:
    """Each variable parameter's card (card()); every problem as one CatalogError."""
    from forgegraph.catalog_build.files import CatalogError

    out, problems = [], []
    for p, _ in catalog.cards:
        if p.path not in catalog.variable:
            continue
        try:
            out.append(card(catalog, p.path, differs, fallback))
        except CatalogError as e:
            problems += e.problems
    if problems:
        raise CatalogError(problems)
    return out


def place(catalog: Catalog, differs: Differs, fallback: Differs | None = None) -> list[Planned]:
    """The cards of a catalog's panel, in order: the baseline, then each variable parameter's
    card (placed()), each numbered baseline before the first card starting from it."""
    first = "Baseline"
    if catalog.always:  # a layer's catalog: say what every card adds to the GraphSpec
        first = " + ".join([f"Baseline: {catalog.baseline}", *(_change(c) for c in catalog.always)])
    cards = [Planned("baseline", first, ())]
    variations = placed(catalog, differs, fallback)
    numbers: dict[str, int] = {}  # each numbered baseline's number, by the change that makes it
    at: dict[str, int] = {}  # and its place in cards
    for v in variations:
        single = len(v.changes) == 1
        base = () if v.base is None else (v.base,)
        if single and _change(v.change) in numbers:  # already shown, as a numbered baseline
            i = at[_change(v.change)]
            cards[i] = replace(cards[i], start=base, numbered=True)
            continue
        if v.base is not None and _change(v.base) not in numbers:
            numbers[_change(v.base)] = len(numbers) + 2
            at[_change(v.base)] = len(cards)
            heading = f"Baseline {numbers[_change(v.base)]}: Baseline + {_change(v.base)}"
            cards.append(Planned(f"baseline-{_id(v.base)}", heading, (v.base,)))
        if single and v.base is None and any(w.base == v.change for w in variations):
            numbers[_change(v.change)] = len(numbers) + 2
            at[_change(v.change)] = len(cards)
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
    its changes: its image and its width in inches. A lenient one draws a card that can't be
    drawn as its problem, in place of its graph; otherwise that's a CatalogError. The
    baseline itself must draw."""

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
        self._drawn: dict[str, tuple[bytes | None, float, list[str]]] = {}

    def png(self, *changes: Change) -> bytes:
        """The card's image."""
        image_, _, problems = self._draw(changes)
        if image_ is not None:
            return image_
        if self.lenient and changes:
            problem = f"Can't be drawn in this theme and format: {problems[0]}"
            return _message_png(problem, self.width())
        from forgegraph.catalog_build.files import CatalogError

        catalog = self.catalog
        card = " + ".join(["Baseline", *(_change(c) for c in changes)])
        kind = catalog.kind.replace("_", " ")
        raise CatalogError([f"{kind} {catalog.name}: {card}: {p}" for p in problems])

    def width(self, *changes: Change) -> float:
        """The card's width, inches; for one that can't be drawn, the baseline's."""
        image_, width, _ = self._draw(changes)
        if image_ is None:
            self.png()  # the baseline itself must draw
            width = self._draw(())[1]
        return width

    def differs(self, start: tuple[Change, ...], changes: tuple[Change, ...]) -> bool:
        """Whether start with changes draws, and differently from start."""
        before = self._draw(start)[0]
        after = self._draw((*start, *changes))[0]
        return before is not None and after is not None and before != after

    def _draw(self, changes: tuple[Change, ...]) -> tuple[bytes | None, float, list[str]]:
        key = " + ".join(_change(c) for c in changes)
        if key not in self._drawn:
            try:
                graph = draw(
                    *self.catalog.always,
                    *changes,
                    spec=self.catalog.baseline,
                    theme=self.theme,
                    format=self.fmt,
                    reg=self.reg,
                )
            except SpecError as e:
                self._drawn[key] = None, 0.0, list(e.problems)
            else:
                self._drawn[key] = _png(graph), graph.figure.get_size_inches()[0], []
        return self._drawn[key]
