"""Layouts: several GraphSpecs arranged on one figure per tab (architecture D11).

A layout file (spec/layout.py) names a format and a grid of GraphSpec files for each tab.
Each tile is drawn as its GraphSpec says, in its own theme, from its own data, into an Axes
of the tab's figure; the layout's format replaces each tile's own, so every tile is drawn at
the layout's base size, and the figure is the format's size. The tiles are then laid out
together (layout/arrange.py), so their plot boxes line up, with the layout's separators
between them.

A rendered tab's figure checks itself as a graph's does (render/figure.py): drawing or saving
it first checks whether it's still as ForgeGraph left it, and watermarks every tile if not.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import matplotlib
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import RendererAgg

from forgegraph import __version__
from forgegraph.graph import (
    NONE,
    PLACE_PASSES,
    Prepared,
    SpecError,
    _artists,
    _created,
    _plain,
    prepare,
    recorded,
    spec_record,
)
from forgegraph.layout.arrange import Grid, Placed, apply_separators, arrange, backgrounds
from forgegraph.render import export, lint, page
from forgegraph.render.figure import (
    MARGIN_IN,
    GraphCanvas,
    GraphFigure,
    LayoutError,
    TileAxes,
    Watermark,
    _inches,
    _watermarked,
    add_footnote,
    footnote_room,
    place_footnote,
)
from forgegraph.render.key import keys
from forgegraph.render.style import Style, isolated, unset
from forgegraph.spec.documents import (
    Registry,
    Resolved,
    explain,
    packs_used,
    registry_for,
    resolve_detailed,
    validate,
)
from forgegraph.spec.documents import load as load_yaml
from forgegraph.spec.layout import Tab, drawing_problems, tabs, tabs_source
from forgegraph.spec.provenance import DataRecord, ProvenanceRecord, TileRecord

SUFFIX = ".layout.yaml"


@dataclass
class Tile:
    """A tile as drawn: its GraphSpec, every value it was drawn with, and its data."""

    name: str
    file: str  # the GraphSpec file, as the layout names it
    spec: dict[str, Any]
    axes: Axes
    values: dict[str, dict[str, Any]]
    resolved: dict[str, dict[str, Resolved]]
    style: Style
    data: DataRecord
    labelling: str
    drawing: list[lint.Issue] = field(default_factory=list)
    specs: dict[str, Any] = field(default_factory=dict)  # each spec used: name and version

    def record(self, full: bool, layout_format: dict[str, Any]) -> TileRecord:
        """Its provenance record; it was drawn in the layout's format, not its own."""
        return TileRecord(
            file=self.file,
            graphspec=recorded(self.spec, full),
            specs={**self.specs, "format": layout_format},
            resolved=_plain(self.values) if full else None,
            data=self.data.file if full else None,
            preprocessing=self.data.preprocessing if full else None,
        )


@dataclass
class TabFigure:
    """A layout's tab as drawn: one figure holding its tiles."""

    layout: Layout
    name: str
    slug: str
    figure: GraphFigure
    tiles: dict[str, Tile]
    grid: Grid
    issues: list[lint.Issue] = field(default_factory=list)
    changed: bool = False  # found changed since rendering (see inspect); never reset
    nonstandard_packs: list[str] = field(default_factory=list)  # used, not in the main config
    _snapshot: tuple[int, ...] = ()
    _drawn: str = ""
    _font_problems: list[str] = field(default_factory=list)

    @property
    def style(self) -> Style:
        """The first tile's style: the figure's own matplotlib settings while drawing."""
        return next(iter(self.tiles.values())).style

    def saving(self) -> AbstractContextManager[None]:
        return _saving(self.style, self.layout.values)

    def mark(self) -> None:
        """Watermark every tile, once: the figure has been found changed."""
        for tile in self.tiles.values():
            if not _watermarked(tile.axes):
                tile.axes.add_artist(Watermark(tile.axes, tile.style))

    @property
    def nonstandard(self) -> bool:
        return self.inspect()

    def inspect(self) -> bool:
        """Check whether the figure is still as ForgeGraph drew it (see Graph.inspect)."""
        if not self.changed:
            self.changed = _artists(self.figure) != self._snapshot or self._pixels() != self._drawn
        return self.changed

    def _pixels(self) -> str:
        renderer = RendererAgg(*self.figure.bbox.size, self.figure.dpi)
        with isolated(self.style), lint.font_messages():
            self.figure.draw(renderer)
        return hashlib.sha256(bytes(renderer.buffer_rgba())).hexdigest()

    def check(self) -> list[lint.Issue]:
        """Lint the tab's figure as it is now, and return the issues (also kept in `issues`).
        Issues of one plot name its tile."""
        with isolated(self.style), lint.font_messages() as font_problems:
            self.figure.canvas.draw()  # type: ignore[union-attr]
        self._font_problems = sorted({*self._font_problems, *font_problems})
        with isolated(self.style):
            issues = lint.figure_issues(self.figure, self._font_problems)
        for tile in self.tiles.values():
            gt = tile.values["graph_type"]
            with isolated(tile.style):
                found = lint.plot_issues(
                    tile.axes,
                    fixed_limits={
                        a: (_limit(gt.get(f"axis.{a}.min")), _limit(gt.get(f"axis.{a}.max")))
                        for a in ("x", "y")
                    },
                    rows_dropped=tile.data.rows_dropped,
                    drawing=tile.drawing,
                )
            issues += [lint.Issue(i.check, f"tile '{tile.name}': {i.message}") for i in found]
        self.issues = issues
        return issues

    def record(self) -> dict[str, Any] | None:
        """The provenance record of files showing this tab."""
        return self.layout.record([self])


