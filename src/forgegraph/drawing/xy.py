"""The xy graph type (graph_types/xy.yaml): y against x, one series per group of rows.

`draw()` draws into an Axes it's given, so a layout can place several graphs on one figure;
`place()` and `label()` finish what needs the figure's final size (drawing.layout.finish runs
them). Every graph type's module provides these three.
Every visual value comes from the resolved theme (via Style); nothing here is a style
constant (architecture principle 4).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.ticker import NullLocator

from forgegraph.drawing import axes as axis_data
from forgegraph.drawing import colorbar, layers, limits, marks, ticks
from forgegraph.drawing import labels as labelling
from forgegraph.drawing.axes import natural
from forgegraph.drawing.errors import DrawError
from forgegraph.drawing.key import Entry
from forgegraph.drawing.layers import Y_VALUE
from forgegraph.drawing.lint import Issue
from forgegraph.drawing.markup import literal, markup
from forgegraph.drawing.style import LINE_STYLES, MARKERS, Style, unset

Y_COLUMN = "__forgegraph_y_column__"  # the y column a long-form row came from
COLUMN_NAME = "column_name"


@dataclass(frozen=True)
class Dimension:
    """A style a column can set: its name here, its parameter, the theme's choices for it
    (and what a warning calls them), and those choices as matplotlib draws them."""

    by: str
    encoding_path: str
    theme_path: str
    words: str
    choices: Callable[[Style], list[Any]]


COLOR = Dimension(
    "color_by", "encoding.color.column", "series.colors", "colors", lambda s: s.series_colors()
)
LINE_STYLE = Dimension(
    "line_style_by",
    "encoding.line.style.column",
    "series.line.style",
    "line styles",
    lambda s: [LINE_STYLES[v] for v in s.theme["series.line.style"]],
)
MARKER_SHAPE = Dimension(
    "marker_shape_by",
    "encoding.marker.shape.column",
    "series.marker.shape",
    "marker shapes",
    lambda s: [MARKERS[v] for v in s.theme["series.marker.shape"]],
)
MARKER_FILL = Dimension(
    "marker_fill_by",
    "encoding.marker.fill.column",
    "series.marker.fill",
    "marker fills",
    lambda s: list(s.theme["series.marker.fill"]),
)
DIMENSIONS = (COLOR, LINE_STYLE, MARKER_SHAPE, MARKER_FILL)  # in Series' order


__all__ = ["DrawError", "draw", "label", "place"]


@dataclass
class Roles:
    """Which axis series are drawn along (series.base_axis) and which holds their values."""

    base: str  # "x" or "y"
    value: str
    base_column: str
    value_columns: list[str]


@dataclass(frozen=True)
class Look:
    """A series' sizes, edges and z-orders, from the theme's series.* parameters, or the
    benchmark's (series.benchmark.*): sizes in points."""

    line_width: float
    marker_size: float
    edge: str  # a filled marker's outline color, or "none"
    edge_width: float
    bar_width: float
    bar_edge: str
    bar_edge_width: float
    line_z: float
    bar_z: float


