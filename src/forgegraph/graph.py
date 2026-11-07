"""Rendering a GraphSpec: the Python API (`render`, `xy`, `graphspec`, `load`) and the Graph it
returns."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import cached_property
from pathlib import Path
from typing import Any

import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from forgegraph.data import read_data
from forgegraph.drawing import export, lint, owners, page
from forgegraph.drawing import toggles as toggled
from forgegraph.drawing import xy as xy_type
from forgegraph.drawing.axes import value_number
from forgegraph.drawing.errors import LayoutError
from forgegraph.drawing.figure import new_figure, watermark
from forgegraph.drawing.layout import Plot, Room, add_footnote, finish, layout, rooms_of, widest
from forgegraph.drawing.readout import Mark, marks
from forgegraph.drawing.style import Style, isolated, unset
from forgegraph.drawn import Inspected, Saved, SpecError
from forgegraph.fonts import font_file
from forgegraph.spec.access import packs_used, use_fonts
from forgegraph.spec.explain import Explained
from forgegraph.spec.loaded import Loaded, load_document
from forgegraph.spec.parameters import (
    NONE,
    PARAMETERS,
    iqr_rule,
    is_none,
    series_definitions,
    tree_set,
)
from forgegraph.spec.provenance import DataRecord, graph_fields, record, used
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import Values, chain
from forgegraph.spec.series import look_definitions, theme_for
from forgegraph.spec.tags import from_json, var
from forgegraph.spec.toggles import Toggles, toggles
from forgegraph.spec.validate import drawing_problems, named_problems, validate
from forgegraph.spec.views import Control, applied, combinations, controls

GRAPH_TYPES = {"xy": xy_type}  # each graph type's drawing module, by the root of its extends chain


@dataclass
class Graph(Inspected, Saved):
    """A drawn graph: its figure, the GraphSpec it came from and every value it used."""

    spec: dict[str, Any]
    figure: Figure
    axes: Axes
    values: dict[str, dict[str, Any]]  # by kind: graphspec, graph_type, theme, format
    style: Style
    data: DataRecord
    labelling: str
    issues: list[lint.Issue] = field(default_factory=list)  # lint's findings
    specs: dict[str, Any] = field(default_factory=dict)  # each spec used: name and version
    freshness: page.Freshness | None = None  # a scheduled run's, for its HTML page
    changed: bool = False  # found changed since rendering (see inspect); never reset
    nonstandard_packs: list[str] = field(default_factory=list)  # used, not in the main config
    style_keys: list[str] = field(default_factory=list)  # the column each style key explains
    _snapshot: tuple[int, ...] = ()  # the figure's artists when rendering finished
    _drawn: str = ""  # a hash of the pixels the figure drew when rendering finished
    _held: bool = False  # inspected already, during one save (see inspected_once)
    _drawing: list[lint.Issue] = field(default_factory=list)  # found while drawing
    _font_problems: list[str] = field(default_factory=list)
    _prepared: Prepared = field(kw_only=True, repr=False, compare=False)  # what it was drawn from
    # Its choice layers' controls, and every view by the names chosen, one for each control:
    # this graph is the first; the others are drawn for its HTML page (spec/views.py).
    controls: list[Control] = field(default_factory=list)
    views: dict[tuple[str, ...], Graph] = field(default_factory=dict, repr=False)

    def mark(self) -> None:
        """Draw the watermark over the plot box, once: the figure has been found changed."""
        watermark(self.axes, self.style)

    def check(self) -> list[lint.Issue]:
        """Lint the figure as it is now, including anything drawn on it since, and return
        the issues (also kept in `issues`)."""
        self._lint_draw()
        with isolated(self.style):
            figure = lint.figure_issues(self.figure, self._font_problems)
        plot = self._prepared.plot_issues(self.axes, self._drawing)
        self.issues = lint.ordered(figure, plot)
        if self.views:
            self.issues = self._with_views([g.check() for g in self._others()])
        return self.issues

    def _others(self) -> list[Graph]:
        return [g for g in self.views.values() if g is not self]

    def _with_views(self, others: list[list[lint.Issue]]) -> list[lint.Issue]:
        """Its own issues, then each other view's, each naming its view."""
        out = []
        for names, issues in zip(self.views, [self.issues, *others], strict=True):
            label = " / ".join(names)
            out += [lint.Issue(i.check, f"view '{label}': {i.message}") for i in issues]
        return out

    @property
    def warnings(self) -> list[str]:
        """Lint's findings, as messages."""
        return [i.message for i in self.issues]

    @property
    def toggles(self) -> Toggles | None:
        """Its toggle layer's items (spec/toggles.py), or None."""
        return self._prepared.toggles

    @property
    def data_records(self) -> list[DataRecord]:
        """What was read and drawn (as a layout's are, by tile)."""
        return [self.data]

    @property
    def labelling_by_name(self) -> str:
        """How its series are named: its one labelling, where a layout's are by tile."""
        return self.labelling

    @property
    def style_keys_by_name(self) -> list[str]:
        """Its style keys' columns, where a layout's are by tile."""
        return self.style_keys

    def record(self) -> dict[str, Any] | None:
        """The provenance record saved files carry, at the format's provenance.level; None
        with off."""
        level = self.values["format"]["provenance.level"]
        if level == "off":
            return None
        return record(
            level,
            specs=self.specs,
            nonstandard=self.nonstandard,
            nonstandard_packs=self.nonstandard_packs or None,
            **graph_fields(self.spec, self.values, self.data, level == "full"),
        )

    def save_all(self, stem: str | Path) -> list[Path]:
        """Save every file type the format lists, as stem.png and so on. A dot in stem is part
        of the name, not a file type."""
        return self._write(Path(stem), list(self.values["format"]["output.file_types"]))

    def _write(self, stem: Path, kinds: list[str]) -> list[Path]:
        dpi = int(self.values["format"]["output.dpi"])
        out = []
        with isolated(self.style), self.inspected_once():  # savefig settings too
            for kind in kinds:
                path = stem.with_name(f"{stem.name}.{kind}")
                if kind == "html":
                    image, found, cut = self._on_page(dpi)
                    shown = page.Shown(None, None, image, marks=found, slices=cut)
                    shown = self._with_view_images(shown, dpi)
                    title = str(self.spec.get("name", stem.name))
                    background = self.style.theme["background.color"]
                    out.append(
                        page.write(
                            path,
                            title,
                            [shown],
                            self.record(),
                            "transparent" if unset(background) else str(background),
                            bar=controls_look(self.style) if self.controls or cut else None,
                            freshness=self.freshness,
                            controls=page_controls(self.controls),
                            toggles=page_toggles([self.toggles]),
                        )
                    )
                else:
                    out.append(export.save(self.figure, path, dpi))
        return out

    def _with_view_images(self, shown: page.Shown, dpi: int) -> page.Shown:
        """The figure on a page, with every view's image if it has views."""
        if not self.views:
            return shown
        viewed = []
        for names, g in self.views.items():
            if g is self:
                svg, found, cut = shown.svg, shown.marks, shown.slices
            else:
                with isolated(g.style), g.inspected_once():
                    svg, found, cut = g._on_page(dpi)
            choices = tuple(zip((c.name for c in self.controls), names, strict=True))
            viewed.append(page.Viewed(choices, svg, found, cut))
        return replace(shown, views=tuple(viewed))

    def _on_page(self, dpi: int) -> tuple[bytes, tuple[Mark, ...], tuple[toggled.Slice, ...]]:
        """The figure as a page shows it: its SVG, its data points and, with a toggle
        layer, its images to stack."""
        owned = owned_items(self.axes, self._prepared.toggles)
        found = tuple(marks(self.figure, owned))
        cut = toggled.slices(self.figure, toggled.member_of(owned), dpi) if owned else []
        return export.svg(self.figure, dpi), found, tuple(cut)

    def _name(self) -> str:
        return str(self.spec.get("name", "graph"))

    def _shown(self) -> tuple[Figure, Style]:
        return self.figure, self.style


