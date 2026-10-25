"""Text measured to its letters (forgegraph.drawing.text), and the layout built on it.

The layout checks measure the drawn pixels, not the module's own arithmetic.
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image
from render_helpers import render

from forgegraph.drawing import text
from forgegraph.drawing.key import keys
from forgegraph.drawing.layout import MARGIN_IN
from forgegraph.drawing.style import isolated

DPI = 600
PT = DPI / 72  # pixels per point


def _font(size: float = 12.0):
    return text.font("Source Sans 3", size)


def test_edges_run_from_capital_height_to_baseline_and_grow_for_what_reaches_further():
    prop = _font()
    digits, cap = text.edges("1.0", prop), text.edges("H", prop)
    assert digits.bottom == pytest.approx(0, abs=0.3) and digits.top >= cap.top - 1e-9
    assert text.edges("gap", prop).bottom > 2  # a descender
    assert text.edges("cm$^{2}$", prop).top > cap.top  # a superscript
    assert text.row(["1.0", "gap"], prop).bottom == text.edges("gap", prop).bottom


def test_matplotlibs_box_is_bigger_than_the_letters():
    prop = _font()
    e, b = text.edges("1.0", prop), text.box("1.0", prop)
    assert b.top > e.top + 2 and b.bottom > e.bottom + 2


def _pixels(g, hide_ticks: bool = False) -> np.ndarray:
    if hide_ticks:
        for axis in (g.axes.xaxis, g.axes.yaxis):
            for t in axis.get_major_ticks():
                t.tick1line.set_visible(False)
                t.tick2line.set_visible(False)
        for spine in g.axes.spines.values():
            spine.set_visible(False)
    buffer = io.BytesIO()
    with isolated(g.style):
        g.figure.savefig(buffer, format="png", dpi=DPI)
    return np.asarray(Image.open(io.BytesIO(buffer.getvalue())).convert("L")) < 200


def test_what_is_drawn_sits_the_margin_from_every_edge():
    g = render(format={"figure.height": "auto"})
    ink = _pixels(g)
    rows, cols = np.where(ink.any(axis=1))[0], np.where(ink.any(axis=0))[0]
    margin = MARGIN_IN * DPI
    h, w = ink.shape
    for gap in (rows[0], h - 1 - rows[-1], cols[0], w - 1 - cols[-1]):
        assert gap == pytest.approx(margin, abs=0.6 * PT)


def test_x_and_y_tick_labels_sit_the_same_gap_from_their_ticks():
    g = render()
    renderer = g.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    scale = DPI / g.figure.dpi
    tick = g.style.pt("axis.tick.length") * PT
    ink = _pixels(g, hide_ticks=True)
    h = ink.shape[0]
    box = g.axes.bbox
    gaps = []
    lo, hi = sorted(g.axes.get_xlim())
    x_label = next(
        t.label1
        for t in g.axes.xaxis.get_major_ticks()
        if t.label1.get_text() and lo < t.get_loc() < hi
    )
    e = x_label.get_window_extent(renderer)
    region = ink[
        int(h - e.y1 * scale) : int(h - e.y0 * scale), int(e.x0 * scale) : int(e.x1 * scale)
    ]
    top = int(h - e.y1 * scale) + np.where(region.any(axis=1))[0][0]
    gaps.append(top - (h - box.y0 * scale + tick))
    y_label = [t for t in g.axes.get_yticklabels() if t.get_text()][2]
    e = y_label.get_window_extent(renderer)
    region = ink[
        int(h - e.y1 * scale) : int(h - e.y0 * scale), int(e.x0 * scale) : int(e.x1 * scale)
    ]
    right = int(e.x0 * scale) + np.where(region.any(axis=0))[0][-1]
    gaps.append(box.x0 * scale - tick - right)
    expected = g.style.pt("axis.tick.label.gap") * PT
    assert gaps[0] == pytest.approx(expected, abs=0.5 * PT)
    assert gaps[1] == pytest.approx(expected, abs=0.5 * PT)


def test_y_tick_labels_are_centred_on_their_ticks():
    g = render()
    renderer = g.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    scale = DPI / g.figure.dpi
    ink = _pixels(g, hide_ticks=True)
    h = ink.shape[0]
    for tick, label in zip(g.axes.yaxis.get_major_ticks(), g.axes.get_yticklabels(), strict=False):
        if not label.get_text():
            continue
        lo, hi = sorted(g.axes.get_ylim())
        if not lo <= tick.get_loc() <= hi:
            continue
        e = label.get_window_extent(renderer)
        y0 = int(h - e.y1 * scale) - 20
        region = ink[y0 : int(h - e.y0 * scale) + 20, int(e.x0 * scale) : int(e.x1 * scale)]
        rows = np.where(region.any(axis=1))[0]
        middle = y0 + (rows[0] + rows[-1]) / 2
        at = h - g.axes.transData.transform((0, tick.get_loc()))[1] * scale
        assert middle == pytest.approx(at, abs=0.3 * PT)


def test_a_framed_key_has_the_same_padding_on_every_side():
    g = render(
        {"legend.method": "key", "legend.key.title.text": "Cells"},
        theme={"legend.key.frame.show": True},
    )
    [key] = keys(g.axes)
    frame = key.bbox()
    scale = DPI / g.figure.dpi
    ink = _pixels(g)
    h = ink.shape[0]
    inset = 3 * PT  # inside the frame line
    x0, x1 = int(frame.x0 * scale + inset), int(frame.x1 * scale - inset)
    y0, y1 = int(h - frame.y1 * scale + inset), int(h - frame.y0 * scale - inset)
    region = ink[y0:y1, x0:x1]
    rows, cols = np.where(region.any(axis=1))[0], np.where(region.any(axis=0))[0]
    line = key.style.pt("legend.key.frame.width") * PT / 2
    pads = [rows[0], (y1 - y0 - 1) - rows[-1], cols[0], (x1 - x0 - 1) - cols[-1]]
    pads = [p + inset - line for p in pads]
    expected = key.style.pt("legend.key.padding") * PT
    for pad in pads:
        assert pad == pytest.approx(expected, abs=0.6 * PT)


def _fresh_layout(string: str, key: tuple, align: str):
    """text._layout's measurement on a figure of its own, as it was first written."""
    import matplotlib
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties

    family, size, weight, style = key
    prop = FontProperties(family=list(family), size=size, weight=weight, style=style)
    fig = Figure(figsize=(2, 2), dpi=72 * text._FINE)
    FigureCanvasAgg(fig)
    with matplotlib.rc_context({"text.hinting": "no_hinting"}):
        artist = fig.text(
            0, 0, string, fontproperties=prop, va="baseline", ha=align, transform=None
        )
        renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
        extent = artist.get_window_extent(renderer)
        _, lines, _ = artist._get_layout(renderer)  # type: ignore[attr-defined]
    fine = text._FINE
    placed = tuple((line, (x - extent.x0) / fine, y / fine) for line, _, (x, y) in lines)
    return extent.y1 / fine, -extent.y0 / fine, extent.width / fine, placed


