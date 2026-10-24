"""The escape hatch (architecture D10): a canvas in a theme and format, for drawing what no
graph type can.

`blank(theme, format)` gives a figure and one Axes in the theme and format, checked against
the configs as a GraphSpec's are; draw inside `with canvas.drawing():` so what's drawn takes
the theme's settings, and the Axes cycles through the theme's palette. Whatever is drawn on
it is non-standard: every drawing and saved file carries the theme's watermark, and the
provenance record says so.
"""

from __future__ import annotations

import io
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from matplotlib.axes import Axes

from forgegraph import __version__
from forgegraph.drawing import export
from forgegraph.drawing.figure import (
    GraphFigure,
    LayoutError,
    Watermark,
    _watermarked,
    layout,
    new_figure,
)
from forgegraph.drawing.style import PALETTES, Style, isolated
from forgegraph.graph import SpecError, _created, _plain, spec_record
from forgegraph.spec.documents import (
    Registry,
    name_problems,
    packs_used,
    registry_for,
    resolve,
    validate,
)
from forgegraph.spec.provenance import ProvenanceRecord


@dataclass
class Blank:
    """A themed canvas. Draw on `axes` with matplotlib; `save` lays the figure out with
    ForgeGraph's margins and saves it in the format's file types, watermarked."""

    figure: GraphFigure
    axes: Axes
    style: Style
    values: dict[str, dict[str, Any]]  # the theme's and format's
    specs: dict[str, Any] = field(default_factory=dict)  # each spec used: name and version
    changed: bool = True  # always non-standard, so always watermarked
    nonstandard_packs: list[str] = field(default_factory=list)  # used, not in the main config

    def inspect(self) -> bool:
        return True

    def mark(self) -> None:
        if not _watermarked(self.axes):
            self.axes.add_artist(Watermark(self.axes, self.style))

    def saving(self) -> AbstractContextManager[None]:
        return isolated(self.style)

    def drawing(self) -> AbstractContextManager[None]:
        """The theme's and format's matplotlib settings, for drawing on the canvas."""
        return isolated(self.style)

    def record(self) -> dict[str, Any] | None:
        """The provenance record saved files carry; None with provenance.level off."""
        level = self.values["format"]["provenance.level"]
        if level == "off":
            return None
        record = ProvenanceRecord(
            provenance_level=level,
            forgegraph_version=__version__,
            created=_created(),
            specs=self.specs,
            nonstandard=True,
            nonstandard_packs=self.nonstandard_packs or None,
            resolved=_plain(self.values) if level == "full" else None,
        )
        return record.model_dump(exclude_none=True)

    def save(self, path: str | Path) -> list[Path]:
        """Save the canvas: a path with a suffix saves that file type; without one, every file
        type the format lists, except html."""
        target = Path(path)
        kinds = [target.suffix.lstrip(".")] if target.suffix else self._kinds()
        stem = target.with_suffix("") if target.suffix else target
        with isolated(self.style):
            try:
                layout(self.figure, self.axes, self.style)
            except LayoutError as e:
                raise SpecError([str(e)]) from None
            dpi = int(self.values["format"]["output.dpi"])
            return [
                export.save(self.figure, stem.with_name(f"{stem.name}.{k}"), dpi) for k in kinds
            ]

    def _kinds(self) -> list[str]:
        return [k for k in self.values["format"]["output.file_types"] if k != "html"]

    def _repr_png_(self) -> bytes:
        buffer = io.BytesIO()
        with isolated(self.style):
            self.figure.savefig(buffer, format="png", dpi=100)
        return buffer.getvalue()


def _registry(folder: str | Path | None) -> Registry:
    return registry_for(Path(folder or Path.cwd()).resolve())


def _values(kind: str, name: str, reg: Registry) -> dict[str, Any]:
    """A theme's or format's values, checked: it exists, it may be used, and it's valid."""
    problems = [f"{kind}: {p}" for p in name_problems(kind, name, reg)]
    if not problems:
        problems = [f"{kind} '{name}': {p}" for p in validate(kind, reg.docs[kind][name], reg)]
    if problems:
        raise SpecError(problems)
    return {p: v for p, (v, _) in resolve(kind, reg.docs[kind][name], reg).items()}


def blank(theme: str, format: str, folder: str | Path | None = None) -> Blank:
    """A canvas in this theme and format, for drawing what no graph type can. The configs
    that apply are found from folder (default: the working folder)."""
    reg = _registry(folder)
    values = {"theme": _values("theme", theme, reg), "format": _values("format", format, reg)}
    style = Style(values["theme"], values["format"])
    with isolated(style):
        fig, ax = new_figure(style)
    ax.set_prop_cycle(color=_colors(values["theme"]))
    canvas = Blank(fig, ax, style, values)
    canvas.specs = {k: spec_record(k, n, reg) for k, n in (("theme", theme), ("format", format))}
    used = packs_used("theme", reg.docs["theme"][theme], reg)
    used |= packs_used("format", reg.docs["format"][format], reg)
    canvas.nonstandard_packs = sorted(used & reg.nonstandard)
    fig.graph = canvas
    return canvas


def _colors(theme: dict[str, Any]) -> list[str]:
    colors = theme["series.colors"]
    return list(PALETTES[colors]) if isinstance(colors, str) else list(colors)
