"""Series labelling methods (architecture D5): direct labels (interior here) and a key.

Each method either places every label cleanly or reports that it can't, so a graph never
gets a partial or overlapping result. legend.method picks a method; auto tries the theme's
legend.methods in order and uses the first that fits. A named method that doesn't fit,
or auto with nothing that fits, is an error (xy.label raises it); there's no fallback.

Direct labels follow six rules, using the theme's legend.direct parameters:
1. never in the margins;
2. next to its own series: its series is the nearest one, at most max_relative_distance of
   the distance to any other, and within one and a half label heights;
3. touching nothing: at least clearance from every line and marker, its own included, and
   from every other label;
4. in open space: prefer positions close to its own series and far from the others, with a
   slight preference for either end of the line;
5. if nothing passes, the x-axis grows by as little as it takes, up to axis.max_extension of
   its range;
6. otherwise direct doesn't fit.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator
from matplotlib.transforms import Bbox

from forgegraph.drawing import limits, text
from forgegraph.drawing.key import KEY, Entry, Key
from forgegraph.drawing.key import keys as keys_of
from forgegraph.drawing.marks import Bars
from forgegraph.drawing.style import Style

DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
REACHES = (1.0, 1.6, 2.4, 3.4)  # a label's distance from its anchor, in offsets
SERIES_LABEL = "forgegraph-series-label"


@dataclass
class Labelled:
    """One name to place, and every line drawn under it (one, or several replicates)."""

    name: str
    color: str
    paths: list[np.ndarray]  # each (n, 2), in data coordinates
    handle: Line2D | Bars  # drawn in this group's style, for a legend


@dataclass
class _Candidate:
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 in display px
    score: float


def _densify(pts: np.ndarray, step: float) -> np.ndarray:
    pts = pts[np.isfinite(pts).all(axis=1)]
    if len(pts) < 2:
        return pts
    out = [pts[:1]]
    for a, b in itertools.pairwise(pts):
        n = max(1, int(np.hypot(*(b - a)) / step))
        t = np.linspace(0, 1, n + 1)[1:, None]
        out.append(a + t * (b - a))
    return np.vstack(out)


def _rect_dist(points: np.ndarray, box: tuple[float, float, float, float]) -> float:
    if len(points) == 0:
        return float("inf")
    x0, y0, x1, y1 = box
    dx = np.maximum(np.maximum(x0 - points[:, 0], 0), points[:, 0] - x1)
    dy = np.maximum(np.maximum(y0 - points[:, 1], 0), points[:, 1] - y1)
    return float(np.min(np.hypot(dx, dy)))


_CHUNK = 64  # candidate boxes measured together


def _near(points: np.ndarray, boxes: np.ndarray, reach: float) -> np.ndarray:
    """Each box's distance from its nearest point, where that's at most reach, else inf:
    _rect_dist's exact value within reach. Only points that could be within reach of a
    group of boxes are measured against it."""
    out = np.full(len(boxes), np.inf)
    if len(points) == 0 or len(boxes) == 0:
        return out
    pts = points[np.argsort(points[:, 0], kind="stable")]
    margin = reach * (1 + 1e-9) + 1e-9  # a little more, for rounding at the window's edge
    order = np.argsort(boxes[:, 0], kind="stable")
    for start in range(0, len(boxes), _CHUNK):
        chunk = order[start : start + _CHUNK]
        b = boxes[chunk]
        near = pts
        if np.isfinite(margin):
            lo = np.searchsorted(pts[:, 0], b[:, 0].min() - margin, side="left")
            hi = np.searchsorted(pts[:, 0], b[:, 2].max() + margin, side="right")
            near = pts[lo:hi]
            near = near[
                (near[:, 1] >= b[:, 1].min() - margin) & (near[:, 1] <= b[:, 3].max() + margin)
            ]
        if len(near) == 0:
            continue
        x0, y0, x1, y1 = (b[:, i : i + 1] for i in range(4))
        dx = np.maximum(np.maximum(x0 - near[:, 0], 0), near[:, 0] - x1)
        dy = np.maximum(np.maximum(y0 - near[:, 1], 0), near[:, 1] - y1)
        d = np.min(np.hypot(dx, dy), axis=1)
        out[chunk] = np.where(d <= reach, d, np.inf)
    return out


def _candidate_boxes(
    anchors: np.ndarray, steps: np.ndarray, offset: float, w: float, h: float
) -> tuple[np.ndarray, np.ndarray]:
    """Every candidate box around each anchor point, in order (anchor, then step), and each
    one's end preference: how far its anchor is from the nearer end of the series."""
    dx, dy, reach = (steps[:, i][None, :] for i in range(3))
    ax_, ay = anchors[:, 0][:, None], anchors[:, 1][:, None]
    cx = np.where(dx != 0, ax_ + dx * (reach * offset + w / 2), ax_)
    cy = np.where(dy != 0, ay + dy * (reach * offset + h / 2), ay)
    boxes = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=-1).reshape(-1, 4)
    t = np.arange(len(anchors)) / max(1, len(anchors) - 1)
    ends = np.repeat(np.minimum(t, 1 - t), len(steps))
    return boxes, ends


