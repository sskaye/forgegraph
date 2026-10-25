"""What a drawn graph, layout and canvas share: SpecError, inspecting a rendered figure
(Inspected) and its pixels (pixel_hash), and saving by path (Saved)."""

from __future__ import annotations

import hashlib
import io
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

from matplotlib.figure import Figure

from forgegraph.drawing import lint
from forgegraph.drawing.figure import GraphFigure, artists
from forgegraph.drawing.style import Style, isolated
from forgegraph.spec.common import ProblemsError


class SpecError(ProblemsError):
    """A GraphSpec that can't be drawn; `problems` lists each one."""


class Inspected:
    """Whether a rendered figure is still as ForgeGraph drew it, for graphs and layout tabs:
    the same artists (_snapshot), drawing the same pixels (_drawn). Once it isn't, it stays
    non-standard, and every drawing of it carries the watermark. Drawing or saving the
    figure, by any route, inspects it first."""

    changed: bool
    nonstandard_packs: list[str]
    _snapshot: tuple[int, ...]
    _drawn: str
    _held: bool
    _font_problems: list[str]

    def _shown(self) -> tuple[Figure, Style]:
        """The figure, and the style it's drawn in."""
        raise NotImplementedError

    def check(self) -> list[lint.Issue]:
        """Lint the figure as it is now, and return the issues."""
        raise NotImplementedError

    def seal(
        self, figure: GraphFigure, font_problems: list[str], nonstandard_packs: list[str]
    ) -> None:
        """Finish rendering: keep the font problems drawing found and the packs used that the
        main config doesn't list (which make it non-standard), lint it in the one draw after
        layout, which the record of its pixels shares, then record its artists and pixels.
        From here on, drawing or saving the figure inspects it first."""
        self.nonstandard_packs = nonstandard_packs
        self.changed = bool(nonstandard_packs)
        self._font_problems = font_problems
        self.check()
        self._snapshot = artists(figure)
        self._drawn = pixel_hash(figure, self._shown()[1], redraw=False)
        figure.graph = self

    def _lint_draw(self) -> None:
        """Draw the figure for lint, adding any font problems drawing it finds."""
        figure, style = self._shown()
        with isolated(style), lint.font_messages() as font_problems:
            figure.canvas.draw()  # type: ignore[union-attr]
        self._font_problems = sorted({*self._font_problems, *font_problems})

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


def pixel_hash(fig: Figure, style: Style, *, redraw: bool = True) -> str:
    """A hash of the figure as its canvas draws it, without the watermark (drawn only once
    the figure is found changed). redraw False: of what the canvas drew last."""
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    if redraw:  # drawn into the canvas's renderer, but not through the canvas: no inspecting
        renderer.clear()
        with isolated(style), lint.font_messages():  # lint reports missing glyphs
            fig.draw(renderer)
    return hashlib.sha256(bytes(renderer.buffer_rgba())).hexdigest()
