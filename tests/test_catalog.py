"""The catalog: deterministic pages, a current recorded hash, and comments surviving rebuilds."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from pack_helpers import cli_problems, needs_node, write_pack
from typer.testing import CliRunner

from forgegraph import forgemark
from forgegraph.catalog_build import build
from forgegraph.catalog_build.page import Card, Instance, Kind, Row, open_commented, page
from forgegraph.cli import app

pytestmark = pytest.mark.slow  # the full suite only (pytest --full)

ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "catalog" / "forgegraph_default.html"
FIXTURE = Path(__file__).parent / "fixtures" / "catalog_comments.html"
# A 1x1 white PNG: the round trip is about text and ids, not pictures.
DOT = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63f8ffff3f0005fe02fea7d6a4d90000000049454e44ae426082"
)


def small_page() -> str:
    """A fixed catalog page, the same in every build: what the round-trip comments sit on."""
    rows = (
        Row("mark.line.show", "true", "true | false", "variable", "Draw lines."),
        Row("mark.line.connect_order", "x", "x | data", "variable", "Point order along each line."),
        Row("mark.marker.show", "true", "true | false", "variable", "Draw markers."),
    )
    cards = (
        Card("graphtype-t-baseline", "Baseline", DOT, 100),
        Card("graphtype-t-card-lines-show", "Baseline + mark.line.show = false", DOT, 100),
    )
    inst = Instance("graphtype-t", "t", "GraphType > t", rows, cards)
    return page([Kind("graphtype", "GraphTypes", (inst,))], "0" * 64, "Round-trip Catalog")


def comments(path: Path) -> list[dict]:
    out = forgemark.run("list", str(path), "--json").stdout
    data = json.loads(out)
    return data if isinstance(data, list) else data["comments"]


@needs_node
def test_comments_survive_a_rebuild(tmp_path):
    page_path = tmp_path / "catalog.html"
    shutil.copy(FIXTURE, page_path)
    before = comments(page_path)
    assert len(before) >= 5
    lint = forgemark.rewrite(page_path, small_page(), reopen=open_commented)
    after = comments(page_path)
    orphans = [c for c in after if c.get("status") == "orphaned" or c.get("orphaned")]
    assert orphans == [], lint
    assert len(after) == len(before)


def test_building_twice_gives_the_same_page(monkeypatch):
    monkeypatch.setattr(build, "KINDS", (("format", "Formats", "Format"),))
    assert build.html() == build.html()


def test_the_catalog_is_current():
    """Rebuild with `uv run forgegraph catalog build` after changing definitions or drawing."""
    assert build.current(CATALOG), (
        "catalog/forgegraph_default.html is out of date: run forgegraph catalog build"
    )


def test_a_page_with_comments_is_not_rebuilt_without_forgemark(tmp_path, monkeypatch):
    page_path = tmp_path / "catalog.html"
    shutil.copy(FIXTURE, page_path)
    old = page_path.read_text(encoding="utf-8")
    monkeypatch.setattr(forgemark.shutil, "which", lambda name: None)
    with pytest.raises(forgemark.ForgemarkError, match="Node 18"):
        forgemark.rewrite(page_path, small_page(), reopen=open_commented)
    assert page_path.read_text(encoding="utf-8") == old


def test_cli_check(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["catalog", "check", str(CATALOG), "--json"])
    assert result.exit_code == 0, result.output
    stale = tmp_path / "old.html"
    stale.write_text(small_page(), encoding="utf-8")
    result = runner.invoke(app, ["catalog", "check", str(stale), "--json"])
    assert result.exit_code == 1
    assert "out of date" in json.loads(result.output)["problems"][0]


def test_cli_build(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "html", lambda root=None: small_page())
    out = tmp_path / "c" / "catalog.html"
    result = CliRunner().invoke(app, ["catalog", "build", "--out", str(out), "--json"])
    assert result.exit_code == 0, result.output
    assert out.read_text(encoding="utf-8") == small_page()


def test_cli_build_reports_what_stops_a_build(tmp_path, monkeypatch):
    def problems(*args):
        return cli_problems("catalog", "build", *args)

    (tmp_path / "empty").mkdir()
    [problem] = problems("--pack", str(tmp_path / "empty"))
    assert "pack.yaml" in problem
    folder = write_pack(tmp_path)  # a theme without its catalog file
    (folder / "themes").mkdir()
    (folder / "themes" / "plain.yaml").write_text(
        "name: plain\nversion: 0\ndescription: Test.\nextends: forgegraph_default/light_theme\n"
        "parameters: None\n"
    )
    [problem] = problems("--pack", str(folder), "--out", str(tmp_path / "house.html"))
    assert "plain" in problem and "catalog" in problem
    page_path = tmp_path / "commented.html"  # comments to keep, and no Node to keep them
    shutil.copy(FIXTURE, page_path)
    monkeypatch.setattr(build, "html", lambda root=None: small_page())
    monkeypatch.setattr(forgemark.shutil, "which", lambda name: None)
    [problem] = problems("--out", str(page_path))
    assert "Node 18" in problem


def make_fixture() -> None:
    """Write the fixture page and comment on it: prose, table cells, a heading and a figure."""
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_text(small_page(), encoding="utf-8")
    env = {**os.environ, "FORGEMARK_AUTHOR": "Fixture"}
    for args in (
        ["--anchor", "GraphType > t", "--body", "On a heading."],
        ["--anchor", "Point order along each line.", "--body", "On a description cell."],
        ["--anchor", "x | data", "--body", "On an allowed-values cell."],
        ["--anchor", "Parameters", "--body", "On a subheading."],
        ["--anchor", "Baseline + mark.line.show = false", "--body", "On a card heading."],
        ["--selector", "#graphtype-t-card-lines-show-figure", "--body", "On a figure."],
    ):
        cmd = ["node", str(forgemark.tool()), "comment", str(FIXTURE), *args]
        subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)


if __name__ == "__main__":  # uv run python tests/test_catalog.py: remake the fixture
    make_fixture()
