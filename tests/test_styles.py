"""Text, line and series styles: a theme category marked [text style], [line style] or [series
style] has the parameters of text, line or series, and takes their values unless it, or a
file nearer in the extends chain, sets its own; a GraphSpec's settings carry through too."""

from __future__ import annotations

import pytest
from pack_helpers import doc

import forgegraph as fg
from forgegraph.spec.explain import explain
from forgegraph.spec.parameters import EXCLUDED, definitions
from forgegraph.spec.registry import Registry, builtin
from forgegraph.spec.resolve import resolve
from forgegraph.spec.tags import var
from forgegraph.spec.validate import validate

BASE = "forgegraph_base/base_theme"


def theme(name: str = "house", **params) -> tuple[dict, Registry]:
    d = doc(BASE, name, untagged={k.replace("__", "."): v for k, v in params.items()})
    reg = builtin().copy()
    reg.add("theme", d)
    return d, reg


def test_a_text_style_has_the_general_texts_parameters():
    defs = definitions("theme")
    for name in ("font", "size", "weight", "color", "gap", "alignment"):
        member, general = defs[f"title.{name}"], defs[f"text.{name}"]
        assert member.inherits == f"text.{name}"
        assert (member.range, member.description) == (general.range, general.description)
    assert defs["title.size"].default == 1.05  # the base theme sets its own
    assert defs["title.font"].default == "Roboto"  # the general text's
    assert defs["axis.tick.label.max_wrap"].inherits is None  # its own parameter


def test_a_line_style_has_the_general_lines_parameters_less_those_it_cant_use():
    defs = definitions("theme")
    assert defs["grid.style"].inherits == "line.style"
    assert defs["axis.tick.width"].default == 0.07
    assert "axis.tick.join" not in defs  # a tick mark has no corners
    assert EXCLUDED["axis.tick"]
    d, reg = theme(axis__tick__join="bevel")
    [problem] = validate("theme", d, reg)
    assert problem.startswith("axis.tick.join: unknown parameter")


def test_a_style_can_widen_or_narrow_a_members_range():
    defs = definitions("theme")
    assert "line" in defs["layer.reference_line.label.color"].range.literals
    assert defs["series.marker.edge.style"].range.literals == ("None", "solid")


def test_a_series_style_has_every_series_parameter():
    defs = definitions("theme")
    assert defs["series.benchmark.line.width"].inherits == "series.line.width"
    assert defs["series.benchmark.value_label.size"].inherits == "series.value_label.size"
    assert defs["series.benchmark.colors"].default == ["#808080"]
    assert "series.benchmark.benchmark.colors" not in defs


def test_a_member_takes_the_general_value_from_the_nearest_file_that_sets_it():
    d, reg = theme(text__font="DejaVu Sans", axis__title__font="Source Sans 3")
    r = resolve("theme", d, reg)
    assert r.value("title.font") == "DejaVu Sans"  # follows the new general font
    assert r.value("axis.tick.label.font") == "DejaVu Sans"
    assert r.value("axis.title.font") == "Source Sans 3"  # its own, set here
    assert r.value("title.size") == 1.05  # the base theme's own, not the general's
    assert r["title.font"].origin == "theme 'house'"


def test_styles_inside_styles_follow_their_chain():
    d, reg = theme(line__width=0.1, series__line__width=0.2)
    r = resolve("theme", d, reg)
    assert r.value("grid.width") == 0.05  # the base theme sets the grid's
    assert r.value("plot_area.border.cap") == "projecting"
    assert r.value("series.benchmark.line.width") == 0.2  # from series.line, not line
    assert r.value("layer.error_bar.cap.width") == 0.25


def test_a_members_status_is_its_own():
    r = resolve("theme", builtin().docs["theme"][BASE], builtin())
    assert r.fixed("title.font")
    assert not r.fixed("series.benchmark.marker.size")  # tagged !var with no value
    assert r.value("series.benchmark.marker.size") == 0.5


def test_a_graphspecs_setting_carries_through_to_the_members_that_inherit_it():
    _, reg = theme("open", text__size=var(), series__line__width=var())
    spec = fg.graphspec(
        "g",
        "xy",
        theme="open",
        settings={"text.size": 1.2, "series.line.width": 0.3, "series.marker.size": 0.6},
    )
    assert validate("graphspec", spec, reg) == []
    t = explain(spec, reg).theme
    assert t.value("axis.tick.label.size") == 1.2  # inherits text.size, which the GraphSpec set
    assert t.value("title.size") == 1.05  # set by the base theme itself
    assert t.value("series.benchmark.line.width") == 0.3
    assert t.value("series.benchmark.marker.size") == 0.6


