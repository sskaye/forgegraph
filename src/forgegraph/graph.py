"""Rendering a GraphSpec: the Python API (`render`, `xy`, `graphspec`, `load`) and the Graph it
returns."""

from __future__ import annotations

import copy
import hashlib
import io
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from forgegraph import __version__
from forgegraph.drawing import export, lint, page
from forgegraph.drawing import xy as xy_type
from forgegraph.drawing.figure import (
    LayoutError,
    add_footnote,
    artists,
    layout,
    new_figure,
    watermark,
)
from forgegraph.drawing.key import keys
from forgegraph.drawing.style import Style, isolated, unset
from forgegraph.spec.common import ProblemsError
from forgegraph.spec.documents import (
    Registry,
    Resolved,
    drawing_problems,
    explain,
    folder_of,
    load_document,
    packs_used,
    resolve,
    setter,
    validate,
)
from forgegraph.spec.parameters import NONE, tree_set
from forgegraph.spec.provenance import DataRecord, ProvenanceRecord, created, plain

GRAPH_TYPES = {"xy": xy_type}  # each graph type's drawing module, by the root of its extends chain
PLACE_PASSES = 3  # place, then lay out again, while value labels widen the axis


class SpecError(ProblemsError):
    """A GraphSpec that can't be drawn; `problems` lists each one."""


class Inspected:
    """Whether a rendered figure is still as ForgeGraph drew it, for graphs and layout tabs:
    the same artists (_snapshot), drawing the same pixels (_drawn). Once it isn't, it stays
    non-standard, and every drawing of it carries the watermark. Drawing or saving the
    figure, by any route, inspects it first."""

    changed: bool
    _snapshot: tuple[int, ...]
    _drawn: str
    _held: bool

    def _shown(self) -> tuple[Figure, Style]:
        """The figure, and the style it's drawn in."""
        raise NotImplementedError

    @property
    def nonstandard(self) -> bool:
        """True if the figure was drawn on or changed after ForgeGraph finished (the escape
        hatch), so its specs no longer reproduce it, or it was drawn with a pack the main
        config doesn't list."""
        return self.inspect()

    def inspect(self) -> bool:
        """Check the figure now, unless it's already found changed or held (see
        inspected_once). Returns `nonstandard`."""
        if not self.changed and not self._held:
            figure, _ = self._shown()
            self.changed = artists(figure) != self._snapshot or self._pixels() != self._drawn
        return self.changed

    @contextmanager
    def inspected_once(self) -> Iterator[None]:
        """Inspect the figure now, and not again until the block ends: saving several files
        doesn't change it."""
        self.inspect()
        self._held = True
        try:
            yield
        finally:
            self._held = False

    def _pixels(self) -> str:
        return pixel_hash(*self._shown())

    def saving(self) -> AbstractContextManager[None]:
        """The matplotlib settings files are saved with."""
        return isolated(self._shown()[1])


class Saved:
    """Saving by path, for graphs and layouts: a path with a suffix saves that one file
    type; a path without one (or none: the spec's name) saves every file type the format
    lists, through save_all."""

    def save(self, path: str | Path | None = None) -> list[Path]:
        """Save it (see the class)."""
        if path is None:
            return self.save_all(Path(self._name()))
        target = Path(path)
        if not target.suffix:
            return self.save_all(target)
        return self._write(target.with_suffix(""), [target.suffix.lstrip(".")])

    def save_all(self, stem: str | Path) -> list[Path]:
        raise NotImplementedError

    def _write(self, stem: Path, kinds: list[str]) -> list[Path]:
        raise NotImplementedError

    def _name(self) -> str:
        raise NotImplementedError

    def _repr_png_(self) -> bytes:  # what a notebook shows
        figure, style = self._shown()
        buffer = io.BytesIO()
        with isolated(style):
            figure.savefig(buffer, format="png", dpi=100)
        return buffer.getvalue()

    def _shown(self) -> tuple[Figure, Style]:
        """The figure a notebook shows, and its style."""
        raise NotImplementedError


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

    def mark(self) -> None:
        """Draw the watermark over the plot box, once: the figure has been found changed."""
        watermark(self.axes, self.style)

    def check(self) -> list[lint.Issue]:
        """Lint the figure as it is now, including anything drawn on it since, and return
        the issues (also kept in `issues`)."""
        gt = self.values["graph_type"]
        with isolated(self.style), lint.font_messages() as font_problems:
            self.figure.canvas.draw()  # type: ignore[union-attr]
        self._font_problems = sorted({*self._font_problems, *font_problems})
        with isolated(self.style):
            self.issues = lint.check(
                self.figure,
                self.axes,
                fixed_limits=fixed_limits(gt),
                rows_dropped=self.data.rows_dropped,
                font_problems=self._font_problems,
                drawing=self._drawing,
            )
        return self.issues

    @property
    def warnings(self) -> list[str]:
        """Lint's findings, as messages."""
        return [i.message for i in self.issues]

    def record(self) -> dict[str, Any] | None:
        """The provenance record saved files carry, at the format's provenance.level; None
        with off."""
        level = self.values["format"]["provenance.level"]
        if level == "off":
            return None
        full = level == "full"
        record = ProvenanceRecord(
            provenance_level=level,
            forgegraph_version=__version__,
            created=created(),
            graphspec=recorded(self.spec, full),
            specs=self.specs,
            nonstandard=self.nonstandard,
            nonstandard_packs=self.nonstandard_packs or None,
            resolved=plain(self.values) if full else None,
            data=self.data.file if full else None,
            preprocessing=self.data.preprocessing if full else None,
        )
        return record.model_dump(exclude_none=True)

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


