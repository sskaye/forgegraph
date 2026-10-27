"""The xy graph type (graph_types/xy.yaml): y against x, one series per group of rows.

`draw()` draws into an Axes it's given, so a layout can place several graphs on one figure;
`place()` and `label()` finish what needs the figure's final size (drawing.layout.finish runs
them). Every graph type's module provides these three.
Every visual value comes from the resolved theme (via Style); nothing here is a style
constant (architecture principle 4).

A GraphSpec lists its series by name (spec/series.py). Each is drawn from its own column,
along the base axis (arrangement.base_axis), with its own settings and its own look: the
theme with the series parameters it sets for itself.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, cast

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator

from forgegraph.drawing import axes as axis_data
from forgegraph.drawing import colorbar, layers, limits, marks, spacing, ticks
from forgegraph.drawing import labels as labelling
from forgegraph.drawing.axes import natural
from forgegraph.drawing.errors import DrawError
from forgegraph.drawing.key import Entry
from forgegraph.drawing.layers import Y_VALUE
from forgegraph.drawing.lint import Issue
from forgegraph.drawing.markup import literal, markup
from forgegraph.drawing.style import LINE_STYLES, MARKERS, Style, unset
from forgegraph.spec.parameters import as_date

SERIES = "__forgegraph_series__"  # the series a long-form row belongs to
COLUMN_NAME = "column_name"
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
SMOOTH_STEPS = 16  # points drawn between neighbouring points on a smooth line


@dataclass(frozen=True)
class Dimension:
    """A style a series sets: its name here, its parameter within a series, the theme's
    choices for it (and what a warning calls them), those choices as matplotlib draws them,
    and a value named in the parameter as matplotlib draws it (None if it isn't one)."""

    by: str
    path: str
    theme_path: str
    words: str
    choices: Callable[[Style], list[Any]]
    named: Callable[[Any], Any]


COLOR = Dimension(
    "color",
    "color",
    "series.colors",
    "colors",
    lambda s: s.series_colors(),
    lambda v: v if isinstance(v, str) and _HEX.match(v) else None,
)
LINE_STYLE = Dimension(
    "line_style",
    "line.style",
    "series.line.styles",
    "line styles",
    lambda s: [LINE_STYLES[v] for v in s.theme["series.line.styles"]],
    lambda v: LINE_STYLES.get(v) if isinstance(v, str) else None,
)
MARKER_SHAPE = Dimension(
    "marker_shape",
    "marker.shape",
    "series.marker.shapes",
    "marker shapes",
    lambda s: [MARKERS[v] for v in s.theme["series.marker.shapes"]],
    lambda v: MARKERS.get(v) if isinstance(v, str) else None,
)
MARKER_FILL = Dimension(
    "marker_fill",
    "marker.fill",
    "series.marker.fills",
    "marker fills",
    lambda s: list(s.theme["series.marker.fills"]),
    lambda v: v if v in ("filled", "open") else None,
)
DIMENSIONS = (COLOR, LINE_STYLE, MARKER_SHAPE, MARKER_FILL)  # in Series' order
STYLED = (LINE_STYLE, MARKER_SHAPE, MARKER_FILL)  # the dimensions a style key explains


__all__ = ["DrawError", "draw", "label", "place"]


@dataclass
class Roles:
    """Which axis series are drawn along (arrangement.base_axis) and which holds their
    values."""

    base: str  # "x" or "y"
    value: str
    base_column: str
    value_columns: list[str]  # the series' columns, each once


@dataclass
class Listed:
    """A series the GraphSpec lists: its name, its settings by path within it, the style it's
    drawn in (the theme with what it sets for itself), its column, and how its rows are
    styled: each dimension's column (SERIES for series), or its value where no column sets
    it."""

    name: str
    values: dict[str, Any]
    style: Style
    column: str
    by: dict[str, str] = field(default_factory=dict)
    fixed: dict[str, Any] = field(default_factory=dict)
    numeric_color: bool = False  # colors on a scale, from numbers
    grouping: list[str] = field(default_factory=list)  # the columns a drawn series' rows share

    def path(self, path: str) -> str:
        """A parameter's path, as an error names it."""
        return f"series.{self.name}.{path}"

    def shows(self, mark: str) -> bool:
        """Whether the series draws its lines, markers or bars."""
        return bool(self.values[f"{mark}.show"])

    @property
    def aggregation(self) -> str | None:
        how = self.values["aggregation.function"]
        return None if unset(how) else str(how)


@dataclass(frozen=True)
class Look:
    """A series' sizes, edges and z-orders, from the theme's series.* parameters, or the
    benchmark's (series.benchmark.*): sizes in points."""

    line_width: float
    line_cap: str
    line_join: str
    marker_size: float
    edge: str  # a filled marker's outline color, or "none"
    edge_width: float
    bar_width: float  # a fraction of the space between places (marks.Spacing)
    bar_gap: float  # the fraction of a side-by-side bar's share left empty
    bar_edge: str
    bar_edge_width: float
    bar_edge_style: str
    bar_join: str
    opacity: float
    line_z: float
    bar_z: float


def _look(style: Style, benchmark: bool) -> Look:
    b = "series.benchmark" if benchmark else "series"
    line = style.line(f"{b}.line")
    edge, bar_edge = style.line(f"{b}.marker.edge"), style.line(f"{b}.bar.edge")
    return Look(
        line.width,
        line.cap,
        line.join,
        style.pt(f"{b}.marker.size"),
        edge.color if edge.visible else "none",
        edge.width,
        float(style.theme[f"{b}.bar.width"]),  # a fraction of the space between places
        float(style.theme["series.bar.gap"]),
        bar_edge.color if bar_edge.visible else "none",
        bar_edge.width,
        bar_edge.style if bar_edge.visible else "solid",
        bar_edge.join,
        float(style.theme[f"{b}.opacity"]),
        3 if benchmark else 2,
        2.8 if benchmark else 1.8,
    )


@dataclass
class Series:
    x: np.ndarray
    y: np.ndarray
    color: str
    linestyle: str
    marker: str
    fill: str  # filled | open
    label: str | None  # its name: the series', its color group's, or the benchmark's
    look: Look
    listed: Listed  # the series the GraphSpec lists that it's drawn for
    benchmark: bool = False
    values: np.ndarray | None = None  # a numeric color column's value at each point
    order: tuple[int, ...] = ()  # position of its groups, for drawing and legend order
    rows: Any = None  # the frame's rows it was drawn from, for layers
    place_column: str = ""  # the frame's base-axis column
    stack: marks.Stacked | None = None  # where its marks start and end (draw)
    shifts: dict[float, tuple[float, float]] = field(default_factory=dict)  # at each place
    spacing: Any = None  # the space between places its bars are fractions of (draw)
    bar_fraction: float = 0.0  # its bars' width, as a fraction of that space

    def shows(self, mark: str) -> bool:
        """Whether it draws its lines, markers or bars."""
        return self.listed.shows(mark)

    @property
    def style(self) -> Style:
        """The style it's drawn in: the theme with what its series sets for itself."""
        return self.listed.style


@dataclass
class Drawn:
    """What drawing did, for the provenance record and warnings."""

    rows_plotted: int = 0
    rows_dropped: dict[str, int] = field(default_factory=dict)
    labelling: str = "none"  # the method actually used
    warnings: list[Issue] = field(default_factory=list)
    kinds: dict[str, str] = field(default_factory=dict)  # each axis's type, by name
    categories: dict[str, list[Any]] = field(default_factory=dict)  # a categorical axis's
    # what place() and label() need from draw(), once the figure's size is final
    series: list[Series] = field(default_factory=list)
    listed: list[Listed] = field(default_factory=list)
    roles: Roles | None = None
    ref_lines: list[layers.RefLine] = field(default_factory=list)
    layers: dict[str, dict[str, Any]] = field(default_factory=dict)  # each layer, by name
    label_groups: list[labelling.Labelled] = field(default_factory=list)
    style_keys: list[StyleKey] = field(default_factory=list)
    y_title: str | None = None  # the value axis's title

    @property
    def lines(self) -> bool:
        """Whether any series draws lines: then lines are obstacles (labels.Obstacles.of)."""
        return any(s.shows("line") for s in self.listed)


@dataclass
class StyleKey:
    """A key explaining the line styles, marker shapes or fills one column sets: its entries,
    its title, and the column (series: the series' names)."""

    entries: list[Entry]
    title: str | None
    column: str

    @property
    def named(self) -> str:
        """The column, as an error names it."""
        return "the series" if self.column == "series" else self.column


def _names(frame: pd.DataFrame) -> str:
    return ", ".join(str(c) for c in frame.columns if not str(c).startswith("__forgegraph"))


def _listed(df: pd.DataFrame, series: dict[str, tuple[dict[str, Any], Style]]) -> list[Listed]:
    """The series the GraphSpec lists, each with its column checked against the data."""
    out = []
    for name, (values, style) in series.items():
        column = name if values["column"] == "name" else str(values["column"])
        if column not in df.columns:
            named = " (column: name, the series' name)" if values["column"] == "name" else ""
            raise DrawError(
                f"series.{name}.column: no column '{column}' in the data{named}; columns are "
                f"{_names(df)}"
            )
        out.append(Listed(name, values, style, column))
    return out


def roles(df: pd.DataFrame, gt: dict[str, Any], listed: list[Listed]) -> Roles:
    """The base axis's column and the series' columns, checked against the data."""
    base = gt["arrangement.base_axis"]
    value = "y" if base == "x" else "x"
    column = gt[f"axis.{base}.data.column"]
    if column not in df.columns:
        raise DrawError(
            f"axis.{base}.data.column: no column '{column}' in the data; columns are {_names(df)}"
        )
    return Roles(base, value, str(column), list(dict.fromkeys(s.column for s in listed)))


def long_form(df: pd.DataFrame, listed: list[Listed]) -> pd.DataFrame:
    """One row per (row, series), with the series' name in SERIES, its value in Y_VALUE and
    the data row's position in layers.ROW."""
    df = cast(pd.DataFrame, df.apply(_clock_time))
    frames = []
    for s in listed:
        part = df.copy()
        part[layers.ROW] = np.arange(len(df))
        part[Y_VALUE] = df[s.column]
        part[SERIES] = s.name
        frames.append(part)
    return pd.concat(frames, ignore_index=True)


def _clock_time(column: pd.Series) -> pd.Series:
    """Times with a time zone as the times their clocks show, which is where they're drawn."""
    if isinstance(column.dtype, pd.DatetimeTZDtype):
        return column.dt.tz_localize(None)
    return column


def _col(frame: pd.DataFrame, name: str) -> pd.Series:
    return cast(pd.Series, frame[name])


def _order(values: pd.Series, how: str) -> list[Any]:
    distinct = list(dict.fromkeys(values.dropna().tolist()))
    return sorted(distinct, key=natural) if how == "sorted" else distinct


def _cycle(items: list[Any], i: int) -> Any:
    return items[i % len(items)]


def build_series(
    df: pd.DataFrame,
    gt: dict[str, Any],
    style: Style,
    drawn: Drawn,
    series: dict[str, tuple[dict[str, Any], Style]],
) -> tuple[list[Series], pd.DataFrame, Roles, _Encodings]:
    """The series to draw, in base and value terms: each Series' x is along the base axis and
    its y along the value axis (arrangement.base_axis); categories are at their positions.
    With them, the frame they're drawn from, the axes' roles, and how the rows were grouped
    and styled."""
    listed = _listed(df, series)
    r = roles(df, gt, listed)
    frame = long_form(df, listed)
    drawn.listed = listed
    kind = _kinds(frame, r, gt, drawn)
    frame = _drawable_rows(frame, r, gt, kind, listed, drawn)
    enc = _encodings(frame, gt, style, listed)
    frame = _category_positions(frame, r, gt, kind, enc, listed, drawn)
    drawn_series = _series(frame, r, enc, listed)
    _group_warnings(enc, listed, drawn)
    return drawn_series, frame, r, enc


@dataclass
class _Encodings:
    """How a frame's rows become series, and how each is styled (build_series)."""

    bench_col: str | None  # SERIES when the benchmark is one of the series
    bench_value: Any
    is_bench: pd.Series  # which rows are the benchmark's
    orders: dict[tuple[str, str], list[Any]]  # each (dimension, column)'s groups, in order
    choices: dict[str, list[Any]]  # each style's choices, by its Dimension's by


def _kinds(frame: pd.DataFrame, r: Roles, gt: dict[str, Any], drawn: Drawn) -> dict[str, str]:
    """Each axis's data type; text that reads as dates is warned of."""
    x, ys = r.base_column, r.value_columns
    kind = {
        r.base: axis_data.data_type(
            _col(frame, x), gt[f"axis.{r.base}.data.type"], f"axis.{r.base}.data.type", x
        ),
        r.value: axis_data.data_type(
            _col(frame, Y_VALUE),
            gt[f"axis.{r.value}.data.type"],
            f"axis.{r.value}.data.type",
            ", ".join(ys),
        ),
    }
    drawn.kinds = kind
    for name, column in ((r.base, x), (r.value, Y_VALUE)):
        if kind[name] == "categorical" and axis_data.reads_as_dates(_col(frame, column)):
            where = f"axis.{name}.data.column" if column == x else "series"
            shown = x if column == x else ", ".join(ys)
            drawn.warnings.append(
                Issue(
                    "dates-as-text",
                    f"{where}: '{shown}' is text that reads as dates; make it a date column "
                    "for a time axis",
                )
            )
    return kind


NOT_DATES = ("sum", "stddev", "stderr", "ci")  # aggregates that dates can't have


def _drawable_rows(
    frame: pd.DataFrame,
    r: Roles,
    gt: dict[str, Any],
    kind: dict[str, str],
    listed: list[Listed],
    drawn: Drawn,
) -> pd.DataFrame:
    """The rows that can be drawn, counting the rest; aggregations and log scales the data
    can't have are errors."""
    x, ys = r.base_column, r.value_columns
    for s in listed:
        how = s.aggregation
        if how is not None and kind[r.value] == "categorical":
            raise DrawError(
                f"{s.path('aggregation.function')}: {how}, but axis.{r.value} is categorical"
            )
        if how in NOT_DATES and kind[r.value] == "date":
            raise DrawError(
                f"{s.path('aggregation.function')}: {how} isn't a date, but axis.{r.value} is "
                "dates; use mean, median, min, max or percentile"
            )
    no_x = _col(frame, x).isna()
    no_y = _col(frame, Y_VALUE).isna()
    if bool(no_x.any()) or bool(no_y.any()):
        drawn.rows_dropped["missing x or y"] = int((no_x | no_y).sum())
    gaps = [s.name for s in listed if s.values["line.missing_values"] == "gap"]
    gap = _col(frame, SERIES).isin(gaps)  # with gap, a missing y breaks the line
    frame = cast(pd.DataFrame, frame.loc[~no_x & (gap | ~no_y)])
    drawn.rows_plotted = int(_col(frame, Y_VALUE).notna().sum())
    for axis, column, name in (
        (f"axis.{r.base}", x, x),
        (f"axis.{r.value}", Y_VALUE, ", ".join(ys)),
    ):
        if gt[f"{axis}.scale"] == "log" and kind[axis[-1]] != "categorical":
            values = axis_data.numbers(_col(frame, column))
            bad = values[values <= 0]  # missing values compare False and are left alone
            if len(bad):
                raise DrawError(
                    f"{axis}.scale: log, but {name} has {len(bad)} values of 0 or below "
                    f"(smallest {bad.min():g}); leave them out of the data, or use linear"
                )

    return frame


def _setting(d: Dimension, s: Listed, frame: pd.DataFrame, style: Style) -> None:
    """How one dimension styles a series' rows: by a column, by series, or one value."""
    value = s.values[d.path]
    if value == "first":
        s.fixed[d.by] = d.choices(style)[0]
    elif value == "series":
        s.by[d.by] = SERIES
    elif (named := d.named(value)) is not None:
        s.fixed[d.by] = named
    elif value not in frame.columns:
        raise DrawError(
            f"{s.path(d.path)}: no column '{value}' in the data; columns are {_names(frame)}"
        )
    else:
        s.by[d.by] = str(value)


def _encodings(
    frame: pd.DataFrame, gt: dict[str, Any], style: Style, listed: list[Listed]
) -> _Encodings:
    """Which columns group and style each series, the benchmark's rows, and each style's
    groups in order."""
    for s in listed:
        for d in DIMENSIONS:
            _setting(d, s, frame, style)
        for p in _splits(s):
            if p not in frame.columns:
                raise DrawError(
                    f"{s.path('split')}: no column '{p}' in the data; columns are {_names(frame)}"
                )
        color_col = s.by.get(COLOR.by)
        data_color = color_col is not None and color_col != SERIES
        numbers = data_color and pd.api.types.is_numeric_dtype(_col(frame, str(color_col)))
        if s.values["color_scale"] == "continuous" and data_color and not numbers:
            raise DrawError(
                f"{s.path('color_scale')}: continuous, but {color_col} isn't numbers; use "
                "categorical or auto"
            )
        s.numeric_color = bool(numbers) and s.values["color_scale"] != "categorical"
        s.grouping = [
            col
            for by, col in s.by.items()
            if not (by == COLOR.by and s.numeric_color and not s.shows("line"))
        ]  # a line joins only one color's points
        s.grouping += [c for c in [*_splits(s), SERIES] if c not in s.grouping]
    numeric = {s.by[COLOR.by] for s in listed if s.numeric_color}
    if len(numeric) > 1:
        raise DrawError(
            f"series: colored on a scale by {', '.join(sorted(numeric))}, but a graph has one "
            "color bar; color them by one column"
        )

    bench_col = gt["benchmark.data_column"]
    bench_value = gt["benchmark.value"]
    is_bench = pd.Series(False, index=frame.index)
    if unset(bench_col):
        bench_col = None
    elif bench_col == "series":
        bench_col = SERIES
        is_bench = _col(frame, SERIES) == str(bench_value)
        if not bool(is_bench.any()):
            names = ", ".join(s.name for s in listed)
            raise DrawError(f"benchmark.value: no series is named '{bench_value}'; they're {names}")
    elif bench_col not in frame.columns:
        raise DrawError(
            f"benchmark.data_column: no column '{bench_col}' in the data; columns are "
            f"{_names(frame)}"
        )
    else:
        bench_col = str(bench_col)
        is_bench = _is_benchmark(_col(frame, bench_col), bench_value)
        if not bool(is_bench.any()):
            raise DrawError(f"benchmark.value: no rows where {bench_col} is '{bench_value}'")
    others = cast(pd.DataFrame, frame.loc[~is_bench])  # the benchmark has its own style
    drawn_names = set(_col(others, SERIES))
    orders: dict[tuple[str, str], list[Any]] = {}
    for s in listed:
        own = cast(pd.DataFrame, others.loc[_col(others, SERIES) == s.name])
        for by, col in s.by.items():
            if by == COLOR.by and s.numeric_color:
                continue
            if col == SERIES:  # the series in the order they're listed
                named = [t.name for t in listed if t.by.get(by) == SERIES]
                orders[by, col] = [n for n in named if n in drawn_names]
                continue
            found = orders.setdefault((by, col), [])
            found += [v for v in _order(_col(own, col), s.values["order"]) if v not in found]
    for (by, col), values in orders.items():
        if col != SERIES:
            how = next(s.values["order"] for s in listed if s.by.get(by) == col)
            orders[by, col] = sorted(values, key=natural) if how == "sorted" else values
    choices = {d.by: d.choices(style) for d in DIMENSIONS}
    return _Encodings(bench_col, bench_value, is_bench, orders, choices)


def _splits(s: Listed) -> list[str]:
    split = s.values["split"]
    return [] if unset(split) else ([split] if isinstance(split, str) else list(split))


def _is_benchmark(values: pd.Series, value: Any) -> pd.Series:
    """Which of a column's values are benchmark.value: in a date column, a date or day number
    drawn at the same place (axes.numbers); otherwise the value as written, or as text. A
    date for a column that isn't dates is an error."""
    if pd.api.types.is_datetime64_any_dtype(values):
        if isinstance(value, str) and as_date(value) is None:
            return pd.Series(False, index=values.index)
        at = axis_data.value_number(value)
        return pd.Series(axis_data.numbers(values) == at, index=values.index)
    if isinstance(value, date):  # YAML's date, not text
        raise DrawError(
            f"benchmark.value: {value} is a date, but benchmark.data_column {values.name} isn't "
            "dates; quote it to match text"
        )
    return (values.astype(str) == str(value)) | (values == value)


def _category_positions(
    frame: pd.DataFrame,
    r: Roles,
    gt: dict[str, Any],
    kind: dict[str, str],
    enc: _Encodings,
    listed: list[Listed],
    drawn: Drawn,
) -> pd.DataFrame:
    """Each categorical axis's categories, in order (the benchmark's at its side), with the
    frame's values replaced by their positions."""
    x = r.base_column
    functions = {s.aggregation for s in listed}
    how = functions.pop() if len(functions) == 1 else None
    grouping = list(dict.fromkeys(c for s in listed for c in s.grouping))
    bench_col, bench_value = enc.bench_col, enc.bench_value
    for name, column in ((r.base, x), (r.value, Y_VALUE)):
        if kind[name] != "categorical":
            continue
        method = gt[f"axis.{name}.data.order.method"]
        other = Y_VALUE if column == x else x
        if method == "value" and kind[r.value if name == r.base else r.base] == "categorical":
            raise DrawError(
                f"axis.{name}.data.order.method: value, but the other axis is categorical too"
            )
        if method == "value":
            totals = frame.groupby([*grouping, column], sort=False, dropna=True)[other]
            per = totals.agg(how if how in ("mean", "median", "sum", "min", "max") else "sum")
            by_frame = per.reset_index()
            cats = axis_data.categories(
                cast(pd.Series, by_frame[column]),
                method,
                gt[f"axis.{name}.data.order.direction"],
                cast(pd.Series, by_frame[other]),
            )
        else:
            cats = axis_data.categories(
                _col(frame, column), method, gt[f"axis.{name}.data.order.direction"]
            )
        if bench_col is not None and bench_col == column:  # the benchmark: its own side
            marked = _is_benchmark(pd.Series(cats), bench_value).tolist()
            bench = [c for c, b in zip(cats, marked, strict=True) if b]
            rest = [c for c in cats if c not in bench]
            cats = bench + rest if gt["benchmark.side"] == "start" else rest + bench
        drawn.categories[name] = cats
        frame = frame.assign(**{column: axis_data.positions(_col(frame, column), cats)})

    return frame


AGGREGATES = {"mean": np.mean, "median": np.median, "sum": np.sum, "min": np.min, "max": np.max}


def _combine(values: np.ndarray, how: str, percentile: float) -> float:
    """The rows at one place, as one value (a series' aggregation.function)."""
    v = values[np.isfinite(values)]
    if not len(v):
        return float("nan")
    if how in ("stddev", "stderr", "ci"):
        return layers.spread(v, how)
    if how == "percentile":
        return float(np.percentile(v, percentile))
    return float(AGGREGATES[how](v))


def _points(rows: pd.DataFrame, x: str, s: Listed) -> tuple[np.ndarray, np.ndarray]:
    """A drawn series' points: one per row, or with an aggregation one per place, its rows'
    aggregate times aggregation.multiplier."""
    how = s.aggregation
    if how is None:
        return axis_data.numbers(_col(rows, x)), axis_data.numbers(_col(rows, Y_VALUE))
    values = pd.Series(axis_data.numbers(_col(rows, Y_VALUE)), index=rows.index)
    percentile = float(s.values["aggregation.percentile"])
    points = values.groupby(_col(rows, x), sort=False, dropna=False).agg(
        lambda v: _combine(np.asarray(v, dtype=float), how, percentile)
    )
    multiplier = float(s.values["aggregation.multiplier"])
    return axis_data.numbers(points.index), np.asarray(points, dtype=float) * multiplier


def _series(frame: pd.DataFrame, r: Roles, enc: _Encodings, listed: list[Listed]) -> list[Series]:
    """One series per group of each listed series' rows, styled by its groups; the benchmark
    last, on top."""
    x = r.base_column
    out: list[Series] = []
    for position, s in enumerate(listed):
        own = _col(frame, SERIES) == s.name
        rows_of = cast(pd.DataFrame, frame.loc[own])
        is_bench = enc.is_bench.loc[own].rename("__bench__")
        groups = rows_of.groupby([*s.grouping, is_bench], sort=False, dropna=False)
        for key, group in groups:
            key = key if isinstance(key, tuple) else (key,)
            values = dict(zip([*s.grouping, "__bench__"], key, strict=True))
            rows = cast(pd.DataFrame, group)
            if s.values["line.connect_order"] == "x":
                rows = rows.sort_values(by=x, kind="stable")
            xs, ys_ = _points(rows, x, s)
            if bool(values["__bench__"]):
                b = s.style.theme
                d = Series(
                    xs,
                    ys_,
                    s.style.palette("series.benchmark.colors")[0],  # each list's first item
                    LINE_STYLES[b["series.benchmark.line.styles"][0]],
                    MARKERS[b["series.benchmark.marker.shapes"][0]],
                    b["series.benchmark.marker.fills"][0],
                    None if enc.bench_col == x else str(enc.bench_value),  # on its axis already
                    _look(s.style, True),
                    s,
                    benchmark=True,
                )
            else:
                index = {
                    by: enc.orders[by, col].index(values[col])
                    if (by, col) in enc.orders and values[col] in enc.orders[by, col]
                    else 0
                    for by, col in s.by.items()
                }
                color, line, shape, fill = (
                    _cycle(enc.choices[dim.by], index[dim.by])
                    if dim.by in s.by
                    else s.fixed[dim.by]
                    for dim in DIMENSIONS
                )
                color_col = s.by.get(COLOR.by)
                label = None if s.numeric_color else s.name
                if color_col is not None and not s.numeric_color:
                    label = str(values[color_col])
                d = Series(
                    xs,
                    ys_,
                    color,
                    line,
                    shape,
                    fill,
                    label,
                    _look(s.style, False),
                    s,
                    values=np.asarray(_col(rows, str(color_col)), dtype=float)
                    if s.numeric_color
                    else None,
                    order=(position, *(index.get(dim.by, 0) for dim in DIMENSIONS)),
                )
            d.rows, d.place_column = rows.index, x
            out.append(d)
    out.sort(key=lambda d: (d.benchmark, d.order))  # group order; the benchmark last, on top
    return out


def _group_warnings(enc: _Encodings, listed: list[Listed], drawn: Drawn) -> None:
    """A style with more groups than the theme has choices repeats them: a warning."""
    for (by, col), groups in enc.orders.items():
        d = next(d for d in DIMENSIONS if d.by == by)
        s = next(s for s in listed if s.by.get(by) == col)
        n, what = len(enc.choices[by]), d.words
        if len(groups) > n:
            drawn.warnings.append(
                Issue(
                    "too-many-groups",
                    f"{s.path(d.path)}: {len(groups)} groups but {n} {what} in "
                    f"{d.theme_path}; {what} repeat",
                )
            )


def _title(value: Any, column: str | None) -> str | None:
    if unset(value):
        return None
    if value == COLUMN_NAME:
        return None if column is None else literal(column)
    return markup(str(value))


def draw(
    ax: Axes,
    df: pd.DataFrame,
    gt: dict[str, Any],
    style: Style,
    title: str | None = None,
    listed: dict[str, dict[str, Any]] | None = None,
    series: dict[str, tuple[dict[str, Any], Style]] | None = None,
) -> Drawn:
    """Draw an xy graph of df into ax, from the graph type's resolved values `gt`, with the
    GraphSpec's layers (`listed`, by name) and series (by name: its values, and the style
    it's drawn in)."""
    drawn = Drawn()
    listed = listed or {}
    drawn_series, frame, r, enc = build_series(df, gt, style, drawn, series or {})
    marks.check(drawn.listed, gt, r.value, drawn.kinds[r.value])
    log_values = gt[f"axis.{r.value}.scale"] == "log"
    stacked = marks.stack(drawn_series, gt["arrangement.stacking"], log_values)
    for s, st in zip(drawn_series, stacked, strict=True):
        s.stack, s.y = st, st.top  # lines and markers sit at the top of their stack
    places = [p for s in drawn_series for p in marks.numbers(s.x)]
    space = marks.Spacing(ax, r.base, np.asarray(places, dtype=float))
    for s in drawn_series:
        s.spacing = space
    for s, shifts in zip(drawn_series, marks.slots(drawn_series, gt), strict=True):
        s.shifts = shifts
    drawn.label_groups, norm = _draw_marks(ax, drawn_series, style, r)
    layers.error_bars(ax, listed, drawn_series, frame, gt, style, r)
    lines = layers.reference_lines(ax, listed, drawn_series, frame, style, drawn.kinds)
    _axes(ax, drawn_series, lines, gt, style, drawn, r)
    drawn.y_title = _decorate(ax, gt, style, r, title, norm, drawn.listed)
    drawn.series, drawn.roles, drawn.ref_lines, drawn.layers = drawn_series, r, lines, listed
    drawn.style_keys = _style_keys(gt, enc, style, drawn.listed)
    layers.notes_outside(ax, listed, style)
    return drawn


def _as_xy(r: Roles, base: Any, value: Any) -> tuple[Any, Any]:
    """Base and value as x and y."""
    return (base, value) if r.base == "x" else (value, base)


def _path(
    base: np.ndarray, value: np.ndarray, how: str, where: str
) -> tuple[np.ndarray, np.ndarray, list[int] | None]:
    """A line's vertices, in base and value terms, as line.interpolate joins its points, and
    which of them are the points (None: all of them)."""
    if how == "linear" or len(base) < 2:
        return base, value, None
    if how == "smooth":
        return _smooth(base, value, where)
    b, v, marked = [base[0]], [value[0]], [0]
    for i in range(1, len(base)):
        b0, v0, b1, v1 = base[i - 1], value[i - 1], base[i], value[i]
        if how == "step_after":  # flat until the next point
            b += [b1, b1]
            v += [v0, v1]
        elif how == "step_before":  # at the next point's value from the start
            b += [b0, b1]
            v += [v1, v1]
        else:  # step_center: the step midway
            middle = (b0 + b1) / 2
            b += [middle, middle, b1]
            v += [v0, v1, v1]
        marked.append(len(b) - 1)
    return np.asarray(b, dtype=float), np.asarray(v, dtype=float), marked


def _smooth(
    base: np.ndarray, value: np.ndarray, where: str
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """A smooth curve through the points: piecewise monotone cubic (Fritsch & Carlson 1980),
    so it never overshoots them; a missing value breaks it."""
    steps = np.diff(base)
    finite = steps[np.isfinite(steps)]
    if len(finite) and not ((finite > 0).all() or (finite < 0).all()):
        raise DrawError(
            f"{where}: smooth needs the points in order along the base axis, one at each "
            "place; set line.connect_order to x, and aggregation to combine rows at one place"
        )
    b_out: list[float] = []
    v_out: list[float] = []
    marked: list[int] = []
    start = 0
    for stop in [*np.flatnonzero(~np.isfinite(value)).tolist(), len(value)]:
        if stop > start:
            bs, vs, at = _monotone(base[start:stop], value[start:stop])
            marked += [len(b_out) + i for i in at]
            b_out += bs.tolist()
            v_out += vs.tolist()
        if stop < len(value):  # the missing value, which breaks the line
            b_out.append(float(base[stop]))
            v_out.append(float("nan"))
        start = stop + 1
    return np.asarray(b_out, dtype=float), np.asarray(v_out, dtype=float), marked


def _monotone(b: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Points along a monotone cubic through (b, v), and which of them are (b, v)."""
    if len(b) < 3:
        return b, v, list(range(len(b)))
    h = np.diff(b)
    delta = np.diff(v) / h
    m = np.empty(len(b))
    m[0], m[-1] = delta[0], delta[-1]
    m[1:-1] = np.where(delta[:-1] * delta[1:] > 0, (delta[:-1] + delta[1:]) / 2, 0.0)
    for k in range(len(delta)):
        if delta[k] == 0:
            m[k] = m[k + 1] = 0.0
            continue
        a, c = m[k] / delta[k], m[k + 1] / delta[k]
        if a * a + c * c > 9:  # keeps the curve between the points' values
            t = 3 / np.hypot(a, c)
            m[k], m[k + 1] = t * a * delta[k], t * c * delta[k]
    t = np.linspace(0, 1, SMOOTH_STEPS + 1)[:-1]
    h00, h10 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t
    h01, h11 = -2 * t**3 + 3 * t**2, t**3 - t**2
    bs = [b[k] + t * h[k] for k in range(len(h))] + [b[-1:]]
    vs = [
        h00 * v[k] + h10 * h[k] * m[k] + h01 * v[k + 1] + h11 * h[k] * m[k + 1]
        for k in range(len(h))
    ] + [v[-1:]]
    return np.concatenate(bs), np.concatenate(vs), [k * SMOOTH_STEPS for k in range(len(b))]


def _draw_marks(
    ax: Axes, series: list[Series], style: Style, r: Roles
) -> tuple[list[labelling.Labelled], Normalize | None]:
    """Each series' line, markers and bars (a numeric color column's markers on its color
    scale); returns the names to label, with what's drawn under each, and the color scale's
    range, if there is one."""
    cmap, norm = style.colormap(), None
    if any(s.values is not None for s in series):
        all_values = np.concatenate([s.values for s in series if s.values is not None])
        norm = Normalize(float(np.nanmin(all_values)), float(np.nanmax(all_values)))
    handles: dict[str, Line2D | marks.Bars] = {}
    paths: dict[str, list[np.ndarray]] = {}
    colors: dict[str, Any] = {}
    for s in series:
        look = s.look
        lines_shown, markers_shown = s.shows("line"), s.shows("marker")
        line_color = s.color
        if s.values is not None and norm is not None:
            line_color = cmap(norm(float(np.nanmean(s.values))))
        open_marker = s.fill == "open"
        rim, rim_width = look.edge, look.edge_width
        px, py = _as_xy(r, s.x, s.y)
        how = s.listed.values["line.interpolate"] if lines_shown else "linear"
        where = s.listed.path("line.interpolate")
        base, value, marked = _path(np.asarray(s.x, float), np.asarray(s.y, float), how, where)
        lx, ly = _as_xy(r, base, value)
        (line,) = ax.plot(
            lx,
            ly,
            color=line_color,
            linestyle=s.linestyle if lines_shown else "none",
            linewidth=look.line_width,
            solid_capstyle=cast(Any, look.line_cap),
            solid_joinstyle=cast(Any, look.line_join),
            dash_joinstyle=cast(Any, look.line_join),
            alpha=look.opacity,
            marker=s.marker if markers_shown and s.values is None else "none",
            markevery=marked,
            markersize=look.marker_size,
            markerfacecolor="none" if open_marker else line_color,
            markeredgecolor=line_color if (open_marker or rim == "none") else rim,
            markeredgewidth=rim_width if (open_marker or rim != "none") else 0.0,
            zorder=look.line_z,
        )
        line.set_transform(marks.shifted(ax, r.base, s.shifts, s.spacing))
        handle = line
        if s.shows("bar"):
            bar = marks.bars(ax, s, r.base, line_color)
            if not (lines_shown or markers_shown):
                handle = bar  # the key's sample is a swatch of the bar
        if s.values is not None and markers_shown and norm is not None:
            dots = ax.scatter(
                px,
                py,
                c=s.values,
                cmap=cmap,
                norm=norm,
                marker=s.marker,
                s=look.marker_size**2,
                edgecolors="none" if look.edge == "none" else look.edge,
                linewidths=look.edge_width,
                alpha=look.opacity,
                zorder=2.5,
            )
            dots.set_offset_transform(marks.shifted(ax, r.base, s.shifts, s.spacing))
        if s.label is not None:
            handles.setdefault(s.label, handle)
            colors.setdefault(s.label, line_color)
            paths.setdefault(s.label, []).append(
                np.c_[axis_data.numbers(lx), axis_data.numbers(ly)]
            )
    groups = [labelling.Labelled(n, colors[n], paths[n], handles[n]) for n in handles]
    return groups, norm


def _axes(
    ax: Axes,
    series: list[Series],
    lines: list[layers.RefLine],
    gt: dict[str, Any],
    style: Style,
    drawn: Drawn,
    r: Roles,
) -> None:
    """Each axis's scale, ticks and limits: bars stand on the value axis, and an automatic
    axis reaches every reference line."""
    ax.set_xscale(gt["axis.x.scale"])
    ax.set_yscale(gt["axis.y.scale"])
    for name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
        along = [np.asarray(_as_xy(r, s.x, s.y)[0 if name == "x" else 1]) for s in series]
        values = axis_data.numbers(np.concatenate(along)) if along else np.array([])
        kind = drawn.kinds[name]
        axis_data.ticks_and_labels(ax, name, kind, gt, style, drawn.categories.get(name), values)
        if kind == "categorical":
            if not (unset(gt[f"axis.{name}.min"]) and unset(gt[f"axis.{name}.max"])):
                raise DrawError(
                    f"axis.{name}.min, max: the axis is categorical, so they don't apply"
                )
            axis.set_minor_locator(NullLocator())
            n = len(drawn.categories[name])
            (ax.set_xlim if name == "x" else ax.set_ylim)(-0.5, n - 0.5)
        else:
            ticks.minor_ticks(axis, style)
    _limits(ax, gt, drawn.kinds)
    with_bars = [s for s in series if s.shows("bar")]
    if with_bars and unset(gt[f"axis.{r.value}.min"]):  # bars stand on the axis
        log = gt[f"axis.{r.value}.scale"] == "log"
        floor = 1.0 if log else 0.0
        get = ax.get_ylim if r.value == "y" else ax.get_xlim
        put = ax.set_ylim if r.value == "y" else ax.set_xlim
        stacks = [np.r_[s.stack.bottom, s.stack.top] for s in with_bars if s.stack is not None]
        ends = np.asarray(np.concatenate(stacks) if stacks else [], dtype=float)
        ends = ends[~np.isnan(ends)]
        if len(ends) and not limits.outside(ends, floor, max(ends.max(), floor), log)[0].any():
            put(floor, get()[1])
    layers.include(ax, lines, gt)


def _decorate(
    ax: Axes,
    gt: dict[str, Any],
    style: Style,
    r: Roles,
    title: str | None,
    norm: Normalize | None,
    listed: list[Listed],
) -> str | None:
    """The axis titles and the title, the plot box's sides and ticks, the grid, and the
    color bar for a color scale's range (norm); returns the value axis's title."""
    columns = {r.base: [r.base_column], r.value: r.value_columns}
    xt = _title(gt["axis.x.title"], columns["x"][0] if len(columns["x"]) == 1 else None)
    yt = _title(gt["axis.y.title"], columns["y"][0] if len(columns["y"]) == 1 else None)
    titled = style.font("axis.title")
    if xt:
        ax.set_xlabel(xt, fontproperties=titled)
    if yt:
        ax.set_ylabel(yt, fontproperties=titled)
    if title:
        ax.set_title(markup(title))
        spacing.align_title(ax, style)
    _box_and_ticks(ax, style)
    shown = [a for a in ("x", "y") if bool(style.theme[f"grid.{a}.show"])]
    if shown:
        ax.grid(True, axis=cast(Any, "both" if len(shown) == 2 else shown[0]))
        ax.set_axisbelow(True)
    if norm is not None:
        color_col = next(s.by[COLOR.by] for s in listed if s.numeric_color)
        bar_title = _title(gt["legend.color_bar.title.text"], color_col)
        colorbar.add(ax, norm, style.colormap(), bar_title, style)
    return yt if r.value == "y" else xt


def place(ax: Axes, drawn: Drawn, gt: dict[str, Any], style: Style) -> bool:
    """What needs the figure's final size: bars' room, value labels and reference lines'
    labels. True if an axis was widened, so the figure must be laid out again."""
    r = cast(Roles, drawn.roles)  # draw() set it
    marks.check_room(ax, drawn.series, gt, r.base)
    widened = marks.value_labels(ax, drawn.series, gt, r.base, drawn.kinds[r.value])
    return layers.label_lines(ax, drawn.ref_lines, gt, style, drawn.lines) or widened


def label(ax: Axes, drawn: Drawn, gt: dict[str, Any], style: Style) -> None:
    """Name the series (legend.method), explain styles, then place notes inside the plot, all
    after the figure's size is final. Keys go first, since they need a corner and a note has
    six places. Anything that can't be placed cleanly is an error, never a fallback. What an
    earlier label() placed is taken away first, to place it again after the layout changed."""
    labelling.unplace(ax)
    layers.unplace_notes(ax)
    axis_data.check_fit(ax, gt, style)
    _name_series(ax, drawn, gt, style)
    layers.notes_inside(ax, drawn.layers, gt, style, drawn.lines)


def _legend_column(listed: list[Listed]) -> str | None:
    """The column the series' names come from, when their colors all come from one."""
    colors = {s.by.get(COLOR.by) for s in listed}
    one = colors.pop() if len(colors) == 1 else None
    return None if one is None or one == SERIES else one


def _name_series(ax: Axes, drawn: Drawn, gt: dict[str, Any], style: Style) -> None:
    groups = drawn.label_groups
    with_lines = drawn.lines  # whether lines are obstacles: labels.Obstacles.of
    taken: list = []
    where = {
        "positions": tuple(gt["legend.key.positions"]),
        "inside": bool(gt["legend.key.inside"]),
    }
    title = gt["legend.key.title.text"]
    one_title = not (unset(title) or title == COLUMN_NAME)  # a text: it can title one key

    def one_key(count: int) -> None:
        if one_title and count > 1:
            raise DrawError(
                f"legend.key.title.text: '{title}' titles one key, but {count} are drawn; use "
                "column_name, for each key its own column's name, or None"
            )

    one_key(len(drawn.style_keys))
    for style_key in drawn.style_keys:
        key = labelling.legend(
            ax,
            style_key.entries,
            style,
            style_key.title,
            taken=taken,
            lines=with_lines,
            **where,
        )
        if key is None:
            raise DrawError(
                f"style key for {style_key.named}: no position in legend.key.positions is free "
                "and clear of data; add positions, put keys outside (legend.key.inside: false), "
                "widen the format or set the plot's limits to leave room"
            )
        taken.append(key)
    method = gt["legend.method"]
    y_title = drawn.y_title
    if method == "none" or not groups or ([g.name for g in groups] == [y_title]):
        drawn.labelling = "none"  # one series named by the y-axis title already
        return
    allowed = [m for m in style.theme["legend.methods"] if m not in ("auto", "none")]
    if any(s.shows("bar") for s in drawn.listed):  # names beside bars would need rules
        if method == "direct":
            raise DrawError("legend.method: direct isn't available with bars; use key or auto")
        allowed = [m for m in allowed if m != "direct"]
    tries = allowed if method == "auto" else [method]
    legend_title = _title(title, _legend_column(drawn.listed))
    for m in tries:
        if m == "direct" and labelling.interior(ax, groups, style):
            drawn.labelling = "direct"
            return
        if m == "key":
            one_key(len(drawn.style_keys) + 1)
            leg = labelling.legend(
                ax,
                [Entry(g.name, g.handle) for g in groups],
                style,
                legend_title,
                taken=taken,
                lines=with_lines,
                **where,
            )
            if leg is not None:
                drawn.labelling = "key"
                return
    if method == "auto":
        raise DrawError(
            f"legend.method: auto, but no labelling method fits ({', '.join(tries)} tried); "
            "put the key outside (legend.key.inside: false), widen the format, draw fewer series, "
            "or set axis.x.min/max or axis.y.min/max to leave room for a key"
        )
    other = [m for m in allowed if m != method]
    hint = (
        f"use auto, or {' or '.join(other)}"
        if other
        else (
            "put the key outside (legend.key.inside: false), widen the format, draw fewer "
            "series, or set axis.x.min/max or axis.y.min/max to leave room for it"
        )
    )
    why = ""
    if method == "key":  # the style keys placed first may have taken the free positions
        took = ", ".join(
            f"the style key for {k.named} took {key.position}"
            for k, key in zip(drawn.style_keys, taken, strict=True)
        )
        why = ": every position in legend.key.positions is taken or covers data" + (
            f" ({took})" if took else ""
        )
    raise DrawError(f"legend.method: {method} doesn't fit this graph{why}; {hint}")


def _style_keys(
    gt: dict[str, Any], enc: _Encodings, style: Style, listed: list[Listed]
) -> list[StyleKey]:
    """Keys explaining line styles, marker shapes and fills a column (or series) sets, where
    it isn't the column the series' colors come from: one per styling column, titled by
    legend.key.title.text. Their entries are the groups the series were styled by
    (enc.orders), so not the benchmark, which has its own style and is named by
    legend.method. Their samples are in the one series' color, or with several colors in
    text.color, neutral among them; their markers are the size the first series they style
    draws."""
    styled: dict[str, list[str]] = {}  # each styling column's dimensions
    for s in listed:
        for d in STYLED:
            col = s.by.get(d.by)
            if col is not None and col != s.by.get(COLOR.by) and d.by not in styled.get(col, []):
                styled.setdefault(col, []).append(d.by)
    one = listed[0].fixed.get(COLOR.by, _cycle(COLOR.choices(style), 0)) if listed else None
    colored = len(listed) > 1 or any(s.by.get(COLOR.by) not in (None, SERIES) for s in listed)
    ink = style.color("text.color") if colored else one
    found = []
    for column, bys in styled.items():
        users = [s for s in listed if any(s.by.get(b) == column for b in bys)]
        size = users[0].style.pt("series.marker.size")
        lines = any(s.shows("line") for s in users)
        markers = any(s.shows("marker") for s in users)
        entries = []
        for i, value in enumerate(enc.orders.get((bys[0], column), [])):
            ls, mk, fill = (
                _cycle(enc.choices[d.by], i if d.by in bys else 0)
                if d.by in bys or d.by not in users[0].fixed
                else users[0].fixed[d.by]
                for d in STYLED
            )
            handle = Line2D(
                [],
                [],
                color=ink,
                linestyle=cast(Any, ls if lines else "none"),
                marker=mk if markers else "none",
                markersize=size,
                markerfacecolor="none" if fill == "open" else ink,
                markeredgecolor=ink,
            )
            entries.append(Entry(literal(str(value)), handle))
        name = "series" if column == SERIES else column
        title = _title(gt["legend.key.title.text"], None if column == SERIES else column)
        if entries:  # none when every row is the benchmark's
            found.append(StyleKey(entries, title, name))
    return found


def _limits(ax: Axes, gt: dict[str, Any], kinds: dict[str, str]) -> None:
    """Each axis's set min and max: numbers, or dates on a date axis (axes.on_axis)."""
    for axis in ("x", "y"):
        lo, hi = gt[f"axis.{axis}.min"], gt[f"axis.{axis}.max"]
        if unset(lo) and unset(hi):
            continue
        get = ax.get_xlim if axis == "x" else ax.get_ylim
        put = ax.set_xlim if axis == "x" else ax.set_ylim
        at = [
            now if unset(v) else axis_data.on_axis(v, axis, kinds[axis], f"axis.{axis}.{end}")
            for end, v, now in zip(("min", "max"), (lo, hi), get(), strict=True)
        ]
        put(*at)


def _box_and_ticks(ax: Axes, style: Style) -> None:
    sides = style.theme["plot_area.border.sides"]
    sides = [] if unset(sides) else list(sides)
    border = style.line("plot_area.border")
    for side in ("left", "bottom", "top", "right"):
        spine = ax.spines[side]
        spine.set_visible(side in sides and border.visible)
        spine.set_linestyle(cast(Any, border.style if border.visible else "solid"))
        spine.set_capstyle(cast(Any, border.cap))
    ticks = style.theme["axis.tick.sides"]
    ticks = [] if unset(ticks) else list(ticks)
    ax.tick_params(
        which="both",
        left="left" in ticks,
        right="right" in ticks,
        top="top" in ticks,
        bottom="bottom" in ticks,
        labelleft="left" in ticks,
        labelright="right" in ticks,
        labeltop="top" in ticks,
        labelbottom="bottom" in ticks,
    )
