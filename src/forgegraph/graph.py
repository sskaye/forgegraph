"""Rendering a GraphSpec: the Python API (`render`, `xy`, `graphspec`, `load`) and the Graph it
returns."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from forgegraph.data import read_data
from forgegraph.drawing import export, lint, page
from forgegraph.drawing import xy as xy_type
from forgegraph.drawing.errors import LayoutError
from forgegraph.drawing.figure import (
    add_footnote,
    layout,
    new_figure,
    watermark,
)
from forgegraph.drawing.key import keys
from forgegraph.drawing.style import Style, isolated, unset
from forgegraph.drawn import Inspected, Saved, SpecError
from forgegraph.spec.access import packs_used, use_fonts
from forgegraph.spec.explain import Explained
from forgegraph.spec.loaded import load_document
from forgegraph.spec.parameters import NONE, tree_set
from forgegraph.spec.provenance import DataRecord, graph_fields, record, used
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import Values, chain
from forgegraph.spec.validate import drawing_problems, named_problems, validate

GRAPH_TYPES = {"xy": xy_type}  # each graph type's drawing module, by the root of its extends chain
PLACE_PASSES = 3  # place, then lay out again, while value labels widen the axis


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
    _snapshot: tuple[int, ...] = ()  # the figure's artists when rendering finished
    _drawn: str = ""  # a hash of the pixels the figure drew when rendering finished
    _held: bool = False  # inspected already, during one save (see inspected_once)
    _drawing: list[lint.Issue] = field(default_factory=list)  # found while drawing
    _font_problems: list[str] = field(default_factory=list)
    _prepared: Prepared = field(kw_only=True, repr=False, compare=False)  # what it was drawn from

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
        return self.issues

    @property
    def warnings(self) -> list[str]:
        """Lint's findings, as messages."""
        return [i.message for i in self.issues]

    @property
    def data_records(self) -> list[DataRecord]:
        """What was read and drawn (as a layout's are, by tile)."""
        return [self.data]

    @property
    def labelling_by_name(self) -> str:
        """How its series are named: its one labelling, where a layout's are by tile."""
        return self.labelling

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
                    shown = [page.Shown(None, None, export.svg(self.figure, dpi))]
                    title = str(self.spec.get("name", stem.name))
                    background = self.style.theme["background.color"]
                    out.append(
                        page.write(
                            path,
                            title,
                            shown,
                            self.record(),
                            "transparent" if unset(background) else str(background),
                            freshness=self.freshness,
                        )
                    )
                else:
                    out.append(export.save(self.figure, path, dpi))
        return out

    def _name(self) -> str:
        return str(self.spec.get("name", "graph"))

    def _shown(self) -> tuple[Figure, Style]:
        return self.figure, self.style


def _lay_out_and_label(
    fig: Figure, ax: Any, module: Any, drawn: Any, gt: dict[str, Any], style: Style
) -> None:
    """Lay out, place what needs the final size (value labels may widen the value axis, so
    again), then name the series and place notes. A second call, after a key went outside
    the plot box, lays out with room for it and places everything again."""
    layout(fig, ax, style)
    for _ in range(PLACE_PASSES):
        if not module.place(ax, drawn, gt, style):
            break
        layout(fig, ax, style)
    module.unlabel(ax)
    module.label(ax, drawn, gt, style)


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

    @cached_property
    def values(self) -> dict[str, dict[str, Any]]:
        """Every value, by kind, without where each came from."""
        return self.explained.plain()

    @property
    def title(self) -> str | None:
        title = self.values["graphspec"]["text.title"]
        return None if title in (None, NONE) else str(title)

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
) -> Prepared:
    """Check and resolve a GraphSpec, given as a file path or a document, and read its data:
    `data` if given, otherwise the Parquet file its data.file names. With `format` (resolved
    format values, as from a layout), those replace the format's."""
    loaded = load_document("graphspec", spec, registry)
    doc, reg = loaded.doc, loaded.reg
    problems = validate("graphspec", doc, reg)
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
    return Prepared(doc, explained, frame, data_record, module, style, specs, nonstandard)


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
    stamp)."""
    p = prepare(spec, data, registry)
    module, style, gt = p.module, p.style, p.values["graph_type"]
    with isolated(style), lint.font_messages() as font_problems:
        fig, ax = new_figure(style)
        drawn = p.draw(ax)
        if footnote:
            add_footnote(fig, footnote, style)
        try:
            _lay_out_and_label(fig, ax, module, drawn, gt, style)
            if any(k.outside for k in keys(ax)):  # it needs room: lay out around it, again
                _lay_out_and_label(fig, ax, module, drawn, gt, style)
                module.check_outside(ax)
        except LayoutError as e:
            raise SpecError([str(e)]) from None
        except module.DrawError as e:
            raise SpecError([str(e)]) from None
    p.finish(drawn)
    graph = Graph(
        p.doc, fig, ax, p.values, style, p.record, drawn.labelling, [], p.specs, _prepared=p
    )
    graph._drawing = list(drawn.warnings)
    graph.seal(fig, font_problems, p.nonstandard_packs)
    return graph


def fixed_limits(gt: dict[str, Any]) -> dict[str, tuple[float | None, float | None]]:
    """Each axis's set min and max (None where automatic), for lint."""
    return {a: (_limit(gt.get(f"axis.{a}.min")), _limit(gt.get(f"axis.{a}.max"))) for a in "xy"}


def _limit(value: Any) -> float | None:
    return None if value is None or value == NONE else float(value)


def xy(
    data: pd.DataFrame,
    x: str,
    y: str | list[str],
    *,
    title: str | None = None,
    theme: str = "forgegraph_base/base_theme",
    format: str = "forgegraph_base/base_format",
    color: str | None = None,
    line_style: str | None = None,
    marker_shape: str | None = None,
    marker_fill: str | None = None,
    detail: str | list[str] | None = None,
    parameters: dict[str, Any] | None = None,
    registry: Registry | None = None,
) -> Graph:
    """Draw y against x from a DataFrame. color, line_style, marker_shape, marker_fill and
    detail set the encoding parameters of those names; `parameters` sets any other variable
    parameter by path, e.g. {"mark.line.show": False, "axis.x.scale": "log"}. registry: as
    for render."""
    settings: dict[str, Any] = {"axis.x.data.column": x, "axis.y.data.column": y}
    for path, value in (
        ("encoding.color", color),
        ("encoding.line_style", line_style),
        ("encoding.marker_shape", marker_shape),
        ("encoding.marker_fill", marker_fill),
        ("encoding.detail", detail),
    ):
        if value is not None:
            settings[path] = value
    settings.update(parameters or {})
    return render(
        graphspec("graph", "xy", theme=theme, format=format, title=title, settings=settings),
        data,
        registry,
    )


def graphspec(
    name: str,
    graph_type: str,
    *,
    theme: str = "forgegraph_base/base_theme",
    format: str = "forgegraph_base/base_format",
    data_file: str | None = None,
    preprocessing: str | None = None,
    title: str | None = None,
    description: str = "",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A GraphSpec document, named `name`, extending nothing: the graph type, theme and format
    it's drawn with; data_file, the Parquet file it's drawn from (None: a DataFrame passed
    to render); preprocessing, a note of how that data was prepared; its title; and
    `settings`, any other variable parameter by path, e.g. {"axis.x.scale": "log"}."""
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
        "fixed_parameters": NONE,
        "variable_parameters": variable,
    }


def load(path: str | Path) -> dict[str, Any] | None:
    """The provenance record stored in a graph file (its GraphSpec is under "graphspec")."""
    return export.read(Path(path))
