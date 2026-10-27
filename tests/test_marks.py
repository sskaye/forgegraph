"""Bars, how series at one place combine (arrangement.stacking, arrangement.offset), and value
labels (graph_types/xy.yaml each series' bar and value_label; themes series.bar,
series.value_label)."""

from __future__ import annotations

import re
from itertools import pairwise
from typing import Any, cast

import numpy as np
import pandas as pd
import pytest

import forgegraph as fg
from forgegraph.drawing.key import KEY, keys
from forgegraph.drawing.marks import VALUE_LABEL, Bars

COUNTS = pd.DataFrame(
    {
        "island": ["Biscoe", "Biscoe", "Dream", "Dream", "Torgersen"],
        "species": ["Adelie", "Gentoo", "Adelie", "Chinstrap", "Adelie"],
        "penguins": [44, 124, 56, 68, 52],
    }
)
BARS = {
    "series.bar.show": True,
    "series.line.show": False,
    "series.marker.show": False,
    "axis.x.tick.algorithm": "all",
}


def graph(
    df: pd.DataFrame = COUNTS, /, *, color: str | None = "species", **parameters: Any
) -> fg.Graph:
    return fg.xy(df, "island", "penguins", color=color, parameters={**BARS, **parameters})


def bar_sets(g: fg.Graph) -> list[Bars]:
    return [c for c in g.axes.collections if isinstance(c, Bars)]


def segments(bars: Bars) -> list[tuple[float, float, float]]:
    """(place, bottom, top) of each of a series' bars."""
    return [
        (float(p), float(lo), float(hi))
        for p, lo, hi in zip(bars.places, bars.bottom, bars.top, strict=True)
        if np.isfinite(hi)
    ]


def centres(g: fg.Graph) -> dict[str, list[float]]:
    """Each series' bar centres along x, in data units, by its first bar's place."""
    inv = g.axes.transData.inverted()
    return {
        str(b.color): [inv.transform(((r.x0 + r.x1) / 2, r.y0))[0] for r in b.rectangles()]
        for b in bar_sets(g)
    }


def value_labels(g: fg.Graph) -> list[str]:
    return [t.get_text() for t in g.axes.texts if t.get_gid() == VALUE_LABEL]


def test_bars_stand_on_zero():
    g = graph(color=None, **{"series.aggregation.function": "sum"})
    [bars] = bar_sets(g)
    assert segments(bars) == [(0, 0, 168), (1, 0, 124), (2, 0, 52)]
    assert g.axes.get_ylim()[0] == 0
    assert bars.edge == "#000000" and bars.edge_width == g.style.pt("series.bar.edge.width")


def test_bars_of_a_sum_that_is_0_but_for_float_noise_stand_on_zero():
    noise = pd.DataFrame({"island": ["Biscoe"] * 3 + ["Dream"], "penguins": [0.3, -0.1, -0.2, 5]})
    g = graph(noise, color=None, **{"series.aggregation.function": "sum"})
    assert min(top for _, _, top in segments(bar_sets(g)[0])) < 0  # -2.8e-17
    assert g.axes.get_ylim()[0] == 0


def _spacing(g: fg.Graph) -> float:
    """The distance between neighbouring places along x, in display px."""
    a, b = (g.axes.transData.transform((p, 1.0))[0] for p in (0, 1))
    return abs(b - a)


def test_a_bar_fills_its_width_of_the_space_between_places_at_any_size():
    g = graph(color=None, **{"series.aggregation.function": "sum"})
    [bars] = bar_sets(g)
    fraction = float(g.style.theme["series.bar.width"])
    for size in ((4, 3), (8, 3)):
        g.figure.set_size_inches(*size)
        widths = {round(r.width, 3) for r in bars.rectangles()}
        assert widths == {round(fraction * _spacing(g), 3)}


def test_side_by_side_bars_share_the_space_and_are_centred_at_each_place():
    g = graph(**{"arrangement.offset": "side_by_side"})
    adelie, chinstrap, gentoo = (centres(g)[str(b.color)] for b in bar_sets(g))
    assert adelie[0] < 0 < gentoo[0] and adelie[0] == pytest.approx(-gentoo[0])  # Biscoe
    assert adelie[1] < 1 < chinstrap[0] and adelie[1] - 1 == pytest.approx(1 - chinstrap[0])
    assert adelie[2] == pytest.approx(2)  # Torgersen: Adelie alone
    width, gap = (float(g.style.theme[f"series.bar.{k}"]) for k in ("width", "gap"))
    room = width * _spacing(g) / 2  # at most two bars at a place
    biscoe_adelie, biscoe_gentoo = bar_sets(g)[0].rectangles()[0], bar_sets(g)[2].rectangles()[0]
    assert biscoe_adelie.width == pytest.approx(room * (1 - gap))
    assert biscoe_gentoo.x0 - biscoe_adelie.x1 == pytest.approx(room * gap)


