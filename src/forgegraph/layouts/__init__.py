"""Layouts: several GraphSpecs arranged on one figure per tab (architecture D11).

A layout file (spec/layout.py) names a format and a grid of GraphSpec files for each tab.
Each tile is drawn as its GraphSpec says, in its own theme, from its own data, into an Axes
of the tab's figure; the layout's format replaces each tile's own, so every tile is drawn at
the layout's base size, and the figure is the format's size. The tiles are then laid out
together (drawing/layout.py), so their plot boxes line up, with the layout's separators
between them (layouts/separators.py).

A rendered tab's figure checks itself as a graph's does (drawing/figure.py): drawing or saving
it first checks whether it's still as ForgeGraph left it, and watermarks every tile if not.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager, nullcontext
from dataclasses import dataclass, field, replace
from functools import partial
from pathlib import Path
from typing import Any, cast

import matplotlib
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from forgegraph.drawing import export, key, lint, page
from forgegraph.drawing import toggles as toggled
from forgegraph.drawing.errors import DrawError, LayoutError
from forgegraph.drawing.figure import GraphFigure, TileAxes, canvas_figure, inches, watermark
from forgegraph.drawing.layout import (
    Grid,
    Placed,
    Plot,
    Room,
    add_footnote,
    arrange,
    finish,
    footnote_room,
    place_footnote,
    rooms_of,
    widest,
)
from forgegraph.drawing.readout import marks
from forgegraph.drawing.style import LineStyle, Style, isolated
from forgegraph.drawing.toggles import Slice
from forgegraph.drawn import Inspected, Saved, SpecError
from forgegraph.fonts import WEIGHTS, font_file, font_weights
from forgegraph.graph import (
    Graph,
    OnPage,
    Prepared,
    key_boxes,
    keyed_owners,
    owned_items,
    page_controls,
    page_toggles,
    prepare,
    render,
)
from forgegraph.layouts.separators import (
    apply_separators,
    backgrounds,
    gap_color,
    line_style,
    text_member,
)
from forgegraph.spec.access import packs_used
from forgegraph.spec.explain import Explained
from forgegraph.spec.layout import Tab, drawing_problems, tabs, tabs_source
from forgegraph.spec.loaded import Loaded, load_document, placed
from forgegraph.spec.provenance import DataRecord, TileRecord, graph_fields, record
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import Resolved, Values, resolve
from forgegraph.spec.tags import to_json
from forgegraph.spec.toggles import Toggles
from forgegraph.spec.validate import named_problems, validate
from forgegraph.spec.views import Control

SUFFIX = ".layout.yaml"


@dataclass
class Tile:
    """A tile as drawn: its GraphSpec prepared (every value it was drawn with, and its data),
    the Axes it was drawn into, and what the graph type drew."""

    name: str
    file: str  # the GraphSpec file, as the layout names it
    prepared: Prepared = field(compare=False)  # what it was drawn from
    axes: Axes
    drawn: Any  # what the graph type drew

    @property
    def spec(self) -> dict[str, Any]:
        return self.prepared.doc

    @property
    def values(self) -> dict[str, dict[str, Any]]:
        """Every value it was drawn with, by kind."""
        return self.prepared.values

    @property
    def style(self) -> Style:
        return self.prepared.style

    @property
    def data(self) -> DataRecord:
        return self.prepared.record

    @property
    def specs(self) -> dict[str, Any]:
        """Each spec used, by kind: its name and version."""
        return self.prepared.specs

    @property
    def labelling(self) -> str:
        return self.drawn.labelling

    @property
    def style_keys(self) -> list[str]:
        """The column each of its style keys explains (see Graph.style_keys)."""
        return [k.column for k in self.drawn.style_keys]

    @property
    def drawing(self) -> list[lint.Issue]:
        """What lint found while drawing it."""
        return list(self.drawn.warnings)

    def record(self, full: bool, layout_format: dict[str, Any]) -> TileRecord:
        """Its provenance record; it was drawn in the layout's format, not its own."""
        return TileRecord(
            file=self.file,
            specs={**self.specs, "format": layout_format},
            **graph_fields(self.spec, self.values, self.data, full),
        )