def _look(style: Style, benchmark: bool) -> Look:
    b = "benchmark." if benchmark else ""
    return Look(
        style.pt(f"series.{b}line.width"),
        style.pt(f"series.{b}marker.size"),
        style.color(f"series.{b}marker.edge.color"),
        style.pt(f"series.{b}marker.edge.width"),
        style.pt(f"series.{b}bar.width"),
        style.color(f"series.{b}bar.edge.color"),
        style.pt(f"series.{b}bar.edge.width"),
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
    label: str | None  # the color group's name, or the benchmark's
    look: Look
    benchmark: bool = False
    values: np.ndarray | None = None  # a numeric encoding.color.column's value at each point
    order: tuple[int, ...] = ()  # position of its groups, for drawing and legend order
    rows: Any = None  # the frame's rows it was drawn from, for layers
    place_column: str = ""  # the frame's base-axis column
    stack: marks.Stacked | None = None  # where its marks start and end (draw)
    shifts: dict[float, float] = field(default_factory=dict)  # its offset at each place (draw)


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
    roles: Roles | None = None
    ref_lines: list[layers.RefLine] = field(default_factory=list)
    layers: dict[str, dict[str, Any]] = field(default_factory=dict)  # each layer, by name
    label_groups: list[labelling.Labelled] = field(default_factory=list)
    style_keys: list[StyleKey] = field(default_factory=list)
    y_title: str | None = None  # the value axis's title


@dataclass
class StyleKey:
    """A key explaining the line styles, marker shapes or fills one column sets: its entries,
    its title, and the column (column_name: the y columns' names)."""

    entries: list[Entry]
    title: str | None
    column: str

    @property
    def named(self) -> str:
        """The column, as an error names it."""
        return "column names" if self.column == COLUMN_NAME else self.column


def _column(gt: dict[str, Any], path: str, frame: pd.DataFrame) -> str | None:
    """A "by" or benchmark column's name in the long-form frame, or None."""
    name = gt[path]
    if unset(name):
        return None
    if name == COLUMN_NAME:
        return Y_COLUMN
    if name not in frame.columns:
        raise DrawError(f"{path}: no column '{name}' in the data; columns are {_names(frame)}")
    return str(name)


def _names(frame: pd.DataFrame) -> str:
    return ", ".join(str(c) for c in frame.columns if not str(c).startswith("__forgegraph"))


def roles(df: pd.DataFrame, gt: dict[str, Any]) -> Roles:
    """The base axis's column and the value axis's columns, checked against the data."""
    base = gt["series.base_axis"]
    value = "y" if base == "x" else "x"
    listed = {}
    for name in ("x", "y"):
        columns = gt[f"axis.{name}.data.column"]
        listed[name] = [columns] if isinstance(columns, str) else list(columns)
        missing = [n for n in listed[name] if n not in df.columns]
        if missing:
            raise DrawError(
                f"axis.{name}.data.column: no column '{missing[0]}' in the data; columns are "
                f"{_names(df)}"
            )
    if len(listed[base]) > 1:
        raise DrawError(
            f"axis.{base}.data.column: series are drawn along {base} (series.base_axis), so it "
            f"takes one column, not {len(listed[base])}"
        )
    return Roles(base, value, str(listed[base][0]), [str(c) for c in listed[value]])


def long_form(df: pd.DataFrame, gt: dict[str, Any]) -> tuple[pd.DataFrame, Roles]:
    """One row per (row, value column), with the value column's name in Y_COLUMN and the
    data row's position in layers.ROW."""
    r = roles(df, gt)
    df = cast(pd.DataFrame, df.apply(_clock_time))
    frames = []
    for y in r.value_columns:
        part = df.copy()
        part[layers.ROW] = np.arange(len(df))
        part[Y_VALUE] = df[y]
        part[Y_COLUMN] = y
        frames.append(part)
    return pd.concat(frames, ignore_index=True), r


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
    df: pd.DataFrame, gt: dict[str, Any], style: Style, drawn: Drawn
) -> tuple[list[Series], pd.DataFrame, Roles]:
    """The series to draw, in base and value terms: each Series' x is along the base axis and
    its y along the value axis (series.base_axis); categories are at their positions."""
    frame, r = long_form(df, gt)
    kind = _kinds(frame, r, gt, drawn)
    frame = _drawable_rows(frame, r, gt, kind, drawn)
    enc = _encodings(frame, gt, style)
    frame = _category_positions(frame, r, gt, kind, enc, drawn)
    series = _series(frame, r, gt, style, enc)
    _group_warnings(enc, drawn)
    return series, frame, r


