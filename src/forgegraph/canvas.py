"""The escape hatch (architecture D10): a canvas in a theme and format, for drawing what no
graph type can.

`blank(theme, format)` gives a figure and one Axes in the theme and format, checked against
the configs as a GraphSpec's are; draw inside `with canvas.drawing():` so what's drawn takes
the theme's settings, and the Axes cycles through the theme's palette. Whatever is drawn on
it is non-standard: every drawing and saved file carries the theme's watermark, and the
provenance record says so.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from forgegraph.drawing import export
from forgegraph.drawing.errors import LayoutError
from forgegraph.drawing.figure import (
    GraphFigure,
    layout,
    new_figure,
    watermark,
)
from forgegraph.drawing.style import Style, isolated
from forgegraph.drawn import Saved, SpecError
from forgegraph.spec.access import name_problems, packs_used, use_fonts
from forgegraph.spec.provenance import plain, record
from forgegraph.spec.registry import Registry, registry_for
from forgegraph.spec.resolve import resolve
from forgegraph.spec.validate import validate


@dataclass
class Blank(Saved):
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
        """A canvas is always non-standard."""
        return True

    def mark(self) -> None:
        """Draw the watermark over the plot box, once."""
        watermark(self.axes, self.style)

    def saving(self) -> AbstractContextManager[None]:
        """The matplotlib settings files are saved with."""
        return isolated(self.style)

    def drawing(self) -> AbstractContextManager[None]:
        """The theme's and format's matplotlib settings, for drawing on the canvas."""
        return isolated(self.style)

    def record(self) -> dict[str, Any] | None:
        """The provenance record saved files carry; None with provenance.level off."""
        level = self.values["format"]["provenance.level"]
        if level == "off":
            return None
        return record(
            level,
            specs=self.specs,
            nonstandard=True,
            nonstandard_packs=self.nonstandard_packs or None,
            resolved=plain(self.values) if level == "full" else None,
        )

    def save_all(self, stem: str | Path) -> list[Path]:
        """Save every file type the format lists but html, as stem.png and so on."""
        return self._write(
            Path(stem), [k for k in self.values["format"]["output.file_types"] if k != "html"]
        )

    def _write(self, stem: Path, kinds: list[str]) -> list[Path]:
        """Lay the figure out, then save each file type."""
        with isolated(self.style):
            try:
                layout(self.figure, self.axes, self.style)
            except LayoutError as e:
                raise SpecError([str(e)]) from None
            dpi = int(self.values["format"]["output.dpi"])
            return [
                export.save(self.figure, stem.with_name(f"{stem.name}.{k}"), dpi) for k in kinds
            ]

    def _name(self) -> str:
        return "canvas"

    def _shown(self) -> tuple[Figure, Style]:
        return self.figure, self.style


def _registry(folder: str | Path | None) -> Registry:
    return registry_for(Path(folder or Path.cwd()).resolve())


def _values(kind: str, name: str, reg: Registry) -> dict[str, Any]:
    """A theme's or format's values, checked: it exists, it may be used, and it's valid."""
    problems = [f"{kind}: {p}" for p in name_problems(kind, name, reg)]
    if not problems:
        problems = [f"{kind} '{name}': {p}" for p in validate(kind, reg.docs[kind][name], reg)]
    if problems:
        raise SpecError(problems)
    return resolve(kind, reg.docs[kind][name], reg).plain()


def blank(
    theme: str,
    format: str,
    folder: str | Path | None = None,
    registry: Registry | None = None,
) -> Blank:
    """A canvas in this theme and format, for drawing what no graph type can. The specs are
    checked against `registry` if given (as fg.render's are), otherwise against the configs
    found from folder (default: the working folder)."""
    reg = registry or _registry(folder)
    values = {"theme": _values("theme", theme, reg), "format": _values("format", format, reg)}
    style = Style(values["theme"], values["format"])
    with isolated(style):
        fig, ax = new_figure(style)
    ax.set_prop_cycle(color=style.series_colors())
    canvas = Blank(fig, ax, style, values)
    canvas.specs = {k: reg.spec_record(k, n) for k, n in (("theme", theme), ("format", format))}
    used = packs_used("theme", reg.docs["theme"][theme], reg)
    used |= packs_used("format", reg.docs["format"][format], reg)
    use_fonts("theme", reg.docs["theme"][theme], reg)
    canvas.nonstandard_packs = sorted(used & reg.nonstandard)
    fig.graph = canvas
    return canvas
