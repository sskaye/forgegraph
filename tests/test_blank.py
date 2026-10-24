"""The escape hatch (architecture D10): a themed canvas, always watermarked and recorded as
non-standard, its theme and format checked against the configs."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pack_helpers import allow

import forgegraph as fg
from forgegraph.render.figure import WATERMARK

THEME, FORMAT = "forgegraph_base/base_theme", "forgegraph_base/base_format"
ACME = Path(__file__).parents[1] / "examples" / "packs" / "acme"


def test_a_canvas_is_drawn_in_its_theme_and_saved_watermarked(tmp_path):
    canvas = fg.blank(THEME, FORMAT, tmp_path)
    with canvas.drawing():
        canvas.axes.plot([1, 2, 3], [2, 1, 3])
        canvas.axes.set_title("Anything")
    [line] = canvas.axes.get_lines()
    assert line.get_color() == "#0072B2"  # okabe_ito's first
    assert line.get_linewidth() == pytest.approx(0.15 * 18)  # series.line.width times base size
    [path] = canvas.save(tmp_path / "c.png")
    assert any(a.get_gid() == WATERMARK for a in canvas.axes.get_children())
    record = fg.load(path)
    assert record is not None and record["nonstandard"] is True and "graphspec" not in record
    assert record["specs"]["theme"]["name"] == THEME


def test_a_canvas_with_provenance_off_records_nothing(tmp_path):
    shutil.copytree(ACME, tmp_path / "acme")
    (tmp_path / "acme" / "formats" / "quiet.yaml").write_text(
        "name: quiet\nversion: 0\ndescription: test\nextends: forgegraph_base/base_format\n"
        "fixed_parameters: None\nvariable_parameters:\n    provenance:\n        level: off\n"
    )
    allow(tmp_path, "forgegraph_base", "./acme")
    canvas = fg.blank(THEME, "acme/quiet", tmp_path)
    [path] = canvas.save(tmp_path / "c.png")
    assert fg.load(path) is None


def test_a_canvas_checks_its_theme_against_the_configs(tmp_path):
    shutil.copytree(ACME, tmp_path / "acme")
    with pytest.raises(fg.SpecError, match="theme: 'acme/acme' is in the pack 'acme'"):
        fg.blank("acme/acme", FORMAT, tmp_path)
    with pytest.raises(fg.SpecError, match="did you mean 'forgegraph_base/base_theme'"):
        fg.blank("forgegraph_base/base_thme", FORMAT, tmp_path)
    allow(tmp_path, "./acme")
    canvas = fg.blank("acme/acme", "acme/slide", tmp_path)
    with canvas.drawing():
        [line] = canvas.axes.plot([1, 2], [1, 2])
    assert line.get_color() == "#CC6677"  # tol_muted, as ForgeGraph orders it
