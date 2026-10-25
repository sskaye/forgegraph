"""Catalog files: the rules a catalog file follows, and what reading one gives."""

from __future__ import annotations

import pytest
from pack_helpers import write_pack

from forgegraph.catalog_build.files import CatalogError, read
from forgegraph.packs import read_pack
from forgegraph.spec.documents import builtin

HEADER = (
    "name: {name}\nversion: 0\ndescription: Test.\nextends: {extends}\n"
    "baseline: forgegraph_base/polarization\n"
)


def catalog_project(tmp_path, catalog: str, kind_folder: str = "formats", name: str = "plain"):
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
    reg = catalog_project(tmp_path, catalog, **kw)
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
    reg = catalog_project(tmp_path, catalog)
    widths = {v.change.value for p, v in read("format", "house/plain", reg).variations if v}
    assert 90 in widths and 100 not in widths


def test_every_file_needs_a_catalog(tmp_path):
    reg = catalog_project(tmp_path, "")
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