@dataclass
class TabFigure(Inspected):
    """A layout's tab as drawn: one figure holding its tiles."""

    layout: Layout
    name: str  # its path, as messages and records write it: Platinum / Voltage
    slug: str  # its path in file names
    link: str  # its path in a page's links
    path: tuple[str, ...]  # the names of the tabs it's in, then its own
    figure: GraphFigure
    tiles: dict[str, Tile]
    grid: Grid
    issues: list[lint.Issue] = field(default_factory=list)
    changed: bool = False  # found changed since rendering (see inspect); never reset
    nonstandard_packs: list[str] = field(default_factory=list)  # used, not in the main config
    _snapshot: tuple[int, ...] = ()
    _drawn: str = ""
    _held: bool = False  # inspected already, during one save (see Graph.inspected_once)
    _font_problems: list[str] = field(default_factory=list)
    # The controls its tiles' choice layers share, by name, and every view by the names
    # chosen, one for each: this tab is the first; the others are drawn for the HTML page.
    controls: tuple[str, ...] = ()
    views: dict[tuple[str, ...], TabFigure] = field(default_factory=dict, repr=False)
    # Draws it again, with room in its tiles' keys for checkboxes (on_page)
    _redraw: Callable[[dict[str, frozenset[str]]], TabFigure] | None = field(
        default=None, repr=False
    )

    @property
    def style(self) -> Style:
        """The first tile's style: the figure's own matplotlib settings while drawing."""
        return next(iter(self.tiles.values())).style

    def saving(self) -> AbstractContextManager[None]:
        return _saving(self.style, self.style)

    def _shown(self) -> tuple[Figure, Style]:
        return self.figure, self.style

    def mark(self) -> None:
        """Watermark every tile, once: the figure has been found changed."""
        for tile in self.tiles.values():
            watermark(tile.axes, tile.style)

    def check(self) -> list[lint.Issue]:
        """Lint the tab's figure as it is now, and return the issues (also kept in `issues`).
        Issues of one plot name its tile."""
        self._lint_draw()
        with isolated(self.style):
            issues = lint.figure_issues(self.figure, self._font_problems)
        for tile in self.tiles.values():
            found = tile.prepared.plot_issues(tile.axes, tile.drawing)
            issues += [lint.Issue(i.check, f"tile '{tile.name}': {i.message}") for i in found]
        self.issues = issues
        if self.views:
            self.issues = self.with_views([t.check() for t in self.others()])
        return self.issues

    def others(self) -> list[TabFigure]:
        return [t for t in self.views.values() if t is not self]

    def with_views(self, others: list[list[lint.Issue]]) -> list[lint.Issue]:
        """Its own issues, then each other view's, each naming its view."""
        out = []
        for names, issues in zip(self.views, [self.issues, *others], strict=True):
            label = " / ".join(names)
            out += [lint.Issue(i.check, f"view '{label}': {i.message}") for i in issues]
        return out

    def owned(self) -> dict[Any, dict[str, str]]:
        """For each tile with a toggle layer, its Axes' toggled owners' items."""
        out: dict[Any, dict[str, str]] = {}
        for tile in self.tiles.values():
            out.update(owned_items(tile.axes, tile.prepared.toggles))
        return out

    def on_page(self, dpi: int, framed: float | None) -> OnPage:
        """The tab as a page shows it: its SVG, its data points and, with toggle layers, its
        images to stack and the checkboxes in its keys. A key naming a tile's toggled series
        needs room for their checkboxes, so the page's figure is then drawn again, with that
        room (graph.Graph._on_page). framed: the border's width, to crop each image to it."""
        shown = self
        boxed = {n: keyed_owners(t.axes, t.prepared.toggles) for n, t in self.tiles.items()}
        if any(boxed.values()) and self._redraw is not None:
            with lint.font_messages():
                shown = self._redraw(boxed)

        def crop(svg: bytes) -> bytes:
            return svg if framed is None else _framed(shown, svg, framed)

        owned = shown.owned()
        with shown.inspected_once() if shown is not self else nullcontext():  # self's is held
            cut = toggled.slices(shown.figure, toggled.member_of(owned), dpi) if owned else []
            svg = crop(export.svg(shown.figure, dpi))
        return (
            svg,
            tuple(marks(shown.figure, owned)),
            tuple(Slice(c.items, crop(c.svg)) for c in cut),
            key_boxes(shown.figure, owned),
        )

    def viewed(self, dpi: int, framed: float | None) -> page.Shown:
        """The tab on a page: its images, and every view's if it has views. framed: the
        border's width, to crop each image to it."""
        svg, found, cut, boxes = self.on_page(dpi, framed)
        shown = page.Shown(self.name, self.link, svg, self.path, found, slices=cut, boxes=boxes)
        if not self.views:
            return shown
        viewed = []
        for names, t in self.views.items():
            if t is self:
                here = (svg, found, cut, boxes)
            else:
                with t.inspected_once():
                    here = t.on_page(dpi, framed)
            choices = tuple(zip(self.controls, names, strict=True))
            viewed.append(page.Viewed(choices, *here))
        return replace(shown, views=tuple(viewed))

    def record(self) -> dict[str, Any] | None:
        """The provenance record of files showing this tab."""
        return self.layout.record([self])


