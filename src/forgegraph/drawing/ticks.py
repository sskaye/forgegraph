"""Where a linear axis's major ticks go: published "nice number" algorithms.

The theme's axis.tick.algorithm picks one. Each takes the axis's range and a target number of
labels, and returns evenly spaced tick values; ticks outside the axis's range aren't drawn.
The target comes from the axis's length, as matplotlib's own rule has it: as many labels as
fit at about one per three tick-label heights along x and two along y, from 2 to 10.

- extended_wilkinson: Talbot, Lin & Hanrahan, "An Extension of Wilkinson's Algorithm for
  Positioning Tick Labels on Axes", IEEE InfoVis 2010 (ggplot2's default);
- wilkinson: Wilkinson, The Grammar of Graphics, 2nd ed., 2005;
- heckbert: Heckbert, "Nice Numbers for Graph Labels", Graphics Gems, 1990;
- nelder: Nelder, "Algorithm AS 96: A Simple Algorithm for Scaling Graphs", Applied
  Statistics, 1976;
- r_pretty: R's pretty(), base R graphics' rule;
- matplotlib: matplotlib's default (MaxNLocator with steps 1, 2, 2.5, 5, 10).

Log axes have their own algorithms, picked by the theme's axis.tick.log_algorithm (LogTicks):
R's scales::breaks_log, ported with its MIT licence, or matplotlib's LogLocator.

On an axis of whole numbers (an int column, or a categorical axis's positions), every
algorithm keeps to whole-number steps of 1 or more: extended_wilkinson and wilkinson skip
other candidates, heckbert, nelder and r_pretty move to their next whole step, matplotlib's
MaxNLocator takes integer=True, and log axes drop breaks below 1.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import lru_cache, wraps
from itertools import pairwise
from typing import Any, cast

import numpy as np
from matplotlib.ticker import Locator, LogLocator, MaxNLocator

from forgegraph.drawing import text

EPS = 1e-10


def _remembered(algorithm: Callable[..., np.ndarray]) -> Any:
    """A published tick algorithm, remembering what it found: it's a pure function of its
    arguments, and a render asks for the same ticks many times (matplotlib asks the locator
    on every get_major_ticks). Arguments of different types never share an answer, and each
    caller gets its own copy."""
    found = lru_cache(maxsize=1024, typed=True)(algorithm)

    @wraps(algorithm)
    def remembered(*args: Any, **kwargs: Any) -> np.ndarray:
        return found(*args, **kwargs).copy()

    remembered.cache_clear = found.cache_clear  # type: ignore[attr-defined]
    remembered.cache_info = found.cache_info  # type: ignore[attr-defined]
    return remembered


def _whole(step: float) -> bool:
    """A step of 1 or more with no fractional part."""
    return step >= 1 - 1e-9 and abs(step - round(step)) < 1e-9


@_remembered
def extended_wilkinson(
    dmin: float,
    dmax: float,
    m: int,
    Q: tuple[float, ...] = (1, 5, 2, 2.5, 4, 3),
    w: tuple[float, float, float, float] = (0.25, 0.2, 0.5, 0.05),
    integer: bool = False,
) -> np.ndarray:
    """Search steps q·j·10^z and label counts k for the best weighted sum of simplicity,
    coverage, density and legibility, pruning with each term's upper bound. With integer,
    only whole-number steps are candidates."""
    if dmax - dmin < EPS:
        return np.linspace(dmin, dmax, m)
    n = len(Q)

    def simplicity(i: int, j: int, lmin: float, lmax: float, lstep: float) -> float:
        rem = lmin % lstep
        v = 1 if (rem < EPS or lstep - rem < EPS) and lmin <= 0 <= lmax else 0
        return 1 - i / (n - 1) - j + v

    def coverage(lmin: float, lmax: float) -> float:
        r = dmax - dmin
        return 1 - 0.5 * ((dmax - lmax) ** 2 + (dmin - lmin) ** 2) / (0.1 * r) ** 2

    def coverage_max(span: float) -> float:
        r = dmax - dmin
        if span > r:
            half = (span - r) / 2
            return 1 - 0.5 * (2 * half**2) / (0.1 * r) ** 2
        return 1.0

    def density(k: int, lmin: float, lmax: float) -> float:
        r = (k - 1) / (lmax - lmin)
        rt = (m - 1) / (max(lmax, dmax) - min(dmin, lmin))
        return 2 - max(r / rt, rt / r)

    def density_max(k: int) -> float:
        return 2 - (k - 1) / (m - 1) if k >= m else 1.0

    best_score, best = -2.0, (dmin, dmax, (dmax - dmin))
    j = 1
    while True:
        stop = False
        for i, q in enumerate(Q):
            sm = 1 - i / (n - 1) - j + 1
            if w[0] * sm + w[1] + w[2] + w[3] < best_score:
                stop = True
                break
            k = 2
            while True:
                dm = density_max(k)
                if w[0] * sm + w[1] + w[2] * dm + w[3] < best_score:
                    break
                delta = (dmax - dmin) / (k + 1) / j / q
                z = math.ceil(math.log10(delta))
                while True:
                    step = j * q * 10.0**z
                    cm = coverage_max(step * (k - 1))
                    if w[0] * sm + w[1] * cm + w[2] * dm + w[3] < best_score:
                        break
                    if integer and not _whole(step):
                        z += 1
                        continue
                    min_start = math.floor(dmax / step) * j - (k - 1) * j
                    max_start = math.ceil(dmin / step) * j
                    for start in range(min_start, max_start + 1):
                        lmin = start * (step / j)
                        lmax = lmin + step * (k - 1)
                        score = (
                            w[0] * simplicity(i, j, lmin, lmax, step)
                            + w[1] * coverage(lmin, lmax)
                            + w[2] * density(k, lmin, lmax)
                            + w[3]  # legibility, which the published method sets to 1
                        )
                        if score > best_score:
                            best_score, best = score, (lmin, lmax, step)
                    z += 1
                k += 1
        if stop:
            break
        j += 1
    lmin, lmax, step = best
    return np.arange(lmin, lmax + step / 2, step)


@_remembered
def wilkinson(
    dmin: float,
    dmax: float,
    m: int,
    Q: tuple[float, ...] = (1, 5, 2, 2.5, 3, 4, 1.5, 7, 6, 8, 9),
    mincoverage: float = 0.8,
    integer: bool = False,
) -> np.ndarray:
    """For each label count from m/2 to 6m, the step from Q scoring best on granularity
    (closeness to m), roundness (early in Q, including zero) and coverage. With integer,
    only whole-number steps are candidates."""
    steps = (10, *Q)
    best: tuple[float, float, float, float] | None = None  # score, lmin, lmax, step
    for k in range(max(m // 2, 2), math.ceil(6 * m) + 1):
        intervals = k - 1
        granularity = 1 - abs(k - m) / m
        base = 10.0 ** math.floor(math.log10((dmax - dmin) / intervals))
        for i, q in enumerate(steps):
            tdelta = q * base
            if integer and not _whole(tdelta):
                continue
            tmin = math.floor(dmin / tdelta) * tdelta
            tmax = tmin + intervals * tdelta
            if tmax < dmax:
                continue
            roundness = 1 - (i - (1 if tmin <= 0 <= tmax else 0)) / len(steps)
            covered = (dmax - dmin) / (tmax - tmin)
            if covered > mincoverage:
                score = granularity + roundness + covered
                if best is None or score > best[0]:
                    best = (score, tmin, tmax, tdelta)
    if best is None:
        raise ValueError(f"wilkinson: no labelling covers {dmin}..{dmax}")
    _, lmin, lmax, step = best
    return np.arange(lmin, lmax + step / 2, step)


def _nice(x: float, rounded: bool) -> float:
    e = math.floor(math.log10(x))
    f = x / 10.0**e
    if rounded:
        nf = 1 if f < 1.5 else 2 if f < 3 else 5 if f < 7 else 10
    else:
        nf = 1 if f <= 1 else 2 if f <= 2 else 5 if f <= 5 else 10
    return nf * 10.0**e


@_remembered
def heckbert(dmin: float, dmax: float, m: int, integer: bool = False) -> np.ndarray:
    """A nice range, then a nice step for m labels across it (1, 2 or 5 times a power of ten).
    With integer, a step below 1 becomes 1."""
    span = _nice(dmax - dmin, False)
    step = _nice(span / (m - 1), True)
    if integer:
        step = max(step, 1.0)
    lmin, lmax = math.floor(dmin / step) * step, math.ceil(dmax / step) * step
    return np.arange(lmin, lmax + step / 2, step)


@_remembered
def nelder(
    dmin: float,
    dmax: float,
    m: int,
    units: tuple[float, ...] = (1, 1.2, 1.6, 2, 2.5, 3, 4, 5, 6, 8, 10),
    integer: bool = False,
) -> np.ndarray:
    """AS 96: the smallest unit step at least the range over m - 1 intervals, the scale centred
    on the data and moved to zero where zero is within reach. As published, it needn't cover
    the whole range. With integer, the step is the next unit step that's a whole number."""
    tol, bias = 5e-6, 1e-4
    intervals = max(1, m - 1)
    if (dmax - dmin) / (abs(dmax) or 1) <= tol:
        return np.array([dmin])
    raw = (dmax - dmin) / intervals
    s = raw
    while s < 1:
        s *= 10
    while s >= 10:
        s /= 10
    unit = next(u for u in units if s - bias <= u)
    step = raw * unit / s
    if integer and not _whole(step):
        step = min(
            c for c in (u * 10.0**e for e in range(16) for u in units) if c >= step and _whole(c)
        )
    span = step * intervals
    x = 0.5 * (1 + (dmin + dmax - span) / step)
    lmin = step * math.floor(x - bias)
    if dmin >= 0 and span >= dmax:
        lmin = 0.0
    lmax = lmin + span
    if not (dmax > 0 or span < -dmin):
        lmax, lmin = 0.0, -span
    return np.arange(lmin, lmax + step / 2, step)


