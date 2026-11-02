"""A reference line from an equation (layer_reference.yaml line_1.equation), such as 2x or x^2.

An equation is written in the letter of the axis that isn't the line's: with axis y, it gives y
in terms of x, and with axis x, x in terms of y. It may use numbers, that letter, +, -, *, /, ^
and parentheses, and a number or a parenthesis before what follows it multiplies: 2x^2 - 3x + 1,
2(x + 1). The text is read by the small parser here and never run as code, as a GraphSpec can
come from someone else's pack.

The line and a band's fill are worked out from the axis limits each time they're asked for, so
they run across the plot however the axes are extended. Where the equation has no value, or
jumps from one side of the plot to the other (1/x at 0), the line has a gap.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from typing import Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

Function = Callable[[np.ndarray], np.ndarray]

SAMPLES = 512  # points along the axis: smooth at any size, and a straight line simplifies
_TOKEN = re.compile(r"\s*(\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?|[A-Za-z_]\w*|\S)")


class EquationError(ValueError):
    """An equation that can't be read, with what's wrong."""


def parse(text: str, letter: str) -> Function:
    """The function an equation in the letter gives."""
    tokens = _TOKEN.findall(text)
    if not tokens:
        raise EquationError("it's empty")
    at = 0

    def peek() -> str | None:
        return tokens[at] if at < len(tokens) else None

    def advance() -> str:
        nonlocal at
        at += 1
        return tokens[at - 1]

    def sum_() -> Function:
        out = product()
        while peek() in ("+", "-"):
            sign, a, b = advance(), out, product()
            out = _add(a, b) if sign == "+" else _subtract(a, b)
        return out

    def product() -> Function:
        out = unary()
        while True:
            token = peek()
            if token in ("*", "/"):
                advance()
                a, b = out, unary()
                out = _multiply(a, b) if token == "*" else _divide(a, b)
            elif token is not None and (token == "(" or token[0].isalnum() or token[0] == "."):
                out = _multiply(out, power())  # 2x, 2(x + 1)
            else:
                return out

    def unary() -> Function:
        if peek() == "-":
            advance()
            inner = unary()
            return lambda v: -inner(v)
        return power()

    def power() -> Function:
        base = atom()
        if peek() == "^":
            advance()
            return _power(base, unary())
        return base

    def atom() -> Function:
        token = peek()
        if token is None:
            raise EquationError("it ends too soon")
        advance()
        if token == "(":
            inner = sum_()
            if peek() != ")":
                raise EquationError("a parenthesis isn't closed")
            advance()
            return inner
        if token == letter:
            return lambda v: v
        if token[0].isdigit() or token[0] == ".":
            number = float(token)
            return lambda v: np.full_like(v, number, dtype=float)
        raise EquationError(
            f"'{token}' isn't understood; it may use numbers, {letter}, +, -, *, /, ^ and "
            "parentheses"
        )

    function = sum_()
    if at != len(tokens):
        raise EquationError(
            f"'{tokens[at]}' isn't understood; it may use numbers, {letter}, +, -, *, /, ^ and "
            "parentheses"
        )

    def checked(v: np.ndarray) -> np.ndarray:
        with np.errstate(all="ignore"):
            out = np.asarray(function(np.asarray(v, dtype=float)), dtype=float)
        return np.where(np.isfinite(out), out, np.nan)

    return checked


def _add(a: Function, b: Function) -> Function:
    return lambda v: a(v) + b(v)


def _subtract(a: Function, b: Function) -> Function:
    return lambda v: a(v) - b(v)


def _multiply(a: Function, b: Function) -> Function:
    return lambda v: a(v) * b(v)


def _divide(a: Function, b: Function) -> Function:
    return lambda v: a(v) / b(v)


def _power(a: Function, b: Function) -> Function:
    return lambda v: np.power(a(v), b(v))


def _interval(ax: Axes, axis: str) -> tuple[float, float, bool]:
    """An axis's limits, lowest first, and whether it's a log axis."""
    lo, hi = sorted(ax.get_ylim() if axis == "y" else ax.get_xlim())
    return float(lo), float(hi), (ax.get_yscale() if axis == "y" else ax.get_xscale()) == "log"


def samples(ax: Axes, axis: str, function: Function) -> tuple[np.ndarray, np.ndarray]:
    """The line across the plot: (places along the other axis, values on axis), with gaps as
    nan. A value far outside the plot is held just beyond it, as it isn't seen."""
    lo, hi, log = _interval(ax, "x" if axis == "y" else "y")
    places = np.geomspace(lo, hi, SAMPLES) if log else np.linspace(lo, hi, SAMPLES)
    values = function(places)
    low, high, on_log = _interval(ax, axis)
    if on_log:
        values = np.where(values > 0, values, np.nan)
    above, below = values > high, values < low
    jumps = (above[:-1] & below[1:]) | (below[:-1] & above[1:])
    values[1:][jumps] = np.nan
    reach = high / low if on_log else high - low
    near = (low / reach, high * reach) if on_log else (low - reach, high + reach)
    return places, np.clip(values, *near)