@dataclass
class Layout(Saved):
    """A drawn layout: its tabs, the layout file and the layout's own values."""

    spec: dict[str, Any]
    values: dict[str, Any]
    resolved: Values
    format: dict[str, Any]
    tabs: list[TabFigure] = field(default_factory=list)
    specs: dict[str, Any] = field(default_factory=dict)  # the layout and its format: name, version
    freshness: page.Freshness | None = None  # a scheduled run's, for its HTML page
    nonstandard_packs: list[str] = field(default_factory=list)  # used, not in the main config
    _own_packs: list[str] = field(default_factory=list)  # the layout's own and its format's
    controls: list[Control] = field(default_factory=list)  # its tiles' choice layers', by name
    toggles: list[tuple[Toggles, Style]] = field(default_factory=list)  # its tiles', each
    # with its tile's style
    _styles: dict[str, Style] = field(default_factory=dict)  # each control's first tile's

    @property
    def issues(self) -> list[lint.Issue]:
        """Every tab's lint issues; with several tabs, each names its tab."""
        if len(self.tabs) == 1:
            return list(self.tabs[0].issues)
        return [
            lint.Issue(i.check, f"tab '{t.name}': {i.message}") for t in self.tabs for i in t.issues
        ]

    @property
    def warnings(self) -> list[str]:
        return [i.message for i in self.issues]

    @property
    def data_records(self) -> list[DataRecord]:
        """What each tile read and drew, tab by tab."""
        return [tile.data for t in self.tabs for tile in t.tiles.values()]

    @property
    def labelling_by_name(self) -> dict[str, str]:
        """How each tile's series are named (see Graph.labelling), by "<tab>.<tile>"."""
        return {f"{t.name}.{n}": tile.labelling for t in self.tabs for n, tile in t.tiles.items()}

    @property
    def style_keys_by_name(self) -> dict[str, list[str]]:
        """Each tile's style keys' columns (see Graph.style_keys), by "<tab>.<tile>"."""
        return {f"{t.name}.{n}": tile.style_keys for t in self.tabs for n, tile in t.tiles.items()}

    def check(self) -> list[lint.Issue]:
        for t in self.tabs:
            t.check()
        return self.issues

    @property
    def nonstandard(self) -> bool:
        return any(t.inspect() for t in self.tabs)

    def record(self, shown: list[TabFigure] | None = None) -> dict[str, Any] | None:
        """The provenance record of files showing these tabs (all by default), at the format's
        provenance.level; None with off."""
        shown = self.tabs if shown is None else shown
        level = self.format["provenance.level"]
        nonstandard = any(t.inspect() for t in shown)
        packs = sorted({p for t in shown for p in t.nonstandard_packs})
        if level == "off":
            return None
        full = level == "full"
        fmt = self.specs["format"]
        return record(
            level,
            specs=self.specs,
            nonstandard=nonstandard,
            nonstandard_packs=packs or None,
            layout=to_json(self.spec),
            tabs={
                t.name: {n: tile.record(full, fmt) for n, tile in t.tiles.items()} for t in shown
            },
        )

    def save_all(self, stem: str | Path) -> list[Path]:
        """Save every file type the format lists. html: one page with every tab; pdf: one file,
        a page per tab; other types: a file per tab, stem-<tab>.png, or stem.png for one tab."""
        return self._write(Path(stem), list(self.format["output.file_types"]))

    def _write(self, stem: Path, kinds: list[str]) -> list[Path]:
        dpi = int(self.format["output.dpi"])
        one = len(self.tabs) == 1
        out = []
        with ExitStack() as held:
            for t in self.tabs:
                held.enter_context(t.inspected_once())
            for kind in kinds:
                out += self._write_one(stem, kind, dpi, one)
        return out

    def _write_one(self, stem: Path, kind: str, dpi: int, one: bool) -> list[Path]:
        """The files of one file type (see save_all)."""
        out = []
        path = stem.with_name(f"{stem.name}.{kind}")
        if kind == "html":
            first = self.tabs[0].style
            base = float(self.format["figure.base_size"])
            look = line_style(self.values, first, base)
            border = look.width if look.visible else 0.0
            framed = not one and look.visible and bool(self.values["separators.border.show"])
            bar = line_style(self.values, first, base, "tab_bar.line")
            with self.tabs[0].saving():
                shown = []
                for t in self.tabs:
                    viewed = t.viewed(dpi, border if framed else None)
                    if one:
                        viewed = replace(viewed, name=None, slug=None, path=())
                    shown.append(viewed)
            color = gap_color(first)
            out.append(
                page.write(
                    path,
                    str(self.spec.get("name", stem.name)),
                    shown,
                    self.record(),
                    "transparent" if color == "none" else color,
                    _tab_bar(self.values, first, base, bar) if not one else None,
                    framed,
                    self.freshness,
                    tuple(page_controls([c], self._styles[c.name])[0] for c in self.controls),
                    page_toggles(list(self.toggles), shown),
                )
            )
        elif kind == "pdf":  # in its settings: a PDF embeds its fonts as it closes
            with self.tabs[0].saving():
                figures = [t.figure for t in self.tabs]
                out.append(export.save_pages(figures, path, dpi, self.record()))
        else:
            for t in self.tabs:
                target = path if one else stem.with_name(f"{stem.name}-{t.slug}.{kind}")
                with t.saving():
                    out.append(export.save(t.figure, target, dpi))
        return out

    def _name(self) -> str:
        return str(self.spec.get("name", "layout"))

    def _shown(self) -> tuple[Figure, Style]:
        return self.tabs[0].figure, self.tabs[0].style