@_remembered
def r_pretty(dmin: float, dmax: float, m: int, integer: bool = False) -> np.ndarray:
    """R's pretty(): about m - 1 intervals of 1, 2, 5 or 10 times a power of ten,
    preferring 1 and 10. With integer, a unit below 1 becomes 1."""
    n = max(1, m - 1)
    min_n = n // 3
    h, h5 = 1.5, 0.5 + 1.5 * 1.5
    dx = dmax - dmin
    if dx == 0 and dmax == 0:
        cell, small = 1.0, True
    else:
        cell = max(abs(dmin), abs(dmax))
        u = 1 + (1 / (1 + h) if h5 >= 1.5 * h + 0.5 else 1.5 / (1 + h5))
        small = dx < cell * u * max(1, n) * np.finfo(float).eps * 3
    if small:
        if cell > 10:
            cell = 9 + cell / 10
        cell *= 0.75
        if min_n > 1:
            cell /= min_n
    else:
        cell = dx / n if n > 1 else dx
    base = 10.0 ** math.floor(math.log10(cell))
    unit = base
    if 2 * base - cell < h * (cell - unit):
        unit = 2 * base
        if 5 * base - cell < h5 * (cell - unit):
            unit = 5 * base
            if 10 * base - cell < h * (cell - unit):
                unit = 10 * base
    if integer:
        unit = max(unit, 1.0)
    ns, nu = math.floor(dmin / unit + 1e-7), math.ceil(dmax / unit - 1e-7)
    while ns * unit > dmin + 1e-10 * unit:
        ns -= 1
    while nu * unit < dmax - 1e-10 * unit:
        nu += 1
    k = math.floor(0.5 + nu - ns)
    if k < min_n:
        k = min_n - k
        if ns >= 0:
            nu, ns = nu + k // 2, ns - k // 2 - k % 2
        else:
            ns, nu = ns - k // 2, nu + k // 2 + k % 2
    return np.arange(ns, nu + 1) * unit


