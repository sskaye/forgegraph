"""The color bar for a numeric encoding.color, laid out by the theme's legend.color_bar.layout:

- title_above: a vertical bar right of the plot box, its title above it, left-aligned; the
  bar runs from the box's bottom to a title gap below the title;
- title_along: a vertical bar the box's height, its title beside it reading downward;
- below: a horizontal bar half the box's width under the x-axis title, its title above it.

The bar's position is worked out each time the figure is drawn (an axes locator), from the
plot box and the letters around it, so it follows the layout. Its ticks and title use the
axes' settings.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Colormap, Normalize
from matplotlib.transforms import Affine2D, Bbox, ScaledTranslation

from forgegraph.render import spacing, text
from forgegraph.render.figure import WATERMARK, texts_of, tick_marks
from forgegraph.render.style import Style
from forgegraph.render.ticks import NiceTicks

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
    minor_ticks: Callable[[Axis], None],
) -> Axes:
    """Draw the color bar for ax, with its title if given, and return its Axes. minor_ticks
    sets its long axis's minor ticks as the plot's."""
    layout = str(style.theme["legend.color_bar.layout"])
    prop = spacing.axis_title_font(style)
    edges = text.edges(title, prop) if title else None
    title_gap = style.pt("axis.title.gap")
    head = edges.height + title_gap if edges is not None and layout != TITLE_ALONG else 0.0
    cax = ax.inset_axes((0, 0, 1, 1))
    cax.set_axes_locator(_Place(ax, style, layout, head))
    orientation = "horizontal" if layout == BELOW else "vertical"
    bar = ax.figure.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation=orientation)
    bar.locator = NiceTicks(str(style.theme["axis.tick.algorithm"]))
    minor_ticks(bar.long_axis)
    if edges is None or not title:
        return cax
    if layout == TITLE_ALONG:  # reads downward: its letters face away from the bar
        bar.set_label(title, rotation=270, va="bottom")
        return cax
    fig = ax.figure
    above_bar = (
        Affine2D().translate(-edges.left, title_gap + edges.bottom).scale(1 / 72)
        + fig.dpi_scale_trans  # type: ignore[union-attr]
        + ScaledTranslation(0, 1, cast(Any, cax.transAxes))
    )
    cax.text(0, 0, title, fontproperties=prop, ha="left", va="baseline", transform=above_bar)
    return cax