def _tab_bar(values: dict[str, Any], first: Style, base: float, line: LineStyle) -> page.TabBar:
    """The page's tab bar: tab_bar.label and tab_bar.line, each member the layout doesn't set
    its first tile's theme's general text or line."""

    def member(name: str) -> Any:
        return text_member(values, first, "tab_bar.label", name)

    family, weight = str(member("font")), WEIGHTS[str(member("weight"))]
    if weight not in font_weights(family):  # one of them the first tile's theme's
        has = ", ".join(n for n, w in WEIGHTS.items() if w in font_weights(family))
        raise SpecError(
            [f"tab_bar.label.weight: {family} has no {member('weight')} weight; it has {has}"]
        )
    return page.TabBar(
        family,
        float(member("size")) * base,
        weight,
        str(member("color")),
        float(member("gap")) * base,
        str(member("alignment")),
        font_file(family, weight),
        line.style if line.visible else "none",
        line.width if line.visible else 0.0,
        line.color,
    )


def _framed(tab: TabFigure, svg: bytes, border: float) -> bytes:
    """A tab's SVG cut down to its border, without the border's top side: on a page, the
    line under the tab bar is the border's top."""
    width, height = page.size(svg)
    out = tab.grid.edge / 2 * 72  # the border's centre, in points from each edge
    half = border / 2
    return page.crop(svg, out - half, out + half, width - out + half, height - out + half)