ALGORITHMS: dict[str, Callable[..., np.ndarray]] = {
    "extended_wilkinson": extended_wilkinson,
    "wilkinson": wilkinson,
    "heckbert": heckbert,
    "nelder": nelder,
    "r_pretty": r_pretty,
}


def target(axis: Any) -> int:
    """How many labels the axis has room for: matplotlib's rule, from 2 to 10 (5 when the
    locator isn't on an axis)."""
    if axis is None:
        return 5
    return int(min(max(axis.get_tick_space(), 2), 10))


class NiceTicks(Locator):
    """Major ticks from one of the published algorithms, by name; with integer, whole-number
    steps only."""

    def __init__(self, algorithm: str, integer: bool = False) -> None:
        if algorithm not in (*ALGORITHMS, "matplotlib"):
            raise ValueError(f"axis.tick.algorithm: unknown algorithm '{algorithm}'")
        self.algorithm = algorithm
        self.integer = integer

    def __call__(self) -> Any:
        axis = cast(Any, self.axis)
        lo, hi = sorted(axis.get_view_interval())
        return self.tick_values(lo, hi)

    def tick_values(self, vmin: float, vmax: float) -> Any:
        lo, hi = sorted((vmin, vmax))
        if self.algorithm == "matplotlib":
            fallback = MaxNLocator(nbins="auto", steps=[1, 2, 2.5, 5, 10], integer=self.integer)
            fallback.set_axis(cast(Any, self.axis))
            return fallback.tick_values(lo, hi)
        ticks = ALGORITHMS[self.algorithm](lo, hi, target(self.axis), integer=self.integer)
        if len(ticks) > 1:  # no 0.30000000000000004; ticks needn't be multiples of the step
            step = abs(ticks[1] - ticks[0])
            ticks = np.round(ticks, max(0, 3 - int(np.floor(np.log10(step)))))
        pad = (hi - lo) * 1e-9
        return ticks[(ticks >= lo - pad) & (ticks <= hi + pad)]


