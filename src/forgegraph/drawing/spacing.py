"""Gaps around an Axes' text, measured to the letters (see forgegraph.drawing.text).

Matplotlib pads tick labels, axis titles and the title from their boxes; `apply()` sets
those paddings so the visible gaps are the theme's, and centres each y tick label's letters
on its tick. It covers the plot's Axes and any Axes inside it (a color bar), and is run
whenever the layout changes, since the tick labels may change with it.
"""

from __future__ import annotations

from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.axis import Axis, XAxis
from matplotlib.font_manager import FontProperties
from matplotlib.text import Text
from matplotlib.transforms import ScaledTranslation, Transform

from forgegraph.drawing import limits, text
from forgegraph.drawing.key import keys
from forgegraph.drawing.style import Style


def tick_font(style: Style) -> FontProperties:
    return style.font("axis.tick.label")


def axis_title_font(style: Style) -> FontProperties:
    return style.font("axis.title")


def title_font(style: Style) -> FontProperties:
    return style.font("title")


def _in_view(axis: Axis) -> list:
    return limits.ticks_in_view(axis, axis.get_major_ticks())


def _labels(axis: Axis, which: int) -> list[str]:
    """The texts of the tick labels drawn on one side (1: bottom or left, 2: top or right)."""
    out = []
    for tick in _in_view(axis):
        label = tick.label1 if which == 1 else tick.label2
        if label.get_visible() and label.get_text().strip():
            out.append(label.get_text())
    return out


def _side(axis: Axis) -> int | None:
    """Which side's tick labels face the axis title: 1, 2, or None if neither is drawn."""
    position = axis.get_label_position()
    which = 1 if position in ("bottom", "left") else 2
    return which if _labels(axis, which) else None


def _tick_excess(axis: Axis, which: int, style: Style) -> float:
    """How far the tick labels' boxes on one side reach past their letters, on the side away
    from the ticks, in points."""
    prop, labels = tick_font(style), _labels(axis, which)
    if not labels:
        return 0.0
    row = text.row(labels, prop)
    box = text.box(labels[0], prop)
    if isinstance(axis, XAxis):
        return box.bottom - row.bottom if which == 1 else box.top - row.top
    widest = max((text.edges(label, prop) for label in labels), key=lambda e: e.advance)
    if which == 1:  # right-aligned: the widest label's box reaches furthest left
        return widest.left
    return widest.advance - widest.right


def _tick_pad(axis: Axis, style: Style) -> None:
    """Pad each tick label so its letters sit axis.tick.label.gap from the tick."""
    gap, prop = style.pt("axis.tick.label.gap"), tick_font(style)
    which = 1 if _labels(axis, 1) else 2
    labels = _labels(axis, which)
    if not labels:
        return
    if isinstance(axis, XAxis):
        row, box = text.row(labels, prop), text.box(labels[0], prop)
        near = box.top - row.top if which == 1 else box.bottom - row.bottom
    else:
        edges = [text.edges(label, prop) for label in labels]
        near = min(e.advance - e.right for e in edges) if which == 1 else min(e.left for e in edges)
    axis.set_tick_params(which="major", pad=gap - near)


_SHIFT = "_forgegraph_shift"  # (the shifted transform, the transform it shifts)


def _shift(label: Text, points: float) -> None:
    """Move a label down by `points`, from the position matplotlib gives it."""
    fig = label.get_figure(root=True)
    current = label.get_transform()
    shifted, base = getattr(label, _SHIFT, (None, None))
    if current is not shifted:  # matplotlib set a new transform: shift that one
        base = current
    assert isinstance(base, Transform) and fig is not None
    moved = base + ScaledTranslation(0, -points / 72, fig.dpi_scale_trans)
    label.set_transform(moved)
    setattr(label, _SHIFT, (moved, base))


def _centre_y_labels(axis: Axis, style: Style) -> None:
    """Centre the y tick labels' letters on their ticks: each sits on its baseline at the
    tick (ytick.alignment is baseline), moved down by the middle of the row's edges."""
    prop = tick_font(style)
    labels = _labels(axis, 1) + _labels(axis, 2)
    if not labels:
        return
    middle = text.row(labels, prop).middle
    for tick in axis.get_major_ticks():
        for label in (tick.label1, tick.label2):
            _shift(label, middle)


def _axis_title_pad(axis: Axis, style: Style, gap: str = "axis.title.gap") -> None:
    """Pad the axis title so its letters sit gap (a theme path) from the tick labels'."""
    title = axis.label.get_text()
    if not title.strip():
        return
    prop = axis.label.get_fontproperties()
    edges, box = text.edges(title, prop), text.box(title, prop)
    position = axis.get_label_position()
    if isinstance(axis, XAxis):  # upright: its top faces down at the bottom, up at the top
        own = box.top - edges.top if position == "bottom" else box.bottom - edges.bottom
    elif round(axis.label.get_rotation()) % 360 == 270:  # reads downward: its baseline faces in
        own = box.bottom - edges.bottom
    else:  # reads upward: on the left its baseline faces the plot, on the right its top does
        own = box.bottom - edges.bottom if position == "left" else box.top - edges.top
    side = _side(axis)
    ticks = _tick_excess(axis, side, style) if side is not None else 0.0
    axis.labelpad = style.pt(gap) - own - ticks


def _title_pad(ax: Axes, style: Style) -> None:
    """Pad the title so its letters sit title.gap above what's under it."""
    title = ax.get_title()
    if not title.strip():
        return
    prop = title_font(style)
    own = text.box(title, prop).bottom - text.edges(title, prop).bottom
    ticks = _tick_excess(ax.xaxis, 2, style) if _labels(ax.xaxis, 2) else 0.0
    above = [  # a key outside, above the plot box: the title sits over it
        k.height + style.pt("legend.key.gap.outer")
        for k in keys(ax)
        if k.outside and k.position and k.position.startswith("top")
    ]
    ax.set_title(title, pad=style.pt("title.gap") - own - ticks + max(above, default=0.0))
    align_title(ax, style)


def align_title(ax: Axes, style: Style) -> None:
    """Put the title in its font at the plot box's left, centre or right (title.alignment).
    Matplotlib's set_title sets its own font and centres it again, so this follows every
    call."""
    ax.title.set_fontproperties(title_font(style))
    alignment = cast(Any, str(style.theme["title.alignment"]))
    ax.title.set_horizontalalignment(alignment)
    ax.title.set_x({"left": 0.0, "center": 0.5, "right": 1.0}[alignment])


def axes_family(ax: Axes) -> list[Axes]:
    """An Axes and every Axes drawn inside it, such as a color bar."""
    return [ax, *cast(list[Axes], ax.child_axes)]


def apply(ax: Axes, style: Style) -> None:
    """Set every padding around the Axes' text from the theme's visible gaps."""
    alignment = cast(Any, str(style.theme["axis.tick.label.alignment"]))  # a wrapped label's lines
    for tick in ax.xaxis.get_major_ticks():
        tick.label1.set_multialignment(alignment)
        tick.label2.set_multialignment(alignment)
    for each in axes_family(ax):
        gap = "axis.title.gap" if each is ax else "legend.color_bar.title.gap"  # a color bar's
        for axis in (each.xaxis, each.yaxis):
            _tick_pad(axis, style)
            _axis_title_pad(axis, style, gap)
        _centre_y_labels(each.yaxis, style)
    _title_pad(ax, style)
    for k in keys(ax):  # a key below the plot box follows the x-axis title
        k.follow(ax)