@contextmanager
def _saving(style: Style, first: Style) -> Iterator[None]:
    """A tile's settings, with the gaps' color (the first tile's theme background) behind
    everything."""
    with isolated(style):
        background = gap_color(first)
        matplotlib.rcParams["savefig.facecolor"] = background
        matplotlib.rcParams["savefig.transparent"] = background == "none"
        yield


def stem(path: Path) -> str:
    """A GraphSpec or layout file's name, without .layout.yaml or .yaml: what its files are
    saved as."""
    name = path.name
    return name[: -len(SUFFIX)] if name.endswith(SUFFIX) else path.stem


def is_layout(path: Path) -> bool:
    return path.name.endswith(SUFFIX)


def draw_file(path: Path, footnote: str | None = None) -> Graph | Layout:
    """Draw a GraphSpec file, or a layout file (.layout.yaml), with an optional footnote."""
    if is_layout(path):
        return render_layout(path, footnote=footnote)
    return render(path, footnote=footnote)


def _format_values(doc: dict[str, Any], reg: Registry, own: Values) -> Values:
    """The layout's format's values, each saying it came through the layout, with the format's
    variable parameters that the layout sets replaced by the layout's values."""
    name = own["specifications.format"].value
    origin = f"layout '{doc['name']}'"
    values = Values(
        {
            p: Resolved(r.value, r.fixed, f"{r.origin}, from {origin}")
            for p, r in resolve("format", reg.docs["format"][name], reg).items()
        }
    )
    values.update({p: r for p, r in own.items() if p in values})
    return values


def _check(doc: Any, reg: Registry) -> None:
    problems = validate("layout", doc, reg)
    if problems:
        raise SpecError(problems)
    problems = named_problems("layout", doc, reg) + drawing_problems(doc, reg)
    if problems:
        raise SpecError(problems)


def tile_files(layout: Loaded) -> tuple[dict[str, dict[str, Path]], list[str]]:
    """Each tab's tiles' GraphSpec files, {tab: {tile: path}}, in reading order, and what's
    wrong with them. A tab is keyed by where it is under tabs: Voltage, or
    Platinum.tabs.Voltage. They're found from the folder of the file listing the layout's tabs."""
    folder = layout.folder_for(tabs_source(layout.doc, layout.reg))
    out: dict[str, dict[str, Path]] = {}
    problems = []
    for tab in tabs(layout.doc, layout.reg):
        key = _key(tab)
        out[key] = {}
        for name in tab.places():
            file = str(tab.tiles[name])
            where = f"{tab.where}.tiles.{name}"
            target = placed(file, folder)
            if is_layout(target):
                problems.append(f"{where}: '{file}' is a layout; a tile is a GraphSpec file")
            elif not target.is_file():
                problems.append(f"{where}: no GraphSpec file at '{target}'")
            else:
                out[key][name] = target
    return out, problems


def tile_documents(layout: Loaded) -> dict[str, dict[str, Loaded]]:
    """Each tile's GraphSpec as the layout's render reads it, {tab: {tile: document}}, in
    reading order, checked against the layout's registry: a layout's tiles use the packs its
    configs allow. A tile whose file isn't found is left out (see tile_files)."""
    files, _ = tile_files(layout)
    return {
        tab: {name: load_document("graphspec", path, layout.reg) for name, path in tiles.items()}
        for tab, tiles in files.items()
    }


def explain_layout(
    spec: dict[str, Any] | str | Path, registry: Registry | None = None
) -> tuple[Values, dict[tuple[str, str], Explained]]:
    """Every value a layout is drawn with, without drawing it: its own values, and each
    tile's, by (tab, tile), in reading order (see spec.explain). Each tile's format values
    are the layout's format's."""
    layout = load_document("layout", spec, registry)
    _check(layout.doc, layout.reg)
    own = layout.resolve()
    fmt = _format_values(layout.doc, layout.reg, own)
    files, problems = tile_files(layout)
    out: dict[tuple[str, str], Explained] = {}
    for tab, tiles in tile_documents(layout).items():
        for name, tile in tiles.items():
            found = validate("graphspec", tile.doc, tile.reg)
            if found:
                where = f"tabs.{tab}.tiles.{name} ({files[tab][name].name})"
                problems += [f"{where}: {p}" for p in found]
                continue
            out[tab, name] = tile.explain(fmt)
    if problems:
        raise SpecError(problems)
    return own, out