# breaks_log and _log_sub_breaks are a Python port of breaks_log() and log_sub_breaks() in R's
# scales package (https://github.com/r-lib/scales, R/breaks-log.R), under its licence:
#
#   MIT License. Copyright (c) 2025 scales authors.
#
#   Permission is hereby granted, free of charge, to any person obtaining a copy of this
#   software and associated documentation files (the "Software"), to deal in the Software
#   without restriction, including without limitation the rights to use, copy, modify, merge,
#   publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
#   to whom the Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in all copies or
#   substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#   INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
#   PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
#   FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#   OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.


def _clean(values: list[float]) -> list[float]:
    """Values without float noise (3 times 0.1 is 0.3, not 0.30000000000000004)."""
    return [float(f"{v:.12g}") for v in values]


def breaks_log(lo: float, hi: float, n: int, base: int = 10) -> list[float] | None:
    """scales::breaks_log: powers of the base, every one or every few, so that at least n - 2
    fall within lo..hi; failing that, _log_sub_breaks. None where scales falls back to its
    linear breaks."""
    rng = (math.log(lo, base), math.log(hi, base))
    low, high = math.floor(rng[0]), math.ceil(rng[1])
    if high == low:
        return [float(base) ** low]
    by = (high - low) // n + 1
    while True:
        breaks = [float(base) ** k for k in range(low, high + 1, by)]
        if sum(lo <= b <= hi for b in breaks) >= n - 2:
            return _clean(breaks)
        if by <= 1:
            break
        by -= 1  # more breaks: every power, or nearer to it
    return _log_sub_breaks(rng, n, base)


def _log_sub_breaks(rng: tuple[float, float], n: int, base: int) -> list[float] | None:
    """scales::log_sub_breaks: add multiples of each power (from 2 to base - 1), each time
    the one leaving the widest smallest gap on the log scale, until n - 2 fall within the
    range; then keep those, and one more beyond each end."""
    low, high = math.floor(rng[0]), math.ceil(rng[1])
    if base <= 2:
        return [float(base) ** k for k in range(low, high + 1)]
    lo, hi = float(base) ** rng[0], float(base) ** rng[1]
    steps = [1]
    candidates = list(range(2, base))

    def smallest_gap(x: int) -> float:
        logs = [math.log(v, base) for v in sorted([x, *steps, base])]
        return min(b - a for a, b in pairwise(logs))

    breaks: list[float] = []
    inside = 0
    while candidates:
        best = max(candidates, key=smallest_gap)  # the first, as R's which.max, on a tie
        steps.append(best)
        candidates.remove(best)
        breaks = sorted(float(base) ** k * s for k in range(low, high + 1) for s in steps)
        inside = sum(lo <= b <= hi for b in breaks)
        if inside >= n - 2:
            break
    if inside < n - 2:
        return None
    first = min(i for i, b in enumerate(breaks) if lo <= b)
    last = max(i for i, b in enumerate(breaks) if b <= hi)
    return _clean(breaks[max(first - 1, 0) : min(last + 1, len(breaks) - 1) + 1])


