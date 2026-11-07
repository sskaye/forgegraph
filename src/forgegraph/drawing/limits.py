"""Whether computed values are within an axis's limits, allowing for float noise.

Arithmetic on floats leaves noise in the last digits: shares of 201 summed in order total
100.00000000000001, not 100. So a value counts as past a limit only when it's past by more
than TOLERANCE of the span from one limit to the other, measured as the axis draws it: in
powers of ten on a log axis. Every check of a computed value against an axis's limits, or
of a tick against the view, goes through here. Values a spec gives are compared exactly, as
are distances in pixels, which have thresholds of their own.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from forgegraph.spec.parameters import iqr_rule, is_none

TOLERANCE = 1e-9  # of the span from one limit to the other


def outside(values: Any, lo: float, hi: float, log: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Which values are below the lower limit, and which above the upper one, by more than
    TOLERANCE of the span; on a log axis, values of 0 or below are below any limit. Missing
    values are neither."""
    v = np.asarray(values, dtype=float)
    a, b = sorted((float(lo), float(hi)))
    if log:
        positive = v > 0
        v = np.where(positive, np.log10(np.where(positive, v, 1.0)), np.where(v <= 0, -np.inf, v))
        a, b = np.log10(a), np.log10(b)
    slack = TOLERANCE * (b - a)
    return v < a - slack, v > b + slack


def inside(values: Any, lo: float, hi: float, log: bool = False) -> np.ndarray:
    """Which values are from one limit to the other, allowing for float noise (outside);
    missing values aren't."""
    below, above = outside(values, lo, hi, log)
    return ~(below | above) & ~np.isnan(np.asarray(values, dtype=float))


def in_view(axis: Any, values: Any) -> np.ndarray:
    """Which values are within a matplotlib Axis's view, on its scale (inside)."""
    lo, hi = axis.get_view_interval()
    return inside(values, lo, hi, axis.get_scale() == "log")


def ticks_in_view(axis: Any, ticks: list[Any]) -> list[Any]:
    """The Axis's ticks within its view (in_view)."""
    drawn = in_view(axis, [t.get_loc() for t in ticks])
    return [t for t, d in zip(ticks, drawn, strict=True) if d]


def automatic(value: Any) -> bool:
    """Whether an axis limit's value leaves that end automatic, so it can grow for a key, a
    note or a label: None, or an IQR rule, which only narrows the automatic range."""
    return is_none(value) or iqr_rule(value) is not None


def fence(values: Any, k: float, end: str, log: bool = False) -> float:
    """The IQR rule's limit at an end: the lower quartile minus k times the interquartile range,
    or the upper quartile plus it; worked on powers of ten on a log axis."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v) & (v > 0)] if log else v[np.isfinite(v)]
    if not len(v):
        return float("nan")
    w = np.log10(v) if log else v
    q1, q3 = np.percentile(w, [25, 75])
    at = q1 - k * (q3 - q1) if end == "min" else q3 + k * (q3 - q1)
    return float(10**at) if log else float(at)