def test_bars_at_a_lone_place_fill_their_width_of_the_plot_area():
    one = pd.DataFrame({"island": ["Biscoe"], "penguins": [44]})
    g = graph(one, color=None)
    [bar] = bar_sets(g)[0].rectangles()
    assert bar.width == pytest.approx(0.8 * g.axes.bbox.width, rel=1e-6)


def test_stacked_bars():
    stacked: dict[str, Any] = {
        "arrangement.stacking": "sum",
        "arrangement.total.show": True,
        "legend.key.inside": False,
    }
    g = graph(**stacked)
    adelie, chinstrap, gentoo = bar_sets(g)
    assert segments(adelie)[0] == (0, 0, 44)
    assert segments(gentoo)[0] == (0, 44, 168)
    assert segments(chinstrap)[0] == (1, 56, 124)
    assert sorted(value_labels(g)) == ["124", "168", "52"]


def test_stacked_to_a_hundred():
    g = graph(**{"arrangement.stacking": "percent", "axis.y.max": 175})  # room for the key
    tops = {}
    for bars in bar_sets(g):
        for place, _, top in segments(bars):
            if np.isfinite(top):
                tops[place] = max(tops.get(place, 0), top)
    assert tops == pytest.approx({0: 100, 1: 100, 2: 100})


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        (
            {"arrangement.stacking": "sum", "arrangement.offset": "side_by_side"},
            "use one or the other",
        ),
        ({"arrangement.stacking": "sum", "axis.y.scale": "log"}, "a log axis can't show"),
        (
            {
                "arrangement.stacking": "sum",
                "series.value_label.show": True,
                "series.value_label.position": "outside",
            },
            "stacked segments are labelled inside",
        ),
        ({"arrangement.total.show": True}, "applies with arrangement.stacking sum"),
        ({"axis.y.min": 10}, "bars start at 0, so the axis must include it"),
    ],
)
def test_impossible_bar_settings(settings, message):
    with pytest.raises(fg.SpecError, match=re.escape(message)):
        graph(**settings)


def test_inside_labels_need_bars():
    with pytest.raises(fg.SpecError, match="inside needs bars"):
        graph(
            **{
                "series.bar.show": False,
                "series.marker.show": True,
                "series.value_label.show": True,
                "series.value_label.position": "inside",
            }
        )


def test_percent_of_mixed_signs_is_an_error():
    df = COUNTS.assign(penguins=[-1, 2, 3, 4, 5])
    with pytest.raises(fg.SpecError, match="a total with mixed signs isn't defined"):
        graph(df, **{"arrangement.stacking": "percent"})


def test_stacking_needs_one_row_per_place():
    df = pd.concat([COUNTS, COUNTS.head(1)])
    with pytest.raises(fg.SpecError, match="several rows at one place; combine them"):
        graph(df, **{"arrangement.stacking": "sum"})


def test_negative_values_stack_downward():
    df = pd.DataFrame(
        {"q": ["a", "a", "b", "b"], "s": ["x", "y", "x", "y"], "v": [3.0, -2.0, -1.0, -4.0]}
    )
    g = fg.xy(df, "q", "v", color="s", parameters={**BARS, "arrangement.stacking": "sum"})
    x, y = bar_sets(g)
    assert segments(x) == [(0, 0, 3), (1, 0, -1)]
    assert segments(y) == [(0, 0, -2), (1, -1, -5)]


SHARES = pd.DataFrame({"x": ["a", "b", "c"], "v": [0.25, 0.5, 0.75]})


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ({}, ["0.2", "0.5", "0.8"]),  # as the tick labels: one decimal
        ({"axis.y.tick.label.format": ".0%"}, ["25%", "50%", "75%"]),  # the axis's format
        (
            {"axis.y.tick.label.format": ".0%", "series.value_label.format": ".2f"},
            ["0.25", "0.50", "0.75"],
        ),  # their own format first
    ],
)
def test_value_labels_write_numbers_as_the_value_axis_does(settings, expected):
    shown = {"series.value_label.show": True, "series.value_label.position": "outside"}
    g = fg.xy(SHARES, "x", "v", parameters={**BARS, **shown, **settings})
    assert value_labels(g) == expected


