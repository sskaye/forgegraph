"""Rendering: sizes, settings isolation, fonts, provenance, determinism, labels and errors."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import cast

import matplotlib
import numpy as np
import pandas as pd
import pytest
from cycler import cycler
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from pack_helpers import allow, dump, graphspec_file, write_pack
from PIL import Image
from render_helpers import BASE, painted_draws, png, polarization, render

import forgegraph as fg
from forgegraph.drawing import xy
from forgegraph.drawing.export import FILE_TYPES, IMAGES
from forgegraph.drawing.figure import WATERMARK
from forgegraph.drawing.key import KEY, keys
from forgegraph.drawing.style import LINE_STYLES, Style, isolated
from forgegraph.drawing.text import footprint
from forgegraph.drawing.ticks import LogTicks, NiceTicks, breaks_log
from forgegraph.spec.parameters import NONE

# --- the figure follows the theme and format ---------------------------------------------


def test_sizes_come_from_the_theme_and_base_font():
    g = render(format={"figure.base_size": 10})
    ax = g.axes
    tick = ax.get_xticklabels()[0]
    assert tick.get_fontsize() == pytest.approx(0.9 * 10)
    assert ax.xaxis.label.get_fontsize() == pytest.approx(1.05 * 10)
    assert ax.xaxis.label.get_fontweight() in ("semibold", 600)
    assert ax.get_lines()[0].get_linewidth() == pytest.approx(0.15 * 10)
    assert ax.spines["left"].get_linewidth() == pytest.approx(0.08 * 10)


def test_given_dimensions_are_exact_and_auto_ones_fit(tmp_path):
    g = render(format={"figure.width": 89, "figure.height": "auto"})
    w, h = g.figure.get_size_inches()
    assert w == pytest.approx(89 / 25.4)
    tight = g.figure.get_tightbbox(g.figure.canvas.get_renderer())  # type: ignore[attr-defined]
    assert tight.height <= h <= tight.height + 0.2
    [path] = g.save(tmp_path / "g.png")
    with Image.open(path) as image:
        assert image.size[0] == round(89 / 25.4 * g.style.format["output.dpi"])


@pytest.mark.parametrize(
    "name", ["okabe_ito", "tol_bright", "tol_muted", "tableau_10", "color_blind"]
)
def test_series_colors_can_name_a_palette(name):
    from forgegraph.drawing.style import PALETTES

    g = render(theme={"series.colors": name})
    drawn = {to_hex(line.get_color()).upper() for line in g.axes.get_lines()}
    assert drawn - {"#808080"} <= set(PALETTES[name])  # the benchmark is grey


def test_series_colors_can_be_a_list_of_colors():
    g = render(theme={"series.colors": ["#112233", "#445566", "#778899"]})
    drawn = {to_hex(line.get_color()).upper() for line in g.axes.get_lines()}
    assert drawn - {"#808080"} <= {"#112233", "#445566", "#778899"}


def test_series_colors_rejects_an_unknown_palette():
    with pytest.raises(fg.SpecError, match=r"series\.colors"):
        render(theme={"series.colors": "rainbow"})


def test_series_colors_follow_the_group_order_and_the_benchmark_has_its_own_style():
    g = render()
    colors = [line.get_color() for line in g.axes.get_lines()]
    assert colors[:6] == [
        "#0072B2",
        "#0072B2",
        "#E69F00",
        "#E69F00",
        "#009E73",
        "#009E73",
    ]  # A, B, C x 2 runs
    assert colors[-1] == "#808080" and g.axes.get_lines()[-1].get_linewidth() == pytest.approx(
        g.style.pt("series.benchmark.line.width")
    )
    data = render({"encoding.order": "data"})  # Cell C appears first in the data
    assert data.axes.get_lines()[0].get_color() == "#0072B2"


def test_the_users_matplotlib_settings_dont_leak_in():
    clean = png(render(), dpi=80)
    hostile = {
        "axes.facecolor": "#202020",
        "figure.facecolor": "#101010",
        "lines.linewidth": 6,
        "font.size": 30,
        "axes.grid": True,
        "xtick.direction": "in",
        "axes.prop_cycle": cycler(color=["#00FF00"]),
        "font.family": "serif",
        "axes.linewidth": 4,
        "legend.frameon": True,
    }
    with matplotlib.rc_context(hostile):  # type: ignore[arg-type]
        assert png(render(), dpi=80) == clean


# --- labelling ----------------------------------------------------------------------------


def test_interior_labels_name_each_cell_in_its_color():
    g = render()
    assert g.labelling == "direct"
    labels = {
        t.get_text(): t.get_color()
        for t in g.axes.texts
        if t.get_gid() == "forgegraph-series-label"
    }
    assert labels == {
        "Cell A": "#0072B2",
        "Cell B": "#E69F00",
        "Cell C": "#009E73",
        "Benchmark": "#808080",
    }


def test_one_series_is_named_unless_the_y_title_names_it():
    frame = pd.DataFrame({"t": [1, 2, 3, 4], "v": [1.0, 2.0, 1.5, 3.0]})
    assert fg.xy(frame, x="t", y="v").labelling == "none"  # the y-axis title is "v"
    assert fg.xy(frame, x="t", y="v", parameters={"axis.y.title": "Volts"}).labelling == "direct"
    none = {"legend.method": "none"}
    message = "legend.method: theme 'forgegraph_base/base_theme' allows only"
    with pytest.raises(fg.SpecError, match=re.escape(message)):
        fg.xy(frame, x="t", y="v", parameters=none)


def test_a_numeric_color_draws_one_line_per_value():
    frame = pd.DataFrame(
        {"t": [1, 2, 3] * 3, "v": [1.0, 2.0, 3.0, 2.0, 3.0, 4.0, 3.0, 4.0, 5.0],
         "d": [1960] * 3 + [1970] * 3 + [1980] * 3}
    )  # fmt: skip
    scale = fg.xy(frame, x="t", y="v", color="d")  # on the color bar
    assert [len(np.asarray(line.get_xdata())) for line in scale.axes.lines] == [3, 3, 3]
    named = fg.xy(frame, x="t", y="v", color="d", parameters={"encoding.color.type": "categorical"})
    labels = [t.get_text() for t in named.axes.texts if t.get_gid() == "forgegraph-series-label"]
    assert sorted(labels) == ["1960", "1970", "1980"]
    text = frame.assign(d=frame["d"].astype(str) + "s")
    message = re.escape("encoding.color.type: continuous, but d isn't numbers")
    with pytest.raises(fg.SpecError, match=message):
        fg.xy(text, x="t", y="v", color="d", parameters={"encoding.color.type": "continuous"})


def test_legend_sits_in_a_corner_clear_of_data_with_its_title():
    g = render({"legend.method": "key", "legend.key.title.text": "Cells"})
    [legend] = keys(g.axes)
    assert g.labelling == "key" and legend.position is not None
    assert legend.title == "Cells"
    assert [e.name for e in legend.entries] == ["Cell A", "Cell B", "Cell C", "Benchmark"]


@pytest.mark.parametrize(
    "algorithm", ["extended_wilkinson", "wilkinson", "heckbert", "nelder", "r_pretty"]
)
def test_ticks_off_a_multiple_of_their_step_stay_distinct(algorithm):
    class Axis:  # room for 5 labels, as on the eval's CO2 graph
        def get_tick_space(self):
            return 5

    locator = NiceTicks(algorithm)
    locator.axis = Axis()  # type: ignore[assignment]
    ticks = locator.tick_values(1954.8705, 2028.2955)  # extended_wilkinson: 1970, 1990, 2010
    assert len(set(ticks)) == len(ticks) and len(set(np.round(np.diff(ticks), 9))) == 1
    assert list(NiceTicks(algorithm).tick_values(0.1, 0.7)) == list(
        np.round(NiceTicks(algorithm).tick_values(0.1, 0.7), 12)
    )


@pytest.mark.parametrize(
    ("lo", "hi", "n", "expected"),
    [
        (1, 1e5, 5, [1, 100, 1e4]),  # every second power gives n - 2 inside
        (
            300,
            5000,
            5,
            [100, 300, 1000, 3000, 1e4],
        ),  # too few powers: 3s added, one beyond each end
        (1, 10, 5, [1, 3, 10, 30]),
        (10, 10, 5, [10]),  # a single power
    ],
)
def test_breaks_log_follows_scales(lo, hi, n, expected):
    """Worked by hand from scales::breaks_log (R/breaks-log.R)."""
    assert breaks_log(lo, hi, n) == expected


def test_log_ticks_by_matplotlib_are_powers_of_ten():
    ticks = LogTicks("matplotlib", "extended_wilkinson").tick_values(7e-6, 0.014)
    assert list(ticks) == [1e-5, 1e-4, 1e-3, 1e-2]


def test_log_tick_labels_fit():
    """With room for 10 labels, the linear algorithm asks breaks_log for 7 across these 3.3
    decades: 1e-05, 3e-05, ... whose labels would overlap. The fit drops to powers of ten."""
    frame = pd.DataFrame({"rate": np.geomspace(1e-5, 1e-2, 10), "v": np.geomspace(50, 2e5, 10)})
    g = fg.xy(frame, x="rate", y="v", parameters={"axis.x.scale": "log", "axis.y.scale": "log"})
    assert [i.check for i in g.issues] == []
    assert len(g.axes.xaxis.get_majorticklocs()) < 7


def test_layout_fits_tick_labels_that_change_with_the_box():
    """Here a taller plot box gets y ticks every 0.25 and a shorter one every 0.4, so the
    layout never settles; whichever labels the final draw has must fit."""
    iris = pd.read_csv(Path(__file__).parents[1] / "examples" / "sample-data" / "iris.csv")
    parameters = {
        "axis.x.title": "Petal length (cm)",
        "axis.y.title": "Petal width (cm)",
        "encoding.color.type": "categorical",
        "mark.line.show": False,
    }
    g = fg.xy(iris, x="petal_length", y="petal_width", color="species",
              title="Iris petal measurements by species", parameters=parameters)  # fmt: skip
    assert [i.check for i in g.issues] == []


def test_a_date_axis_has_no_offset_text_beside_it():
    frame = pd.DataFrame({"t": pd.date_range("2026-03-01", periods=48, freq="h"), "v": range(48)})
    g = fg.xy(frame, x="t", y="v")  # the date goes under the ticks instead
    assert g.axes.xaxis.get_offset_text().get_text() == ""


def test_key_samples_have_their_own_marker_size():
    small = {"series.marker.size": 0.1, "series.benchmark.marker.size": 0.1}
    g = render({"legend.method": "key", **small})
    [legend] = keys(g.axes)
    sizes = {
        a.get_markersize()
        for a in legend.artists
        if isinstance(a, Line2D) and a.get_marker() not in ("none", "None")
    }
    expected = Style(g.values["theme"], g.values["format"]).pt("legend.key.sample.marker.size")
    assert sizes == {expected}
    series = {
        line.get_markersize()
        for line in g.axes.lines
        if line not in legend.artists and len(np.asarray(line.get_xdata()))
    }
    assert expected not in series  # the plot's markers are smaller


def test_a_style_key_explains_line_styles():
    g = render({"encoding.line.style.column": "size", "legend.method": "direct"})
    assert any(k.title == "size" for k in keys(g.axes))


def test_column_name_groups_by_y_column():
    frame = polarization()
    settings = {
        "axis.y.data.column": ["cell_voltage", "temperature"],
        "encoding.color.column": "column_name",
        "encoding.detail.column": NONE,
        "benchmark.data_column": NONE,
        "benchmark.value": NONE,
        "legend.method": "key",
        "legend.key.title.text": NONE,
    }
    with pytest.raises(fg.SpecError, match="several y columns have no single name"):
        render(settings, data=frame)
    with pytest.raises(
        fg.SpecError, match=re.escape("legend.key.title.text: encoding.color.column is column_name")
    ):
        render(
            {**settings, "axis.y.title": NONE, "legend.key.title.text": "column_name"}, data=frame
        )
    g = render({**settings, "axis.y.title": NONE}, data=frame)
    [legend] = keys(g.axes)
    assert [e.name for e in legend.entries] == [
        "cell_voltage",
        "temperature",
    ]
    assert g.axes.yaxis.label.get_text() == ""  # axis.y.title: None


def test_numeric_color_by_draws_a_color_bar():
    g = render(
        {
            "encoding.color.column": "temperature",
            "benchmark.data_column": NONE,
            "benchmark.value": NONE,
            "legend.color_bar.title.text": "Temperature (°C)",
        }
    )
    [bar] = g.axes.child_axes
    [title] = bar.texts  # legend.color_bar.layout: title_above
    assert title.get_text() == "Temperature (°C)"
    renderer = g.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    letters, box, px = footprint(title, renderer), g.axes.bbox, g.figure.dpi / 72
    assert bar.bbox.x0 == pytest.approx(letters.x0, abs=0.5)  # left-aligned with the bar
    assert letters.y1 == pytest.approx(box.y1, abs=0.5)  # level with the plot box's top
    gap = g.style.pt("axis.title.gap") * px
    assert letters.y0 - bar.bbox.y1 == pytest.approx(gap, abs=0.5)
    assert bar.bbox.y0 == pytest.approx(box.y0)


def test_a_color_bar_title_can_read_down_its_side():
    g = render(
        {
            "encoding.color.column": "temperature",
            "benchmark.data_column": NONE,
            "benchmark.value": NONE,
            "legend.color_bar.title.text": "Temperature (°C)",
        },
        theme={"legend.color_bar.layout": "title_along"},
    )
    [bar] = g.axes.child_axes
    assert bar.get_ylabel() == "Temperature (°C)"
    assert bar.yaxis.label.get_rotation() == 270  # its letters face away from the bar
    assert bar.bbox.height == pytest.approx(g.axes.bbox.height)


def test_a_color_bar_can_go_below_the_plot():
    g = render(
        {
            "encoding.color.column": "temperature",
            "benchmark.data_column": NONE,
            "benchmark.value": NONE,
            "legend.color_bar.title.text": "Temperature (°C)",
        },
        theme={"legend.color_bar.layout": "below"},
    )
    [bar] = g.axes.child_axes
    [title] = bar.texts
    renderer = g.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    x_title = footprint(g.axes.xaxis.label, renderer)
    letters, px = footprint(title, renderer), g.figure.dpi / 72
    assert bar.bbox.width == pytest.approx(g.axes.bbox.width / 2)
    assert bar.bbox.x0 == pytest.approx(g.axes.bbox.x0)
    assert x_title.y0 - letters.y1 == pytest.approx(
        g.style.pt("legend.color_bar.gap") * px, abs=0.5
    )


def test_missing_values_drop_or_break_the_line():
    drop, gap = render(), render({"mark.line.missing_values": "gap"})
    assert drop.data.rows_dropped == {"missing x or y": 1} == gap.data.rows_dropped
    has_nan = [
        np.isnan(np.asarray(line.get_ydata(), dtype=float)).any() for line in gap.axes.get_lines()
    ]
    assert any(has_nan) and not any(
        np.isnan(np.asarray(line.get_ydata(), dtype=float)).any() for line in drop.axes.get_lines()
    )


def test_connect_order():
    by_x = render()
    xs = np.asarray(by_x.axes.get_lines()[0].get_xdata(), dtype=float)
    assert (np.diff(xs) >= 0).all()
    by_row = render({"mark.line.connect_order": "data"})
    xs = np.asarray(by_row.axes.get_lines()[0].get_xdata(), dtype=float)
    assert not (np.diff(xs) >= 0).all()


def test_scales_limits_and_titles():
    positive = polarization()
    lowest = positive["current_density"].min()
    zeros = positive.assign(current_density=positive["current_density"].replace(lowest, 0.0))
    with pytest.raises(
        fg.SpecError, match=re.escape("axis.x.scale: log, but current_density has 8 values of 0")
    ):
        render({"axis.x.scale": "log"}, data=zeros)
    g = render(
        {
            "axis.x.scale": "log",
            "axis.x.min": 1.0,
            "axis.y.max": 1.8,
            "axis.x.title": "Current (mA/cm^2)",
            "axis.y.title": NONE,
        },
        title="P_{max}",
        data=positive,
    )
    ax = g.axes
    assert ax.get_xscale() == "log" and ax.get_xlim()[0] == 1.0 and ax.get_ylim()[1] == 1.8
    assert ax.xaxis.label.get_text() == "Current (mA/cm$^{2}$)" and ax.yaxis.label.get_text() == ""
    assert ax.get_title() == "P$_{max}$"


def test_too_many_groups_warns():
    frame = pd.DataFrame(
        {
            "x": np.tile(np.arange(5.0), 12),
            "y": np.repeat(np.arange(12.0) * 3, 5),
            "g": np.repeat(list("abcdefghijkl"), 5),
        }
    )
    g = fg.xy(frame, "x", "y", color="g")
    assert (
        "encoding.color.column: 12 groups but 7 colors in series.colors; colors repeat"
        in g.warnings
    )


# --- errors --------------------------------------------------------------------------------


def test_drawing_errors_name_the_parameter():
    with pytest.raises(
        fg.SpecError, match=re.escape("axis.x.data.column: no column 'curent' in the data")
    ):
        render({"axis.x.data.column": "curent"})
    with pytest.raises(
        fg.SpecError, match=re.escape("axis.x.data.type: decimal, but 'cell' isn't numbers")
    ):
        render({"axis.x.data.column": "cell", "axis.x.data.type": "decimal"})
    with pytest.raises(fg.SpecError, match=re.escape("encoding.color.column: no column 'cel'")):
        render({"encoding.color.column": "cel"})


def test_no_data_file_needs_a_dataframe():
    doc = fg.graphspec("g", "xy", settings={"axis.x.data.column": "a", "axis.y.data.column": "b"})
    with pytest.raises(fg.SpecError, match=re.escape("data.file: None, so pass the data")):
        fg.render(doc)


def test_required_columns():
    doc = fg.graphspec("g", "xy", settings={"axis.x.data.column": "a"})
    with pytest.raises(
        fg.SpecError,
        match=re.escape("axis.y.data.column: must be set before the graph can be drawn"),
    ):
        fg.render(doc, pd.DataFrame({"a": [1.0]}))


# --- files, provenance, determinism ---------------------------------------------------------


@pytest.mark.parametrize("kind", ["png", "jpg", "tiff", "svg", "pdf"])
def test_provenance_round_trip(tmp_path, kind):
    g = render(title="Polarization, 60 °C")
    [path] = g.save(tmp_path / f"g.{kind}")
    record = fg.load(path)
    assert record is not None and record["provenance_level"] == "full"
    assert record["graphspec"] == g.spec
    assert record["resolved"]["theme"]["font.family"] == "Roboto"


@pytest.mark.slow
def test_provenance_levels(tmp_path):
    reference = "scripts/prepare.py"
    full = render({"data.preprocessing": reference})
    [path] = full.save(tmp_path / "f.png")
    record = fg.load(path)
    assert record is not None and record["preprocessing"] == reference
    minimal = render({"data.preprocessing": reference}, format={"provenance.level": "minimal"})
    minimal.spec["parameters"]["data"]["file"] = "secret/p.parquet"
    [path] = minimal.save(tmp_path / "m.png")
    record = fg.load(path)
    assert record is not None and "data" not in record and "preprocessing" not in record
    assert "data" not in record["graphspec"]["parameters"]  # no file, no preprocessing
    [path] = render(format={"provenance.level": "off"}).save(tmp_path / "o.png")
    assert fg.load(path) is None


@pytest.mark.slow
def test_the_provenance_spec_lists_what_each_level_records(tmp_path):
    """src/forgegraph/spec/provenance.yaml names every entry of the record, by level."""
    from ruamel.yaml import YAML

    spec = YAML(typ="safe").load(
        (Path(fg.__file__).parent / "spec" / "provenance.yaml").read_text(encoding="utf-8")
    )
    minimal, full = spec["minimal"], spec["full"]
    [path] = render(format={"provenance.level": "minimal"}).save(tmp_path / "m.png")
    record = fg.load(path)
    # nonstandard_packs is left out when every pack used is in the main config, as here
    assert record is not None and set(record) | {"nonstandard_packs"} == set(minimal)
    assert set(record["specs"]) == {"graph_type", "theme", "format"}
    assert record["specs"]["theme"] == {
        "name": "forgegraph_base/base_theme",
        "version": 0,
        "pack_version": fg.__version__,
    }
    [path] = render({"data.preprocessing": "prepare.py"}).save(tmp_path / "f.png")
    record = fg.load(path)
    # data is left out for a DataFrame passed in, as here
    assert record is not None
    assert set(record) | {"data", "nonstandard_packs"} == set(minimal) | set(full)
    [path] = render(format={"provenance.level": "off"}).save(tmp_path / "o.png")
    assert fg.load(path) is None


def test_every_format_file_type_is_saved(tmp_path):
    g = render(format={"output.file_types": ["png", "svg", "pdf"]})
    saved = g.save(tmp_path / "graph")
    assert sorted(p.name for p in saved) == ["graph.pdf", "graph.png", "graph.svg"]


@pytest.mark.slow
def test_output_is_byte_identical_with_source_date_epoch(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    for kind in ("png", "svg", "pdf"):
        a = render().save(tmp_path / f"a.{kind}")[0].read_bytes()
        b = render().save(tmp_path / f"b.{kind}")[0].read_bytes()
        assert a == b, kind


def test_pdf_embeds_truetype_fonts(tmp_path):
    [path] = render(title="Polarization").save(tmp_path / "g.pdf")
    data = path.read_bytes()
    assert b"/FontFile2" in data and b"/Type3" not in data
    assert re.search(rb"/BaseFont /[A-Z]{6}\+Roboto", data) or b"Roboto" in data


def test_drawing_on_the_figure_marks_it_non_standard(tmp_path):
    g = render()
    assert not g.nonstandard
    g.axes.axhline(1.4)  # the escape hatch: raw matplotlib on a ForgeGraph figure
    assert g.nonstandard
    [path] = g.save(tmp_path / "g.png")
    record = fg.load(path)
    assert record is not None and record["nonstandard"] is True
    assert any(a.get_gid() == "forgegraph-watermark" for a in g.axes.get_children())


def _watermarked(g: fg.Graph) -> bool:
    return any(a.get_gid() == WATERMARK for a in g.axes.get_children())


@pytest.mark.parametrize(
    "change",
    [
        lambda ax: ax.get_lines()[0].set_color("#FF00FF"),
        lambda ax: ax.set_xlim(0, 2000),
        lambda ax: ax.xaxis.label.set_text("changed"),
        lambda ax: ax.axhline(0.7),
    ],
    ids=["line color", "axis limits", "axis title", "added line"],
)
@pytest.mark.slow
def test_any_change_after_rendering_makes_the_graph_non_standard(change, tmp_path):
    g = render()
    change(g.axes)
    assert g.nonstandard
    [path] = g.save(tmp_path / "g.png")
    record = fg.load(path)
    assert record is not None and record["nonstandard"] is True
    assert _watermarked(g)


@pytest.mark.slow
def test_an_unchanged_graph_stays_standard_however_it_is_drawn_or_saved(tmp_path):
    g = render(format={"output.file_types": list(FILE_TYPES)})
    g.check()
    g.figure.canvas.draw()
    g._repr_png_()
    saved = g.save(tmp_path / "g")
    assert not g.nonstandard and not _watermarked(g)
    assert all(fg.load(p)["nonstandard"] is False for p in saved)  # type: ignore[index]


def _horizontal_bars() -> fg.Graph:
    """Bars along y, which are fitted to the pixel grid by the renderer's height."""
    counts = pd.DataFrame({"n": [44, 124, 56], "kind": ["Adelie", "Gentoo", "Chinstrap"]})
    bars = {"mark.bar.show": True, "mark.line.show": False, "mark.marker.show": False}
    return fg.xy(counts, "n", "kind", parameters={**bars, "series.base_axis": "y"})