@dataclass
class Prepared:
    """A GraphSpec checked and resolved, with its data, ready to draw into an Axes."""

    doc: dict[str, Any]
    explained: Explained  # every value, by kind, with where each came from
    frame: pd.DataFrame
    record: DataRecord
    module: Any  # the graph type's drawing module
    style: Style
    specs: dict[str, Any]  # each spec used, by kind: its name and version
    nonstandard_packs: list[str] = field(default_factory=list)  # used, not in the main config
    controls: list[Control] = field(default_factory=list)  # its choice layers' (spec/views.py)
    toggles: Toggles | None = None  # its toggle layer's items (spec/toggles.py)

    @cached_property
    def values(self) -> dict[str, dict[str, Any]]:
        """Every value, by kind, without where each came from."""
        return self.explained.plain()

    @property
    def title(self) -> str | None:
        title = self.values["graphspec"]["text.title"]
        return None if is_none(title) else str(title)

    @property
    def series(self) -> dict[str, tuple[dict[str, Any], Style]]:
        """Each series by name: its values, and the style it's drawn in, the theme with what
        it sets for itself."""
        s = self.style
        return {
            name: (
                values,
                Style(theme_for(self.explained.theme, values["look"]), s.format, s.fixed),
            )
            for name, values in self.values.get("series", {}).items()
        }

    def draw(self, ax: Axes) -> Any:
        """Draw the graph into ax; returns what the graph type drew."""
        try:
            return self.module.draw(
                ax,
                self.frame,
                self.values["graph_type"],
                self.style,
                self.title,
                self.values.get("layers", {}),
                self.series,
            )
        except self.module.DrawError as e:
            raise SpecError([str(e)]) from None

    def finish(self, drawn: Any) -> None:
        """Record what drawing found about the data."""
        self.record.rows_plotted = drawn.rows_plotted
        self.record.rows_dropped = drawn.rows_dropped

    def plot_issues(self, ax: Axes, drawing: list[lint.Issue]) -> list[lint.Issue]:
        """Lint's issues with the graph as drawn into ax, with those drawing it found."""
        with isolated(self.style):
            return lint.plot_issues(
                ax,
                fixed_limits=fixed_limits(self.values["graph_type"]),
                rows_dropped=self.record.rows_dropped,
                drawing=drawing,
            )