@dataclass
class Layout:
    """A drawn layout: its tabs, the layout file and the layout's own values."""

    spec: dict[str, Any]
    values: dict[str, Any]
    resolved: dict[str, Resolved]
    format: dict[str, Any]
    tabs: list[TabFigure] = field(default_factory=list)
    specs: dict[str, Any] = field(default_factory=dict)  # the layout and its format: name, version
    freshness: page.Freshness | None = None  # a scheduled run's, for its HTML page
    nonstandard_packs: list[str] = field(default_factory=list)  # used, not in the main config
    _own_packs: list[str] = field(default_factory=list)  # the layout's own and its format's

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

    def check(self) -> list[lint.Issue]:
        for t in self.tabs:
            t.check()
        return self.issues

    @property
    def nonstandard(self) -> bool:
        return any(t.inspect() for t in self.tabs)

    def tab(self, name: str) -> TabFigure:
        for t in self.tabs:
            if t.name == name:
                return t
        raise KeyError(f"no tab '{name}'; tabs are {', '.join(t.name for t in self.tabs)}")

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
        record = ProvenanceRecord(
            provenance_level=level,
            forgegraph_version=__version__,
            created=_created(),
            specs=self.specs,
            nonstandard=nonstandard,
            nonstandard_packs=packs or None,
            layout=self.spec,
            tabs={
                t.name: {n: tile.record(full, fmt) for n, tile in t.tiles.items()} for t in shown
            },
        )
        return record.model_dump(exclude_none=True)

    def save(self, path: str | Path | None = None) -> list[Path]:
        """Save the layout. A path with a suffix saves that one file type; a path without one
        (or none: the layout's name, here) saves every file type the format lists."""
        if path is None:
            return self.save_all(Path(str(self.spec.get("name", "layout"))))
        target = Path(path)
        if not target.suffix:
            return self.save_all(target)
        return self._write(target.with_suffix(""), [target.suffix.lstrip(".")])

    def save_all(self, stem: str | Path) -> list[Path]:
        """Save every file type the format lists. html: one page with every tab; pdf: one file,
        a page per tab; other types: a file per tab, stem-<tab>.png, or stem.png for one tab."""
        return self._write(Path(stem), list(self.format["output.file_types"]))

    def _write(self, stem: Path, kinds: list[str]) -> list[Path]:
        dpi = int(self.format["output.dpi"])
        one = len(self.tabs) == 1
        out = []
        for kind in kinds:
            path = stem.with_name(f"{stem.name}.{kind}")
            if kind == "html":
                rule = float(self.values["separators.line.width"]) * float(
                    self.format["figure.base_size"]
                )
                framed = not one and bool(self.values["separators.line.border"])
                with self.tabs[0].saving():
                    shown = [
                        page.Shown(
                            None if one else t.name,
                            None if one else t.slug,
                            _framed(t, export.svg(t.figure, dpi), rule)
                            if framed
                            else export.svg(t.figure, dpi),
                        )
                        for t in self.tabs
                    ]
                color = self.values["separators.color"]
                out.append(
                    page.write(
                        path,
                        str(self.spec.get("name", stem.name)),
                        shown,
                        self.record(),
                        "transparent" if unset(color) else str(color),
                        str(self.values["separators.line.color"]),
                        rule,
                        framed,
                        self.freshness,
                    )
                )
            elif kind == "pdf":
                with self.tabs[0].saving():
                    figures = [t.figure for t in self.tabs]
                    out.append(export.save_pages(figures, path, dpi, self.record()))
            else:
                for t in self.tabs:
                    target = path if one else stem.with_name(f"{stem.name}-{t.slug}.{kind}")
                    with t.saving():
                        out.append(export.save(t.figure, target, dpi))
        return out

    def _repr_png_(self) -> bytes:
        import io

        buffer = io.BytesIO()
        with self.tabs[0].saving():
            self.tabs[0].figure.savefig(buffer, format="png", dpi=100)
        return buffer.getvalue()