@dataclass
class _Encodings:
    """How a frame's rows become series, and how each is styled (build_series)."""

    by: dict[str, str | None]  # each style's column, by its Dimension's by
    path_columns: list[str]  # encoding.detail.column
    bench_col: str | None
    bench_value: Any
    numeric_color: bool  # colors on a scale, from numbers
    is_bench: pd.Series  # which rows are the benchmark's
    orders: dict[str, list[Any]]  # each style's groups, in order
    grouping: list[str]  # the columns a series' rows share
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
            shown = x if column == x else ", ".join(ys)
            drawn.warnings.append(
                Issue(
                    "dates-as-text",
                    f"axis.{name}.data.column: '{shown}' is text that reads as dates; make it a "
                    "date column for a time axis",
                )
            )
    return kind


def _drawable_rows(
    frame: pd.DataFrame, r: Roles, gt: dict[str, Any], kind: dict[str, str], drawn: Drawn
) -> pd.DataFrame:
    """The rows that can be drawn, counting the rest; aggregations and log scales the data
    can't have are errors."""
    x, ys = r.base_column, r.value_columns
    aggregation = gt[f"axis.{r.value}.data.aggregation"]
    if gt[f"axis.{r.base}.data.aggregation"] != "none":
        raise DrawError(
            f"axis.{r.base}.data.aggregation: series are drawn along {r.base}, so its values are "
            f"where points go; aggregate the values instead, with axis.{r.value}.data.aggregation"
        )
    if aggregation != "none" and kind[r.value] == "categorical":
        raise DrawError(
            f"axis.{r.value}.data.aggregation: {aggregation}, but the axis is categorical"
        )
    no_x = _col(frame, x).isna()
    no_y = _col(frame, Y_VALUE).isna()
    if bool(no_x.any()) or bool(no_y.any()):
        drawn.rows_dropped["missing x or y"] = int((no_x | no_y).sum())
    gap = gt["mark.line.missing_values"] == "gap"
    keep = ~no_x if gap else ~(no_x | no_y)  # with gap, a missing y breaks the line
    frame = cast(pd.DataFrame, frame.loc[keep])
    drawn.rows_plotted = int(_col(frame, Y_VALUE).notna().sum())
    for axis, column, name in (
        (f"axis.{r.base}", x, x),
        (f"axis.{r.value}", Y_VALUE, ", ".join(ys)),
    ):
        if gt[f"{axis}.scale"] == "log" and kind[axis[-1]] != "categorical":
            values = np.asarray(pd.to_numeric(_col(frame, column), errors="coerce"), dtype=float)
            bad = values[values <= 0]  # missing values compare False and are left alone
            if len(bad):
                raise DrawError(
                    f"{axis}.scale: log, but {name} has {len(bad)} values of 0 or below "
                    f"(smallest {bad.min():g}); leave them out of the data, or use linear"
                )

    return frame


