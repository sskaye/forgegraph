"""Keys: a legend naming the series, or a style key explaining line styles and markers.

ForgeGraph lays a key out itself, with every gap measured to the letters (see
forgegraph.drawing.text): an optional title, then one row per entry, a line sample then the
entry's name. The theme's legend parameters set the border, the gap inside it (the same on
every side), the gaps between title and rows and between rows, the sample's length and its
gap to the name, the gap from the plot box, and the names' and title's text styles.

A `Key` is measured when it's made and drawn when it's placed: inside the plot box at one of
POSITIONS (the labelling code tries the GraphSpec's legend.key.positions in order until the
key is clear of the data), or outside it (place_outside): above the plot box, under the
title; below the x-axis title; or to the plot box's right. Layout makes room for a key
outside, which follows the plot box (and, below it, the x-axis title).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Bbox, ScaledTranslation, Transform

from forgegraph.drawing import text
from forgegraph.drawing.marks import Bars
from forgegraph.drawing.style import Style

# Each position: where it is on the plot box (axes fraction), and which way the key extends
# from it: right (1), left (-1) or centred (0); down (-1), up (1) or centred (0).
POSITIONS = {
    "top_left": (0.0, 1.0, 1, -1),
    "top_center": (0.5, 1.0, 0, -1),
    "top_right": (1.0, 1.0, -1, -1),
    "bottom_left": (0.0, 0.0, 1, 1),
    "bottom_center": (0.5, 0.0, 0, 1),
    "bottom_right": (1.0, 0.0, -1, 1),
    "right_top": (1.0, 1.0, -1, -1),
    "right_center": (1.0, 0.5, -1, 0),
    "right_bottom": (1.0, 0.0, -1, 1),
}


@dataclass(frozen=True)
class Entry:
    name: str
    handle: Line2D | Bars  # a line or bars in the entry's style: its sample copies it


class Key:
    """A key's layout, in points from its top-left corner (y grows downward)."""

    def __init__(self, entries: list[Entry], title: str | None, style: Style) -> None:
        self.entries, self.title, self.style = entries, title, style
        self.names = style.text("legend.key.label")
        self.heading = style.text("legend.key.title")
        self.font, self.title_font = self.names.font, self.heading.font
        self.border = style.line("legend.key.border")
        self.pad = style.pt("legend.key.gap.inner")
        self.sample = style.pt("legend.key.sample.length")
        self.sample_gap = style.pt("legend.key.sample.gap")
        names = [e.name for e in entries]
        self.row = text.row(names, self.font)
        self.name_edges = [text.edges(n, self.font) for n in names]
        self.title_edges = text.edges(title, self.title_font) if title else None
        names_w = max((e.width for e in self.name_edges), default=0.0)
        self.names_w = names_w
        content_w = self.sample + self.sample_gap + names_w
        if self.title_edges is not None:
            content_w = max(content_w, self.title_edges.width)
        self.content_w = content_w
        self.width = 2 * self.pad + content_w
        rows = len(entries) * self.row.height + max(0, len(entries) - 1) * style.pt(
            "legend.key.gap.row"
        )
        title_h = self.title_edges.height + (self.heading.gap or 0.0) if self.title_edges else 0
        self.height = 2 * self.pad + title_h + rows
        self.frame = self.border.visible
        self.artists: list[Any] = []
        self.position: str | None = None
        self.outside = False
        self._shift = Affine2D()  # below the plot box: down past the x-axis title (follow)
        self._place: Transform | None = None
        self._ax: Axes | None = None

    def place(self, ax: Axes, position: str) -> None:
        """Draw the key inside the plot box at a position, legend.key.gap.outer in from it."""
        cx, cy, sx, sy = POSITIONS[position]
        inset = self.style.pt("legend.key.gap.outer")
        left = {1: inset, 0: -self.width / 2, -1: -inset - self.width}[sx]  # from the anchor
        top = {-1: -inset, 0: self.height / 2, 1: inset + self.height}[sy]
        self._draw(ax, position, (cx, cy), left, top, outside=False)

    def place_outside(self, ax: Axes, position: str) -> None:
        """Draw the key outside the plot box, legend.key.gap.outer from it: top_* above it
        (the title moves up), bottom_* below the x-axis title, right_* to its right."""
        cx, cy, _, _ = POSITIONS[position]
        inset = self.style.pt("legend.key.gap.outer")
        side, along = position.split("_")
        if side == "right":
            left = inset
            top = {"top": 0.0, "center": self.height / 2, "bottom": self.height}[along]
        else:
            left = {"left": 0.0, "center": -self.width / 2, "right": -self.width}[along]
            top = inset + self.height if side == "top" else -inset
        self._draw(ax, position, (cx, cy), left, top, outside=True)
        self.follow(ax)

    def follow(self, ax: Axes) -> None:
        """Below the plot box, move the key down past the x-axis's tick labels and title as
        they are now: layout calls this on every pass."""
        if not (self.outside and self.position and self.position.startswith("bottom")):
            return
        boxes = [ax.xaxis.get_tightbbox()]
        if ax.xaxis.label.get_text():
            boxes.append(ax.xaxis.label.get_window_extent())
        lowest = min((b.y0 for b in boxes if b is not None), default=ax.bbox.y0)
        depth = max(0.0, ax.bbox.y0 - lowest) * 72 / ax.figure.dpi  # type: ignore[union-attr]
        self._shift.clear().translate(0, -depth)

    def _draw(
        self,
        ax: Axes,
        position: str,
        anchor: tuple[float, float],
        left: float,
        top: float,
        outside: bool,
    ) -> None:
        self.remove()
        fig = ax.figure
        to_display = (
            Affine2D().translate(left, top)
            + self._shift
            + Affine2D().scale(1 / 72)
            + fig.dpi_scale_trans  # type: ignore[union-attr]
            + ScaledTranslation(*anchor, cast(Any, ax.transAxes))  # moves with the plot box
        )
        self._place, self.position, self.outside, self._ax = to_display, position, outside, ax
        setattr(ax, _PLACED, [*keys(ax), self])
        fill = self.style.color("legend.key.background")
        if self.frame or fill != "none":
            b = self.border
            self._add(
                ax,
                Rectangle(
                    (0, -self.height),
                    self.width,
                    self.height,
                    transform=to_display,
                    facecolor=fill,
                    edgecolor=b.color if self.frame else "none",
                    linewidth=b.width if self.frame else 0,
                    linestyle=b.style if self.frame else "solid",
                    joinstyle=cast(Any, b.join),
                ),
            )
        y = -self.pad  # the top of what comes next
        if self.title_edges is not None and self.title:
            e = self.title_edges
            align = self.heading.alignment or "left"
            free = self.content_w - e.width
            shift = {"left": 0.0, "center": free / 2, "right": free}[align]
            self._add(
                ax,
                Text(
                    self.pad + shift - e.left,
                    y - e.top,
                    self.title,
                    fontproperties=self.title_font,
                    color=self.heading.color,
                    va="baseline",
                    ha="left",
                    transform=to_display,
                ),
            )
            y -= e.height + (self.heading.gap or 0.0)
        row_gap = self.style.pt("legend.key.gap.row")
        align = self.names.alignment or "left"
        for entry, e in zip(self.entries, self.name_edges, strict=True):
            baseline = y - self.row.top
            centre = baseline + self.row.middle
            h = entry.handle
            if isinstance(h, Bars):  # a swatch of the bar, no taller than the name beside it
                tall = min(h.width, self.row.height)
                self._add(
                    ax,
                    Rectangle(
                        (self.pad, centre - tall / 2),
                        self.sample,
                        tall,
                        transform=to_display,
                        facecolor=h.color,
                        edgecolor=h.edge,
                        linewidth=h.edge_width if h.edge != "none" else 0.0,
                        alpha=h.get_alpha(),
                    ),
                )
            else:
                self._sample(ax, h, centre, to_display)
            shift = {"left": 0.0, "center": 0.5, "right": 1.0}[align] * (self.names_w - e.width)
            self._add(
                ax,
                Text(
                    self.pad + self.sample + self.sample_gap + shift - e.left,
                    baseline,
                    entry.name,
                    fontproperties=self.font,
                    color=self.names.color,
                    va="baseline",
                    ha="left",
                    transform=to_display,
                ),
            )
            y = baseline - self.row.bottom - row_gap

    def _sample(self, ax: Axes, h: Line2D, centre: float, to_display: Transform) -> None:
        """A line sample in the handle's style, with its marker at the middle."""
        self._add(
            ax,
            Line2D(
                [self.pad, self.pad + self.sample],
                [centre, centre],
                transform=to_display,
                color=h.get_color(),
                linestyle=h.get_linestyle(),
                linewidth=h.get_linewidth(),
                marker="none",
                solid_capstyle="butt",  # ends exactly where the sample does
                dash_capstyle="butt",
                alpha=h.get_alpha(),
            ),
        )
        if h.get_marker() not in ("None", "none", None, ""):
            self._add(
                ax,
                Line2D(
                    [self.pad + self.sample / 2],
                    [centre],
                    transform=to_display,
                    linestyle="none",
                    marker=h.get_marker(),
                    markersize=h.get_markersize(),
                    markerfacecolor=h.get_markerfacecolor(),
                    markeredgecolor=h.get_markeredgecolor(),
                    markeredgewidth=h.get_markeredgewidth(),
                    alpha=h.get_alpha(),
                ),
            )

    def _add(self, ax: Axes, artist: Any) -> None:
        artist.set_clip_on(False)
        artist.set_gid(KEY)
        ax.add_artist(artist)  # not add_line or add_patch: a key mustn't change the data limits
        self.artists.append(artist)

    def bbox(self) -> Bbox:
        """The key's frame (drawn or not), in display pixels."""
        assert self._place is not None, "place the key first"
        corners = self._place.transform([(0, 0), (self.width, -self.height)])
        return Bbox.from_extents(
            min(corners[:, 0]), min(corners[:, 1]), max(corners[:, 0]), max(corners[:, 1])
        )

    def remove(self) -> None:
        for artist in self.artists:
            artist.remove()
        if self._ax is not None:
            setattr(self._ax, _PLACED, [k for k in keys(self._ax) if k is not self])
        self.artists, self._place, self.position, self._ax = [], None, None, None
        self.outside = False
        self._shift.clear()


_PLACED = "_forgegraph_keys"
KEY = "forgegraph-key"  # every artist of a key


def keys(ax: Axes) -> list[Key]:
    """The keys placed in an Axes, in the order they were placed."""
    return list(getattr(ax, _PLACED, []))
