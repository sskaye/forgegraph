"""ForgeGraph's figures: sized by the format, laid out by drawing.layout.

The figure is a GraphFigure on a GraphCanvas, so that whatever draws or saves it, ForgeGraph
or matplotlib directly (`figure.savefig`, a notebook), first checks whether it's still as
ForgeGraph drew it, draws the watermark if it isn't, and embeds the provenance record in
what it saves (architecture D10, D13).
"""

from __future__ import annotations

import warnings
from typing import Any, cast

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch
from matplotlib.text import Text
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D, ScaledTranslation

from forgegraph.drawing import export
from forgegraph.drawing.style import MM_PER_INCH, Style, isolated

WATERMARK = "forgegraph-watermark"


def inches(value: object) -> float | None:
    """A format's size, in mm or auto, in inches (None for auto)."""
    return None if value == "auto" else float(value) / MM_PER_INCH  # type: ignore[arg-type]


class GraphFigure(Figure):
    """A ForgeGraph figure. Once rendering has finished, `graph` is what was drawn on it (a
    Graph, or a layout's tab), and every drawing of the figure carries the watermark if that
    has found it changed."""

    graph: Any = None
    footnote: Text | None = None  # small text at the bottom right, below everything else

    def draw(self, renderer: Any) -> None:
        graph = self.graph
        if graph is not None and graph.changed:
            graph.mark()
        super().draw(renderer)


def artists(fig: Figure) -> tuple[int, ...]:
    """The identities of what the figure draws, but its watermark: what drawing finished
    with, to compare with later."""
    return tuple(
        id(a)
        for a in [*(c for ax in fig.axes for c in ax.get_children()), *fig.get_children()]
        if a.get_gid() != WATERMARK
    )


def watermarked(ax: Axes) -> bool:
    return any(a.get_gid() == WATERMARK for a in ax.get_children())


def watermark(ax: Axes, style: Style) -> None:
    """Draw the watermark over the plot box, once."""
    if not watermarked(ax):
        ax.add_artist(Watermark(ax, style))


class TileAxes(Axes):
    """A layout tile's Axes, drawn in its own tile's matplotlib settings, since the tiles on
    one figure may use different themes."""

    tile_style: Style | None = None

    def draw(self, renderer: Any) -> None:
        if self.tile_style is None:
            super().draw(renderer)
            return
        with isolated(self.tile_style):
            super().draw(renderer)


class GraphCanvas(FigureCanvasAgg):
    """The canvas of a GraphFigure. Drawing or saving it first checks whether the figure is
    still as ForgeGraph drew it; saving it also embeds the Graph's provenance record, in the
    theme's settings, unless the caller set the record's own metadata key."""

    def draw(self) -> None:
        graph = getattr(self.figure, "graph", None)
        if graph is not None:
            graph.inspect()
        super().draw()

    def print_figure(self, filename: Any, *args: Any, **kwargs: Any) -> Any:
        graph = getattr(self.figure, "graph", None)
        if graph is None:
            return super().print_figure(filename, *args, **kwargs)
        record = graph.record()  # inspects the figure first, so the record and image agree
        with graph.saving(), warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Unknown infodict keyword")  # pdf's key
            kind = export.kind_of(filename, kwargs.get("format"))
            kwargs = export.with_record(kind, kwargs, record)
            return super().print_figure(filename, *args, **kwargs)


def canvas_figure(width: float, height: float) -> GraphFigure:
    """A GraphFigure on its GraphCanvas, this size in inches until it's laid out."""
    fig = GraphFigure(figsize=(width, height))
    GraphCanvas(fig)  # without pyplot there's no canvas, and text can't be measured
    return fig


def new_figure(style: Style) -> tuple[GraphFigure, Axes]:
    """A figure with a drawing canvas and one Axes, sized provisionally until it's laid out
    (drawing.layout.layout)."""
    width = inches(style.format["figure.width"])
    height = inches(style.format["figure.height"])
    aspect = float(style.theme["plot_area.aspect"])
    w = width if width is not None else height * aspect  # type: ignore[operator]
    h = height if height is not None else w / aspect
    fig = canvas_figure(w, h)
    ax = fig.add_axes((0.2, 0.2, 0.6, 0.6))
    return fig, ax


class Watermark(PathPatch):
    """The theme's watermark across the plot box: its letters' outlines, centred on the box and
    spanning watermark.span of the box's width or height, whichever they reach first. It takes
    its size, color and opacity from the theme each time it's drawn, so it follows the plot box
    at any size or resolution."""

    def __init__(self, ax: Axes, style: Style) -> None:
        t = style.theme
        prop = style.font(1.0, "watermark.weight")  # 1 pt: draw() scales it to the box
        turn = Affine2D().rotate_deg(float(t["watermark.angle"]))
        outline = TextPath((0, 0), str(t["watermark.text"]), prop=prop).transformed(turn)
        if np.asarray(outline.vertices).size == 0:  # the theme check's backstop
            raise ValueError(f"watermark.text: {str(t['watermark.text'])!r} has no letters to draw")
        super().__init__(outline, edgecolor="none", zorder=100, clip_on=False, gid=WATERMARK)
        self._box, self._style = ax, style

    def draw(self, renderer: Any) -> None:
        ax, style = self._box, self._style
        fig = ax.figure
        ink = self.get_path().get_extents()  # at 1 pt, turned
        box_w = ax.bbox.width * 72 / fig.dpi  # points
        box_h = ax.bbox.height * 72 / fig.dpi
        size = float(style.theme["watermark.span"]) * min(box_w / ink.width, box_h / ink.height)
        centre = ((ink.x0 + ink.x1) / 2, (ink.y0 + ink.y1) / 2)
        self.set_transform(
            Affine2D().translate(-centre[0], -centre[1]).scale(size / 72)
            + fig.dpi_scale_trans
            + ScaledTranslation(0.5, 0.5, cast(Any, ax.transAxes))  # the plot box's centre
        )
        self.set_facecolor(style.color("watermark.color"))
        self.set_alpha(float(style.theme["watermark.opacity"]))
        super().draw(renderer)