@pytest.mark.parametrize("make", [render, _horizontal_bars], ids=["lines", "horizontal bars"])
def test_the_record_of_a_figures_pixels_is_what_its_canvas_draws(make):
    import hashlib

    g = make()
    with isolated(g.style):  # as ForgeGraph draws and saves it: in the theme's settings
        g.figure.canvas.draw()
    assert hashlib.sha256(bytes(g.figure.canvas.buffer_rgba())).hexdigest() == g._drawn
    assert not g.nonstandard


def test_rendering_draws_the_figure_once_its_layout_is_final(monkeypatch):
    """Lint and the record of the figure's pixels share the one draw that follows layout."""
    from forgegraph import graph as graph_module
    from forgegraph.drawing.figure import GraphFigure

    draws, laid_out = [], []
    lay_out = graph_module.finish

    def counting_lay_out(*args, **kwargs):
        laid_out.clear()
        lay_out(*args, **kwargs)
        laid_out.append(True)

    original = GraphFigure.draw

    def counting_draw(self, renderer):
        if laid_out:
            draws.append(renderer)
        original(self, renderer)

    monkeypatch.setattr(graph_module, "finish", counting_lay_out)
    monkeypatch.setattr(GraphFigure, "draw", counting_draw)
    render()
    assert len(draws) == 1