def prepare(
    spec: dict[str, Any] | str | Path,
    data: pd.DataFrame | None = None,
    registry: Registry | None = None,
    format: Values | None = None,
    view: dict[str, Any] | None = None,
) -> Prepared:
    """Check and resolve a GraphSpec, given as a file path or a document, and read its data:
    `data` if given, otherwise the Parquet file its data.file names. With `format` (resolved
    format values, as from a layout), those replace the format's. With `view` (changes by
    dotted path, from its choice layers' views), it's the GraphSpec with those changes."""
    loaded = load_document("graphspec", spec, registry)
    if view is not None:
        loaded = _viewed(loaded, view)
    doc, reg = loaded.doc, loaded.reg
    problems = validate("graphspec", doc, reg, views=view is None)
    if problems:
        raise SpecError(problems)
    problems = named_problems("graphspec", doc, reg)
    if problems:
        raise SpecError(problems)
    problems = drawing_problems(doc, reg)
    if problems:
        raise SpecError(problems)
    explained = loaded.explain(format)
    values = explained.plain()
    frame, data_record = read_data(loaded, values, data)
    gt = reg.docs["graph_type"][values["graphspec"]["specifications.graph_type"]]
    module = GRAPH_TYPES[str(chain("graph_type", gt, reg)[-1]["name"])]
    fixed = frozenset(p for p, r in explained.theme.items() if r.fixed)
    style = Style(values["theme"], values["format"], fixed)
    nonstandard = sorted(packs_used("graphspec", doc, reg) & reg.nonstandard)
    use_fonts("graphspec", doc, reg)
    specs = used(values, reg)
    listed = controls(doc, reg)
    p = Prepared(doc, explained, frame, data_record, module, style, specs, nonstandard, listed)
    p.toggles = toggles(doc, reg)
    return p


def _viewed(loaded: Loaded, change: dict[str, Any]) -> Loaded:
    """The GraphSpec with a view's changes, checked against its registry, holding it in
    place of the GraphSpec it changes."""
    doc = applied(loaded.doc, change)
    reg = loaded.reg.copy()
    name = loaded.doc.get("name")
    if isinstance(name, str) and reg.docs["graphspec"].get(name) is loaded.doc:
        reg.docs["graphspec"][name] = doc
    return Loaded(loaded.kind, doc, reg, loaded.folder)


