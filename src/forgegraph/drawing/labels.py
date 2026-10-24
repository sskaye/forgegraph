"""Series labelling methods (architecture D5): interior labels and a clear-corner legend.

Each method either places every label cleanly or reports that it can't, so a graph never
gets a partial or overlapping result. legend.method picks a method; auto tries the theme's
legend.methods in order and uses the first that fits. A named method that doesn't fit,
or auto with nothing that fits, is an error (xy.label raises it); there's no fallback.

Interior labels follow six rules:
1. never in the margins;
2. next to its own series: its series is the nearest one, at most max_relative_distance of
   the distance to any other, and within one and a half label heights;
3. touching nothing: at least clearance from every line and marker, its own included, and
   from every other label;
4. in open space: prefer positions close to its own series and far from the others, with a
   slight preference for either end of the line;
5. if nothing passes, the x-axis grows by as little as it takes, up to max_axis_extension of
   its range;
6. otherwise interior doesn't fit.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator
from matplotlib.transforms import Bbox

from forgegraph.drawing import text
from forgegraph.drawing.key import KEY, Entry, Key
from forgegraph.drawing.marks import Bars
from forgegraph.drawing.style import Style

DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
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


def _overlap(a: tuple, b: tuple, pad: float) -> bool:
    return not (
        a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1]
    )


def _drawn_points(ax: Axes, lines_shown: bool) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """(dense line samples, marker centres) of every drawn series, in display px. A bar is
    sampled across its whole width."""
    dense, centres = [], []
    for line in ax.get_lines():
        if line.get_gid() == KEY:  # a key's own samples aren't data
            continue
        raw = line.get_transform().transform(np.asarray(line.get_xydata(), dtype=float))
        xy = raw[np.isfinite(raw).all(axis=1)]  # dates as numbers
        if line.get_linestyle() not in ("None", "none", " ", "") and lines_shown:
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


def place_interior(ax: Axes, groups: list[Labelled], style: Style, draw: bool = True) -> bool:
    """Place one label per group inside the plot (rules 1-4). True if every label fits; with
    draw False, only find out."""
    fig = ax.figure
    fig.canvas.draw()  # type: ignore[union-attr]
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    px = fig.dpi / 72.0
    size = style.pt("legend.label.size")
    weight = style.weight("legend.label.weight")
    clearance = style.pt("legend.direct.clearance") * px
    association = float(style.theme["legend.direct.max_relative_distance"])
    prop = text.font(str(style.theme["font.family"]), size, weight)
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
    all_dense, all_centres = _drawn_points(ax, True)
    every_line = np.vstack(all_dense) if all_dense else np.empty((0, 2))
    every_marker = np.vstack(all_centres) if all_centres else np.empty((0, 2))
    box = ax.get_window_extent(renderer)
    inner = (box.x0 + 2 * px, box.y0 + 2 * px, box.x1 - 2 * px, box.y1 - 2 * px)
    texts = [  # what layers wrote inside the plot: notes, value labels, a line's label
        t.get_window_extent(renderer).extents
        for t in ax.texts
        if t.get_visible() and t.get_text() and t.get_gid() not in (SERIES_LABEL, KEY)
    ]

    candidates: list[list[_Candidate]] = []
    for k, (pts, (w, h)) in enumerate(zip(own_dense, sizes, strict=True)):
        found: list[_Candidate] = []
        pts = pts[np.isfinite(pts).all(axis=1)]
        if len(pts) == 0:
            return False
        idx = np.unique(np.linspace(0, len(pts) - 1, 60).round().astype(int))
        for j, i in enumerate(idx):
            p = pts[i]
            t = j / max(1, len(idx) - 1)
            for (dx, dy), reach in itertools.product(DIRECTIONS, (1.0, 1.6, 2.4, 3.4)):
                cx = p[0] + dx * (reach * offset + w / 2) if dx else p[0]
                cy = p[1] + dy * (reach * offset + h / 2) if dy else p[1]
                cand = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                if (
                    cand[0] < inner[0]
                    or cand[1] < inner[1]
                    or cand[2] > inner[2]
                    or cand[3] > inner[3]
                ):
                    continue  # rule 1
                if _rect_dist(every_line, cand) < line_clear:
                    continue  # rule 3: lines
                if _rect_dist(every_marker, cand) < marker_clear:
                    continue  # rule 3: markers
                if any(_overlap(cand, tuple(o), clearance) for o in texts):
                    continue  # rule 3: other text
                d_own = _rect_dist(own_dense[k], cand)
                others = [_rect_dist(d, cand) for m, d in enumerate(own_dense) if m != k]
                if others and d_own > association * min(others):
                    continue  # rule 2: its own series must be the nearest
                if d_own > 1.5 * h:
                    continue  # rule 2: close by
                end_pref = min(t, 1 - t)
                clarity = min(min(others), 3 * h) if others else 3 * h
                found.append(_Candidate(cand, (d_own - 0.7 * clarity) / px + 4 * end_pref))
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
    x0, x1 = ax.get_xlim()
    most = float(style.theme["legend.direct.max_axis_extension"])
    if most <= 0:
        return False
    # The extra room is for labels: keep the ticks the layout made room for.
    locator = ax.xaxis.get_major_locator()
    ticks = [t for t in ax.get_xticks() if min(x0, x1) <= t <= max(x0, x1)]
    ax.xaxis.set_major_locator(FixedLocator(ticks))

    def extend(fraction: float) -> None:
        if ax.get_xscale() == "log":
            ax.set_xlim(x0, x1 * (x1 / x0) ** fraction)
        else:
            ax.set_xlim(x0, x1 + fraction * (x1 - x0))

    extend(most)
    if not place_interior(ax, groups, style, draw=False):
        ax.xaxis.set_major_locator(locator)
        ax.set_xlim(x0, x1)
        return False
    fails, fits = 0.0, most  # the smallest extension that fits, to 1/64 of the most allowed
    for _ in range(6):
        middle = (fails + fits) / 2
        extend(middle)
        if place_interior(ax, groups, style, draw=False):
            fits = middle
        else:
            fails = middle
    extend(fits)
    return place_interior(ax, groups, style)


def _clear_of_data(ax: Axes, key: Key, lines_shown: bool) -> bool:
    ax.figure.canvas.draw()  # type: ignore[union-attr]
    return box_clear(ax, key.bbox(), lines_shown)


def box_clear(ax: Axes, bbox: Bbox, lines_shown: bool, texts: bool = True) -> bool:
    """Whether a box, in display px, keeps clear of every line, marker and bar drawn, and of
    the plot's other text inside it (value labels, notes, a reference line's label)."""
    pad = 2 * ax.figure.dpi / 72  # type: ignore[union-attr]
    box = (bbox.x0 - pad, bbox.y0 - pad, bbox.x1 + pad, bbox.y1 + pad)
    dense, centres = _drawn_points(ax, lines_shown)
    if not all(_rect_dist(pts, box) > 0 for pts in [*dense, *centres]):
        return False
    if not texts:
        return True
    others = [
        t.get_window_extent()
        for t in ax.texts
        if t.get_visible() and t.get_text() and t.get_gid() != KEY
    ]
    return not any(o.overlaps(bbox) and o.bounds != bbox.bounds for o in others)


def legend(
    ax: Axes,
    handles: list[Line2D | Bars],
    names: list[str],
    style: Style,
    title: str | None,
    *,
    taken: list[Key] | None = None,
    lines_shown: bool = True,
    positions: tuple[str, ...] = ("top_right", "top_left", "bottom_right", "bottom_left"),
    inside: bool = True,
) -> Key | None:
    """A key at the first free position of `positions`: inside the plot box, the first whose
    frame no line or marker passes through; outside it, the first not taken (layout makes
    room). None if there's no such position. Keys already placed (`taken`) keep theirs."""
    used = {k.position for k in taken or []}
    key = Key([Entry(n, h) for n, h in zip(names, handles, strict=True)], title, style)
    for position in positions:
        if position in used:
            continue
        if not inside:
            key.place_outside(ax, position)
            return key
        key.place(ax, position)
        if _clear_of_data(ax, key, lines_shown):
            return key
        key.remove()
    return None