def test_only_the_last_draw_of_a_render_paints(monkeypatch):
    painted = painted_draws(monkeypatch)
    render(settings={"legend.method": "direct"})  # direct labels: many measuring draws
    assert len(painted) == 1


def test_one_save_inspects_the_figure_once_whatever_it_writes(tmp_path, monkeypatch):
    g = render(format={"output.file_types": list(FILE_TYPES)})
    hashes = []
    pixels = g._pixels
    monkeypatch.setattr(g, "_pixels", lambda: hashes.append(1) or pixels())
    saved = g.save(tmp_path / "g")
    assert len(saved) == len(FILE_TYPES) and len(hashes) == 1


def test_a_change_between_saves_is_still_found(tmp_path):
    g = render()
    [first] = g.save(tmp_path / "first.png")
    g.axes.axhline(0.7)
    [second] = g.save(tmp_path / "second.png")
    assert fg.load(first)["nonstandard"] is False  # type: ignore[index]
    assert fg.load(second)["nonstandard"] is True and _watermarked(g)  # type: ignore[index]


def test_saving_through_matplotlib_still_watermarks_and_records(tmp_path):
    g = render()
    g.axes.axhline(0.7)
    for kind in IMAGES:  # what matplotlib saves
        g.figure.savefig(tmp_path / f"direct.{kind}")
        record = fg.load(tmp_path / f"direct.{kind}")
        assert record is not None and record["nonstandard"] is True, kind
    assert _watermarked(g)
    [ours] = g.save(tmp_path / "ours.png")
    g.figure.savefig(tmp_path / "direct.png", dpi=int(g.values["format"]["output.dpi"]))
    assert np.array_equal(
        np.asarray(Image.open(ours)), np.asarray(Image.open(tmp_path / "direct.png"))
    )