def recorded(spec: dict[str, Any], full: bool) -> dict[str, Any]:
    """A GraphSpec as provenance records it: below full, without the data's file and
    preprocessing reference."""
    spec = copy.deepcopy(spec)
    if full:
        return spec
    for section in ("fixed_parameters", "variable_parameters"):
        listed = spec.get(section)
        if isinstance(listed, dict) and isinstance(listed.get("data"), dict):
            listed["data"].pop("file", None)
            listed["data"].pop("preprocessing", None)
            if not listed["data"]:
                del listed["data"]
    return spec


def spec_record(kind: str, name: str, reg: Registry) -> dict[str, Any]:
    """A spec's name and version, and its pack's version if it's a pack's."""
    out = {"name": name, "version": reg.docs[kind][name]["version"]}
    pack = reg.pack_of(kind, name)
    if pack is not None:
        out["pack_version"] = reg.packs[pack].version
    return out


def used(values: dict[str, dict[str, Any]], reg: Registry) -> dict[str, Any]:
    """Each spec a graph is drawn with, by kind, as its name and version (and its pack's)."""
    chosen = values["graphspec"]
    out: dict[str, Any] = {}
    for kind in ("graph_type", "theme", "format"):
        out[kind] = spec_record(kind, chosen[f"specifications.{kind}"], reg)
    layers = values.get("layers") or {}
    if layers:
        out["layers"] = {
            n: {"type": v["type"], "version": reg.docs["layer"][v["type"]]["version"]}
            for n, v in layers.items()
        }
    return out


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
    resolved: dict[str, Any]  # explain's values, by kind, with where each came from
    values: dict[str, dict[str, Any]]
    frame: pd.DataFrame
    record: DataRecord
    module: Any  # the graph type's drawing module
    style: Style
    specs: dict[str, Any]  # each spec used, by kind: its name and version
    nonstandard_packs: list[str] = field(default_factory=list)  # used, not in the main config

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


def prepare(
    spec: dict[str, Any] | str | Path,
    data: pd.DataFrame | None = None,
    registry: Registry | None = None,
    format: dict[str, Resolved] | None = None,
) -> Prepared:
    """Check and resolve a GraphSpec, given as a file path or a document, and read its data:
    `data` if given, otherwise the Parquet file its data.file names. With `format` (resolved
    format values, as from a layout), those replace the format's."""
    # folder: where a relative data.file the document itself sets is found
    doc, reg, folder = load_document("graphspec", spec, registry)
    problems = validate("graphspec", doc, reg)
    if problems:
        raise SpecError(problems)
    problems = _named_problems(doc, reg)
    if problems:
        raise SpecError(problems)
    problems = drawing_problems(doc, reg)
    if problems:
        raise SpecError(problems)
    resolved = explain(doc, reg)
    if format is not None:
        resolved["format"] = dict(format)
    values = {kind: {p: r.value for p, r in v.items()} for kind, v in resolved.items()}
    frame, record = _data(doc, values, reg, data, folder)
    gt_name = values["graphspec"]["specifications.graph_type"]
    module = GRAPH_TYPES[_graph_type_root(gt_name, reg)]
    fixed = frozenset(p for p, r in resolved["theme"].items() if r.fixed)
    style = Style(values["theme"], values["format"], fixed)
    nonstandard = sorted(packs_used("graphspec", doc, reg) & reg.nonstandard)
    reg.use_fonts("graphspec", doc)
    return Prepared(
        doc, resolved, values, frame, record, module, style, used(values, reg), nonstandard
    )


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
    graph = Graph(p.doc, fig, ax, p.values, style, p.record, drawn.labelling, [], p.specs)
    graph.nonstandard_packs = p.nonstandard_packs
    graph.changed = bool(p.nonstandard_packs)  # drawn with a pack the main config doesn't list
    graph._drawing = list(drawn.warnings)
    graph._font_problems = font_problems
    graph.check()  # the one draw after layout, which the record of its pixels shares
    graph._snapshot = artists(fig)
    graph._drawn = pixel_hash(fig, style, redraw=False)
    fig.graph = graph  # from here on, drawing or saving the figure inspects it first
    return graph