def test_value_labels_and_the_axis_grows_to_fit_them():
    g = graph(
        color=None,
        **{
            "series.aggregation.function": "sum",
            "series.value_label.show": True,
            "series.value_label.position": "outside",
        },
    )
    assert value_labels(g) == ["168", "124", "52"]
    assert g.axes.get_ylim()[1] > 168
    plot = g.axes.get_window_extent()
    assert all(
        plot.contains(*t.get_window_extent().get_points().mean(axis=0)) for t in g.axes.texts
    )


def test_a_label_inside_its_bar_stands_out_from_it():
    totals = cast(pd.DataFrame, COUNTS.groupby("species", as_index=False)["penguins"].sum())
    g = fg.xy(
        totals,
        "penguins",
        "species",
        parameters={
            **BARS,
            "axis.x.tick.algorithm": "auto",
            "axis.y.tick.algorithm": "all",
            "arrangement.base_axis": "y",
            "series.value_label.show": True,
        },
    )
    [label] = [t for t in g.axes.texts if t.get_text() == "152"]
    assert label.get_color() == "#FFFFFF"  # the background color: more contrast on blue


def test_a_label_running_into_another_bar_is_an_error():
    with pytest.raises(fg.SpecError, match="runs into a neighbouring bar"):
        wide = COUNTS.assign(penguins=COUNTS["penguins"] * 1000)  # labels wider than bars
        graph(wide, **{"arrangement.offset": "side_by_side", "series.value_label.show": True})


def test_bars_never_overlap_however_close_the_places():
    df = pd.DataFrame({"x": np.arange(200), "y": np.arange(200.0)})
    g = fg.xy(df, "x", "y", parameters={**BARS, "axis.x.tick.algorithm": "auto"})
    rects = sorted(bar_sets(g)[0].rectangles(), key=lambda r: r.x0)
    assert all(b.x0 >= a.x1 - 1e-6 for a, b in pairwise(rects))


def test_side_by_side_markers_too_wide_for_the_space_are_an_error():
    df = pd.DataFrame({"x": np.repeat(np.arange(200), 2), "y": 1.0, "g": ["a", "b"] * 200})
    with pytest.raises(fg.SpecError) as e:
        fg.xy(df, "x", "y", color="g", parameters={"arrangement.offset": "side_by_side"})
    [problem] = e.value.problems
    assert problem.startswith("arrangement.offset: 2 markers side by side need")


def test_the_key_shows_a_swatch_of_each_bar():
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Rectangle

    g = graph(**{"arrangement.offset": "side_by_side", "legend.method": "key"})
    swatches = [a for a in g.axes.get_children() if a.get_gid() == KEY and isinstance(a, Rectangle)]
    swatches = [a for a in swatches if to_rgba(a.get_facecolor())[3] > 0]  # not the key's frame
    assert len(swatches) == 3
    widest = max(b.width for b in bar_sets(g))
    assert all(a.get_height() <= widest + 1e-9 for a in swatches)
    assert all(a.get_edgecolor()[:3] == (0, 0, 0) for a in swatches)


def test_names_beside_bars_arent_offered():
    with pytest.raises(fg.SpecError, match="direct isn't available with bars"):
        graph(**{"arrangement.offset": "side_by_side", "legend.method": "direct"})
    assert graph(**{"arrangement.offset": "side_by_side"}).labelling == "key"


def test_the_benchmarks_series_stack_among_themselves():
    df = pd.DataFrame(
        {"who": ["ref", "ref", "cell", "cell"], "run": [1, 2, 1, 2], "v": [1.0, 2.0, 3.0, 4.0]}
    )
    g = fg.xy(
        df,
        "who",
        "v",
        color="run",
        parameters={
            **BARS,
            "series.color_scale": "categorical",
            "arrangement.stacking": "sum",
            "arrangement.total.show": True,
            "benchmark.data_column": "who",
            "benchmark.value": "ref",
        },
    )
    stacks = sorted(seg for bars in bar_sets(g) for seg in segments(bars))
    assert stacks == [(0, 0, 1), (0, 1, 3), (1, 0, 3), (1, 3, 7)]  # ref on the left, then cell
    assert sorted(value_labels(g)) == ["3", "7"]