def test_a_notebook_showing_the_figure_gets_the_watermark():
    g = render()
    g.axes.axhline(0.7)
    g.figure.canvas.print_figure(io.BytesIO(), format="png")  # what IPython calls
    assert _watermarked(g)


def test_once_changed_a_graph_stays_non_standard():
    g = render()
    line = g.axes.get_lines()[0]
    color = line.get_color()
    line.set_color("#FF00FF")
    assert g.nonstandard
    line.set_color(color)
    assert g.nonstandard


def test_provenance_off_records_nothing_even_for_a_non_standard_graph(tmp_path):
    g = render(format={"provenance.level": "off"})
    g.axes.axhline(0.7)
    [path] = g.save(tmp_path / "g.png")
    assert fg.load(path) is None and g.nonstandard  # the watermark still shows it


@pytest.mark.parametrize("text", ["   ", "\u200b\u00a0"], ids=["spaces", "invisible"])
def test_watermark_text_needs_a_visible_character(text):
    with pytest.raises(fg.SpecError, match=re.escape("watermark.text: has no letters")):
        render(theme={"watermark.text": text})


# --- layouts --------------------------------------------------------------------------------


def test_xy_draws_into_any_axes_so_layouts_can_place_it():
    g = render()
    style = Style(g.values["theme"], g.values["format"])
    with isolated(style):
        fig = Figure(figsize=(12, 5), layout="constrained")
        FigureCanvasAgg(fig)
        left, right = fig.subplots(1, 2)
        for ax in (left, right):
            drawn = xy.draw(ax, polarization(), g.values["graph_type"], style)
            xy.label(ax, drawn, g.values["graph_type"], style)
        fig.canvas.draw()
    assert (
        len(left.get_lines()) == len(right.get_lines()) == 8
    )  # 3 cells and the benchmark, 2 runs each
    assert left.get_position().x1 < right.get_position().x0


