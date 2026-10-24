"""The catalog: deterministic pages, a current recorded hash, and comments surviving rebuilds."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from pack_helpers import write_pack
from typer.testing import CliRunner

from forgegraph.catalog import build, forgemark
from forgegraph.catalog.files import CatalogError, read
from forgegraph.catalog.page import Card, Instance, Kind, Row, page
from forgegraph.cli import app
from forgegraph.packs import read_pack
from forgegraph.spec.documents import builtin

ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "catalog" / "forgegraph_base.html"
FIXTURE = Path(__file__).parent / "fixtures" / "catalog_comments.html"
# A 1x1 white PNG: the round trip is about text and ids, not pictures.
DOT = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63f8ffff3f0005fe02fea7d6a4d90000000049454e44ae426082"
)
needs_node = pytest.mark.skipif(
    shutil.which("node") is None and not os.environ.get("FORGEGRAPH_REQUIRE_NODE"),
    reason="Forgemark needs Node",
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
    lint = build.write(page_path, small_page())
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
        "catalog/forgegraph_base.html is out of date: run forgegraph catalog build"
    )


def test_the_forgegraph_base_2_catalog_is_current():
    """Rebuild with `uv run forgegraph catalog build --pack packs/forgegraph_base_2`."""
    pack = read_pack(CATALOG.parents[1] / "packs" / "forgegraph_base_2", "folder")
    assert build.current(CATALOG.parent / "forgegraph_base_2.html", pack), (
        "catalog/forgegraph_base_2.html is out of date: "
        "run forgegraph catalog build --pack packs/forgegraph_base_2"
    )


def test_a_packs_table_shows_its_own_values():
    """A row shows the value the shown spec draws with, and whether it fixes it, not the
    definition's: the forgegraph_base_2 theme's, not the base theme's."""
    text = (CATALOG.parent / "forgegraph_base_2.html").read_text(encoding="utf-8")

    def cells(row: str) -> list[str]:
        start = text.index(f'<tr id="{row}">')
        row_text = text[start : text.index("</tr>", start)]
        found = re.findall(r"<td[^>]*>(.*?)</td>", row_text)
        return [re.sub(r"<[^>]+>", "", c) for c in found[1:]]  # after the parameter's name

    theme = "theme-forgegraph_base_2-base_theme-param-"
    assert cells(theme + "title-size")[0] == "1.45"
    assert cells(theme + "series-marker-edge_color")[0] == "#000000"
    assert cells("format-forgegraph_base_2-compact_format-param-output-dpi")[0] == "200"


def test_a_packs_catalog_shows_graph_and_layer_types_in_its_theme():
    text = (CATALOG.parent / "forgegraph_base_2.html").read_text(encoding="utf-8")
    panels = set(re.findall(r'<section class="panel" id="([^"]+)"', text))
    assert {"graphtype-xy", "layer-error_bar", "layer-note", "layer-reference_line"} <= panels
    assert '<p id="version" class="version">version 0.3.0</p>' in text


def test_a_page_with_comments_is_not_rebuilt_without_forgemark(tmp_path, monkeypatch):
    page_path = tmp_path / "catalog.html"
    shutil.copy(FIXTURE, page_path)
    old = page_path.read_text(encoding="utf-8")
    monkeypatch.setattr(forgemark.shutil, "which", lambda name: None)
    with pytest.raises(forgemark.ForgemarkError, match="Node 18"):
        build.write(page_path, small_page())
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


# --- catalog files ---------------------------------------------------------------------

HEADER = (
    "name: {name}\nversion: 0\ndescription: Test.\nextends: {extends}\n"
    "baseline: forgegraph_base/polarization\n"
)


def _project(tmp_path, catalog: str, kind_folder: str = "formats", name: str = "plain"):
    """A pack, house, with a format (or theme) extending the base one, and its catalog."""
    folder = write_pack(tmp_path)
    kind = "format" if kind_folder == "formats" else "theme"
    (folder / kind_folder).mkdir()
    (folder / kind_folder / f"{name}.yaml").write_text(
        f"name: {name}\nversion: 0\ndescription: Test.\nextends: forgegraph_base/base_{kind}\n"
        "fixed_parameters: None\nvariable_parameters: None\n"
    )
    (folder / "catalogs" / kind_folder).mkdir(parents=True)
    (folder / "catalogs" / kind_folder / f"{name}.yaml").write_text(catalog)
    reg = builtin().add_pack(read_pack(folder, "folder"))
    reg.allowed = frozenset({"forgegraph_base", "house"})
    return reg


