"""The catalog's record of its inputs: any package change that can alter a card marks the
catalog out of date; changes that can't alter one leave it current."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import forgegraph
from forgegraph.catalog import build
from forgegraph.packs import BASE

PACKAGE = Path(forgegraph.__file__).parent


@pytest.fixture
def package(tmp_path, monkeypatch):
    """A copy of the package, which inputs_hash reads in place of the installed one."""
    copy = tmp_path / "forgegraph"
    shutil.copytree(PACKAGE, copy, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(build, "files", lambda _: copy)
    return copy


def _edit(path: Path) -> None:
    path.write_bytes(path.read_bytes() + b"\n# changed\n")


@pytest.mark.parametrize(
    "name",
    [
        "drawing/xy.py",
        "drawing/marks.py",
        "graph.py",
        "spec/documents.py",
        "graph_types/xy.yaml",
        "layers/error_bar.yaml",
        f"packs/{BASE}/themes/base_theme.yaml",
        "catalog/page.py",
        "fonts/__init__.py",
    ],
)
def test_a_change_to_a_file_the_catalog_draws_with_marks_it_out_of_date(package, name):
    before = build.inputs_hash()
    _edit(package / name)
    assert build.inputs_hash() != before


def test_a_new_module_marks_it_out_of_date(package):
    before = build.inputs_hash()
    (package / "drawing" / "new.py").write_text("X = 1\n")
    assert build.inputs_hash() != before


@pytest.mark.parametrize(
    "name", ["cli/__init__.py", "jobs/run.py", "skill/__init__.py", "layouts/__init__.py"]
)
def test_a_change_the_catalog_cant_depend_on_leaves_it_current(package, name):
    before = build.inputs_hash()
    _edit(package / name)
    assert build.inputs_hash() == before


def test_another_built_in_packs_files_leave_the_base_catalog_current(package):
    before = build.inputs_hash()
    _edit(package / "packs" / "forgegraph_base_2" / "themes" / "base_theme.yaml")
    assert build.inputs_hash() == before


def test_a_packs_catalog_follows_its_own_files(package):
    from forgegraph.packs import read_pack

    pack = read_pack(package / "packs" / "forgegraph_base_2", "built in")
    before = build.inputs_hash(pack)
    _edit(pack.folder / "themes" / "base_theme.yaml")
    assert build.inputs_hash(pack) != before


@pytest.mark.parametrize(
    "name", ["drawing/xy.py", "packs/config.toml", "skill/forgegraph/SKILL.md"]
)
def test_line_endings_dont_count(package, name):
    """Whatever kind of text file: a Windows checkout writes CRLF line endings."""
    before = build.inputs_hash()
    target = package / name
    lf = target.read_bytes().replace(b"\r\n", b"\n")  # however it was checked out
    target.write_bytes(lf.replace(b"\n", b"\r\n"))
    assert build.inputs_hash() == before
    target.write_bytes(lf)
    assert build.inputs_hash() == before


@pytest.mark.parametrize("name", [".DS_Store", "drawing/.DS_Store", "packs/.hidden"])
def test_hidden_files_dont_count(package, name):
    """A file a desktop or editor leaves, which a clean checkout doesn't have."""
    before = build.inputs_hash()
    (package / name).write_bytes(b"\0\1")
    assert build.inputs_hash() == before


@pytest.mark.parametrize(
    "settings",
    [{}, {"legend.method": "key", "legend.key.inside": False}],
    ids=["plain", "key outside"],
)
@pytest.mark.parametrize("dpi", [72 * 1.5, 100.0, 93.7])
def test_a_cards_pixels_are_its_pngs(settings, dpi):
    """A card is quantized from the graph's pixels, taken as they're drawn: the same
    pixels its PNG would hold."""
    import io

    from PIL import Image
    from render_helpers import render

    from forgegraph.catalog.examples import image, png

    g = render(settings=settings, format={"figure.width": 83.3})
    decoded = Image.open(io.BytesIO(png(g, dpi))).convert("RGBA")
    taken = image(g, dpi)
    assert taken.size == decoded.size and taken.tobytes() == decoded.tobytes()