def _write_graphspec(path, **kw) -> None:
    """A GraphSpec drawing the example data, without writing the data."""
    dump(fg.graphspec(path.stem, "xy", settings=BASE, **kw), path)


def test_data_file_relative_to_the_graphspec(tmp_path):
    graphspec_file(tmp_path / "graphspecs", data="../data/p.parquet")
    g = fg.render(tmp_path / "graphspecs" / "p.yaml")
    assert g.data.file == "../data/p.parquet" and g.data.rows_read == 96


def test_data_file_absolute_or_from_home(tmp_path, monkeypatch):
    graphspec_file(tmp_path / "specs", "a", str(tmp_path / "p.parquet"))
    assert fg.render(tmp_path / "specs" / "a.yaml").data.rows_read == 96
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows finds ~ here
    _write_graphspec(tmp_path / "specs" / "h.yaml", data_file="~/p.parquet")
    assert fg.render(tmp_path / "specs" / "h.yaml").data.rows_read == 96


def test_inherited_data_file_is_found_from_the_file_that_sets_it(tmp_path):
    """A GraphSpec extending another finds a relative data.file from the other's folder."""
    house = write_pack(tmp_path / "packs")
    graphspec_file(house / "graphspecs", "base")
    allow(tmp_path, "forgegraph_base", "./packs/house")
    (tmp_path / "elsewhere").mkdir()
    child = tmp_path / "elsewhere" / "child.yaml"
    child.write_text(
        "name: child\nversion: 0\ndescription: test\nextends: house/base\n"
        "parameters:\n    text:\n        title: Child\n"
    )
    g = fg.render(child)
    assert g.data.rows_read == 96