def _problems(tmp_path, catalog: str, **kw) -> list[str]:
    reg = _project(tmp_path, catalog, **kw)
    with pytest.raises(CatalogError) as e:
        read(
            "format" if kw.get("kind_folder", "formats") == "formats" else "theme",
            f"house/{kw.get('name', 'plain')}",
            reg,
        )
    return e.value.problems


def test_a_catalog_extending_another_lists_only_what_differs(tmp_path):
    catalog = HEADER.format(name="plain", extends="forgegraph_base/base_format") + (
        "baselines: None\nvariations:\n    figure:\n        width: 90\n"
    )
    reg = _project(tmp_path, catalog)
    widths = {v.change.value for p, v in read("format", "house/plain", reg).variations if v}
    assert 90 in widths and 100 not in widths


def test_every_file_needs_a_catalog(tmp_path):
    reg = _project(tmp_path, "")
    (tmp_path / "house" / "catalogs" / "formats" / "plain.yaml").unlink()
    with pytest.raises(CatalogError, match="missing; every format needs a catalog"):
        read("format", "house/plain", reg)


def test_catalog_rules_are_errors(tmp_path):
    catalog = HEADER.format(name="plain", extends="None") + (
        "baselines:\n"
        "    two: [90, 80]\n"
        "variations:\n"
        "    figure:\n"
        "        width: -5\n"
        "        height: {value: auto, from: nowhere}\n"
        "        depth: 3\n"
    )
    problems = _problems(tmp_path, catalog)
    assert any("baselines.two: must be parameters and their values" in p for p in problems)
    assert any("variations: missing figure.base_size" in p for p in problems)
    assert any("variations.figure.depth: unknown parameter" in p for p in problems)
    assert any("variations.figure.width: must be" in p for p in problems)
    assert any("from: no numbered baseline 'nowhere'" in p for p in problems)


def test_a_card_drawing_the_same_as_its_baseline_is_an_error(tmp_path):
    from forgegraph.catalog.build import instance

    catalog = HEADER.format(name="plain", extends="forgegraph_base/base_theme") + (
        "baselines: None\nvariations:\n    grid:\n        show: false\n"  # the baseline's
    )
    reg = _project(tmp_path, catalog, kind_folder="themes")
    with pytest.raises(CatalogError, match=r"Baseline \+ grid.show = false draws the same"):
        instance("theme", "house/plain", "Theme > plain", reg)


def test_builtin_catalogs_follow_the_rules():
    for kind, names in (("theme", builtin().docs["theme"]), ("format", builtin().docs["format"])):
        for name in names:
            read(kind, name, builtin())
    read("graph_type", "xy", builtin())
    for name in builtin().docs["layer"]:
        read("layer", name, builtin())


def test_a_numbered_baseline_can_change_several_parameters():
    catalog = read("graph_type", "xy", builtin())
    offset = next(v for p, v in catalog.variations if p.path == "series.offset")
    assert offset is not None and offset.base is not None
    parts = {c.path: c.value for c in offset.base.parts}
    assert parts["encoding.color"] == "Run" and parts["mark.bar.show"] is True


def test_a_layer_catalog_draws_its_layer_on_every_card():
    catalog = read("layer", "note", builtin())
    always = {c.path: c.value for c in catalog.always}
    assert always["layers.note.type"] == "note"
    assert always["layers.note.position"] == "bottom_left"
    paths = [v.change.path for _, v in catalog.variations if v]
    assert paths == ["layers.note.text", "layers.note.position", "layers.note.inside"]


def test_a_layer_catalogs_settings_are_on_every_card():
    always = {c.path: c.value for c in read("layer", "error_bar", builtin()).always}
    assert always["axis.y.data.aggregation"] == "mean"
    assert always["layers.error_bar.type"] == "error_bar"


def test_commented_categories_are_open():
    from forgegraph.catalog.page import open_commented

    page_ = (
        '<details class="category" id="a"><summary>a</summary>'
        '<details class="category" id="a-b"><summary>a.b</summary><!-- fmc:1 -->x<!-- /fmc:1 -->'
        '</details></details><details class="category" id="c"></details>'
    )
    opened = open_commented(page_)
    assert opened.count(" open") == 2 and 'category" open id="c"' not in opened
    assert open_commented(opened) == opened