def nonstandard_packs_of(
    spec: dict[str, Any] | str | Path, registry: Registry | None = None
) -> list[str]:
    """The packs a layout is drawn with, its own specs' and its tiles', that the main config
    doesn't list, without drawing it."""
    layout = load_document("layout", spec, registry)
    used = packs_used("layout", layout.doc, layout.reg)
    for tiles in tile_documents(layout).values():
        for tile in tiles.values():
            if isinstance(tile.doc, dict):
                used |= packs_used("graphspec", tile.doc, tile.reg)
    return sorted(used & layout.reg.nonstandard)


def render_layout(
    spec: dict[str, Any] | str | Path,
    data: dict[str, pd.DataFrame] | None = None,
    registry: Registry | None = None,
    footnote: str | None = None,
) -> Layout:
    """Draw a layout, given as a file path or a document. `data` gives DataFrames by tile
    name, for tiles drawn from a DataFrame rather than their GraphSpec's data.file. A
    footnote is written small at the bottom right of each tab, below every tile."""
    loaded = load_document("layout", spec, registry)
    doc, reg = loaded.doc, loaded.reg
    _check(doc, reg)
    own = loaded.resolve()
    values = own.plain()
    fmt = _format_values(doc, reg, own)
    data = dict(data or {})
    listed = tabs(doc, reg)
    names = {t for tab in listed for t in tab.tiles}
    unknown = sorted(set(data) - names)
    if unknown:
        raise SpecError(
            [f"data: no tile '{n}'; tiles are {', '.join(sorted(names))}" for n in unknown]
        )
    files, problems = tile_files(loaded)
    if problems:
        raise SpecError(problems)
    layout = Layout(doc, values, own, fmt.plain())
    layout.specs = {
        "layout": {"name": doc["name"], "version": doc["version"]},
        "format": reg.spec_record("format", values["specifications.format"]),
    }
    layout._own_packs = sorted(packs_used("layout", doc, reg) & reg.nonstandard)
    prepared: dict[str, dict[str, Prepared]] = {}
    for tab in listed:
        prepared[_key(tab)] = {}
        for name, path in files[_key(tab)].items():
            try:
                prepared[_key(tab)][name] = prepare(path, data.get(name), reg, format=fmt)
            except SpecError as e:
                problems += [f"{_where(tab, name)}: {p}" for p in e.problems]
    if problems:
        raise SpecError(problems)
    shared = _shared(listed, prepared)
    layout.controls = [c for c, _ in shared]
    layout._styles = {c.name: style for c, style in shared}
    layout.toggles = _shared_toggles(listed, prepared)
    for tab in listed:
        drawing = (files[_key(tab)], data, reg, fmt)
        layout.tabs.append(_draw_views(layout, tab, prepared[_key(tab)], drawing, footnote))
    layout.nonstandard_packs = sorted({p for t in layout.tabs for p in t.nonstandard_packs})
    return layout


def _shared(
    listed: list[Tab], prepared: dict[str, dict[str, Prepared]]
) -> list[tuple[Control, Style]]:
    """The page's controls, each with its first tile's style: the tiles' choice layers, one
    for each name. Those of the same name must have the same views, in the same order, and
    the same position."""
    found: dict[str, tuple[Control, str, Style]] = {}
    problems = []
    for tab in listed:
        for name, p in prepared[_key(tab)].items():
            for c in p.controls:
                if c.name not in found:
                    found[c.name] = (c, _where(tab, name), p.style)
                    continue
                first, where, _ = found[c.name]
                if c.position != first.position:
                    problems.append(
                        f"{_where(tab, name)}: layers.{c.name}.position: {c.position}, and "
                        f"{first.position} in {where}; choice layers of the same name share "
                        "one control, so they need the same position"
                    )
                if c.names != first.names:
                    problems.append(
                        f"{_where(tab, name)}: layers.{c.name}: its views ({', '.join(c.names)}) "
                        f"aren't those of the choice layer of that name in {where} "
                        f"({', '.join(first.names)}); choice layers of the same name share one "
                        "control, so their views need the same names in the same order"
                    )
    if problems:
        raise SpecError(problems)
    return [(c, style) for c, _, style in found.values()]