def test_a_dataframe_passed_in_is_drawn_whatever_data_file_says(tmp_path):
    _write_graphspec(tmp_path / "g.yaml", data_file="missing.parquet")
    g = fg.render(tmp_path / "g.yaml", polarization())  # missing.parquet is never read
    assert g.data.rows_read == 96 and g.data.file is None


def test_a_missing_or_unreadable_data_file_is_an_error(tmp_path):
    _write_graphspec(tmp_path / "g.yaml", data_file="missing.parquet")
    with pytest.raises(fg.SpecError, match=re.escape("data.file: no file at")):
        fg.render(tmp_path / "g.yaml")
    polarization().to_csv(tmp_path / "p.parquet", index=False)  # not Parquet inside
    graphspec_file(tmp_path, "h")
    with pytest.raises(fg.SpecError, match="isn't a Parquet file"):
        fg.render(tmp_path / "h.yaml")


def test_column_types_survive_parquet(tmp_path):
    frame = pd.DataFrame(
        {
            "when": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05"]),
            "value": [1.5, None, 3.0],
            "group": ["a", "b", "a"],
        }
    )
    frame.to_parquet(tmp_path / "d.parquet")

    doc = fg.graphspec(
        "d",
        "xy",
        data_file="d.parquet",
        settings={"axis.x.data.column": "when", "axis.y.data.column": "value"},
    )
    dump(doc, tmp_path / "d.yaml")
    g = fg.render(tmp_path / "d.yaml")
    assert g.data.rows_read == 3 and g.data.rows_dropped == {"missing x or y": 1}


