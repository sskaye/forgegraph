"""The color bar for a numeric encoding.color.column, laid out by the theme's
legend.color_bar.position and legend.color_bar.title.position:

- right, above: a vertical bar right of the plot box, its title above it; the bar runs from
  the box's bottom to a title gap below the title;
- right, beside: a vertical bar the box's height, its title beside it reading downward;
- below, above: a horizontal bar half the box's width under the x-axis title, its title
  above it.

The title's alignment places it along the bar: from its start, centred, or to its end.

The bar's position is worked out each time the figure is drawn (an axes locator), from the
plot box and the letters around it, so it follows the layout. Its ticks and title use the
axes' settings.
"""

from __future__ import annotations

from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Colormap, Normalize
from matplotlib.transforms import Affine2D, Bbox, ScaledTranslation

from forgegraph.drawing import text
from forgegraph.drawing.figure import WATERMARK
from forgegraph.drawing.layout import texts_of, tick_marks
from forgegraph.drawing.style import Style
from forgegraph.drawing.ticks import NiceTicks, minor_ticks

TITLE_ABOVE, TITLE_ALONG, BELOW = "title_above", "title_along", "below"


def _lowest(ax: Axes, renderer: Any) -> float:
    """The lowest letter or tick drawn under the plot box, in display pixels."""
    ax.xaxis.get_tightbbox(renderer)  # places the tick labels and title for this draw
    lows = [ax.bbox.y0 - ax.spines["bottom"].get_linewidth() / 2 * ax.figure.dpi / 72]
    lows += [b.y0 for b in tick_marks(ax, renderer)]
    for t in texts_of(ax):
        if t.get_visible() and t.get_text().strip() and t.get_gid() != WATERMARK:
            box = text.footprint(t, renderer)
            if box.height > 0 and box.y1 <= ax.bbox.y0 + 1:  # only what's below the box
                lows.append(box.y0)
    return min(lows)


class _Place:
    """Where the bar goes, as an axes locator: figure-relative bounds at each draw."""

    def __init__(self, parent: Axes, style: Style, layout: str, head: float) -> None:
        self.parent, self.style, self.layout, self.head = parent, style, layout, head

    def __call__(self, cax: Any, renderer: Any) -> Bbox:
        fig = self.parent.figure
        px = fig.dpi / 72
        box = self.parent.bbox
        gap, width = self.style.pt("legend.color_bar.gap"), self.style.pt("legend.color_bar.width")
        if self.layout == BELOW:
            top = _lowest(self.parent, renderer) - (gap + self.head) * px
            bounds = Bbox.from_extents(box.x0, top - width * px, box.x0 + box.width / 2, top)
        else:
            x0 = box.x1 + gap * px
            y1 = box.y1 - (self.head * px if self.layout == TITLE_ABOVE else 0)
            bounds = Bbox.from_extents(x0, box.y0, x0 + width * px, y1)
        return bounds.transformed(fig.transSubfigure.inverted())  # type: ignore[union-attr]


def add(
    ax: Axes,
    norm: Normalize,
    cmap: Colormap,
    title: str | None,
    style: Style,
) -> Axes:
    """Draw the color bar for ax, with its title if given, and return its Axes. Its long
    axis has the plot's minor ticks."""
    layout = _layout(style)
    look = style.text("legend.color_bar.title")
    prop, alignment = look.font, look.alignment or "left"
    edges = text.edges(title, prop) if title else None
    title_gap = look.gap or 0.0
    head = edges.height + title_gap if edges is not None and layout != TITLE_ALONG else 0.0
    cax = ax.inset_axes((0, 0, 1, 1))
    cax.set_axes_locator(_Place(ax, style, layout, head))
    orientation = "horizontal" if layout == BELOW else "vertical"
    bar = ax.figure.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation=orientation)
    bar.locator = NiceTicks(str(style.theme["axis.tick.algorithm"]))
    minor_ticks(bar.long_axis, style)
    if edges is None or not title:
        return cax
    if layout == TITLE_ALONG:  # reads downward: its letters face away from the bar
        bar.set_label(title, rotation=270, va="bottom", fontproperties=prop, color=look.color)
        if alignment != "center":  # along the bar: its start at the top, or its end at the bottom
            label = cax.yaxis.label
            label.set_y(1.0 if alignment == "left" else 0.0)
            label.set_verticalalignment("top" if alignment == "left" else "bottom")
        return cax
    fig = ax.figure
    across, start = {
        "left": (0.0, edges.left),
        "center": (0.5, (edges.left + edges.right) / 2),
        "right": (1.0, edges.right),
    }[alignment]
    above_bar = (
        Affine2D().translate(-start, title_gap + edges.bottom).scale(1 / 72)
        + fig.dpi_scale_trans  # type: ignore[union-attr]
        + ScaledTranslation(across, 1, cast(Any, cax.transAxes))
    )
    cax.text(
        0,
        0,
        title,
        fontproperties=prop,
        color=look.color,
        ha="left",
        va="baseline",
        transform=above_bar,
    )
    return cax


def _layout(style: Style) -> str:
    """The bar's and its title's places, as one of TITLE_ABOVE, TITLE_ALONG and BELOW."""
    position = str(style.theme["legend.color_bar.position"])
    title = str(style.theme["legend.color_bar.title.position"])
    if position == "below":
        return BELOW
    return TITLE_ALONG if title == "beside" else TITLE_ABOVE
