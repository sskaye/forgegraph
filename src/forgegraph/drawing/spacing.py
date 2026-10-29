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
from forgegraph.drawing.layers import TOP_NOTE
from forgegraph.drawing.style import Style

TICK_LABEL = "axis.tick.label"  # a color bar's tick labels; a graph's are each axis's own


def tick_font(style: Style, path: str = TICK_LABEL) -> FontProperties:
    return style.font(path)


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


def _tick_excess(axis: Axis, which: int, style: Style, path: str) -> float:
    """How far the tick labels' boxes on one side reach past their letters, on the side away
    from the ticks, in points. path: their text style."""
    prop, labels = tick_font(style, path), _labels(axis, which)
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


def _tick_pad(axis: Axis, style: Style, path: str) -> None:
    """Pad each tick label so its letters sit its style's gap (path) from the tick."""
    gap, prop = style.pt(f"{path}.gap"), tick_font(style, path)
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


def _centre_y_labels(axis: Axis, style: Style, path: str) -> None:
    """Centre the y tick labels' letters on their ticks: each sits on its baseline at the
    tick (ytick.alignment is baseline), moved down by the middle of the row's edges."""
    prop = tick_font(style, path)
    labels = _labels(axis, 1) + _labels(axis, 2)
    if not labels:
        return
    middle = text.row(labels, prop).middle
    for tick in axis.get_major_ticks():
        for label in (tick.label1, tick.label2):
            _shift(label, middle)


def _axis_title_pad(axis: Axis, style: Style, gap: str, path: str) -> None:
    """Pad the axis title so it sits gap (a theme path) from the tick labels' letters: from
    its own letters where its top faces them, and from its baseline where its baseline does,
    so a title's descenders don't move it."""
    title = axis.label.get_text()
    if not title.strip():
        return
    prop = axis.label.get_fontproperties()
    edges, box = text.edges(title, prop), text.box(title, prop)
    position = axis.get_label_position()
    if isinstance(axis, XAxis):  # upright: its top faces down at the bottom, up at the top
        own = box.top - edges.top if position == "bottom" else box.bottom
    elif round(axis.label.get_rotation()) % 360 == 270:  # reads downward: its baseline faces in
        own = box.bottom
    else:  # reads upward: on the left its baseline faces the plot, on the right its top does
        own = box.bottom if position == "left" else box.top - edges.top
    side = _side(axis)
    ticks = _tick_excess(axis, side, style, path) if side is not None else 0.0
    axis.labelpad = style.pt(gap) - own - ticks


def _box_height(box: text.Box) -> float:
    return box.top + box.bottom


def _title_pad(ax: Axes, style: Style) -> None:
    """Pad the title so its baseline sits title.gap above what's under it: descenders hang
    into the gap, so titles beside each other share a baseline whatever their letters.
    Matplotlib's title pad is to its baseline (va baseline)."""
    if not ax.get_title().strip():
        return
    ticks = _tick_excess(ax.xaxis, 2, style, "axis.x.tick.label") if _labels(ax.xaxis, 2) else 0.0
    above = [  # a key outside, above the plot box: the title sits over it
        k.height + style.pt("legend.key.gap.outer")
        for k in keys(ax)
        if k.outside and k.position and k.position.startswith("top")
    ]
    notes = [  # a note outside at the top, over any key: the title sits over it too
        _box_height(text.box(t.get_text(), t.get_fontproperties())) + getattr(t, TOP_NOTE)
        for t in ax.texts
        if hasattr(t, TOP_NOTE) and t.get_visible()
    ]
    room = max(above, default=0.0) + max(notes, default=0.0)
    ax.set_title(ax.get_title(), pad=style.pt("title.gap") - ticks + room)
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


def _tick_labels(axis: Axis, style: Style, path: str) -> None:
    """Draw the tick labels in their text style (path): its font, weight, size and color, and
    for wrapped x labels, its alignment. Ticks matplotlib makes later copy the first one's."""
    prop, color = tick_font(style, path), style.color(f"{path}.color")
    alignment = style.theme.get(f"{path}.alignment")  # a wrapped label's lines (x only)
    for tick in axis.get_major_ticks():
        for label in (tick.label1, tick.label2):
            label.set_fontproperties(prop)
            label.set_color(color)
            if alignment is not None:
                label.set_multialignment(cast(Any, str(alignment)))


def apply(ax: Axes, style: Style) -> None:
    """Set every padding around the Axes' text from the theme's visible gaps."""
    for each in axes_family(ax):
        gap = "axis.title.gap" if each is ax else "legend.color_bar.title.gap"  # a color bar's
        for name, axis in (("x", each.xaxis), ("y", each.yaxis)):
            path = f"axis.{name}.tick.label" if each is ax else TICK_LABEL
            _tick_labels(axis, style, path)
            _tick_pad(axis, style, path)
            _axis_title_pad(axis, style, gap, path)
        _centre_y_labels(each.yaxis, style, "axis.y.tick.label" if each is ax else TICK_LABEL)
    _title_pad(ax, style)
    for k in keys(ax):  # a key below the plot box follows the x-axis title
        k.follow(ax)