def test_impossible_drawings_are_errors_not_fallbacks():
    with pytest.raises(
        fg.SpecError, match=re.escape("benchmark.value: no rows where cell is 'Benchmrk'")
    ):
        render({"benchmark.value": "Benchmrk"})
    # Two groups of points in a checkerboard filling the plot: no label is nearer its own
    # group than the other, and no corner is clear for a legend.
    gx, gy = np.meshgrid(np.linspace(0, 100, 30), np.linspace(1, 1.7, 30))
    board = pd.DataFrame(
        {
            "current_density": gx.ravel(),
            "cell_voltage": gy.ravel(),
            "cell": np.where((np.arange(30)[:, None] + np.arange(30)) % 2, "A", "B").ravel(),
            "run": 1,
        }
    )
    no_margin = {"plot_area.margin": 0.0}  # no room beside the outer rows either
    scatter = {
        "mark.line.show": False,
        "benchmark.data_column": NONE,
        "benchmark.value": NONE,
        "encoding.detail.column": NONE,
    }
    with pytest.raises(
        fg.SpecError,
        match=re.escape(
            "legend.method: key doesn't fit this graph: every position in legend.key.positions "
            "is taken or covers data; use auto, or direct"
        ),
    ):
        render({**scatter, "legend.method": "key"}, theme=no_margin, data=board)
    with pytest.raises(
        fg.SpecError,
        match=re.escape("legend.method: auto, but no labelling method fits (direct, key tried)"),
    ):
        render(scatter, theme=no_margin, data=board)


def test_each_styling_column_gets_its_own_key():
    g = render({"encoding.line.style.column": "size", "encoding.marker.shape.column": "run"})
    assert {"size", "run"} <= {k.title for k in keys(g.axes)}


def _banded() -> pd.DataFrame:
    """A median line and an IQR's two edges, the line style set by band (issue 22)."""
    rows = []
    for x in range(5):
        rows += [
            {"x": x, "band": "median", "edge": "line", "y": 10 + x},
            {"x": x, "band": "IQR", "edge": "lo", "y": 8 + x},
            {"x": x, "band": "IQR", "edge": "hi", "y": 12 + x},
        ]
    return pd.DataFrame(rows)


BANDED = {
    "axis.x.data.column": "x",
    "axis.y.data.column": "y",
    "encoding.color.column": NONE,
    "encoding.line.style.column": "band",
    "encoding.detail.column": "edge",
    "encoding.order": "data",
    "benchmark.data_column": NONE,
    "benchmark.value": NONE,
    "mark.marker.show": False,
    "legend.method": "key",
}


def test_the_key_title_is_every_keys():
    def titles(**settings) -> list[str | None]:
        g = render({**BANDED, **settings}, data=_banded())
        return [k.title for k in keys(g.axes)]

    assert titles() == ["band"]  # column_name: its own column's
    assert titles(**{"legend.key.title.text": NONE}) == [None]
    assert titles(**{"legend.key.title.text": "Percentiles"}) == ["Percentiles"]
    colored = {"encoding.color.column": "edge", "encoding.detail.column": NONE}
    assert sorted(map(str, titles(**colored))) == ["band", "edge"]
    assert titles(**colored, **{"legend.key.title.text": NONE}) == [None, None]
    with pytest.raises(fg.SpecError, match=re.escape("legend.key.title.text: 'Percentiles'")):
        titles(**colored, **{"legend.key.title.text": "Percentiles"})
    two = {"encoding.marker.shape.column": "edge", "mark.marker.show": True}
    with pytest.raises(fg.SpecError, match=re.escape("legend.key.title.text: 'Percentiles'")):
        titles(**two, **{"legend.key.title.text": "Percentiles"})


def test_style_samples_take_the_series_color_with_no_color_encoding():
    def samples(**settings) -> tuple[set[str], fg.Graph]:
        g = render({**BANDED, **settings}, data=_banded())
        [key] = [k for k in keys(g.axes) if k.title == "band"]
        return {to_hex(cast(Line2D, e.handle).get_color()) for e in key.entries}, g

    colors, g = samples()
    drawn = {to_hex(ln.get_color()) for ln in g.axes.get_lines() if ln.get_gid() != KEY}
    assert colors == drawn == {to_hex(g.style.series_colors()[0])}
    colors, g = samples(**{"encoding.color.column": "edge", "encoding.detail.column": NONE})
    assert colors == {to_hex(g.style.color("font.color"))}  # neutral among the colors


def test_the_style_keys_drawn_are_reported():
    g = render(BANDED, data=_banded())
    assert g.labelling == "none" and g.style_keys == ["band"]
    assert render({**BANDED, "encoding.line.style.column": NONE}, data=_banded()).style_keys == []


# A delivered median, two percentile bands' edges, and the programmed schedule as the
# benchmark, the line style set by the same column (issue 23); each at its own height.
BASAL_Y = {"Delivered": 5.0, "Programmed": 5.5, "25-75%": (4.0, 6.0), "10-90%": (3.0, 7.0)}
BASAL = {
    "axis.x.data.column": "x",
    "axis.y.data.column": "y",
    "encoding.color.column": NONE,
    "encoding.line.style.column": "basal",
    "encoding.detail.column": "edge",
    "encoding.order": "data",
    "benchmark.data_column": "basal",
    "benchmark.value": "Programmed",
    "mark.marker.show": False,
}


def _basal() -> pd.DataFrame:
    rows = []
    for x in range(4):
        for basal, y in BASAL_Y.items():
            edges = {"lo": y[0], "hi": y[1]} if isinstance(y, tuple) else {"mid": y}
            rows += [{"x": x, "basal": basal, "edge": e, "y": v} for e, v in edges.items()]
    return pd.DataFrame(rows)