def _encodings(frame: pd.DataFrame, gt: dict[str, Any], style: Style) -> _Encodings:
    """Which columns group and style the series, the benchmark's rows, and each style's
    groups in order."""
    by = {d.by: _column(gt, d.encoding_path, frame) for d in DIMENSIONS}
    paths = gt["encoding.detail.column"]
    path_columns = [] if unset(paths) else ([paths] if isinstance(paths, str) else list(paths))
    for p in path_columns:
        if p not in frame.columns:
            raise DrawError(
                f"encoding.detail.column: no column '{p}' in the data; columns are {_names(frame)}"
            )
    bench_col = _column(gt, "benchmark.data_column", frame)
    bench_value = gt["benchmark.value"]

    color_type = gt["encoding.color.type"]
    color_col = by[COLOR.by]
    data_color = color_col is not None and color_col != Y_COLUMN
    numbers = (
        color_col is not None
        and data_color
        and pd.api.types.is_numeric_dtype(_col(frame, color_col))
    )
    if color_type == "continuous" and data_color and not numbers:
        raise DrawError(
            f"encoding.color.type: continuous, but {color_col} isn't numbers; "
            "use categorical or auto"
        )
    numeric_color = numbers and color_type != "categorical"  # drawn on a color scale
    how = gt["encoding.order"]
    is_bench = pd.Series(False, index=frame.index)
    if bench_col is not None:
        column = _col(frame, bench_col)
        is_bench = (column.astype(str) == str(bench_value)) | (column == bench_value)
    if bench_col is not None and not bool(is_bench.any()):
        where = "no y column is named" if bench_col == Y_COLUMN else f"no rows where {bench_col} is"
        raise DrawError(f"benchmark.value: {where} '{bench_value}'")
    others = cast(pd.DataFrame, frame.loc[~is_bench])  # the benchmark has its own style
    orders = {
        path: _order(_col(others, col), how)
        for path, col in by.items()
        if col is not None and not (path == COLOR.by and numeric_color)
    }
    lines_shown = bool(gt["mark.line.show"])  # a line joins only one color's points
    grouping = [
        col
        for path, col in by.items()
        if col is not None and not (path == COLOR.by and numeric_color and not lines_shown)
    ]
    grouping += [
        c for c in [*path_columns, Y_COLUMN] if c not in grouping
    ]  # each y column: its own line
    choices = {d.by: d.choices(style) for d in DIMENSIONS}

    return _Encodings(
        by,
        path_columns,
        bench_col,
        bench_value,
        bool(numeric_color),
        is_bench,
        orders,
        grouping,
        choices,
    )


def _category_positions(
    frame: pd.DataFrame,
    r: Roles,
    gt: dict[str, Any],
    kind: dict[str, str],
    enc: _Encodings,
    drawn: Drawn,
) -> pd.DataFrame:
    """Each categorical axis's categories, in order (the benchmark's at its side), with the
    frame's values replaced by their positions."""
    x = r.base_column
    aggregation = gt[f"axis.{r.value}.data.aggregation"]
    grouping, bench_col, bench_value = enc.grouping, enc.bench_col, enc.bench_value
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
            per = totals.agg(aggregation if aggregation != "none" else "sum")
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
            bench = [c for c in cats if str(c) == str(bench_value) or c == bench_value]
            rest = [c for c in cats if c not in bench]
            cats = bench + rest if gt["benchmark.side"] == "start" else rest + bench
        drawn.categories[name] = cats
        frame = frame.assign(**{column: axis_data.positions(_col(frame, column), cats)})

    return frame


def _series(
    frame: pd.DataFrame, r: Roles, gt: dict[str, Any], style: Style, enc: _Encodings
) -> list[Series]:
    """One series per group of rows, styled by its groups; the benchmark last, on top."""
    x = r.base_column
    aggregation = gt[f"axis.{r.value}.data.aggregation"]
    by, orders, grouping, is_bench = enc.by, enc.orders, enc.grouping, enc.is_bench
    bench_col, bench_value, numeric_color = enc.bench_col, enc.bench_value, enc.numeric_color
    series: list[Series] = []
    groups = (
        frame.groupby([*grouping, is_bench.rename("__bench__")], sort=False, dropna=False)
        if grouping
        else frame.groupby(is_bench.rename("__bench__"), sort=False)
    )
    for key, group in groups:
        key = key if isinstance(key, tuple) else (key,)
        values = dict(zip([*grouping, "__bench__"], key, strict=True))
        rows = cast(pd.DataFrame, group)
        if gt["mark.line.connect_order"] == "x":
            rows = rows.sort_values(by=x, kind="stable")
        if aggregation != "none":  # one point per place: the aggregate of its rows
            points = rows.groupby(x, sort=False, dropna=False)[Y_VALUE].agg(aggregation)
            xs, ys_ = np.asarray(points.index), np.asarray(points.to_numpy())
        else:
            xs, ys_ = np.asarray(_col(rows, x)), np.asarray(_col(rows, Y_VALUE))
        index = {
            path: (
                orders[path].index(values[col])
                if col is not None and path in orders and values[col] in orders[path]
                else 0
            )
            for path, col in by.items()
        }
        bench = bool(values["__bench__"])
        if bench:
            b = style.theme
            s = Series(
                xs,
                ys_,
                style.color("series.benchmark.color"),
                LINE_STYLES[b["series.benchmark.line.style"]],
                MARKERS[b["series.benchmark.marker.shape"]],
                b["series.benchmark.marker.fill"],
                None if bench_col == x else str(bench_value),  # named on its axis already
                _look(style, True),
                benchmark=True,
            )
        else:
            color_col = by[COLOR.by]
            label = None if color_col is None or numeric_color else str(values[color_col])
            color, line, shape, fill = (_cycle(enc.choices[d.by], index[d.by]) for d in DIMENSIONS)
            s = Series(
                xs,
                ys_,
                color,
                line,
                shape,
                fill,
                label,
                _look(style, False),
                values=np.asarray(_col(rows, color_col), dtype=float)
                if numeric_color and color_col
                else None,
                order=tuple(index.values()),
            )
        s.rows, s.place_column = rows.index, x
        series.append(s)
    series.sort(key=lambda s: (s.benchmark, s.order))  # group order; the benchmark last, on top
    return series


