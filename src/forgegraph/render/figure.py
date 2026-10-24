"""Figures sized by the format, laid out by what's visible.

Width and height are in mm. ForgeGraph lays the figure out itself rather than with
matplotlib's layout engines, which space text by its box (see forgegraph.render.text): the
plot box is placed so that everything drawn, measured to its letters and lines, sits MARGIN
from each edge of the figure. With both sizes given, the plot box takes the space left; with
one auto, the plot box keeps the theme's plot_area.aspect and the figure is fitted around it.

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
from matplotlib.transforms import Affine2D, Bbox, ScaledTranslation

from forgegraph.render import export, spacing, text
from forgegraph.render.key import keys
from forgegraph.render.markup import literal
from forgegraph.render.style import MM_PER_INCH, Style, isolated

MARGIN_IN = 0.04  # space kept between what's drawn and the figure's edges
WATERMARK = "forgegraph-watermark"
FOOTNOTE = "forgegraph-footnote"


class LayoutError(ValueError):
    """The format is too small for what has to be drawn around the plot box."""


def _inches(value: object) -> float | None:
    return None if value == "auto" else float(value) / MM_PER_INCH  # type: ignore[arg-type]


PASSES = 6  # layout passes; if none settles, the last two passes' most room is used


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


def _watermarked(ax: Axes) -> bool:
    return any(a.get_gid() == WATERMARK for a in ax.get_children())


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


def new_figure(style: Style) -> tuple[GraphFigure, Axes]:
    """A figure with a drawing canvas and one Axes, sized provisionally until `layout()`."""
    width = _inches(style.format["figure.width"])
    height = _inches(style.format["figure.height"])
    aspect = float(style.theme["plot_area.aspect"])
    w = width if width is not None else height * aspect  # type: ignore[operator]
    h = height if height is not None else w / aspect
    fig = GraphFigure(figsize=(w, h))
    GraphCanvas(fig)  # without pyplot there's no canvas, and text can't be measured
    ax = fig.add_axes((0.2, 0.2, 0.6, 0.6))
    return fig, ax


def tick_marks(ax: Axes, renderer: Any) -> list[Bbox]:
    """The Axes' tick marks in view, in display pixels."""
    out = []
    for axis in (ax.xaxis, ax.yaxis):
        lo, hi = sorted(axis.get_view_interval())
        for tick in [*axis.get_major_ticks(), *axis.get_minor_ticks()]:
            if not lo <= tick.get_loc() <= hi:
                continue
            for line in (tick.tick1line, tick.tick2line):
                if line.get_visible():
                    out.append(line.get_window_extent(renderer))
    return out


def texts_of(ax: Axes) -> list[Text]:
    """The Axes' titles, its texts and its tick labels in view."""
    out: list[Text] = [ax.title, ax.xaxis.label, ax.yaxis.label, *ax.texts]
    out += [ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()]  # e.g. a date axis's year
    for axis in (ax.xaxis, ax.yaxis):
        lo, hi = sorted(axis.get_view_interval())
        for tick in axis.get_major_ticks():
            if lo <= tick.get_loc() <= hi:
                out += [tick.label1, tick.label2]
    return out


def visible_extent(ax: Axes, renderer: Any) -> Bbox:
    """Everything drawn for an Axes and any Axes inside it, measured to letters and lines, in
    display pixels. The watermark, drawn over the plot box, isn't included."""
    boxes = []
    for each in spacing.axes_family(ax):
        boxes.append(each.bbox)
        for side, spine in each.spines.items():  # a box line is centred on the box's edge
            if spine.get_visible():
                half = spine.get_linewidth() / 2 * ax.figure.dpi / 72  # type: ignore[union-attr]
                grow = {
                    "left": (half, 0, 0, 0),
                    "right": (0, 0, half, 0),
                    "bottom": (0, half, 0, 0),
                    "top": (0, 0, 0, half),
                }.get(side, (half, half, half, half))  # a color bar's outline: every side
                b = each.bbox
                boxes.append(
                    Bbox.from_extents(
                        b.x0 - grow[0], b.y0 - grow[1], b.x1 + grow[2], b.y1 + grow[3]
                    )
                )
        boxes += tick_marks(each, renderer)
        for t in texts_of(each):
            if t.get_visible() and t.get_text().strip() and t.get_gid() != WATERMARK:
                boxes.append(text.footprint(t, renderer))
        boxes += [k.bbox() for k in keys(each) if k.outside]  # its frame, drawn or not
    return Bbox.union([b for b in boxes if b.width > 0 or b.height > 0])