def _shared_toggles(
    listed: list[Tab], prepared: dict[str, dict[str, Prepared]]
) -> list[tuple[Toggles, Style]]:
    """The page's toggles: the tiles' toggle layers, each with its tile's style, sharing one
    checkbox for each item's name and one list. Items of the same name must be hidden at
    first in every tile, or in none, and the layers must have the same position."""
    found: dict[str, tuple[bool, str]] = {}
    layers: list[tuple[Toggles, Style]] = []
    problems = []
    first: tuple[str, str] | None = None  # the first layer's position, and where it is
    for tab in listed:
        for name, p in prepared[_key(tab)].items():
            t = p.toggles
            if t is not None:
                layers.append((t, p.style))
                if first is None:
                    first = (t.position, _where(tab, name))
                elif t.position != first[0]:
                    problems.append(
                        f"{_where(tab, name)}: layers.{t.name}.position: {t.position}, and "
                        f"{first[0]} in {first[1]}; toggle layers share one list of checkboxes, "
                        "so they need the same position"
                    )
            for item in t.names if t is not None else ():
                hidden = t is not None and item in t.hidden
                if item not in found:
                    found[item] = (hidden, _where(tab, name))
                elif found[item][0] != hidden:
                    problems.append(
                        f"{_where(tab, name)}: layers.{cast(Any, t).name}: '{item}' is "
                        f"{'hidden' if hidden else 'shown'} at first, and not in "
                        f"{found[item][1]}; items of the same name share one checkbox, so they "
                        "start hidden in every tile or in none"
                    )
    if problems:
        raise SpecError(problems)
    return layers


def _draw_views(
    layout: Layout,
    tab: Tab,
    prepared: dict[str, Prepared],
    drawing: tuple[dict[str, Path], dict[str, pd.DataFrame], Registry, Values],
    footnote: str | None,
) -> TabFigure:
    """Draw a tab; with choice layers in its tiles, every combination of the views they use,
    each tile drawn with its own changes for the views chosen (spec/views.py). drawing: the
    tiles' files, their DataFrames, and the registry and format they're drawn with."""
    files, data, reg, fmt = drawing
    used = [c for c in layout.controls if any(c.name in _names(p) for p in prepared.values())]
    if not used:
        return _draw_tab(layout, tab, prepared, footnote)
    viewed: dict[tuple[str, ...], dict[str, Prepared]] = {}
    for picked in itertools.product(*(c.names for c in used)):
        chosen = dict(zip((c.name for c in used), picked, strict=True))
        tiles = {}
        for name, p in prepared.items():
            if not p.controls:
                tiles[name] = p
                continue
            change: dict[str, Any] = {}
            for c in p.controls:
                change.update(dict(c.views)[chosen[c.name]])
            try:
                tiles[name] = prepare(files[name], data.get(name), reg, format=fmt, view=change)
            except SpecError as e:
                raise SpecError([f"{_where(tab, name)}: {m}" for m in e.problems]) from None
        viewed[picked] = tiles

    def draw(floor: dict[str, Room] | None) -> dict[tuple[str, ...], TabFigure]:
        out = {}
        for picked, tiles in viewed.items():
            try:
                out[picked] = _draw_tab(layout, tab, tiles, footnote, floor)
            except SpecError as e:
                label = " / ".join(picked)
                raise SpecError([f"view '{label}': {m}" for m in e.problems]) from None
        return out

    # As a graph's views do (graph.render): drawn again, each tile in every view takes the
    # most room it needed in any, so the tiles stay put as the views switch.
    drawn = draw(None)
    floor = widest(
        [
            rooms_of(t.figure, {n: (tile.axes, tile.style) for n, tile in t.tiles.items()})
            for t in drawn.values()
        ]
    )
    drawn = draw(floor)
    first = next(iter(drawn.values()))
    first.controls, first.views = tuple(c.name for c in used), drawn
    first.issues = first.with_views([t.issues for t in first.others()])
    return first