@pytest.mark.parametrize("path", ["title.font", "legend.key.title.font"])
def test_a_text_styles_font_must_be_installed(path):
    d, reg = theme(**{path.replace(".", "__"): "Comic Nonexistent"})
    assert validate("theme", d, reg) == [
        f"{path}: no font 'Comic Nonexistent' is bundled or installed"
    ]


def test_a_text_styles_weight_must_be_one_its_own_font_has():
    d, reg = theme(title__font="DejaVu Sans", title__weight="semibold")
    assert validate("theme", d, reg) == [
        "title.weight: DejaVu Sans has no semibold weight; it has regular, bold"
    ]


# --- what each style's members do -------------------------------------------------------


def _title_box(g):
    g.figure.canvas.draw()
    return g.axes.title.get_window_extent(), g.axes.get_window_extent()


@pytest.mark.parametrize("alignment", ["left", "center", "right"])
def test_the_titles_alignment_places_it_over_the_plot_area(alignment):
    from render_helpers import render

    g = render(theme={"title.alignment": alignment}, title="Polarization")
    title, plot = _title_box(g)
    centre = (plot.x0 + plot.x1) / 2
    if alignment == "left":
        assert abs(title.x0 - plot.x0) < 6
    elif alignment == "right":
        assert abs(title.x1 - plot.x1) < 6
    else:
        assert abs((title.x0 + title.x1) / 2 - centre) < 6


def test_each_text_takes_its_own_color_and_font():
    from matplotlib.colors import to_hex
    from render_helpers import render

    g = render(
        theme={
            "title.color": "#AA0000",
            "axis.title.font": "DejaVu Sans",
            "axis.title.weight": "bold",
            "axis.tick.label.color": "#00AA00",
            "axis.tick.minor.color": "#0000AA",
            "axis.tick.minor.count": 1,
        },
        title="Polarization",
    )
    g.figure.canvas.draw()
    assert to_hex(g.axes.title.get_color()) == "#aa0000"
    assert g.axes.xaxis.label.get_fontproperties().get_family() == ["DejaVu Sans"]
    assert to_hex(g.axes.xaxis.get_ticklabels()[0].get_color()) == "#00aa00"
    minor = g.axes.xaxis.get_minor_ticks()[0]
    assert to_hex(minor.tick1line.get_color()) == "#0000aa"
    assert to_hex(g.axes.xaxis.get_major_ticks()[0].tick1line.get_color()) == "#000000"


@pytest.mark.parametrize(("alignment", "location"), [("left", "left"), ("right", "right")])
def test_an_axis_titles_alignment_places_it_along_its_axis(alignment, location):
    from render_helpers import render

    g = render(theme={"axis.title.alignment": alignment})
    g.figure.canvas.draw()
    x = g.axes.xaxis.label.get_window_extent()
    plot = g.axes.get_window_extent()
    edge = plot.x0 if location == "left" else plot.x1
    assert abs((x.x0 if location == "left" else x.x1) - edge) < 6


def test_the_plot_areas_border_takes_its_line_style():
    from render_helpers import render

    g = render(theme={"plot_area.border.style": "dashed"})
    assert g.axes.spines["left"].get_linestyle() == "--"
    g = render(theme={"plot_area.border.style": None})
    assert not any(s.get_visible() for s in g.axes.spines.values())


@pytest.mark.parametrize("alignment", ["left", "center", "right"])
def test_the_footnotes_alignment_places_it_across_the_figure(alignment):
    from render_helpers import render

    from forgegraph.drawing.layout import add_footnote, place_footnote

    g = render(theme={"footnote.alignment": alignment})
    note = add_footnote(g.figure, "Data as of today", g.style)
    place_footnote(g.figure, 0.1, 0.1)
    g.figure.canvas.draw()
    box = note.get_window_extent()
    width = g.figure.bbox.width
    if alignment == "left":
        assert box.x0 < width * 0.1
    elif alignment == "right":
        assert box.x1 > width * 0.9
    else:
        assert abs((box.x0 + box.x1) / 2 - width / 2) < width * 0.02