def layout(fig: Figure, ax: Axes, style: Style) -> None:
    """Size the figure and place the plot box from what's drawn around it. Each pass measures
    the room needed on each side and lays out again; it has settled when a pass changes the
    figure's size by under 0.001 in and moves the box by under 0.0001 of the figure. Tick
    labels can keep it from settling, alternating between two states (a taller box gets more,
    wider labels, which shrink the box again), so after PASSES unsettled passes it lays out
    once more with, on each side, the most room either of the last two passes needed: both
    states' labels fit. Earlier passes, made while the figure was still far from its size,
    don't count."""
    width = _inches(style.format["figure.width"])
    height = _inches(style.format["figure.height"])
    aspect = float(style.theme["plot_area.aspect"])
    last = both = (0.0, 0.0, 0.0, 0.0)
    for _ in range(PASSES):
        spacing.apply(ax, style)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
        dpi = fig.dpi
        extent, box = visible_extent(ax, renderer), ax.bbox
        room = (
            (box.x0 - extent.x0) / dpi,
            (extent.x1 - box.x1) / dpi,
            (box.y0 - extent.y0) / dpi + footnote_room(fig),
            (extent.y1 - box.y1) / dpi,
        )
        if _place(fig, ax, room, width, height, aspect):
            break
        both, last = tuple(max(a, b) for a, b in zip(last, room, strict=True)), room
    else:
        _place(fig, ax, both, width, height, aspect)
    spacing.apply(ax, style)
    place_footnote(fig, MARGIN_IN, MARGIN_IN)


def add_footnote(fig: Figure, words: str, style: Style) -> Text:
    """The figure's footnote, in the theme's footnote look; layout places it."""
    prop = text.font(
        str(style.theme["font.family"]), style.pt("footnote.size"), style.weight("font.weight")
    )
    note = fig.text(
        0,
        0,
        literal(words),
        fontproperties=prop,
        color=style.color("footnote.color"),
        ha="right",
        va="baseline",
        gid=FOOTNOTE,
    )
    note.gap = style.pt("footnote.gap")  # type: ignore[attr-defined]
    fig.footnote = note  # type: ignore[attr-defined]
    return note


def footnote_room(fig: Figure) -> float:
    """The room a figure's footnote needs below everything else, in inches: its gap and its
    letters."""
    note = getattr(fig, "footnote", None)
    if note is None:
        return 0.0
    e = text.edges(note.get_text(), note.get_fontproperties())
    return (float(note.gap) + e.top + e.bottom) / 72


def place_footnote(fig: Figure, right: float, bottom: float) -> None:
    """Put the footnote's letters `right` and `bottom` inches from the figure's bottom right."""
    note = getattr(fig, "footnote", None)
    if note is None:
        return
    w, h = fig.get_size_inches()
    e = text.edges(note.get_text(), note.get_fontproperties())
    cut = (e.advance - e.right) / 72  # its box reaches past its last letter by this much
    note.set_position((1 - (right - cut) / w, (bottom + e.bottom / 72) / h))


def _place(
    fig: Figure,
    ax: Axes,
    room: tuple[float, ...],
    width: float | None,
    height: float | None,
    aspect: float,
) -> bool:
    """Size the figure and place the plot box with this room (left, right, bottom, top, in
    inches) around it. Returns whether nothing moved: the layout has settled."""
    left, right, bottom, top = room
    around_w, around_h = left + right + 2 * MARGIN_IN, bottom + top + 2 * MARGIN_IN
    if width is not None:
        box_w = width - around_w
        box_h = height - around_h if height is not None else box_w / aspect
    else:
        assert height is not None
        box_h = height - around_h
        box_w = box_h * aspect
    if box_w <= 0 or box_h <= 0:
        raise LayoutError(
            "size: too small for the titles, tick labels and keys around the plot box; "
            "make the format larger or its base font smaller"
        )
    fig_w = width if width is not None else box_w + around_w
    fig_h = height if height is not None else box_h + around_h
    position = (
        (left + MARGIN_IN) / fig_w,
        (bottom + MARGIN_IN) / fig_h,
        box_w / fig_w,
        box_h / fig_h,
    )
    old_size, old_position = fig.get_size_inches(), ax.get_position().bounds
    fig.set_size_inches(fig_w, fig_h)
    ax.set_position(position)
    moved = max(abs(a - b) for a, b in zip(old_position, position, strict=True))
    return abs(old_size[0] - fig_w) < 1e-3 and abs(old_size[1] - fig_h) < 1e-3 and moved < 1e-4


class Watermark(PathPatch):
    """The theme's watermark across the plot box: its letters' outlines, centred on the box and
    spanning watermark.span of the box's width or height, whichever they reach first. It takes
    its size, color and opacity from the theme each time it's drawn, so it follows the plot box
    at any size or resolution."""

    def __init__(self, ax: Axes, style: Style) -> None:
        t = style.theme
        prop = text.font(str(t["font.family"]), 1.0, style.weight("watermark.weight"))
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