def _overlaps(boxes: np.ndarray, other: Any, pad: float) -> np.ndarray:
    """_overlap for many boxes against one."""
    return ~(
        (boxes[:, 2] + pad <= other[0])
        | (other[2] + pad <= boxes[:, 0])
        | (boxes[:, 3] + pad <= other[1])
        | (other[3] + pad <= boxes[:, 1])
    )


def _overlap(a: tuple, b: tuple, pad: float) -> bool:
    return not (
        a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1]
    )


def _drawn_points(ax: Axes, lines: bool) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """(dense line samples, marker centres) of everything drawn but keys, in display px: with
    lines, along every line drawn with a line style. A bar is sampled across its whole
    width."""
    dense, centres = [], []
    for line in ax.get_lines():
        if line.get_gid() == KEY:  # a key's own samples aren't data
            continue
        raw = line.get_transform().transform(np.asarray(line.get_xydata(), dtype=float))
        xy = raw[np.isfinite(raw).all(axis=1)]  # dates as numbers
        if line.get_linestyle() not in ("None", "none", " ", "") and lines:
            dense.append(_densify(xy, 1.5))
        if line.get_marker() not in ("None", "none", None, ""):
            centres.append(xy)
    for bars in ax.collections:
        if isinstance(bars, Bars):
            dense += [_bar_samples(box) for box in bars.rectangles()]
    return dense, centres


def _bar_samples(box: Bbox) -> np.ndarray:
    """Points filling a bar's rectangle, 1.5 px apart."""
    xs = np.linspace(box.x0, box.x1, max(2, int(box.width / 1.5) + 1))
    ys = np.linspace(box.y0, box.y1, max(2, int(box.height / 1.5) + 1))
    gx, gy = np.meshgrid(xs, ys)
    return np.c_[gx.ravel(), gy.ravel()]


@dataclass
class Obstacles:
    """What a box placed on a plot must keep clear of, in display px: points along lines and
    filling bars, markers' centres, texts, and named boxes (keys, color bars)."""

    dense: list[np.ndarray] = field(default_factory=list)
    centres: list[np.ndarray] = field(default_factory=list)
    texts: list[tuple[Text, Bbox]] = field(default_factory=list)
    boxes: list[tuple[str, Bbox | None]] = field(default_factory=list)  # what each is, its box

    @classmethod
    def of(cls, ax: Axes, *, lines: bool, keys: bool, renderer: Any = None) -> Obstacles:
        """What's drawn inside the plot: every marker and bar; with lines, every line drawn
        with a line style (the series' lines are drawn only when shown, so with
        mark.line.show false reference lines and error-bar stems don't count either); the
        plot's text (value labels, notes, a reference line's label, direct labels); with
        keys, the keys' frames. A key's own lines and text never count."""
        dense, centres = _drawn_points(ax, lines)
        texts = [
            (t, t.get_window_extent(renderer))
            for t in ax.texts
            if t.get_visible() and t.get_text() and t.get_gid() != KEY
        ]
        boxes: list[tuple[str, Bbox | None]] = (
            [(f"the key at {k.position}", k.bbox()) for k in keys_of(ax)] if keys else []
        )
        return cls(dense, centres, texts, boxes)

    def hits(self, box: Bbox, pad: float = 0.0) -> list[str]:
        """What box runs into, in order: "the data" if a point comes within pad px of it,
        then each text and named box it overlaps. One with exactly box's bounds is box
        itself, being placed, and doesn't count."""
        padded = (box.x0 - pad, box.y0 - pad, box.x1 + pad, box.y1 + pad)
        found = []
        if not all(_rect_dist(pts, padded) > 0 for pts in [*self.dense, *self.centres]):
            found.append("the data")
        found += [
            repr(t.get_text()) for t, b in self.texts if b.overlaps(box) and b.bounds != box.bounds
        ]
        found += [
            what
            for what, b in self.boxes
            if b is not None and box.overlaps(b) and b.bounds != box.bounds
        ]
        return found

    def clear(self, box: Bbox, pad: float = 0.0) -> bool:
        """Whether box runs into nothing here (see hits)."""
        return not self.hits(box, pad)