def render(
    spec: dict[str, Any] | str | Path,
    data: pd.DataFrame | None = None,
    registry: Registry | None = None,
    footnote: str | None = None,
) -> Graph:
    """Draw a GraphSpec, given as a file path or a document. With `data`, the graph is drawn
    from that DataFrame; otherwise from the Parquet file its data.file names. The specs are
    checked against `registry` if given, otherwise against the configs found from the
    GraphSpec file's folder (or, for a document, the working folder). A footnote is written
    small at the bottom right, below everything else (a scheduled run's "data as of"
    stamp). With choice layers, every view is drawn (spec/views.py): the Graph is the first,
    holding the others for its HTML page."""
    p = prepare(spec, data, registry)
    if not p.controls:
        return _draw(p, footnote)
    viewed = {}
    for names, change in combinations(p.controls):
        try:
            viewed[names] = prepare(spec, data, registry, view=change)
        except SpecError as e:
            label = " / ".join(names)
            raise SpecError([f"view '{label}': {m}" for m in e.problems]) from None
    graphs = _draw_views(viewed, footnote)
    # Each view laid out alone takes the room its own tick labels and keys need, so its plot
    # box moves as the views switch: drawn again, every view takes the most any one needed.
    floor = widest([rooms_of(g.figure, {"graph": (g.axes, g.style)}) for g in graphs.values()])
    graphs = _draw_views(viewed, footnote, floor["graph"])
    first = next(iter(graphs.values()))
    first.controls, first.views = p.controls, graphs
    first.issues = first._with_views([g.issues for g in first._others()])
    return first


def _draw_views(
    viewed: dict[tuple[str, ...], Prepared], footnote: str | None, floor: Room | None = None
) -> dict[tuple[str, ...], Graph]:
    """Draw each view, naming it in any problem."""
    out = {}
    for names, p in viewed.items():
        try:
            out[names] = _draw(p, footnote, floor)
        except SpecError as e:
            label = " / ".join(names)
            raise SpecError([f"view '{label}': {m}" for m in e.problems]) from None
    return out


def _draw(p: Prepared, footnote: str | None, floor: Room | None = None) -> Graph:
    """Draw a prepared GraphSpec into a figure of its own; floor: the least room around its
    plot box (drawing/layout.arrange)."""
    module, style, gt = p.module, p.style, p.values["graph_type"]
    with isolated(style), lint.font_messages() as font_problems:
        fig, ax = new_figure(style)
        drawn = p.draw(ax)
        if footnote:
            add_footnote(fig, footnote, style)
        try:
            plot = Plot(ax, module, drawn, gt, style, _call)
            finish([plot], lambda: layout(fig, ax, style, floor))
        except LayoutError as e:
            raise SpecError([str(e)]) from None
        except module.DrawError as e:
            raise SpecError([str(e)]) from None
    p.finish(drawn)
    graph = Graph(
        p.doc, fig, ax, p.values, style, p.record, drawn.labelling, [], p.specs, _prepared=p
    )
    graph.style_keys = [k.column for k in drawn.style_keys]
    graph._drawing = list(drawn.warnings)
    if p.toggles is not None and p.toggles.hidden:  # files show the page's opening state
        owned = owned_items(ax, p.toggles)
        toggled.hide(fig, toggled.member_of(owned), p.toggles.hidden)
    graph.seal(fig, font_problems, p.nonstandard_packs)
    return graph


def _call(function: Any, *args: Any) -> Any:
    """Call a graph type's function on a graph alone: render's settings and its handling of
    errors already apply."""
    return function(*args)


def fixed_limits(gt: dict[str, Any]) -> dict[str, tuple[float | str | None, float | str | None]]:
    """Each axis's set min and max (None where automatic), for lint: as drawn, a date as its
    day number (axes.value_number)."""
    return {a: (_limit(gt.get(f"axis.{a}.min")), _limit(gt.get(f"axis.{a}.max"))) for a in "xy"}


def _limit(value: Any) -> float | str | None:
    """A set limit as a number; an IQR rule as "view", the end where the rule put it."""
    if is_none(value):
        return None
    return "view" if iqr_rule(value) is not None else value_number(value)