def _framed(tab: TabFigure, svg: bytes, rule: float) -> bytes:
    """A tab's SVG cut down to its border, without the border's top side: on a page, the
    line under the tab bar is the border's top."""
    width, height = page.size(svg)
    out = tab.grid.edge / 2 * 72  # the border's centre, in points from each edge
    half = rule / 2
    return page.crop(svg, out - half, out + half, width - out + half, height - out + half)


@contextmanager
def _saving(style: Style, values: dict[str, Any]) -> Iterator[None]:
    """A tile's settings, with the layout's color behind everything."""
    color = values["separators.color"]
    with isolated(style):
        background = "none" if unset(color) else str(color)
        matplotlib.rcParams["savefig.facecolor"] = background
        matplotlib.rcParams["savefig.transparent"] = background == "none"
        yield


def _limit(value: Any) -> float | None:
    return None if value is None or value == NONE else float(value)


def stem(path: Path) -> str:
    """A layout file's name without .layout.yaml (or .yaml)."""
    name = path.name
    return name[: -len(SUFFIX)] if name.endswith(SUFFIX) else path.stem


def is_layout(path: Path) -> bool:
    return path.name.endswith(SUFFIX)


def _format_values(
    doc: dict[str, Any], reg: Registry, own: dict[str, Resolved]
) -> dict[str, Resolved]:
    """The layout's format's values, each saying it came through the layout, with the format's
    variable parameters that the layout sets replaced by the layout's values."""
    name = own["specifications.format"].value
    origin = f"layout '{doc['name']}'"
    values = {
        p: Resolved(r.value, r.fixed, f"{r.origin}, from {origin}")
        for p, r in resolve_detailed("format", reg.docs["format"][name], reg).items()
    }
    values.update({p: r for p, r in own.items() if p in values})
    return values


def _check(doc: Any, reg: Registry) -> None:
    problems = validate("layout", doc, reg)
    if problems:
        raise SpecError(problems)
    chosen = resolve_detailed("layout", doc, reg)["specifications.format"].value
    while chosen not in (None, NONE):
        named = reg.docs["format"][chosen]
        problems += [f"format '{chosen}': {p}" for p in validate("format", named, reg)]
        chosen = named.get("extends")
    problems += drawing_problems(doc, reg)
    if problems:
        raise SpecError(problems)


def _tile_folder(doc: dict[str, Any], reg: Registry, folder: Path) -> Path:
    """Where a layout's tile files are found from: the folder of the file listing its tabs
    (`folder` for doc itself)."""
    source = tabs_source(doc, reg)
    if source is doc:
        return folder
    known = reg.paths["layout"].get(source["name"])
    return known.parent if known is not None else folder


def _load(
    spec: dict[str, Any] | str | Path, registry: Registry | None
) -> tuple[Any, Registry, Path]:
    """The layout document, the registry it's checked against, and the folder its own
    relative paths are found from."""
    if isinstance(spec, str | Path):
        path = Path(spec)
        doc = load_yaml(path)
        reg = (registry or registry_for(path.parent)).copy()
        if isinstance(doc, dict) and "name" in doc:
            reg.add("layout", doc, path)
        return doc, reg, path.parent
    reg = (registry or registry_for(Path.cwd())).copy()
    if isinstance(spec, dict) and "name" in spec and spec["name"] not in reg.docs["layout"]:
        reg.add("layout", spec)
    return spec, reg, Path.cwd()


