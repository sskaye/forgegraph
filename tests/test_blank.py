"""The escape hatch (architecture D10): a themed canvas, always watermarked and recorded as
non-standard, its theme and format checked against the configs."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pack_helpers import allow

import forgegraph as fg
from forgegraph.drawing.figure import WATERMARK

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


def test_a_canvas_is_always_non_standard(tmp_path):
    canvas = fg.blank(THEME, FORMAT, tmp_path)
    assert canvas.inspect() is True and canvas.changed


def test_a_canvas_saved_without_a_file_type_saves_its_formats_image_types(tmp_path):
    canvas = fg.blank(THEME, FORMAT, tmp_path)
    with canvas.drawing():
        canvas.axes.plot([1, 2], [1, 2])
    listed = canvas.values["format"]["output.file_types"]
    saved = canvas.save(tmp_path / "c")
    assert [p.suffix.lstrip(".") for p in saved] == [k for k in listed if k != "html"]
    assert all(p.is_file() for p in saved)


def test_a_canvas_too_big_for_its_format_is_an_error(tmp_path):
    canvas = fg.blank(THEME, FORMAT, tmp_path)
    with canvas.drawing():
        canvas.axes.set_ylabel("\n".join(["a very tall axis title"] * 40))
    with pytest.raises(fg.SpecError):
        canvas.save(tmp_path / "c.png")


def test_a_notebook_shows_a_canvas_as_a_png(tmp_path):
    canvas = fg.blank(THEME, FORMAT, tmp_path)
    assert canvas._repr_png_().startswith(b"\x89PNG")


def test_a_canvas_saves_as_a_graph_does(tmp_path, monkeypatch):
    """With no path, under its own name, every image type its format lists."""
    canvas = fg.blank(THEME, FORMAT, tmp_path)
    monkeypatch.chdir(tmp_path)
    saved = canvas.save()
    listed = [k for k in canvas.values["format"]["output.file_types"] if k != "html"]
    assert [p.name for p in saved] == [f"canvas.{k}" for k in listed]


def test_a_canvas_takes_a_registry_as_render_does(tmp_path):
    """Like fg.render and fg.xy, fg.blank can be given the registry to check against."""
    from forgegraph.spec.registry import registry_for

    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "./acme")
    canvas = fg.blank("acme/acme", "acme/slide", registry=registry_for(tmp_path))
    assert canvas.specs["theme"]["name"] == "acme/acme"