def xy(
    data: pd.DataFrame,
    x: str | list[str],
    y: str | list[str],
    *,
    title: str | None = None,
    theme: str = "forgegraph_default/light_theme",
    format: str = "forgegraph_default/compact_format",
    color: str | None = None,
    line_style: str | None = None,
    marker_shape: str | None = None,
    marker_fill: str | None = None,
    split: str | list[str] | None = None,
    parameters: dict[str, Any] | None = None,
    registry: Registry | None = None,
) -> Graph:
    """Draw y against x from a DataFrame: a series for each y column, named after it. color,
    line_style, marker_shape, marker_fill and split set each series' color, line.style,
    marker.shape, marker.fill and split; `parameters` sets any other variable parameter by
    path, e.g. {"axis.x.scale": "log"}, and a series parameter under series, e.g.
    {"series.bar.show": True}, for every series. With arrangement.base_axis y, the series are
    drawn along y: y is then the column they're drawn along, and x their columns. registry:
    as for render."""
    parameters = dict(parameters or {})
    base = parameters.get("arrangement.base_axis", "x")
    along, columns = (x, y) if base == "x" else (y, x)
    settings: dict[str, Any] = {"series": {}, f"axis.{base}.data.column": along}
    each: dict[str, Any] = {}
    for path, value in (
        ("color", color),
        ("line.style", line_style),
        ("marker.shape", marker_shape),
        ("marker.fill", marker_fill),
        ("split", split),
    ):
        if value is not None:
            each[path] = value
    own = {*series_definitions(), *look_definitions()}
    for path, value in parameters.items():
        within = path.removeprefix("series.")
        if path.startswith("series.") and within in own:
            each[within] = value
        else:
            settings[path] = value
    entry: dict[str, Any] = {}
    for path, value in each.items():
        tree_set(entry, path, value)
    names = [columns] if isinstance(columns, str) else columns
    settings["series"] = {str(name): dict(entry) for name in names}  # a name may have dots;
    # first, so another path under series is in the GraphSpec as given, to be reported
    return render(
        graphspec("graph", "xy", theme=theme, format=format, title=title, settings=settings),
        data,
        registry,
    )


def graphspec(
    name: str,
    graph_type: str,
    *,
    theme: str = "forgegraph_default/light_theme",
    format: str = "forgegraph_default/compact_format",
    data_file: str | None = None,
    preprocessing: str | None = None,
    title: str | None = None,
    description: str = "",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A GraphSpec document, named `name`, extending nothing: the graph type, theme and format
    it's drawn with; data_file, the Parquet file it's drawn from (None: a DataFrame passed
    to render); preprocessing, a note of how that data was prepared; its title; and
    `settings`, any other variable parameter by path, e.g. {"axis.x.scale": "log"}. Its
    parameters are tagged !var, so a GraphSpec extending it may change any of them."""
    variable: dict[str, dict[str, Any]] = {
        "specifications": {
            "graph_type": graph_type,
            "theme": theme,
            "format": format,
        },
        "text": {"title": title if title is not None else NONE},
        "data": {
            "file": data_file if data_file is not None else NONE,
            "preprocessing": preprocessing if preprocessing is not None else NONE,
        },
    }
    for path, value in (settings or {}).items():
        tree_set(variable, path, value)
    return {
        "name": name,
        "version": 0,
        "description": description,
        "extends": NONE,
        PARAMETERS: var(variable),
    }


def load(path: str | Path) -> dict[str, Any] | None:
    """The provenance record stored in a graph file (its GraphSpec is under "graphspec", a
    layout's file under "layout"), with their !var and !fix tags."""
    record = export.read(Path(path))
    if record is None:
        return None
    return {k: from_json(v) if k in ("graphspec", "layout") else v for k, v in record.items()}


def controls_look(style: Style) -> page.TabBar:
    """The look of a graph page's controls: the theme's general text, left-aligned."""
    t = style.theme
    family, weight = str(t["text.font"]), style.weight("text.weight")
    return page.TabBar(
        family,
        style.pt("text.size"),
        weight,
        str(t["text.color"]),
        style.pt("text.gap"),
        "left",
        font_file(family, weight),
        "none",
        0.0,
        "none",
    )


def page_controls(listed: list[Control]) -> tuple[page.Control, ...]:
    """Choice layers' controls, as a page shows them."""
    return tuple(page.Control(c.name, c.label, c.kind, c.names) for c in listed)


def owned_items(ax: Axes, listed: Toggles | None) -> dict[Any, dict[str, str]]:
    """For an Axes with a toggle layer, each toggled owner's item (drawing/toggles.py)."""
    if listed is None:
        return {}
    return {ax: {owners.name(kind, name): name for name, kind in listed.items}}


def page_toggles(listed: list[Toggles | None]) -> tuple[page.Toggle, ...]:
    """Toggle layers' checkboxes, as a page shows them: one for each item's name."""
    out: dict[str, page.Toggle] = {}
    for t in listed:
        if t is not None:
            for name in t.names:
                out.setdefault(name, page.Toggle(name, name in t.hidden))
    return tuple(out.values())