def test_a_style_key_matches_the_drawing_and_leaves_the_benchmark_to_the_labelling():
    outside = {"legend.key.positions": ["right_top"], "legend.key.inside": False}
    g = render({**BASAL, **outside, "legend.method": "direct"}, data=_basal())
    [key] = [k for k in keys(g.axes) if k.title == "basal"]
    sampled = {e.name: cast(Line2D, e.handle).get_linestyle() for e in key.entries}
    assert list(sampled) == ["Delivered", "25-75%", "10-90%"]  # no sample for the benchmark
    at = {v: name for name, y in BASAL_Y.items() for v in np.atleast_1d(y)}
    drawn = {
        at[float(np.asarray(ln.get_ydata(), dtype=float)[0])]: ln.get_linestyle()
        for ln in g.axes.get_lines()
        if ln.get_gid() != KEY and np.size(ln.get_xdata()) > 1
    }
    assert {name: drawn[name] for name in sampled} == sampled
    assert drawn["Programmed"] == LINE_STYLES[g.style.theme["series.benchmark.line.style"]]
    assert g.labelling == "direct"  # names the benchmark, once
    assert [t.get_text() for t in g.axes.texts if t.get_text() == "Programmed"] == ["Programmed"]


def test_a_key_that_doesnt_fit_says_why():
    with pytest.raises(
        fg.SpecError,
        match=re.escape(
            "legend.method: key doesn't fit this graph: every position in legend.key.positions "
            "is taken or covers data (the style key for basal took right_top)"
        ),
    ):
        render(
            {
                **BASAL,
                "legend.method": "key",
                "legend.key.positions": ["right_top"],
                "legend.key.inside": False,
            },
            data=_basal(),
        )


def test_each_y_column_is_its_own_line():
    g = render({"axis.y.data.column": ["cell_voltage", "ir_free_voltage"], "axis.y.title": "V"})
    lines = [line for line in g.axes.get_lines() if np.size(line.get_xdata()) > 1]
    assert len(lines) == 4 * 2 * 2  # cells x runs x y columns
    for line in lines:  # every curve falls; stepping up to the other column would rise
        ys = np.asarray(line.get_ydata(), dtype=float)
        assert np.nanmax(np.diff(ys)) < 0.01


def test_log_axis_labels_are_plain_or_powers_never_both():
    narrow = render({"axis.y.scale": "log"})
    labels = [t.get_text() for t in narrow.axes.get_yticklabels() if t.get_text()]
    assert labels and all("10^" not in t for t in labels)
    wide = polarization().assign(current_density=lambda d: 10 ** (d["current_density"] / 20 - 5))
    g = render({"axis.x.scale": "log"}, data=wide)
    labels = [t.get_text() for t in g.axes.get_xticklabels() if t.get_text()]
    assert labels and all(t.startswith("$10^") for t in labels)


@pytest.mark.slow
def test_extending_the_x_axis_for_labels_adds_no_ticks():
    from forgegraph.catalog_build.cards import Change
    from forgegraph.catalog_build.examples import draw

    fanned = Change("data.file", "fanned.parquet")  # long names: they need room
    g = draw(
        fanned,
        Change("legend.direct.max_axis_extension", 0.4),
        spec="forgegraph_base/graphspec_example",
    )
    assert g.labelling == "direct"
    ticks = [t for t in g.axes.get_xticks() if t <= g.axes.get_xlim()[1]]
    assert max(ticks) <= 100  # the data ends at 100; the room beyond holds labels only


def test_direct_labels_can_widen_a_date_axis(monkeypatch):
    """A date axis's locator gives its ticks as a list; the room beyond keeps them too."""
    from forgegraph.drawing import labels

    place = labels.place_interior
    tries: list[bool] = []

    def no_room_at_first(ax, groups, style, draw=True):  # as if the labels need more room
        tries.append(draw)
        return len(tries) > 1 and place(ax, groups, style, draw=draw)

    monkeypatch.setattr(labels, "place_interior", no_room_at_first)
    days = pd.DataFrame(
        {
            "day": list(pd.date_range("2025-08-25", periods=6, freq="D")) * 2,
            "y": [1.0, 2, 3, 4, 5, 6, 6, 5, 4, 3, 2, 1],
            "run": ["up"] * 6 + ["down"] * 6,
        }
    )
    settings = {
        "axis.x.data.column": "day",
        "axis.y.data.column": "y",
        "encoding.color.column": "run",
        "encoding.detail.column": NONE,
        "benchmark.data_column": NONE,
        "benchmark.value": NONE,
        "legend.method": "direct",
    }
    g = render(settings, data=days)
    assert g.labelling == "direct" and tries[:2] == [True, False]  # widened, then placed


# --- matplotlib's settings while drawing ------------------------------------------------------


def test_drawing_settings_are_the_defaults_and_the_style_whatever_the_users_are():
    g = render()
    expected = matplotlib.RcParams({**dict.copy(matplotlib.rcParamsDefault), **g.style.rc()})
    with matplotlib.rc_context({"lines.linewidth": 7.0, "font.size": 3.0}):
        with isolated(g.style):
            inside = dict.copy(matplotlib.rcParams)
        after = (matplotlib.rcParams["lines.linewidth"], matplotlib.rcParams["font.size"])
    assert {k: v for k, v in inside.items() if k != "backend"} == {
        k: v for k, v in dict.items(expected) if k != "backend"
    }
    assert after == (7.0, 3.0)


def test_drawing_settings_are_checked_once_per_style(monkeypatch):
    g = render()
    with isolated(g.style):
        pass
    checked = []
    setitem = matplotlib.RcParams.__setitem__
    monkeypatch.setattr(
        matplotlib.RcParams,
        "__setitem__",
        lambda self, k, v: checked.append(k) or setitem(self, k, v),
    )
    for _ in range(3):
        with isolated(g.style):
            pass
    assert checked == []