def place_interior(ax: Axes, groups: list[Labelled], style: Style, draw: bool = True) -> bool:
    """Place one label per group inside the plot (rules 1-4). True if every label fits; with
    draw False, only find out. Everything it reads is worked out from the axes as they are
    now, so it draws nothing."""
    fig = ax.figure
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    px = fig.dpi / 72.0
    clearance = style.pt("legend.label.gap") * px
    association = float(style.theme["legend.direct.max_relative_distance"])
    prop = style.font("legend.label")
    label_edges = [text.edges(g.name, prop) for g in groups]
    sizes = [(e.width * px, e.height * px) for e in label_edges]  # each label's letters

    lines = ax.get_lines()
    lw = max((line.get_linewidth() for line in lines), default=0.0) * px
    ms = max((line.get_markersize() for line in lines), default=0.0) * px
    line_clear = lw / 2 + clearance
    marker_clear = ms / 2 + clearance
    offset = max(line_clear, marker_clear) + clearance

    own_paths = [[ax.transData.transform(p) for p in g.paths] for g in groups]
    own_dense = [np.vstack([_densify(p, 1.5) for p in paths]) for paths in own_paths]
    drawn = Obstacles.of(ax, lines=True, keys=False, renderer=renderer)
    every_line = np.vstack(drawn.dense) if drawn.dense else np.empty((0, 2))
    every_marker = np.vstack(drawn.centres) if drawn.centres else np.empty((0, 2))
    box = ax.get_window_extent(renderer)
    inner = (box.x0 + 2 * px, box.y0 + 2 * px, box.x1 - 2 * px, box.y1 - 2 * px)
    texts = [  # what layers wrote inside the plot: notes, value labels, a line's label
        b.extents for t, b in drawn.texts if t.get_gid() != SERIES_LABEL
    ]

    steps = np.array(
        [(dx, dy, reach) for (dx, dy), reach in itertools.product(DIRECTIONS, REACHES)]
    )
    candidates: list[list[_Candidate]] = []
    for k, (pts, (w, h)) in enumerate(zip(own_dense, sizes, strict=True)):
        pts = pts[np.isfinite(pts).all(axis=1)]
        if len(pts) == 0:
            return False
        idx = np.unique(np.linspace(0, len(pts) - 1, 60).round().astype(int))
        boxes, ends = _candidate_boxes(pts[idx], steps, offset, w, h)
        keep = (  # rule 1
            (boxes[:, 0] >= inner[0])
            & (boxes[:, 1] >= inner[1])
            & (boxes[:, 2] <= inner[2])
            & (boxes[:, 3] <= inner[3])
        )
        boxes, ends = boxes[keep], ends[keep]
        keep = (_near(every_line, boxes, line_clear) >= line_clear) & (  # rule 3: lines
            _near(every_marker, boxes, marker_clear) >= marker_clear  # rule 3: markers
        )
        for o in texts:  # rule 3: other text
            keep &= ~_overlaps(boxes, o, clearance)
        boxes, ends = boxes[keep], ends[keep]
        d_own = _near(own_dense[k], boxes, 1.5 * h)  # rule 2: close by (inf beyond)
        others = [d for m, d in enumerate(own_dense) if m != k]
        if others:
            # beyond this, clarity is 3h and the association test passes either way
            reach = max(3 * h, 1.5 * h / association) if association > 0 else np.inf
            nearest = np.min([_near(d, boxes, reach) for d in others], axis=0)
            keep = (d_own <= 1.5 * h) & ~(d_own > association * nearest)  # rule 2
            clarity = np.minimum(nearest, 3 * h)
        else:
            keep = d_own <= 1.5 * h
            clarity = np.full(len(boxes), 3 * h)
        scores = (d_own - 0.7 * clarity) / px + 4 * ends
        found = [_Candidate(tuple(b), sc) for b, sc in zip(boxes[keep], scores[keep], strict=True)]
        found.sort(key=lambda c: c.score)
        candidates.append(found[:40])
    if any(not c for c in candidates):
        return False

    first = sorted(range(len(groups)), key=lambda k: len(candidates[k]))
    orders = [first] + [list(p) for p in itertools.islice(itertools.permutations(first), 1, 24)]
    best, best_score = None, float("inf")
    for order in orders:
        chosen: dict[int, _Candidate] = {}
        for k in order:
            for c in candidates[k]:
                if all(not _overlap(c.box, o.box, clearance) for o in chosen.values()):
                    chosen[k] = c
                    break
            else:
                break
        if len(chosen) == len(groups):
            total = sum(c.score for c in chosen.values())
            if total < best_score:
                best, best_score = chosen, total
    if best is None:
        return False
    if not draw:
        return True
    inverse = ax.transAxes.inverted()
    for k, g in enumerate(groups):
        x0, y0, _, _ = best[k].box  # where the letters go: the text starts and sits before them
        e = label_edges[k]
        ax_x, ax_y = inverse.transform((x0 - e.left * px, y0 + e.bottom * px))
        ax.text(
            ax_x,
            ax_y,
            g.name,
            transform=ax.transAxes,
            ha="left",
            va="baseline",
            color=g.color,
            fontproperties=prop,
            gid=SERIES_LABEL,
        )
    return True