def _tile_files(doc: dict[str, Any], reg: Registry, folder: Path) -> tuple[dict, list[str]]:
    """Each tab's tiles' GraphSpec files, {tab: {tile: path}}, in reading order, and what's
    wrong with them."""
    files = _tile_folder(doc, reg, folder)
    out: dict[str, dict[str, Path]] = {}
    problems = []
    for tab in tabs(doc, reg):
        out[tab.name] = {}
        for name in tab.places():
            file = str(tab.tiles[name])
            where = f"tabs.{tab.name}.tiles.{name}"
            target = Path(file).expanduser()
            target = target if target.is_absolute() else files / target
            if is_layout(target):
                problems.append(f"{where}: '{file}' is a layout; a tile is a GraphSpec file")
            elif not target.is_file():
                problems.append(f"{where}: no GraphSpec file at '{target}'")
            else:
                out[tab.name][name] = target
    return out, problems


def explain_layout(
    spec: dict[str, Any] | str | Path, registry: Registry | None = None
) -> dict[str, dict[str, Resolved]]:
    """Every value a layout is drawn with, without drawing it: {"layout": its own values},
    then each tile's values by kind, as {"tabs.<tab>.tiles.<tile>.<kind>": ...} (see
    spec.documents.explain). Each tile's format values are the layout's format's."""
    doc, reg, folder = _load(spec, registry)
    _check(doc, reg)
    own = resolve_detailed("layout", doc, reg)
    fmt = _format_values(doc, reg, own)
    files, problems = _tile_files(doc, reg, folder)
    out: dict[str, dict[str, Resolved]] = {"layout": own}
    for tab, tiles in files.items():
        for name, path in tiles.items():
            where = f"tabs.{tab}.tiles.{name}"
            gdoc = load_yaml(path)
            greg = reg.copy()  # a layout's tiles use the packs its configs allow
            if isinstance(gdoc, dict) and "name" in gdoc:
                greg.add("graphspec", gdoc, path)
            found = validate("graphspec", gdoc, greg)
            if found:
                problems += [f"{where} ({path.name}): {p}" for p in found]
                continue
            values = explain(gdoc, greg)
            values["format"] = dict(fmt)
            out.update({f"{where}.{kind}": v for kind, v in values.items()})
    if problems:
        raise SpecError(problems)
    return out


def nonstandard_packs_of(
    spec: dict[str, Any] | str | Path, registry: Registry | None = None
) -> list[str]:
    """The packs a layout is drawn with, its own specs' and its tiles', that the main config
    doesn't list, without drawing it."""
    doc, reg, folder = _load(spec, registry)
    used = packs_used("layout", doc, reg)
    files, _ = _tile_files(doc, reg, folder)
    for tiles in files.values():
        for path in tiles.values():
            gdoc = load_yaml(path)
            if isinstance(gdoc, dict):
                greg = reg.copy()
                if "name" in gdoc:
                    greg.add("graphspec", gdoc, path)
                used |= packs_used("graphspec", gdoc, greg)
    return sorted(used & reg.nonstandard)


def render_layout(
    spec: dict[str, Any] | str | Path,
    data: dict[str, pd.DataFrame] | None = None,
    registry: Registry | None = None,
    footnote: str | None = None,
) -> Layout:
    """Draw a layout, given as a file path or a document. `data` gives DataFrames by tile
    name, for tiles drawn from a DataFrame rather than their GraphSpec's data.file. A
    footnote is written small at the bottom right of each tab, below every tile."""
    doc, reg, folder = _load(spec, registry)
    _check(doc, reg)
    own = resolve_detailed("layout", doc, reg)
    values = {p: r.value for p, r in own.items()}
    fmt = _format_values(doc, reg, own)
    data = dict(data or {})
    listed = tabs(doc, reg)
    names = {t for tab in listed for t in tab.tiles}
    unknown = sorted(set(data) - names)
    if unknown:
        raise SpecError(
            [f"data: no tile '{n}'; tiles are {', '.join(sorted(names))}" for n in unknown]
        )
    files, problems = _tile_files(doc, reg, folder)
    if problems:
        raise SpecError(problems)
    layout = Layout(doc, values, own, {p: r.value for p, r in fmt.items()})
    layout.specs = {
        "layout": {"name": doc["name"], "version": doc["version"]},
        "format": spec_record("format", values["specifications.format"], reg),
    }
    layout._own_packs = sorted(packs_used("layout", doc, reg) & reg.nonstandard)
    prepared: dict[str, dict[str, Prepared]] = {}
    for tab in listed:
        prepared[tab.name] = {}
        for name, path in files[tab.name].items():
            try:
                prepared[tab.name][name] = prepare(path, data.get(name), reg, format=fmt)
            except SpecError as e:
                problems += [f"{_where(tab, name)}: {p}" for p in e.problems]
    if problems:
        raise SpecError(problems)
    for tab in listed:
        layout.tabs.append(_draw_tab(layout, tab, prepared[tab.name], footnote))
    layout.nonstandard_packs = sorted({p for t in layout.tabs for p in t.nonstandard_packs})
    return layout


