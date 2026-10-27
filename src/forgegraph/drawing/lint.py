"""Lint: what's wrong with a drawn graph that an agent or a reader would otherwise miss.

Lint runs on every render, on the finished figure, and returns issues; it never changes the
drawing. Each issue names its check:

- overlapping-text: two texts whose letters overlap;
- clipped-text: a text running past the figure's edge;
- key-over-data: a key's box crossing a line or marker;
- too-many-groups: more groups than the theme has colors, line styles or marker shapes, so
  they repeat;
- log-axis-values: values of 0 or below on a log axis, which can't be drawn;
- outside-limits: points outside an axis's fixed minimum or maximum, so not drawn (past it
  by more than float noise: drawing.limits);
- small-text: text smaller than MIN_TEXT_PT, too small to read at the figure's size;
- font-fallback: a font or a letter the theme's font doesn't have, drawn with another or not
  at all;
- dropped-rows: data rows left out of the drawing, by reason;
- dates-as-text: an axis of text that reads as dates or times, drawn as categories rather
  than as a time axis.

The checks look at the figure itself, so they also cover a graph drawn on afterwards.
"""

from __future__ import annotations

import logging
import re
import warnings
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from forgegraph.drawing import limits, text
from forgegraph.drawing.figure import WATERMARK
from forgegraph.drawing.key import KEY, keys
from forgegraph.drawing.layers import GIDS as LAYERS
from forgegraph.drawing.layout import texts_of

MIN_TEXT_PT = 6.0  # the smallest text journals accept in a printed figure
OVERLAP_PX = 0.5  # letters closer than this count as touching, not overlapping


@dataclass(frozen=True)
class Issue:
    check: str
    message: str

    def __str__(self) -> str:
        return self.message

    def as_dict(self) -> dict[str, str]:
        return {"check": self.check, "message": self.message}