def _drawn_offsets(g: fg.Graph, base: str, dpi: int) -> list[float]:
    """Each side-by-side group's centre less its tick's centre, in px, as the PNG draws them."""
    import io

    from PIL import Image

    from forgegraph.drawing.style import isolated

    with isolated(g.style):
        buf = io.BytesIO()
        g.figure.savefig(buf, format="png", dpi=dpi)
        g.figure.set_dpi(dpi)
        g.figure.canvas.draw()
        k = 0 if base == "x" else 1
        axis = g.axes.xaxis if base == "x" else g.axes.yaxis
        ticks = [g.axes.transData.transform((t, t))[k] for t in axis.get_ticklocs()]
    im = np.asarray(Image.open(buf).convert("L")).astype(float)
    if base == "y":
        ticks = [im.shape[0] - t for t in ticks]  # rows run down
    if base == "y":
        im = im.T  # the base axis runs across
    rows, cols = im.shape
    spine = [r for r in range(rows) if (im[r] < 80).sum() > cols * 0.5]
    spine_at = spine[-1] if base == "x" else spine[0]
    out = 1 if base == "x" else -1  # ticks point out of the plot
    tick = (255 - im[spine_at + 3 * out]) / 255
    bar = im[spine_at - 15 * out]
    found = np.where(tick > 0.3)[0]
    offsets = []
    for run in np.split(found, np.where(np.diff(found) > 1)[0] + 1):
        lo, hi = run[0] - 1, run[-1] + 2
        centre = ((np.arange(lo, hi) + 0.5) * tick[lo:hi]).sum() / tick[lo:hi].sum()
        if min(abs(centre - t) for t in ticks) > 2:  # not one of the base axis's ticks
            continue
        ends = []
        for step in (-1, 1):
            at, white, last = int(centre), 0, int(centre)
            while 0 < at < cols - 1 and white <= 8:
                at += step
                last, white = (at, 0) if bar[at] < 250 else (last, white + 1)
            ends.append(last)
        a, b = ends
        left, right = a + 1 - (255 - bar[a]) / 255, b + (255 - bar[b]) / 255
        offsets.append((left + right) / 2 - centre)
    return offsets


@pytest.mark.parametrize("base", ["x", "y"])
@pytest.mark.parametrize("dpi", [100, 137, 300])
def test_side_by_side_bars_are_drawn_centred_on_their_tick_to_the_pixel(base, dpi):
    data = COUNTS.head(4)  # two places, two series at each
    x, y = ("island", "penguins") if base == "x" else ("penguins", "island")
    g = fg.xy(
        data,
        x,
        y,
        color="species",
        parameters={
            **BARS,
            f"axis.{base}.tick.algorithm": "all",
            "axis.x.tick.algorithm": "all" if base == "x" else "auto",
            "arrangement.offset": "side_by_side",
            "arrangement.base_axis": base,
            "legend.method": "key",
            f"axis.{'y' if base == 'x' else 'x'}.max": 200,
        },
    )
    offsets = _drawn_offsets(g, base, dpi)
    assert len(offsets) == 2 and all(abs(o) < 0.01 for o in offsets), offsets


def test_place_shift_moves_each_point_by_its_places_offset(monkeypatch):
    """Each point moves by its place's offset, looked up once per distinct place."""
    from forgegraph.drawing import marks

    g = graph()
    ax = g.axes
    rng = np.random.default_rng(1)
    places = np.array([0.0, 1.0, 2.0, 1.0 + 1e-12, np.nan])  # 1 + 1e-12 is place 1
    xs = rng.choice(places, 5000)
    points = np.c_[xs, rng.uniform(0, 100, 5000)]
    shifts = {0.0: (0.0, -6.0), 1.0: (0.0, 4.5)}
    transform = marks.PlaceShift(ax, "x", shifts, marks.Spacing(ax, "x", places))
    looked_up = []
    key = marks.key
    monkeypatch.setattr(marks, "key", lambda p: looked_up.append(p) or key(p))
    moved = transform.transform(points)
    monkeypatch.setattr(marks, "key", key)
    px = g.figure.dpi / 72
    plain = ax.transData.transform(points)
    expected = plain.copy()
    expected[:, 0] += [
        shifts.get(key(p), (0.0, 0.0))[1] * px if np.isfinite(p) else 0.0 for p in xs
    ]
    assert np.array_equal(moved, expected, equal_nan=True)
    assert len(looked_up) <= len(places)


def test_series_opacity_fades_lines_markers_and_bars():
    g = graph(**{"series.opacity": 0.4, "series.line.show": True, "series.marker.show": True})
    assert {b.get_alpha() for b in bar_sets(g)} == {0.4}
    lines = [ln for ln in g.axes.lines if ln.get_gid() is None and np.size(ln.get_xdata())]
    assert lines and {ln.get_alpha() for ln in lines} == {0.4}
    [key] = keys(g.axes)
    assert 0.4 in {a.get_alpha() for a in key.artists}  # the key's samples look like the series