def _group_warnings(enc: _Encodings, drawn: Drawn) -> None:
    """A style with more groups than the theme has choices repeats them: a warning."""
    by, orders, numeric_color = enc.by, enc.orders, enc.numeric_color
    for d in DIMENSIONS:
        if by[d.by] is None or (d is COLOR and numeric_color):
            continue
        groups, choices, what = len(orders[d.by]), len(enc.choices[d.by]), d.words
        if groups > choices:
            drawn.warnings.append(
                Issue(
                    "too-many-groups",
                    f"{d.encoding_path}: {groups} groups but {choices} {what} in "
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
) -> Drawn:
    """Draw an xy graph of df into ax, from the graph type's resolved values `gt`, with the
    GraphSpec's layers (`listed`, by name)."""
    drawn = Drawn()
    listed = listed or {}
    series, frame, r = build_series(df, gt, style, drawn)
    marks.check(gt, r.value)
    log_values = gt[f"axis.{r.value}.scale"] == "log"
    stacked = marks.stack(series, gt["series.aggregation"], log_values)
    for s, st in zip(series, stacked, strict=True):
        s.stack, s.y = st, st.top  # lines and markers sit at the top of their stack
    for s, shifts in zip(series, marks.slots(series, gt, style), strict=True):
        s.shifts = shifts
    drawn.label_groups, norm = _draw_marks(ax, series, gt, style, r)
    layers.error_bars(ax, listed, series, frame, gt, style, r)
    lines = layers.reference_lines(ax, listed, series, frame, style, drawn.kinds)
    _axes(ax, series, lines, gt, style, drawn, r)
    drawn.y_title = _decorate(ax, gt, style, r, title, norm)
    drawn.series, drawn.roles, drawn.ref_lines, drawn.layers = series, r, lines, listed
    drawn.style_keys = _style_keys(gt, frame, style)
    layers.notes_outside(ax, listed, style)
    return drawn


def _as_xy(r: Roles, base: Any, value: Any) -> tuple[Any, Any]:
    """Base and value as x and y."""
    return (base, value) if r.base == "x" else (value, base)


def _draw_marks(
    ax: Axes, series: list[Series], gt: dict[str, Any], style: Style, r: Roles
) -> tuple[list[labelling.Labelled], Normalize | None]:
    """Each series' line, markers and bars (a numeric encoding.color.column's markers on its color
    scale); returns the names to label, with what's drawn under each, and the color scale's
    range, if there is one."""
    bars_shown = bool(gt["mark.bar.show"])
    lines_shown, markers_shown = bool(gt["mark.line.show"]), bool(gt["mark.marker.show"])
    cmap, norm = style.colormap(), None
    if any(s.values is not None for s in series):
        all_values = np.concatenate([s.values for s in series if s.values is not None])
        norm = Normalize(float(np.nanmin(all_values)), float(np.nanmax(all_values)))
    handles: dict[str, Line2D | marks.Bars] = {}
    paths: dict[str, list[np.ndarray]] = {}
    colors: dict[str, Any] = {}
    for s in series:
        look = s.look
        line_color = s.color
        if s.values is not None and norm is not None:
            line_color = cmap(norm(float(np.nanmean(s.values))))
        open_marker = s.fill == "open"
        rim, rim_width = look.edge, look.edge_width
        px, py = _as_xy(r, s.x, s.y)
        (line,) = ax.plot(
            px,
            py,
            color=line_color,
            linestyle=s.linestyle if lines_shown else "none",
            linewidth=look.line_width,
            marker=s.marker if markers_shown and s.values is None else "none",
            markersize=look.marker_size,
            markerfacecolor="none" if open_marker else line_color,
            markeredgecolor=line_color if (open_marker or rim == "none") else rim,
            markeredgewidth=rim_width if (open_marker or rim != "none") else 0.0,
            zorder=look.line_z,
        )
        line.set_transform(marks.shifted(ax, r.base, s.shifts))
        handle = line
        if bars_shown:
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
                zorder=2.5,
            )
            dots.set_offset_transform(marks.shifted(ax, r.base, s.shifts))
        if s.label is not None:
            handles.setdefault(s.label, handle)
            colors.setdefault(s.label, line_color)
            paths.setdefault(s.label, []).append(np.c_[marks.numbers(px), marks.numbers(py)])
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
        values = marks.numbers(np.concatenate(along)) if along else np.array([])
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
    _limits(ax, gt)
    if bool(gt["mark.bar.show"]) and unset(gt[f"axis.{r.value}.min"]):  # bars stand on the axis
        log = gt[f"axis.{r.value}.scale"] == "log"
        floor = 1.0 if log else 0.0
        get = ax.get_ylim if r.value == "y" else ax.get_xlim
        put = ax.set_ylim if r.value == "y" else ax.set_xlim
        stacks = [np.r_[s.stack.bottom, s.stack.top] for s in series if s.stack is not None]
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
) -> str | None:
    """The axis titles and the title, the plot box's sides and ticks, the grid, and the
    color bar for a color scale's range (norm); returns the value axis's title."""
    columns = {r.base: [r.base_column], r.value: r.value_columns}
    xt = _title(gt["axis.x.title"], columns["x"][0] if len(columns["x"]) == 1 else None)
    yt = _title(gt["axis.y.title"], columns["y"][0] if len(columns["y"]) == 1 else None)
    if xt:
        ax.set_xlabel(xt)
    if yt:
        ax.set_ylabel(yt)
    if title:
        ax.set_title(markup(title))
    _box_and_ticks(ax, style)
    if bool(style.theme["grid.show"]):
        ax.grid(True)
        ax.set_axisbelow(True)
    if norm is not None:
        color_col = gt["encoding.color.column"]
        bar_title = _title(
            gt["legend.color_bar.title.text"], None if unset(color_col) else str(color_col)
        )
        colorbar.add(ax, norm, style.colormap(), bar_title, style)
    return yt if r.value == "y" else xt