def _names(p: Prepared) -> set[str]:
    return {c.name for c in p.controls}


def _draw_tab(
    layout: Layout,
    tab: Tab,
    prepared: dict[str, Prepared],
    footnote: str | None = None,
    floor: dict[str, Room] | None = None,
    boxed: dict[str, frozenset[str]] | None = None,
) -> TabFigure:
    fmt = layout.format
    width, height = inches(fmt["figure.width"]), inches(fmt["figure.height"])
    first = next(iter(prepared.values()))
    places = tab.places()
    with isolated(first.style), lint.font_messages() as font_problems:
        fig = canvas_figure(width or 6.0, height or 4.0)
        placed, drawn = [], {}
        for name, p in prepared.items():
            with isolated(p.style):
                ax = cast(TileAxes, fig.add_axes((0.1, 0.1, 0.8, 0.8), axes_class=TileAxes))
                ax.tile_style = p.style
                try:
                    drawn[name] = p.draw(ax)
                except SpecError as e:
                    raise SpecError([f"{_where(tab, name)}: {m}" for m in e.problems]) from None
            placed.append(Placed(name, places[name], ax, p.style))
        base = float(fmt["figure.base_size"])
        gap = float(layout.values["separators.gap.outer"]) * base / 72  # between tiles
        edge = float(layout.values["separators.gap.inner"]) * base / 72  # at the figure's edges
        if footnote:
            add_footnote(fig, footnote, first.style)
        foot = footnote_room(fig)
        sizes = (gap, width, height, tab.column_widths, tab.row_heights, edge, foot)
        plots = [
            Plot(
                p.ax,
                prepared[p.name].module,
                drawn[p.name],
                prepared[p.name].values["graph_type"],
                p.style,
                partial(_tile_call, tab, p, (boxed or {}).get(p.name, frozenset())),
            )
            for p in placed
        ]
        try:
            grid = finish(plots, lambda: arrange(fig, tab.areas, placed, *sizes, floor=floor))
        except LayoutError as e:
            raise SpecError([f"{tab.where}: {e}"]) from None
        backgrounds(fig, grid, placed, float(layout.values["separators.corner_radius"]) * base)
        place_footnote(fig, edge, edge)
        apply_separators(fig, grid, layout.values, base, first.style)
    tiles = {}
    for p in placed:
        prepared[p.name].finish(drawn[p.name])
        tiles[p.name] = Tile(p.name, str(tab.tiles[p.name]), prepared[p.name], p.ax, drawn[p.name])
    result = TabFigure(layout, tab.name, tab.slug, tab.link, tab.path, fig, tiles, grid)
    result._redraw = partial(_draw_tab, layout, tab, prepared, footnote, floor)
    for tile in tiles.values():  # files show the page's opening state
        t = tile.prepared.toggles
        if t is not None and t.hidden:
            owned = owned_items(tile.axes, t)
            toggled.hide(fig, toggled.member_of(owned), t.hidden)
    used = {p for prep in prepared.values() for p in prep.nonstandard_packs}
    result.seal(fig, font_problems, sorted({*layout._own_packs, *used}))
    return result


def _where(tab: Tab, name: str) -> str:
    """Where a tile's problem is: its place in the layout, and its GraphSpec file."""
    return f"{tab.where}.tiles.{name} ({tab.tiles[name]})"


def _key(tab: Tab) -> str:
    """A tab's key in tile_files and explain_layout: where it is under tabs."""
    return tab.where.removeprefix("tabs.")


def _tile_call(tab: Tab, tile: Placed, boxed: frozenset[str], function: Any, *args: Any) -> Any:
    """Call a graph type's function on a tile, in the tile's settings, naming the tile in any
    error; its keys leave room for checkboxes for boxed (drawing/key.py)."""
    with isolated(tile.style), key.boxed(boxed):
        try:
            return function(*args)
        except DrawError as e:
            raise SpecError([f"{_where(tab, tile.name)}: {e}"]) from None