@contextmanager
def font_messages() -> Iterator[list[str]]:
    """Collect matplotlib's messages about missing fonts and letters while drawing. A weight
    a font doesn't have isn't one: a theme's weights are checked against its fonts, so that
    comes from maths loading faces it doesn't draw with at the text's weight."""
    found: list[str] = []

    class _Catch(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            message = record.getMessage()
            if "findfont" in message and "Failed to find font weight" not in message:
                found.append(message)

    handler = _Catch(logging.WARNING)
    logger = logging.getLogger("matplotlib.font_manager")
    logger.addHandler(handler)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            yield found
        for w in caught:
            message = str(w.message)
            if "missing from" in message and "font" in message:
                found.append(message)
            else:  # not ours to judge: pass it on
                warnings.warn_explicit(w.message, w.category, w.filename, w.lineno)
    finally:
        logger.removeHandler(handler)


def _texts(fig: Figure) -> list[tuple[Text, str]]:
    """Every visible text with letters, and where it is, for messages."""
    out: list[tuple[Text, str]] = []
    for ax in fig.axes:
        where = "color bar" if ax.get_label() == "<colorbar>" else "plot"
        for t in texts_of(ax):
            if t.get_visible() and t.get_text().strip() and t.get_gid() != WATERMARK:
                out.append((t, where))
        for key in keys(ax):
            out += [(a, "key") for a in key.artists if isinstance(a, Text) and a.get_text().strip()]
    for t in fig.texts:
        if t.get_visible() and t.get_text().strip():
            out.append((t, "figure"))
    seen: set[int] = set()
    return [(t, w) for t, w in out if not (id(t) in seen or seen.add(id(t)))]


def _name(t: Text) -> str:
    s = t.get_text().replace("\n", " ")
    return f"'{s}'" if len(s) <= 40 else f"'{s[:37]}...'"


def _overlapping(found: list[tuple[Text, Bbox]]) -> list[Issue]:
    issues = []
    for i, (a, box_a) in enumerate(found):
        for b, box_b in found[i + 1 :]:
            w = min(box_a.x1, box_b.x1) - max(box_a.x0, box_b.x0)
            h = min(box_a.y1, box_b.y1) - max(box_a.y0, box_b.y0)
            if w > OVERLAP_PX and h > OVERLAP_PX:
                issues.append(Issue("overlapping-text", f"{_name(a)} and {_name(b)} overlap"))
    return issues


def _clipped(fig: Figure, found: list[tuple[Text, Bbox]]) -> list[Issue]:
    edge = fig.bbox
    return [
        Issue("clipped-text", f"{_name(t)} runs past the figure's edge")
        for t, box in found
        if box.x0 < edge.x0 - OVERLAP_PX
        or box.y0 < edge.y0 - OVERLAP_PX
        or box.x1 > edge.x1 + OVERLAP_PX
        or box.y1 > edge.y1 + OVERLAP_PX
    ]


def _size(t: Text) -> float:
    return float(t.get_fontproperties().get_size_in_points())


def _small(found: list[tuple[Text, str]]) -> list[Issue]:
    small = [(t, w) for t, w in found if _size(t) < MIN_TEXT_PT - 1e-9]
    if not small:
        return []
    t, _ = min(small, key=lambda tw: _size(tw[0]))
    return [
        Issue(
            "small-text",
            f"{len(small)} texts are smaller than {MIN_TEXT_PT:g} pt (smallest {_name(t)}, "
            f"{_size(t):.1f} pt); make the format's base size larger",
        )
    ]


def _data_lines(ax: Axes) -> list[Line2D]:
    """The lines and markers drawing data: not a key's samples."""
    return [
        ln
        for ln in ax.get_lines()
        if ln.get_visible() and np.size(ln.get_xdata()) > 0 and ln.get_gid() != KEY
    ]


def _key_over_data(ax: Axes) -> list[Issue]:
    issues = []
    for key in keys(ax):
        box = key.bbox()
        for line in _data_lines(ax):
            path = line.get_transform().transform_path(line.get_path())
            crosses = line.get_linestyle() not in ("None", "none", "") and path.intersects_bbox(
                box, filled=False
            )
            radius = line.get_markersize() / 2 * ax.figure.dpi / 72  # type: ignore[union-attr]
            near = box.expanded(1, 1).padded(radius)
            marked = line.get_marker() not in (None, "None", "none", "") and bool(
                _inside(near, np.asarray(path.vertices)).any()
            )
            if crosses or marked:
                issues.append(Issue("key-over-data", "a key covers a line or marker"))
                break
    return issues


def _points(ax: Axes, axis: str) -> np.ndarray:
    """Every data point's finite value along an axis. A layer's lines aren't points: a
    reference line's ends are the plot's edges, and an error bar's are distances from a point."""
    values = np.concatenate(
        [
            np.asarray(ln.get_xydata(), dtype=float)[:, 0 if axis == "x" else 1]
            for ln in _data_lines(ax)
            if ln.get_gid() not in LAYERS
        ]
        or [np.array([])]
    )
    return values[np.isfinite(values)]


def _inside(box: Any, points: np.ndarray) -> np.ndarray:
    """Which points a box holds, edges included: matplotlib's Bbox.contains, for many."""
    x, y = points[:, 0], points[:, 1]
    across = ((box.x0 <= x) & (x <= box.x1)) | ((box.x0 >= x) & (x >= box.x1))
    down = ((box.y0 <= y) & (y <= box.y1)) | ((box.y0 >= y) & (y >= box.y1))
    return across & down


def _limits(ax: Axes, fixed: dict[str, tuple[Any, Any]]) -> list[Issue]:
    issues = []
    for axis, (lo, hi) in fixed.items():
        view = ax.xaxis if axis == "x" else ax.yaxis
        start, end = sorted(view.get_view_interval())  # an automatic end: where it is
        low, high = limits.outside(
            _points(ax, axis),
            start if lo is None else lo,
            end if hi is None else hi,
            view.get_scale() == "log",
        )
        below = int(low.sum()) if lo is not None else 0
        above = int(high.sum()) if hi is not None else 0
        if below or above:
            parts = [
                f"{below} below axis.{axis}.min" if below else "",
                f"{above} above axis.{axis}.max" if above else "",
            ]
            issues.append(
                Issue(
                    "outside-limits",
                    f"{' and '.join(p for p in parts if p)}: those points aren't drawn",
                )
            )
    return issues


def _log_values(ax: Axes) -> list[Issue]:
    issues = []
    for axis in ("x", "y"):
        scale = ax.get_xscale() if axis == "x" else ax.get_yscale()
        if scale != "log":
            continue
        bad = int((_points(ax, axis) <= 0).sum())
        if bad:
            issues.append(
                Issue(
                    "log-axis-values",
                    f"{bad} values of 0 or below on the log {axis}-axis aren't drawn",
                )
            )
    return issues


def _fonts(messages: list[str]) -> list[Issue]:
    issues, seen = [], set()
    for m in messages:
        glyph = re.search(r"Glyph (\d+) .*missing from (?:current )?font\(?s?\)? ?(.*)", m)
        if glyph:
            letter = chr(int(glyph[1]))
            text_ = f"the letter '{letter}' isn't in the theme's font, so it isn't drawn"
        else:
            family = re.search(r"Font family ['\[]?([^'\]]+)['\]]? not found", m)
            what = f"font '{family[1]}'" if family else "a font"
            text_ = f"{what} isn't installed, so another font is used"
        if text_ not in seen:
            seen.add(text_)
            issues.append(Issue("font-fallback", text_))
    return issues


def ordered(figure: list[Issue], plot: list[Issue]) -> list[Issue]:
    """Every issue in a drawn graph, from its figure's (figure_issues) and its plot's
    (plot_issues): text problems first, and dropped rows last."""
    texts = ("overlapping-text", "clipped-text")  # first; dropped rows last
    return [
        *(i for i in figure if i.check in texts),
        *(i for i in plot if i.check != "dropped-rows"),
        *(i for i in figure if i.check not in texts),
        *(i for i in plot if i.check == "dropped-rows"),
    ]


def figure_issues(fig: Figure, font_problems: list[str]) -> list[Issue]:
    """The issues of a figure as a whole, just drawn: its texts, wherever they are, and its
    fonts."""
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    found = _texts(fig)
    boxes = [(t, text.footprint(t, renderer)) for t, _ in found]
    boxes = [(t, b) for t, b in boxes if b.width > 0 and b.height > 0]
    return [*_overlapping(boxes), *_clipped(fig, boxes), *_small(found), *_fonts(font_problems)]


def plot_issues(
    ax: Axes,
    *,
    fixed_limits: dict[str, tuple[Any, Any]],
    rows_dropped: dict[str, int],
    drawing: Sequence[Issue] = (),
) -> list[Issue]:
    """The issues of one plot: its key, its data and what drawing it found. fixed_limits:
    each axis's set minimum and maximum (None where automatic); drawing: issues the drawing
    code found, such as repeated colors."""
    issues = [*_key_over_data(ax), *drawing, *_log_values(ax), *_limits(ax, fixed_limits)]
    issues += [
        Issue("dropped-rows", f"{n} {'row' if n == 1 else 'rows'} left out: {reason}")
        for reason, n in rows_dropped.items()
        if n
    ]
    return issues
