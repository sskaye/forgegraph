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