def pixel_hash(fig: Figure, style: Style, *, redraw: bool = True) -> str:
    """A hash of the figure as its canvas draws it, without the watermark (drawn only once
    the figure is found changed). redraw False: of what the canvas drew last."""
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    if redraw:  # drawn into the canvas's renderer, but not through the canvas: no inspecting
        renderer.clear()
        with isolated(style), lint.font_messages():  # lint reports missing glyphs
            fig.draw(renderer)
    return hashlib.sha256(bytes(renderer.buffer_rgba())).hexdigest()


def fixed_limits(gt: dict[str, Any]) -> dict[str, tuple[float | None, float | None]]:
    """Each axis's set min and max (None where automatic), for lint."""
    return {a: (_limit(gt.get(f"axis.{a}.min")), _limit(gt.get(f"axis.{a}.max"))) for a in "xy"}


def _limit(value: Any) -> float | None:
    return None if value is None or value == NONE else float(value)


def _named_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems in the files a GraphSpec names, and the files they extend."""
    problems = []
    names = resolve("graphspec", doc, reg)
    for kind in ("graph_type", "theme", "format"):
        name = names[f"specifications.{kind}"][0]
        label = kind.replace("_", " ")
        while name not in (None, NONE):
            named = reg.docs[kind][name]
            problems += [f"{label} '{name}': {p}" for p in validate(kind, named, reg)]
            name = named.get("extends")
    return problems


def _graph_type_root(name: str, reg: Registry) -> str:
    doc = reg.docs["graph_type"][name]
    while doc.get("extends") not in (None, NONE):
        doc = reg.docs["graph_type"][doc["extends"]]
    return str(doc["name"])


def data_path(doc: dict[str, Any], reg: Registry, folder: Path) -> Path | None:
    """Where the Parquet file a GraphSpec's data.file names is, or None if it names none.
    `~` is the home folder; a relative path is found from the folder of the GraphSpec file
    that sets it: `folder` for doc itself, or the file of a GraphSpec it extends."""
    file = resolve("graphspec", doc, reg).get("data.file", (None,))[0]
    if file in (None, NONE):
        return None
    where = Path(str(file)).expanduser()
    if where.is_absolute():
        return where
    return (
        folder_of("graphspec", setter("graphspec", doc, reg, "data.file"), doc, reg, folder) / where
    )


def _data(
    doc: dict[str, Any],
    values: dict[str, dict[str, Any]],
    reg: Registry,
    data: pd.DataFrame | None,
    folder: Path,
) -> tuple[pd.DataFrame, DataRecord]:
    """The DataFrame to draw: the one given, or the one in the Parquet file data.file names."""
    preprocessing = values["graphspec"]["data.preprocessing"]
    reference = None if preprocessing in (None, NONE) else str(preprocessing)
    if data is not None:
        return data, DataRecord(preprocessing=reference, rows_read=len(data))
    where = data_path(doc, reg, folder)
    if where is None:
        raise SpecError(["data.file: None, so pass the data as a DataFrame"])
    if not where.is_file():
        raise SpecError([f"data.file: no file at '{where}'"])
    try:
        frame = pd.read_parquet(where)
    except Exception as e:  # pyarrow raises several kinds for a file that isn't Parquet
        problem = f"data.file: '{where}' isn't a Parquet file ({type(e).__name__})"
        raise SpecError([problem]) from None
    file = str(values["graphspec"]["data.file"])
    return frame, DataRecord(file=file, preprocessing=reference, rows_read=len(frame))


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