def in_view(ax: Axes, axis: str, function: Function) -> tuple[np.ndarray, np.ndarray]:
    """The points of the line inside the plot."""
    places, values = samples(ax, axis, function)
    low, high, _ = _interval(ax, axis)
    keep = np.isfinite(values) & (values >= low) & (values <= high)
    return places[keep], values[keep]


class EquationLine(Line2D):
    """A line that's worked out across the plot from the axis limits as they are."""

    def __init__(self, ax: Axes, axis: str, function: Function, **style: Any) -> None:
        super().__init__([], [], **style)
        self._ax, self._axis, self._function = ax, axis, function
        self._seen: tuple[Any, ...] | None = None

    def _refresh(self) -> None:
        ax = self._ax
        seen = (ax.get_xlim(), ax.get_ylim(), ax.get_xscale(), ax.get_yscale())
        if seen != self._seen:
            self._seen = seen
            places, values = samples(ax, self._axis, self._function)
            self.set_data(*((places, values) if self._axis == "y" else (values, places)))

    def get_xydata(self) -> Any:
        self._refresh()
        return super().get_xydata()

    def draw(self, renderer: Any) -> None:
        self._refresh()
        super().draw(renderer)


class EquationBand(PolyCollection):
    """The fill between two lines, each from an equation or at a value, worked out across the
    plot from the axis limits as they are."""

    def __init__(self, ax: Axes, axis: str, low: Function, high: Function, **style: Any) -> None:
        super().__init__([np.empty((0, 2))], **style)
        self._ax, self._axis, self._low, self._high = ax, axis, low, high

    def draw(self, renderer: Any) -> None:
        places, a = samples(self._ax, self._axis, self._low)
        _, b = samples(self._ax, self._axis, self._high)
        keep = np.isfinite(a) & np.isfinite(b)
        along = np.r_[places[keep], places[keep][::-1]]
        across = np.r_[a[keep], b[keep][::-1]]
        ends = (along, across) if self._axis == "y" else (across, along)
        self.set_verts([np.c_[ends]])
        super().draw(renderer)


def constant(value: float) -> Function:
    """The function of a line at a value, for a band."""
    return lambda v: np.full_like(v, value, dtype=float)


def angle(ax: Axes, axis: str, place: float, function: Function) -> float:
    """The line's direction at a place on the other axis, in degrees on screen, from
    -90 to 90, so text along it reads upright."""
    lo, hi, log = _interval(ax, "x" if axis == "y" else "y")
    step = (hi / lo) ** (1 / SAMPLES) if log else (hi - lo) / SAMPLES
    near = np.array([place / step, place * step] if log else [place - step, place + step])
    values = function(near)
    points = np.c_[near, values] if axis == "y" else np.c_[values, near]
    (x0, y0), (x1, y1) = ax.transData.transform(points)
    degrees = math.degrees(math.atan2(y1 - y0, x1 - x0))
    return degrees - 180 if degrees > 90 else degrees + 180 if degrees <= -90 else degrees