def interior(ax: Axes, groups: list[Labelled], style: Style) -> bool:
    """Interior labels (rules 1-6), growing the x-axis as little as it takes (rule 5)."""
    if place_interior(ax, groups, style):
        return True
    most = float(style.theme["axis.max_extension"])
    if not grow_until(ax, "x", "max", lambda: place_interior(ax, groups, style, draw=False), most):
        return False
    return place_interior(ax, groups, style)


def grow_until(ax: Axes, axis: str, end: str, fits: Callable[[], bool], most: float) -> bool:
    """Extend an axis at one end (min or max) by as little as it takes, to 1/64 of most (a
    fraction of its range), until fits(); keep its ticks, since the extra room is for labels.
    False, with the axis as it was, if even most doesn't do it."""
    if most <= 0:
        return False
    which = ax.xaxis if axis == "x" else ax.yaxis
    get, put = (ax.get_xlim, ax.set_xlim) if axis == "x" else (ax.get_ylim, ax.set_ylim)
    log = (ax.get_xscale() if axis == "x" else ax.get_yscale()) == "log"
    lo, hi = get()
    locator = which.get_major_locator()
    ticks = np.asarray(which.get_majorticklocs(), dtype=float)  # a date axis's are a list
    which.set_major_locator(FixedLocator(list(ticks[limits.in_view(which, ticks)])))

    def extend(fraction: float) -> None:
        if log:
            grow = (hi / lo) ** fraction
            put(lo, hi * grow) if end == "max" else put(lo / grow, hi)
        else:
            grow = fraction * (hi - lo)
            put(lo, hi + grow) if end == "max" else put(lo - grow, hi)

    extend(most)
    if not fits():
        which.set_major_locator(locator)
        put(lo, hi)
        return False
    failed, fitted = 0.0, most  # the smallest extension that fits
    for _ in range(6):
        middle = (failed + fitted) / 2
        extend(middle)
        if fits():
            fitted = middle
        else:
            failed = middle
    extend(fitted)
    return True


def _clear_of_data(ax: Axes, key: Key, lines: bool) -> bool:
    text.measure(ax.figure)
    return box_clear(ax, key.bbox(), lines)


def box_clear(ax: Axes, bbox: Bbox, lines: bool, keys: bool = False) -> bool:
    """Whether a box, in display px, keeps 2 pt clear of what's drawn inside the plot, and
    off its other text (with keys, its keys too): see Obstacles.of."""
    pad = 2 * ax.figure.dpi / 72  # type: ignore[union-attr]
    return Obstacles.of(ax, lines=lines, keys=keys).clear(bbox, pad)


def unplace(ax: Axes) -> None:
    """Take away the keys and direct labels placed in ax, to place them again."""
    for k in keys_of(ax):
        k.remove()
    for t in [t for t in ax.texts if t.get_gid() == SERIES_LABEL]:
        t.remove()


def legend(
    ax: Axes,
    entries: list[Entry],
    style: Style,
    title: str | None,
    *,
    taken: list[Key] | None = None,
    lines: bool = True,
    positions: tuple[str, ...] = ("top_right", "top_left", "bottom_right", "bottom_left"),
    inside: bool = True,
) -> Key | None:
    """A key at the first free position of `positions`: inside the plot box, the first whose
    frame no line or marker passes through; outside it, the first not taken (layout makes
    room). None if there's no such position. Keys already placed (`taken`) keep theirs."""
    used = {k.position for k in taken or []}
    key = Key(entries, title, style)
    for position in positions:
        if position in used:
            continue
        if not inside:
            key.place_outside(ax, position)
            return key
        key.place(ax, position)
        if _clear_of_data(ax, key, lines):
            return key
        key.remove()
    return None
