"""Text, line and series styles: a theme category marked [text style], [line style] or [series
style] has the parameters of text, line or series, and takes their values unless it, or a
file nearer in the extends chain, sets its own; a GraphSpec's settings carry through too."""

from __future__ import annotations

import pytest
from pack_helpers import doc

import forgegraph as fg
from forgegraph.spec.explain import explain
from forgegraph.spec.parameters import EXCLUDED, definition_file, definitions
from forgegraph.spec.registry import Registry, builtin, load_yaml
from forgegraph.spec.resolve import resolve
from forgegraph.spec.series import theme_for
from forgegraph.spec.tags import fix, untag, var
from forgegraph.spec.validate import validate


def plain() -> dict:
    """The theme specification as a theme to extend, every parameter fixed: it sets no style's
    members, so each takes its general parameter's value."""
    spec = load_yaml(definition_file("theme"))
    return {**spec, "name": "plain", "parameters": fix(untag(spec["parameters"]))}


def theme(name: str = "house", **params) -> tuple[dict, Registry]:
    d = doc("plain", name, untagged={k.replace("__", "."): v for k, v in params.items()})
    reg = builtin().copy()
    reg.add("theme", plain())
    reg.add("theme", d)
    return d, reg


def test_a_text_style_has_the_general_texts_parameters():
    defs = definitions("theme")
    for name in ("font", "size", "weight", "color", "gap", "alignment"):
        member, general = defs[f"title.{name}"], defs[f"text.{name}"]
        assert member.inherits == f"text.{name}"
        assert (member.range, member.description) == (general.range, general.description)
    assert defs["title.size"].default == defs["text.size"].default  # the general text's
    assert defs["title.font"].default == "Roboto"
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
    assert "line" in defs["layer.reference.label.color"].range.literals
    assert defs["series.marker.edge.style"].range.literals == ("None", "solid")


def test_a_series_style_has_every_series_parameter():
    defs = definitions("theme")
    assert defs["series.benchmark.line.width"].inherits == "series.line.width"
    assert defs["series.benchmark.value_label.size"].inherits == "series.value_label.size"
    assert defs["series.benchmark.colors"].default == defs["series.colors"].default
    assert "series.benchmark.benchmark.colors" not in defs


def test_a_member_takes_the_general_value_from_the_nearest_file_that_sets_it():
    _d, reg = theme("base", title__size=1.05)
    child = doc("base", "child", untagged={"text.font": "DejaVu Sans", "text.size": 1.2})
    child["parameters"]["axis"] = {"title": {"font": "Source Sans 3"}}
    reg.add("theme", child)
    r = resolve("theme", child, reg)
    assert r.value("title.font") == "DejaVu Sans"  # follows the new general font
    assert r.value("axis.tick.label.font") == "DejaVu Sans"
    assert r.value("axis.title.font") == "Source Sans 3"  # its own, set here
    assert r.value("title.size") == 1.05  # its own, from the theme it extends
    assert r.value("axis.title.size") == 1.2  # the new general size
    assert r["title.font"].origin == "theme 'child'"


def test_styles_inside_styles_follow_their_chain():
    d, reg = theme(line__width=0.1, series__line__width=0.2)
    r = resolve("theme", d, reg)
    assert r.value("grid.width") == 0.1  # the new general line's
    assert r.value("plot_area.border.cap") == "projecting"
    assert r.value("series.benchmark.line.width") == 0.2  # from series.line, not line
    assert r.value("layer.error_bar.cap.width") == 0.25


def test_a_members_status_is_its_own():
    d, reg = theme(series__benchmark__marker__size=var())
    r = resolve("theme", d, reg)
    assert r.fixed("title.font")
    assert not r.fixed("series.benchmark.marker.size")  # tagged !var with no value
    assert r.value("series.benchmark.marker.size") == 0.5
    assert r.fixed("series.marker.edge.width")  # its general's tag is the general's own


def test_a_graphspecs_setting_carries_through_to_the_members_that_inherit_it():
    _, reg = theme(
        "open",
        text__size=var(),
        series__line__width=var(),
        series__marker__size=var(),
        title__size=1.05,
    )
    look = {"line": {"width": 0.3}, "marker": {"size": 0.6}}
    spec = fg.graphspec("g", "xy", theme="open", settings={"text.size": 1.2, "series": {"y": look}})
    assert validate("graphspec", spec, reg) == []
    explained = explain(spec, reg)
    t = explained.theme
    assert t.value("axis.tick.label.size") == 1.2  # inherits text.size, which the GraphSpec set
    assert t.value("title.size") == 1.05  # set by the theme itself
    drawn = theme_for(t, explained.series.value("y")["look"])  # as its series draws it
    assert drawn["series.benchmark.line.width"] == 0.3
    assert drawn["series.benchmark.marker.size"] == 0.6
    assert t.value("series.benchmark.line.width") != 0.3  # the theme's own is unchanged


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
            "title.font": "IBM Plex Serif",
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
    assert g.axes.title.get_fontproperties().get_family() == ["IBM Plex Serif"]
    assert g.axes.xaxis.label.get_fontproperties().get_family() == ["DejaVu Sans"]
    assert to_hex(g.axes.xaxis.get_ticklabels()[0].get_color()) == "#00aa00"
    minor = g.axes.xaxis.get_minor_ticks()[0]
    assert to_hex(minor.tick1line.get_color()) == "#0000aa"
    assert to_hex(g.axes.xaxis.get_major_ticks()[0].tick1line.get_color()) == "#000000"


def test_each_axis_tick_labels_take_their_own_style_and_axis_tick_labels_otherwise():
    """axis.x.tick.label and axis.y.tick.label set each axis's tick labels; what they don't set
    is axis.tick.label's, including its font and weight, which are drawn."""
    from matplotlib.colors import to_hex
    from render_helpers import render

    g = render(
        theme={
            "axis.tick.label.font": "Source Sans 3",
            "axis.tick.label.weight": "bold",
            "axis.x.tick.label.size": 0.5,
            "axis.y.tick.label.color": "#00AA00",
        }
    )
    g.figure.canvas.draw()
    x = next(t for t in g.axes.xaxis.get_ticklabels() if t.get_text())
    y = next(t for t in g.axes.yaxis.get_ticklabels() if t.get_text())
    assert x.get_fontsize() == pytest.approx(g.style.pt("axis.x.tick.label.size"))
    assert y.get_fontsize() == pytest.approx(g.style.pt("axis.tick.label.size"))
    assert float(x.get_fontsize()) < float(y.get_fontsize())
    assert to_hex(y.get_color()) == "#00aa00" and to_hex(x.get_color()) == "#000000"
    for label in (x, y):
        assert label.get_fontproperties().get_family() == ["Source Sans 3"]
        assert label.get_fontweight() in ("bold", 700)


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


def test_a_title_beside_a_color_bar_below_the_plot_is_an_error():
    d, reg = theme(legend__color_bar__position="below", legend__color_bar__title__position="beside")
    assert validate("theme", d, reg) == [
        "legend.color_bar.title.position: beside, but the bar is below the plot "
        "(legend.color_bar.position); a title beside a horizontal bar isn't drawn"
    ]