def place(ax: Axes, drawn: Drawn, gt: dict[str, Any], style: Style) -> bool:
    """What needs the figure's final size: bars' room, value labels and reference lines'
    labels. True if an axis was widened, so the figure must be laid out again."""
    r = cast(Roles, drawn.roles)  # draw() set it
    marks.check_room(ax, drawn.series, gt, style, r.base)
    widened = marks.value_labels(ax, drawn.series, gt, style, r.base)
    return layers.label_lines(ax, drawn.ref_lines, gt, style) or widened


def label(ax: Axes, drawn: Drawn, gt: dict[str, Any], style: Style) -> None:
    """Name the series (legend.method), explain styles, then place notes inside the plot, all
    after the figure's size is final. Keys go first, since they need a corner and a note has
    six places. Anything that can't be placed cleanly is an error, never a fallback. What an
    earlier label() placed is taken away first, to place it again after the layout changed."""
    labelling.unplace(ax)
    layers.unplace_notes(ax)
    axis_data.check_fit(ax, gt, style)
    _name_series(ax, drawn, gt, style)
    layers.notes_inside(ax, drawn.layers, gt, style)


def _name_series(ax: Axes, drawn: Drawn, gt: dict[str, Any], style: Style) -> None:
    groups = drawn.label_groups
    with_lines = bool(gt["mark.line.show"])  # whether lines are obstacles: labels.Obstacles.of
    taken: list = []
    where = {
        "positions": tuple(gt["legend.key.positions"]),
        "inside": bool(gt["legend.key.inside"]),
    }
    color_col = gt["encoding.color.column"]
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
    if bool(gt["mark.bar.show"]):  # names beside bars would need rules of their own
        if method == "direct":
            raise DrawError("legend.method: direct isn't available with bars; use key or auto")
        allowed = [m for m in allowed if m != "direct"]
    tries = allowed if method == "auto" else [method]
    legend_title = _title(
        title, None if unset(color_col) or color_col == COLUMN_NAME else str(color_col)
    )
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
    raise DrawError(f"legend.method: {method} doesn't fit this graph; {hint}")