def _draw_tab(
    layout: Layout, tab: Tab, prepared: dict[str, Prepared], footnote: str | None = None
) -> TabFigure:
    fmt = layout.format
    width, height = _inches(fmt["figure.width"]), _inches(fmt["figure.height"])
    first = next(iter(prepared.values()))
    places = tab.places()
    with isolated(first.style), lint.font_messages() as font_problems:
        fig = GraphFigure(figsize=(width or 6.0, height or 4.0))
        GraphCanvas(fig)
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
        gap = float(layout.values["separators.gap"]) * float(fmt["figure.base_size"]) / 72
        edge = gap if layout.values["separators.line.border"] else MARGIN_IN  # room for it
        if footnote:
            add_footnote(fig, footnote, first.style)
        foot = footnote_room(fig)
        sizes = (gap, width, height, tab.column_widths, tab.row_heights, edge, foot)
        try:
            grid = _lay_out_and_label(fig, tab, placed, prepared, drawn, sizes)
            if any(k.outside for p in placed for k in keys(p.ax)):  # room for keys outside
                grid = _lay_out_and_label(fig, tab, placed, prepared, drawn, sizes)
                for p in placed:
                    with isolated(p.style):
                        _tile_call(tab, p.name, prepared[p.name].module.check_outside, p.ax)
        except LayoutError as e:
            where = f"tabs.{tab.name}: " if len(tab.tiles) else ""
            raise SpecError([f"{where}{e}"]) from None
        backgrounds(fig, grid, placed)
        place_footnote(fig, edge, edge)
        apply_separators(fig, grid, layout.values, float(fmt["figure.base_size"]))
        fig.canvas.draw()
    tiles = {}
    for p in placed:
        prep = prepared[p.name]
        prep.finish(drawn[p.name])
        tiles[p.name] = Tile(
            p.name,
            str(tab.tiles[p.name]),
            prep.doc,
            p.ax,
            prep.values,
            prep.resolved,
            prep.style,
            prep.record,
            drawn[p.name].labelling,
            list(drawn[p.name].warnings),
            prep.specs,
        )
    result = TabFigure(layout, tab.name, tab.slug, fig, tiles, grid)
    used = {p for prep in prepared.values() for p in prep.nonstandard_packs}
    result.nonstandard_packs = sorted({*layout._own_packs, *used})
    result.changed = bool(result.nonstandard_packs)  # drawn with a pack not in the main config
    result._font_problems = font_problems
    result.check()
    result._snapshot = _artists(fig)
    result._drawn = result._pixels()
    fig.graph = result  # from here on, drawing or saving the figure inspects it first
    return result


def _where(tab: Tab, name: str) -> str:
    """Where a tile's problem is: its place in the layout, and its GraphSpec file."""
    return f"tabs.{tab.name}.tiles.{name} ({tab.tiles[name]})"


def _tile_call(tab: Tab, name: str, function: Any, *args: Any) -> Any:
    """Call a graph type's function on a tile, naming the tile in any error."""
    try:
        return function(*args)
    except Exception as e:
        if type(e).__name__ != "DrawError":
            raise
        raise SpecError([f"{_where(tab, name)}: {e}"]) from None


def _lay_out_and_label(
    fig: Any,
    tab: Tab,
    placed: list[Placed],
    prepared: dict[str, Prepared],
    drawn: dict[str, Any],
    sizes: tuple[Any, ...],
) -> Grid:
    """As graph._lay_out_and_label, for every tile at once: lay out, place what needs the
    final sizes (again while that changes anything), then name each tile's series."""
    grid = arrange(fig, tab.areas, placed, *sizes)
    for _ in range(PLACE_PASSES):
        moved = False
        for p in placed:
            prep = prepared[p.name]
            with isolated(p.style):
                gt = prep.values["graph_type"]
                moved |= bool(
                    _tile_call(tab, p.name, prep.module.place, p.ax, drawn[p.name], gt, p.style)
                )
        if not moved:
            break
        grid = arrange(fig, tab.areas, placed, *sizes)
    for p in placed:
        prep = prepared[p.name]
        with isolated(p.style):
            prep.module.unlabel(p.ax)
            gt = prep.values["graph_type"]
            _tile_call(tab, p.name, prep.module.label, p.ax, drawn[p.name], gt, p.style)
    return grid