@pytest.mark.parametrize("align", ["left", "center", "right"])
@pytest.mark.parametrize(
    ("family", "size", "weight"),
    [("Source Sans 3", 12.0, "normal"), ("Roboto", 7.5, 700), ("IBM Plex Serif", 30.0, 300)],
)
def test_a_measurement_is_what_a_figure_of_its_own_gives(family, size, weight, align):
    key = text._key(text.font(family, size, weight))
    for string in ["Hg", "1.0", "", " ", "Wide line\nnarrow", "a\nbb\nccc", "$x^2$ mV", "45° ±1"]:
        text._layout.cache_clear()
        assert text._layout(string, key, align) == _fresh_layout(string, key, align), string


def test_measuring_new_texts_makes_no_figure_each(monkeypatch):
    made = []
    figure = text.Figure

    def counting(*args, **kwargs):
        made.append(1)
        return figure(*args, **kwargs)

    monkeypatch.setattr(text, "Figure", counting)
    text._layout.cache_clear()
    prop = _font(11.0)
    for i in range(5):
        text.box(f"label {i}", prop)
    assert len(made) <= 1


def _probe(string: str, prop, dpi: float) -> tuple[float, float]:
    """A tick label's extent as the axes measured it: a Text of its own on a figure."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.text import Text

    fig = Figure(dpi=dpi)
    FigureCanvasAgg(fig)
    probe = Text(text=string, fontproperties=prop)
    probe.set_figure(fig)
    box = probe.get_window_extent()
    return box.width, box.height


@pytest.mark.parametrize("dpi", [100.0, 300.0, 600.0])
def test_a_labels_extent_is_a_probes(dpi):
    g = render()
    prop = _font(9.5)
    with isolated(g.style):
        for string in [
            "0.25",
            "1,000",
            "\u22123",  # a minus sign, as tick labels write it
            "$10^{3}$",
            "$\\mathregular{10^{-2}}$",
            "Jan\n2026",
            "",
        ]:
            assert text.extent(string, prop, dpi) == _probe(string, prop, dpi), string


def test_measuring_a_label_again_lays_nothing_out(monkeypatch):
    from matplotlib.text import Text

    g = render()
    made = []
    init = Text.__init__
    monkeypatch.setattr(
        Text, "__init__", lambda self, *a, **k: made.append(1) or init(self, *a, **k)
    )
    with isolated(g.style):
        text.extent("12.5", _font(8.25), 123.0)
        made.clear()
        text.extent("12.5", _font(8.25), 123.0)
    assert made == []