def _style_keys(gt: dict[str, Any], frame: pd.DataFrame, style: Style) -> list[StyleKey]:
    """Keys explaining line styles, marker shapes and fills set by an encoding other than
    encoding.color.column: one per styling column, titled by legend.key.title.text. Their
    samples are in the one series color, or with a color encoding in font.color, neutral
    among the colors."""
    styled = {
        d.by: gt[d.encoding_path]
        for d in DIMENSIONS
        if d is not COLOR
        and not unset(gt[d.encoding_path])
        and gt[d.encoding_path] != gt[COLOR.encoding_path]
    }
    choices = {d.by: d.choices(style) for d in (LINE_STYLE, MARKER_SHAPE, MARKER_FILL)}
    colored = not unset(gt[COLOR.encoding_path])
    ink = style.color("font.color") if colored else _cycle(COLOR.choices(style), 0)
    found = []
    for column in dict.fromkeys(styled.values()):
        bys = [b for b, c in styled.items() if c == column]
        source = Y_COLUMN if column == COLUMN_NAME else column
        values = _order(_col(frame, source), gt["encoding.order"])
        entries = []
        for i, value in enumerate(values):
            ls, mk, fill = (_cycle(choices[b], i if b in bys else 0) for b in choices)
            handle = Line2D(
                [],
                [],
                color=ink,
                linestyle=cast(Any, ls if gt["mark.line.show"] else "none"),
                marker=mk if gt["mark.marker.show"] else "none",
                markersize=style.pt("series.marker.size"),
                markerfacecolor="none" if fill == "open" else ink,
                markeredgecolor=ink,
            )
            entries.append(Entry(literal(str(value)), handle))
        title = _title(gt["legend.key.title.text"], None if column == COLUMN_NAME else str(column))
        found.append(StyleKey(entries, title, str(column)))
    return found


def _limits(ax: Axes, gt: dict[str, Any]) -> None:
    for axis in ("x", "y"):
        lo, hi = gt[f"axis.{axis}.min"], gt[f"axis.{axis}.max"]
        if unset(lo) and unset(hi):
            continue
        get = ax.get_xlim if axis == "x" else ax.get_ylim
        put = ax.set_xlim if axis == "x" else ax.set_ylim
        cur_lo, cur_hi = get()
        put(cur_lo if unset(lo) else float(lo), cur_hi if unset(hi) else float(hi))


def _box_and_ticks(ax: Axes, style: Style) -> None:
    sides = style.theme["plot_area.sides"]
    sides = [] if unset(sides) else list(sides)
    for side in ("left", "bottom", "top", "right"):
        ax.spines[side].set_visible(side in sides)
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
