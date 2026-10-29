"""Layouts: GraphSpecs on a grid per tab, their plot boxes aligned, with separators between
them, saved per tab (images), as one PDF and as one HTML page; and the layout file's rules."""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from matplotlib.lines import Line2D
from pack_helpers import (
    BUILT_IN,
    allow,
    cli_problems,
    doc,
    dump,
    graphspec_file,
    needs_node,
    write_pack,
)
from PIL import Image
from render_helpers import BASE, painted_draws, polarization, with_series
from typer.testing import CliRunner

import forgegraph as fg
from forgegraph.cli import app
from forgegraph.drawing.figure import WATERMARK
from forgegraph.drawing.layout import visible_extent
from forgegraph.layouts import Layout, explain_layout
from forgegraph.spec.layout import slug
from forgegraph.spec.parameters import definition_file
from forgegraph.spec.registry import builtin
from forgegraph.spec.tags import fix
from forgegraph.spec.validate import validate

runner = CliRunner()
FORMAT = {"width": 200, "height": "auto", "base_size": 10}


def _format(name: str, file_types: tuple[str, ...] = ("png",), **figure: Any) -> dict[str, Any]:
    fixed = {"figure": {**FORMAT, **figure}}
    variable = {"output.file_types": list(file_types)}
    return doc("forgegraph_default/compact_format", name, fixed=fixed, variable=variable)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project: the example data, GraphSpecs whose y tick labels differ in width, a theme
    with other colors, formats with an auto and a fixed height, and a layout to extend that
    is the layout specification's own: it sets no separator's look."""
    for name, y, extra in (
        ("volt", "cell_voltage", {}),
        ("power", "power_density", {}),
        ("bright", "cell_voltage", {}),
    ):
        graphspec_file(
            tmp_path,
            name,
            theme="house/bright" if name == "bright" else "forgegraph_default/light_theme",
            settings={**BASE, "axis.y.data.column": y, **extra},
        )
    theme = doc(
        "forgegraph_default/light_theme", "bright", variable={"series.colors": "tol_bright"}
    )
    dump(theme, tmp_path / "house" / "themes" / "bright.yaml")
    dump(_format("auto"), tmp_path / "house" / "formats" / "auto.yaml")
    dump(_format("fixed", height=150), tmp_path / "house" / "formats" / "fixed.yaml")
    (tmp_path / "house" / "layouts").mkdir()
    spec = definition_file("layout").read_text(encoding="utf-8")
    plain = spec.replace("name: layout_example ", "name: plain ", 1)
    (tmp_path / "house" / "layouts" / "plain.yaml").write_text(plain, encoding="utf-8")
    write_pack(tmp_path)
    allow(tmp_path, "forgegraph_default", "./house")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    return tmp_path


def write_layout(
    folder,
    tabs: dict[str, Any],
    name: str = "fig",
    fmt: str = "house/auto",
    extends: str = "house/plain",
    **variable: Any,
) -> Any:
    variable = {"specifications": {"format": fmt}, **variable, "tabs": tabs}
    return dump(doc(extends, name, variable=variable), folder / f"{name}.layout.yaml")


def tab(areas: list[list[str]], **tiles: str) -> dict[str, Any]:
    return {"grid": {"areas": areas}, "tiles": tiles}


def boxes(layout: Layout, tab_index: int = 0) -> dict[str, Any]:
    t = layout.tabs[tab_index]
    return {name: tile.axes.get_window_extent() for name, tile in t.tiles.items()}


def record_of(path) -> dict[str, Any]:
    record = fg.load(path)
    assert record is not None
    return record


def problems(path) -> list[str]:
    with pytest.raises(fg.SpecError) as e:
        fg.layout(path)
    return e.value.problems


def test_only_the_last_draw_of_a_tab_paints(project, monkeypatch):
    painted = painted_draws(monkeypatch)
    fg.layout(
        write_layout(
            project, {"Figure": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
        )
    )
    assert len(painted) == 1


@pytest.mark.slow
def test_one_save_inspects_each_tab_once_whatever_it_writes(project, monkeypatch):
    tabs = {"A": tab([["volt"]], volt="volt.yaml"), "B": tab([["power"]], power="power.yaml")}
    standard = {"fmt": "forgegraph_default/wide_format", "extends": "forgegraph_default/layout"}
    layout = fg.layout(write_layout(project, tabs, **standard))
    assert not layout.nonstandard  # standard tabs are the ones inspected
    hashes = []
    for t in layout.tabs:
        pixels = t._pixels
        monkeypatch.setattr(t, "_pixels", lambda p=pixels: hashes.append(1) or p())
    for kind in ("html", "pdf", "png"):
        layout.save(project / f"fig.{kind}")
    assert len(hashes) == 3 * len(layout.tabs)  # once per tab, for each save


@pytest.mark.slow
def test_a_layouts_checks_records_and_saves(project, tmp_path, monkeypatch):
    """What Graph offers, a layout offers too: lint by tab, non-standard by tab, a record
    (none with provenance off), a save under its own name, and a PNG for notebooks."""
    tabs = {"A": tab([["volt"]], volt="volt.yaml"), "B": tab([["power"]], power="power.yaml")}
    standard = {"fmt": "forgegraph_default/wide_format", "extends": "forgegraph_default/layout"}
    layout = fg.layout(write_layout(project, tabs, **standard))
    assert layout.check() == layout.issues
    assert all(not t.nonstandard for t in layout.tabs)
    assert layout.record() is not None
    monkeypatch.setitem(layout.format, "provenance.level", "off")
    assert layout.record() is None
    monkeypatch.chdir(tmp_path)
    saved = layout.save()
    assert sorted(p.name for p in saved) == ["fig-a.png", "fig-b.png"]  # its name, a file a tab
    assert all((tmp_path / p.name).is_file() for p in saved)
    assert layout._repr_png_().startswith(b"\x89PNG")


def test_tiles_a_parent_layout_lists_are_found_from_its_folder(project):
    """A layout extending a pack's layout: the tile files the pack's layout lists are found
    from its folder, not from the layout that extends it."""
    layouts = project / "house" / "layouts"
    graphspec_file(layouts / "graphs", "v")
    parent = write_layout(layouts, {"Figure": tab([["v"]], v="graphs/v.yaml")}, name="shared")
    parent.rename(layouts / "shared.yaml")
    work = project / "work"
    work.mkdir()
    allow(work, "forgegraph_default", "../house")
    dump(doc("house/shared", "mine"), work / "mine.layout.yaml")
    layout = fg.layout(work / "mine.layout.yaml")
    assert list(layout.tabs[0].tiles) == ["v"]


# The grid


@pytest.mark.slow
def test_plot_boxes_line_up_whatever_their_tick_labels(project):
    path = write_layout(
        project,
        {
            "Figure": tab(
                [["volt", "bright"], ["power", "bright"]],
                volt="volt.yaml",
                power="power.yaml",
                bright="bright.yaml",
            )
        },
    )
    b = boxes(fg.layout(path))
    assert b["volt"].x0 == pytest.approx(b["power"].x0, abs=0.5)  # labels differ in width
    assert b["volt"].x1 == pytest.approx(b["power"].x1, abs=0.5)
    assert b["bright"].y1 == pytest.approx(b["volt"].y1, abs=0.5)  # the span: top to bottom
    assert b["bright"].y0 == pytest.approx(b["power"].y0, abs=0.5)


def test_column_widths_are_ratios_of_plot_boxes(project):
    grid = {"areas": [["volt", "power"]], "column_widths": [1, 2]}
    path = write_layout(
        project, {"T": {"grid": grid, "tiles": {"volt": "volt.yaml", "power": "power.yaml"}}}
    )
    b = boxes(fg.layout(path))
    assert b["power"].width / b["volt"].width == pytest.approx(2, rel=1e-3)


@pytest.mark.slow
def test_a_span_runs_across_the_margins_and_gap_inside_it(project):
    path = write_layout(
        project,
        {
            "T": tab(
                [["volt", "volt"], ["power", "bright"]],
                volt="volt.yaml",
                power="power.yaml",
                bright="bright.yaml",
            )
        },
    )
    b = boxes(fg.layout(path))
    assert b["volt"].x0 == pytest.approx(b["power"].x0, abs=0.5)
    assert b["volt"].x1 == pytest.approx(b["bright"].x1, abs=0.5)


def test_with_height_auto_each_plot_keeps_its_aspect_or_more(project):
    path = write_layout(
        project, {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
    )
    layout = fg.layout(path)
    aspect = float(layout.tabs[0].tiles["volt"].style.theme["plot_area.aspect_ratio"])
    for box in boxes(layout).values():
        assert box.width / box.height == pytest.approx(aspect, rel=1e-3)


def test_with_width_auto_each_plot_keeps_its_aspect_too(project):
    dump(_format("tall", width="auto", height=150), project / "house" / "formats" / "tall.yaml")
    path = write_layout(
        project,
        {"T": tab([["volt"], ["power"]], volt="volt.yaml", power="power.yaml")},
        fmt="house/tall",
    )
    layout = fg.layout(path)
    aspect = float(layout.tabs[0].tiles["volt"].style.theme["plot_area.aspect_ratio"])
    for box in boxes(layout).values():
        assert box.width / box.height == pytest.approx(aspect, rel=1e-3)
    height = layout.tabs[0].figure.get_size_inches()[1] * 25.4
    assert height == pytest.approx(150, abs=0.01)


@pytest.mark.slow
def test_a_fixed_size_is_the_figures_size(project):
    path = write_layout(
        project,
        {"T": tab([["volt"], ["power"]], volt="volt.yaml", power="power.yaml")},
        fmt="house/fixed",
    )
    fig = fg.layout(path).tabs[0].figure
    assert tuple(fig.get_size_inches() * 25.4) == pytest.approx((200, 150), abs=0.01)


def test_tiles_are_a_gap_apart(project):
    path = write_layout(
        project, {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
    )
    layout = fg.layout(path)
    t = layout.tabs[0]
    renderer = t.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    a = visible_extent(t.tiles["volt"].axes, renderer)
    b = visible_extent(t.tiles["power"].axes, renderer)
    gap_px = 1.5 * 10 / 72 * t.figure.dpi
    assert b.x0 - a.x1 == pytest.approx(gap_px, abs=0.5)


@pytest.mark.slow
def test_a_blank_cell_is_left_empty(project):
    path = write_layout(
        project,
        {
            "T": tab(
                [["volt", "power"], ["bright", "."]],
                volt="volt.yaml",
                power="power.yaml",
                bright="bright.yaml",
            )
        },
    )
    b = boxes(fg.layout(path))
    assert b["bright"].x1 == pytest.approx(b["volt"].x1, abs=0.5)  # one column wide


def test_too_small_a_format_names_the_tiles_that_dont_fit(project):
    dump(_format("tiny", width=40), project / "house" / "formats" / "tiny.yaml")
    path = write_layout(
        project,
        {
            "T": tab(
                [["volt", "power", "bright"]],
                volt="volt.yaml",
                power="power.yaml",
                bright="bright.yaml",
            )
        },
        fmt="house/tiny",
    )
    [problem] = problems(path)
    assert problem.startswith("tabs.T: size: too small") and "'volt'" in problem


# Each tile as its GraphSpec says


def test_each_tile_keeps_its_own_theme(project):
    path = write_layout(
        project, {"T": tab([["volt", "bright"]], volt="volt.yaml", bright="bright.yaml")}
    )
    t = fg.layout(path).tabs[0]
    first = {tile: t.tiles[tile].axes.get_lines()[0].get_color() for tile in ("volt", "bright")}
    assert first == {"volt": "#0072B2", "bright": "#4477AA"}  # okabe_ito, tol_bright


def test_the_layouts_format_replaces_each_tiles(project):
    path = write_layout(project, {"T": tab([["volt"]], volt="volt.yaml")})
    tile = fg.layout(path).tabs[0].tiles["volt"]
    assert tile.values["format"]["figure.base_size"] == 10  # the GraphSpec names default
    label = tile.axes.xaxis.get_major_ticks()[0].label1
    tick = float(tile.style.theme["axis.tick.label.size"]) * 10
    assert label.get_fontsize() == pytest.approx(tick)


def test_a_tile_can_be_drawn_from_a_dataframe(project):
    doc = fg.graphspec("frame", "xy", settings=with_series(BASE))
    dump(doc, project / "frame.yaml")
    path = write_layout(project, {"T": tab([["f"]], f="frame.yaml")})
    assert fg.layout(path, data={"f": polarization()}).tabs[0].tiles["f"].data.rows_read == 96
    with pytest.raises(fg.SpecError, match="data: no tile 'g'"):
        fg.layout(path, data={"g": polarization()})


def test_lint_names_the_tile(project):
    frame = polarization()
    frame.loc[0, "cell_voltage"] = np.nan
    frame.to_parquet(project / "gaps.parquet")
    doc = fg.graphspec("gaps", "xy", data_file="gaps.parquet", settings=with_series(BASE))
    dump(doc, project / "gaps.yaml")
    path = write_layout(project, {"T": tab([["volt", "gaps"]], volt="volt.yaml", gaps="gaps.yaml")})
    messages = fg.layout(path).warnings
    assert any(m.startswith("tile 'gaps': ") and "left out" in m for m in messages), messages


# Separators


@pytest.mark.slow
def test_lines_run_between_tiles_but_not_through_a_span(project):
    path = write_layout(
        project,
        {
            "T": tab(
                [["volt", "bright"], ["power", "bright"]],
                volt="volt.yaml",
                power="power.yaml",
                bright="bright.yaml",
            )
        },
        separators={"line": {"width": 0.05}},
    )
    t = fg.layout(path).tabs[0]
    lines = [a for a in t.figure.artists if isinstance(a, Line2D)]
    vertical = [ln for ln in lines if np.ptp(np.asarray(ln.get_xdata())) == 0]
    horizontal = [ln for ln in lines if np.ptp(np.asarray(ln.get_ydata())) == 0]
    assert len(vertical) == 2 and len(horizontal) == 1  # beside each row; under volt only
    bright = t.tiles["bright"].axes.get_position()
    assert max(np.asarray(horizontal[0].get_xdata())) < bright.x0


@pytest.mark.slow
def test_a_blank_cell_counts_as_a_tile_for_lines(project):
    areas = [["volt", "power"], ["bright", "."]]
    tiles = {"volt": "volt.yaml", "power": "power.yaml", "bright": "bright.yaml"}
    path = write_layout(project, {"T": tab(areas, **tiles)}, separators={"line": {"width": 0.05}})
    t = fg.layout(path).tabs[0]
    lines = [a for a in t.figure.artists if isinstance(a, Line2D)]
    vertical = [ln for ln in lines if np.ptp(np.asarray(ln.get_xdata())) == 0]
    horizontal = [ln for ln in lines if np.ptp(np.asarray(ln.get_ydata())) == 0]
    assert len(vertical) == 2 and len(horizontal) == 2  # beside and above the blank cell too


def test_a_border_runs_round_the_tiles_through_the_middle_of_the_inner_gap(project):
    path = write_layout(
        project,
        {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")},
        separators={"border": {"show": True}},
    )
    t = fg.layout(path).tabs[0]
    [border] = [
        a for a in t.figure.artists if isinstance(a, Line2D) and np.size(a.get_xdata()) == 5
    ]
    xs = np.asarray(border.get_xdata())
    gap = 1.5 * 10 / 72  # inches: gap.inner
    width = t.figure.get_size_inches()[0]
    assert min(xs) * width == pytest.approx(gap / 2)
    renderer = t.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    left = visible_extent(t.tiles["volt"].axes, renderer).x0 / t.figure.dpi
    assert left == pytest.approx(gap, abs=0.01)


def test_the_inner_gap_is_at_the_figures_edges_and_the_outer_between_tiles(project):
    path = write_layout(
        project,
        {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")},
        separators={"gap": {"inner": 1.0, "outer": 3.0}},
    )
    t = fg.layout(path).tabs[0]
    renderer = t.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    volt, power = (visible_extent(t.tiles[n].axes, renderer) for n in ("volt", "power"))
    dpi = t.figure.dpi
    assert volt.x0 / dpi == pytest.approx(1.0 * 10 / 72, abs=0.01)
    assert (power.x0 - volt.x1) / dpi == pytest.approx(3.0 * 10 / 72, abs=0.01)


def _lines_between(t) -> list[Line2D]:
    return [a for a in t.figure.artists if isinstance(a, Line2D)]


def test_the_lines_between_tiles_take_the_first_tiles_theme_line(project):
    from matplotlib.colors import to_hex

    tiles = {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
    t = fg.layout(write_layout(project, tiles)).tabs[0]
    [line] = _lines_between(t)
    theme = t.style.theme
    assert to_hex(line.get_color()) == theme["line.color"].lower()
    assert line.get_linewidth() == pytest.approx(theme["line.width"] * 10)  # the layout's base
    own = {"line": {"width": 0.2, "color": "#336699", "style": "dashed"}}
    t = fg.layout(write_layout(project, tiles, "own", separators=own)).tabs[0]
    [line] = _lines_between(t)
    assert (to_hex(line.get_color()), line.get_linewidth(), line.get_linestyle()) == (
        "#336699",
        pytest.approx(2.0),
        "--",
    )
    none = {"line": {"style": None}, "border": {"show": True}}
    t = fg.layout(write_layout(project, tiles, "none", separators=none)).tabs[0]
    assert _lines_between(t) == []  # no line, so no border either


def test_tile_backgrounds_can_have_rounded_corners(project):
    from matplotlib.patches import FancyBboxPatch

    tiles = {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
    t = fg.layout(write_layout(project, tiles, separators={"corner_radius": 1.0})).tabs[0]
    rounded = [a for a in t.figure.artists if isinstance(a, FancyBboxPatch)]
    assert len(rounded) == 2
    assert cast(Any, rounded[0].get_boxstyle()).rounding_size == pytest.approx(
        10 / 72
    )  # 1 base size, in inches


@pytest.mark.slow
def test_the_gaps_take_the_first_tiles_theme_background(project):
    red = doc("forgegraph_default/light_theme", "red", variable={"background.color": "#FF0000"})
    dump(red, project / "house" / "themes" / "red.yaml")
    graphspec_file(project, "reddish", theme="house/red", settings={**BASE})
    tiles = {"T": tab([["reddish", "volt"]], reddish="reddish.yaml", volt="volt.yaml")}
    none = {"line": {"style": None}}
    [png] = fg.layout(write_layout(project, tiles, separators=none)).save(project / "o" / "r.png")
    pixels: np.ndarray = np.asarray(Image.open(png).convert("RGB"))
    assert tuple(pixels[0, -1]) == (255, 0, 0)  # the figure's edge, by the second tile too
    tiles = {"T": tab([["volt", "reddish"]], reddish="reddish.yaml", volt="volt.yaml")}
    [png] = fg.layout(write_layout(project, tiles, "w", separators=none)).save(
        project / "o" / "w.png"
    )
    pixels = np.asarray(Image.open(png).convert("RGB"))
    assert tuple(pixels[0, -1]) == (255, 255, 255)


# Tabs and output


@pytest.mark.slow
def test_tabs_save_a_file_each_a_pdf_page_each_and_one_page(project):
    types = {"output": {"file_types": ["png", "pdf", "html"]}}
    dump(
        _format("all", tuple(types["output"]["file_types"])),
        project / "house" / "formats" / "all.yaml",
    )
    path = write_layout(
        project,
        {
            "Overview": tab([["volt"]], volt="volt.yaml"),
            "By cell": tab([["power"]], power="power.yaml"),
        },
        fmt="house/all",
    )
    saved = fg.layout(path).save_all(project / "out" / "fig")
    names = [p.name for p in saved]
    assert names == ["fig-overview.png", "fig-by-cell.png", "fig.pdf", "fig.html"]
    pdf = (project / "out" / "fig.pdf").read_bytes()
    assert len(re.findall(rb"/Type /Page\b", pdf)) == 2
    page = (project / "out" / "fig.html").read_text()
    assert '<a role="tab" href="#overview">Overview</a>' in page
    assert '<section id="by-cell"><h2>By cell</h2><img' in page
    for p in saved:
        record = record_of(p)
        assert record["layout"]["name"] == "fig"
    assert list(record_of(project / "out" / "fig-by-cell.png")["tabs"]) == ["By cell"]
    assert sorted(record_of(project / "out" / "fig.html")["tabs"]) == ["By cell", "Overview"]


NESTED = {
    "Platinum": {
        "tabs": {
            "Voltage": tab([["pv"]], pv="volt.yaml"),
            "Power": tab([["pp"]], pp="power.yaml"),
        }
    },
    "Nickel": {"tabs": {"Voltage": tab([["nv"]], nv="volt.yaml")}},
    "Notes": {"tabs": {"Deep": {"tabs": {"Deeper": tab([["d"]], d="power.yaml")}}}},
}


def test_tabs_hold_tabs_to_any_depth(project):
    """Each tab that's a grid is drawn, named by its path: its files by every tab on the path,
    and the page has a tab bar for each tab holding tabs."""
    types = ("png", "html")
    dump(_format("both", types), project / "house" / "formats" / "both.yaml")
    path = write_layout(project, NESTED, fmt="house/both")
    layout = fg.layout(path)
    assert [t.name for t in layout.tabs] == [
        "Platinum / Voltage",
        "Platinum / Power",
        "Nickel / Voltage",
        "Notes / Deep / Deeper",
    ]
    saved = [p.name for p in layout.save_all(project / "out" / "fig")]
    assert saved == [
        "fig-platinum-voltage.png",
        "fig-platinum-power.png",
        "fig-nickel-voltage.png",
        "fig-notes-deep-deeper.png",
        "fig.html",
    ]
    page = (project / "out" / "fig.html").read_text()
    assert re.findall(r'<nav role="tablist" data-under="([^"]*)">', page) == [
        "",
        "platinum",
        "nickel",
        "notes",
        "notes/deep",
    ]
    assert '<a role="tab" href="#nickel">Nickel</a>' in page
    assert '<a role="tab" href="#notes/deep/deeper">Deeper</a>' in page
    assert '<section id="nickel/voltage"><h2>Nickel / Voltage</h2><img' in page
    assert sorted(record_of(project / "out" / "fig.html")["tabs"])[0] == "Nickel / Voltage"
    tile = explain_layout(path)[1]["Platinum.tabs.Power", "pp"]
    assert tile.theme["title.size"].value is not None


@needs_node
def test_a_pages_link_to_a_tab_holding_tabs_keeps_the_ones_showing_below_it(project):
    path = write_layout(project, NESTED, output={"file_types": ["html"]})
    [page] = fg.layout(path).save_all(project / "out" / "fig")
    script = re.search(r"<script>\s*(function pick.*?)\n\(function", page.read_text(), re.S)
    assert script
    ids = ["platinum/voltage", "platinum/power", "nickel/voltage", "notes/deep/deeper"]
    cases = [
        ("nickel", "platinum/voltage", "nickel/voltage"),  # the same chart in another group
        ("nickel", "platinum/power", "nickel/voltage"),  # it has no Power: its first
        ("platinum", "nickel/voltage", "platinum/voltage"),
        ("platinum/power", "nickel/voltage", "platinum/power"),  # a tab itself
        ("notes", None, "notes/deep/deeper"),
        ("", None, "platinum/voltage"),  # no link: the first tab
        ("nowhere", None, "platinum/voltage"),
    ]
    calls = "".join(
        f"console.log(pick({json.dumps(ids)}, {json.dumps(to)}, {json.dumps(now)}));"
        for to, now, _ in cases
    )
    node = shutil.which("node")
    assert node is not None
    done = subprocess.run(
        [node, "-e", script[1] + calls], capture_output=True, text=True, check=True
    )
    assert done.stdout.split() == [want for _, _, want in cases]


@pytest.mark.parametrize(
    ("tabs", "message"),
    [
        (
            {"T": {"tabs": {"A": tab([["a"]], a="a.yaml")}, "grid": {"areas": [["b"]]}}},
            "tabs.T.grid: a tab holding tabs has no grid; put it in one of its tabs",
        ),
        ({"T": {"tabs": {}}}, "tabs.T.tabs: must be one or more tabs, each under its name"),
        (
            {"T": {"tabs": {"A": {"grid": {"areas": [["a", "b"]]}, "tiles": {"a": "a.yaml"}}}}},
            "tabs.T.tabs.A.tiles: no tile for 'b', which grid.areas names",
        ),
        (
            {
                "A b": {"tabs": {"C": tab([["a"]], a="a.yaml")}},
                "A": {"tabs": {"B c": tab([["b"]], b="b.yaml")}},
            },
            "tabs.A.tabs.B c: gives the same file names as tab 'A b / C' (a-b-c); rename one",
        ),
        (
            {"T": {"tabs": {"A": tab([["a"]], a="a.yaml")}}, "U": tab([["a"]], a="b.yaml")},
            "tabs.U.tiles.a: also a tile in tab 'T / A'; names are unique",
        ),
    ],
)
def test_nested_tab_rules(tabs, message):
    found = _check({"tabs": tabs})
    assert message in found, found


def _page_style(page: str) -> str:
    found = re.search(r"<style>(.*?)</style>", page, re.S)
    assert found
    return found[1]


def test_the_tab_bar_takes_tab_bar_label_and_line(project):
    two = {"One": tab([["volt"]], volt="volt.yaml"), "Two": tab([["power"]], power="power.yaml")}
    label = {"color": "#AA0000", "weight": "bold", "size": 1.0, "alignment": "right"}
    line = {"style": "dashed", "width": 0.1, "color": "#00AA00"}
    path = write_layout(
        project, two, output={"file_types": ["html"]}, tab_bar={"label": label, "line": line}
    )
    [page] = fg.layout(path).save_all(project / "out" / "fig")
    css = _page_style(page.read_text())
    base = 10  # the auto format's base size
    assert '@font-face { font-family: "Roboto"; font-weight: 700;' in css
    assert f"font-size: {base:g}pt; font-weight: 700;\n  color: #AA0000;" in css
    assert "justify-content: flex-end;" in css
    assert f"border-bottom: {0.1 * base:g}pt dashed #00AA00;" in css
    assert 'nav a[aria-selected="true"] { border-bottom-color: #AA0000; }' in css


def test_the_tab_bar_takes_the_first_tiles_theme_text_and_line_by_default(project):
    two = {"One": tab([["volt"]], volt="volt.yaml"), "Two": tab([["power"]], power="power.yaml")}
    [page] = fg.layout(write_layout(project, two, output={"file_types": ["html"]})).save_all(
        project / "out" / "fig"
    )
    css = _page_style(page.read_text())
    assert "font-weight: 400;\n  color: #000000;" in css and "justify-content: center;" in css
    assert "border-bottom: 0.7pt solid #000000;" in css  # the theme's line, times base size 10


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ({"style": "dashdot"}, "tab_bar.line.style"),
        ({"cap": "round"}, "tab_bar.line.cap"),
    ],
)
def test_the_tab_bar_line_is_one_a_page_can_draw(line, message):
    found = _check({"tab_bar": {"line": line}, "tabs": {"T": tab([["a"]], a="a.yaml")}})
    assert any(message in p for p in found), found


def test_a_layout_sets_its_formats_variable_parameters(project):
    path = write_layout(
        project,
        {"Overview": tab([["volt"]], volt="volt.yaml")},
        fmt="house/auto",
        output={"file_types": ["html", "png"]},
    )
    saved = fg.layout(path).save_all(project / "out" / "fig")
    assert sorted(p.name for p in saved) == ["fig.html", "fig.png"]
    tile = explain_layout(path)[1]["Overview", "volt"].format["output.file_types"]
    assert tile.value == ["html", "png"] and tile.origin == "layout 'fig'"


def test_a_layout_cant_set_its_formats_fixed_parameters():
    reg = builtin().copy()
    reg.add("format", doc(BUILT_IN["format"], "pinned", fixed={"figure.width": 300}))
    variable = {"figure": {"width": 200}, "tabs": {"T": tab([["a"]], a="a.yaml")}}
    layout = doc(BUILT_IN["layout"], variable={**variable, "specifications": {"format": "pinned"}})
    [found] = validate("layout", layout, reg)
    assert found == "figure.width: fixed by format 'pinned'"


@pytest.mark.slow
def test_with_a_border_the_tab_bars_line_is_its_top(project):
    dump(
        _format("page", ("html",)),
        project / "house" / "formats" / "page.yaml",
    )
    path = write_layout(
        project,
        {"One": tab([["volt"]], volt="volt.yaml"), "Two": tab([["power"]], power="power.yaml")},
        fmt="house/page",
        separators={"border": {"show": True}},
    )
    layout = fg.layout(path)
    [page_file] = layout.save_all(project / "out" / "fig")
    text = page_file.read_text()
    figure = layout.tabs[0].figure
    width_pt = figure.get_size_inches()[0] * 72
    out, half = 1.5 * 10 / 2, 0.07 * 10 / 2  # the border's centre and half its width, pt
    svg = base64.b64decode(re.findall(r"base64,([^\"]+)", text)[0])
    box = re.search(rb'viewBox="([^"]+)"', svg)
    assert box is not None
    left, top, width, _ = (float(v) for v in box[1].split())
    assert (left, top) == pytest.approx((out - half, out + half), abs=1e-3)  # top side cut off
    assert width == pytest.approx(width_pt - 2 * out + 2 * half, abs=1e-3)
    assert f"main {{ max-width: {width:g}pt; }}" in text
    assert "border-bottom: 0.7pt solid #000000" in text  # the tab bar's line, as the border


@pytest.mark.slow
def test_one_tab_is_saved_without_its_name(project):
    path = write_layout(project, {"Figure": tab([["volt"]], volt="volt.yaml")})
    [png] = fg.layout(path).save_all(project / "out" / "fig")
    assert png.name == "fig.png"
    [page] = fg.layout(path).save(project / "out" / "fig.html")
    assert "<nav" not in page.read_text()


def test_tab_names_become_file_names_and_links():
    assert slug("By instrument") == "by-instrument"
    assert slug("  Cells: A/C ") == "cells-ac"


@pytest.mark.slow
def test_the_record_holds_each_tiles_graphspec_and_data(project):
    path = write_layout(
        project, {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
    )
    [png] = fg.layout(path).save(project / "out" / "fig.png")
    tiles = record_of(png)["tabs"]["T"]
    assert tiles["power"]["file"] == "power.yaml"
    assert tiles["power"]["graphspec"]["name"] == "power"
    assert tiles["power"]["data"] == "p.parquet"
    assert tiles["power"]["resolved"]["format"]["figure.base_size"] == 10
    assert tiles["power"]["specs"]["format"]["name"] == "house/auto"  # the layout's, not its own


@pytest.mark.slow
def test_rendering_twice_gives_the_same_file(project):
    path = write_layout(
        project, {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
    )
    [a] = fg.layout(path).save(project / "a.png")
    [b] = fg.layout(path).save(project / "b.png")
    assert a.read_bytes() == b.read_bytes()


@pytest.mark.slow
def test_drawing_on_a_tab_watermarks_every_tile(project):
    path = write_layout(
        project, {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
    )
    layout = fg.layout(path)
    t = layout.tabs[0]
    t.tiles["volt"].axes.axhline(0.7)
    [png] = layout.save(project / "out" / "fig.png")
    assert record_of(png)["nonstandard"] is True
    for tile in t.tiles.values():
        assert any(a.get_gid() == WATERMARK for a in tile.axes.get_children())


# A GraphSpec's page


def test_a_graphspec_saves_as_a_page(project):
    g = fg.render(project / "volt.yaml")
    [page] = g.save(project / "out" / "volt.html")
    text = page.read_text()
    assert text.count("<img") == 1 and "<nav" not in text
    assert record_of(page)["graphspec"]["name"] == "volt"


# The layout file's rules


def _check(variable: dict[str, Any]) -> list[str]:
    layout = doc("forgegraph_default/layout", variable=variable)
    return validate("layout", layout, builtin().copy())


@pytest.mark.parametrize(
    ("grid", "tiles", "message"),
    [
        ([["a", "b"], ["c"]], ["a", "b", "c"], "every row needs the same number of cells"),
        ([["a", "b"], ["b", "a"]], ["a", "b"], "'a' must fill a rectangle"),
        ([["a"], ["."]], ["a"], "row 2 is all blank"),
        ([["a", "."]], ["a"], "column 2 is all blank"),
        ([["a", "b"]], ["a"], "no tile for 'b'"),
        ([["a"]], ["a", "z"], "tiles.z: not in grid.areas"),
    ],
)
def test_grid_rules(grid, tiles, message):
    found = _check(
        {"tabs": {"T": {"grid": {"areas": grid}, "tiles": {t: f"{t}.yaml" for t in tiles}}}}
    )
    assert any(message in p for p in found), found


def test_sizes_need_one_per_column_or_row():
    grid = {"areas": [["a", "b"]], "column_widths": [1, 2, 3]}
    found = _check({"tabs": {"T": {"grid": grid, "tiles": {"a": "a.yaml", "b": "b.yaml"}}}})
    assert found == ["tabs.T.grid.column_widths: 3 sizes, but the grid has 2 columns"]


def test_row_heights_with_height_auto_is_an_error():
    grid = {"areas": [["a"], ["b"]], "row_heights": [1, 2]}
    [found] = _check({"tabs": {"T": {"grid": grid, "tiles": {"a": "a.yaml", "b": "b.yaml"}}}})
    assert "format 'forgegraph_default/wide_format' has figure.height auto" in found


def test_tile_names_are_unique_and_tab_names_give_distinct_files():
    found = _check({"tabs": {"One": tab([["a"]], a="a.yaml"), "one": tab([["a"]], a="b.yaml")}})
    assert any("gives the same file names and links as tab 'One'" in p for p in found)
    assert any("tiles.a: also a tile in tab 'One'" in p for p in found)
    found = _check({"tabs": {"!!": tab([["a"]], a="a.yaml")}})
    assert any("tabs.!!: a tab's name needs a letter or digit" in p for p in found)


def test_cli_explain_reports_a_layout_that_fails(project):
    path = write_layout(project, {"T": tab([["volt"]], volt="missing.yaml")})
    [problem] = cli_problems("explain", str(path))
    assert "missing.yaml" in problem


@pytest.mark.slow
def test_a_layouts_tabs_replace_those_it_inherits(project):
    old = {
        "specifications.format": "house/auto",
        "tabs": {"Old": tab([["volt"]], volt="volt.yaml")},
    }
    base = doc("forgegraph_default/layout", "base", variable=old)
    dump(base, project / "house" / "layouts" / "base.yaml")
    new = {"tabs": {"New": tab([["power"]], power="power.yaml")}}
    dump(doc("house/base", "child", variable=new), project / "child.layout.yaml")
    layout = fg.layout(project / "child.layout.yaml")
    assert [t.name for t in layout.tabs] == ["New"]


def test_tabs_tagged_fix_cant_be_replaced_and_tags_go_on_tabs():
    reg = builtin().copy()
    base = doc(
        "forgegraph_default/layout", "base", fixed={"tabs": {"Old": tab([["a"]], a="a.yaml")}}
    )
    reg.add("layout", base)
    child = doc("base", "child", untagged={"tabs": {"New": tab([["b"]], b="b.yaml")}})
    assert validate("layout", child, reg) == ["tabs: fixed by layout 'base'"]
    inside = {"tabs": {"T": {"grid": fix({"areas": [["a"]]}), "tiles": {"a": "a.yaml"}}}}
    assert _check(inside) == ["tabs.T.grid: a tag goes on tabs, not inside them"]


def test_unset_and_missing_tiles_are_errors(project):
    path = write_layout(
        project, {"T": tab([["a", "b", "c"]], a="None", b="nowhere.yaml", c="fig.layout.yaml")}
    )
    found = problems(path)
    assert found == ["tabs.T.tiles.a: must be set before the layout can be drawn: a GraphSpec file"]
    path = write_layout(project, {"T": tab([["b", "c"]], b="nowhere.yaml", c="fig.layout.yaml")})
    found = problems(path)
    assert found[0].startswith("tabs.T.tiles.b: no GraphSpec file at")
    assert found[1] == "tabs.T.tiles.c: 'fig.layout.yaml' is a layout; a tile is a GraphSpec file"


def test_a_tiles_problems_say_where_they_are(project):
    (project / "bad.yaml").write_text(
        (project / "volt.yaml").read_text().replace("cell_voltage", "nope")
    )
    path = write_layout(project, {"T": tab([["bad"]], bad="bad.yaml")})
    [found] = problems(path)
    assert found.startswith("tabs.T.tiles.bad (bad.yaml): ")


# The command line


@pytest.mark.slow
def test_cli_renders_explains_and_loads_a_layout(project):
    path = write_layout(
        project, {"T": tab([["volt", "power"]], volt="volt.yaml", power="power.yaml")}
    )
    result = runner.invoke(app, ["render", str(path), "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["saved"] == [str(project / "fig.png")]
    assert set(report["labelling"]) == {"T.volt", "T.power"}
    assert report["style_keys"] == {"T.volt": [], "T.power": []}
    result = runner.invoke(app, ["explain", str(path), "--json"])
    rows = json.loads(result.output)["values"]
    base = next(
        r
        for r in rows
        if r["kind"] == "tabs.T.tiles.power.format" and r["parameter"] == "figure.base_size"
    )
    assert base["value"] == 10 and base["set_by"] == "format 'house/auto', from layout 'fig'"
    result = runner.invoke(app, ["load", str(project / "fig.png")])
    assert (
        "layout: fig" in result.output
        and "tab T: power (power.yaml), volt (volt.yaml)" in result.output
    )
    result = runner.invoke(app, ["schema", "layout", "--json"])
    params = [p["parameter"] for p in json.loads(result.output)["layout"]]
    assert "tabs.<tab>.grid.areas" in params and "tabs.<tab>.tiles.<tile>" in params


@pytest.mark.slow
@pytest.mark.parametrize(
    ("folder", "layout"),
    [("paper", "cell_performance.layout.yaml"), ("dashboard", "lab_throughput.layout.yaml")],
)
def test_the_example_layouts_render(folder, layout, tmp_path, monkeypatch):
    """examples/layouts: each a folder project with its format in a folder pack."""
    source = Path(__file__).parents[1] / "examples" / "layouts" / folder
    work = tmp_path / folder
    shutil.copytree(source, work)
    monkeypatch.chdir(work)
    drawn = fg.layout(work / layout)
    assert drawn.tabs and not drawn.issues