LOG_ALGORITHMS = ("breaks_log", "matplotlib")


class LogTicks(Locator):
    """Major ticks on a log axis, by the theme's axis.tick.log_algorithm:

    - breaks_log: R's scales::breaks_log (ggplot2's default for log axes). Its target number
      of breaks is how many ticks the theme's linear algorithm (axis.tick.algorithm) places
      across the axis's log10 range. Where breaks_log gives up (an axis within one power of
      ten), the linear algorithm places the ticks, as scales' own fallback does.
    - matplotlib: matplotlib's LogLocator: powers of ten only, as many as the axis has room
      for. Fewer than two in view, and the linear algorithm places them.

    On an axis, the labels must fit: while the formatted labels would overlap, or come
    within gap points of each other, the algorithm is asked for one tick fewer."""

    def __init__(
        self, algorithm: str, linear: str, gap: float = 0.0, integer: bool = False
    ) -> None:
        if algorithm not in LOG_ALGORITHMS:
            raise ValueError(f"axis.tick.log_algorithm: unknown algorithm '{algorithm}'")
        self.algorithm = algorithm
        self.linear = linear
        self.gap = gap  # points
        self.integer = integer  # an int column: no breaks below 1

    def __call__(self) -> Any:
        axis = cast(Any, self.axis)
        lo, hi = sorted(axis.get_view_interval())
        n = self._count(lo, hi)
        ticks = self._ticks(lo, hi, n)
        while n > 2 and not self._fits(ticks):
            n -= 1
            ticks = self._ticks(lo, hi, n)
        return ticks

    def tick_values(self, vmin: float, vmax: float) -> Any:
        lo, hi = sorted((vmin, vmax))
        return self._ticks(lo, hi, self._count(lo, hi))

    def _linear(self) -> NiceTicks:
        locator = NiceTicks(self.linear)
        if self.axis is not None:
            locator.set_axis(self.axis)
        return locator

    def _count(self, lo: float, hi: float) -> int:
        """The algorithm's target: for breaks_log, the linear algorithm's tick count across
        the log10 range; for matplotlib, the room-based count."""
        if self.algorithm == "breaks_log":
            return len(self._linear().tick_values(math.log10(lo), math.log10(hi)))
        return target(self.axis)

    def _ticks(self, lo: float, hi: float, n: int) -> np.ndarray:
        if self.algorithm == "breaks_log":
            found = breaks_log(lo, hi, n)
            ticks = np.asarray(found if found is not None else self._linear().tick_values(lo, hi))
        else:
            ticks = np.asarray(LogLocator(base=10, numticks=n).tick_values(lo, hi))
            if np.sum((ticks >= lo) & (ticks <= hi)) < 2:
                ticks = self._linear().tick_values(lo, hi)
        ticks = np.asarray(_clean(list(np.asarray(ticks, dtype=float))))  # LogLocator: 9.99e-06
        if self.integer:
            ticks = ticks[ticks >= 1]
        pad = (hi - lo) * 1e-9
        return ticks[(ticks > 0) & (ticks >= lo - pad) & (ticks <= hi + pad)]

    def _fits(self, ticks: np.ndarray) -> bool:
        """Whether these ticks' labels, as the axis formats and draws them, keep gap apart."""
        axis = cast(Any, self.axis)
        figure = axis.axes.figure
        formatter = axis.get_major_formatter()
        formatter.set_locs(ticks)
        sample = axis.get_major_ticks(1)[0].label1
        along_x = axis.axis_name == "x"
        spans = []
        prop = sample.get_fontproperties()
        for v in ticks:
            width, height = text.extent(formatter(v), prop, figure.dpi)
            at = axis.axes.transData.transform((v, 1.0) if along_x else (1.0, v))[
                0 if along_x else 1
            ]
            half = (width if along_x else height) / 2
            spans.append((at - half, at + half))
        gap = self.gap * figure.dpi / 72
        spans.sort()
        return all(b[0] - a[1] >= gap for a, b in pairwise(spans))
