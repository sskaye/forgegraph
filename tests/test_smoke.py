import io
from importlib.metadata import version
from pathlib import Path

import matplotlib
import matplotlib.image
import numpy as np
from matplotlib import font_manager
from matplotlib.figure import Figure
from typer.testing import CliRunner

import forgegraph
from forgegraph.cli import app
from forgegraph.fonts import FONT_FAMILY, font_dir, register_fonts


def test_version_matches_package_metadata():
    assert forgegraph.__version__ == version("forgegraph")


def test_cli_reports_version():
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert forgegraph.__version__ in result.output


def test_bundled_fonts_are_registered():
    paths = register_fonts()
    weights = ["Light", "Regular", "Medium", "Semibold", "Bold", "It"]
    assert {p.name for p in paths} >= {f"SourceSans3-{w}.ttf" for w in weights}
    found = font_manager.findfont(
        font_manager.FontProperties(family=FONT_FAMILY), fallback_to_default=False
    )
    assert font_dir() in Path(found).parents


class _Counted(list):
    """matplotlib's list of fonts, counting how often it is read through."""

    reads = 0

    def __iter__(self):
        type(self).reads += 1
        return super().__iter__()


def test_registering_again_doesnt_read_through_every_font(monkeypatch):
    register_fonts()
    manager = font_manager.fontManager
    monkeypatch.setattr(manager, "ttflist", _Counted(manager.ttflist))
    _Counted.reads = 0
    for _ in range(5):
        register_fonts()
    assert _Counted.reads == 0


def test_fonts_taken_away_from_matplotlib_are_registered_again(monkeypatch):
    register_fonts()
    manager = font_manager.fontManager
    bundled = {str(p) for p in register_fonts()}
    monkeypatch.setattr(manager, "ttflist", [f for f in manager.ttflist if f.fname not in bundled])
    register_fonts()
    assert bundled <= {f.fname for f in manager.ttflist}


def _render_text_png() -> np.ndarray:
    register_fonts()
    with matplotlib.rc_context(matplotlib.rcParamsDefault):
        matplotlib.rcParams["font.family"] = FONT_FAMILY
        fig = Figure(figsize=(3, 1), dpi=100)
        fig.text(0.05, 0.4, "Cell Voltage (V) 0123456789", fontsize=14)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", metadata={"Software": None})
    buf.seek(0)
    return matplotlib.image.imread(buf)


def test_text_rendering_is_pixel_identical_across_runs():
    first, second = _render_text_png(), _render_text_png()
    assert (first < 0.5).any(), "expected visible text"
    assert np.array_equal(first, second)
