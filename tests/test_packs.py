"""Packs and configs (architecture D4): finding packs, the configs that apply, a project only
narrowing, which specs a file may use, and every misconfiguration's error."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

import pytest
from pack_helpers import allow, write_pack
from render_helpers import BASE, polarization
from ruamel.yaml import YAML

import forgegraph as fg
from forgegraph import packs
from forgegraph.drawing.figure import WATERMARK
from forgegraph.packs import PackError, read_pack
from forgegraph.packs import setup as pack_setup  # pytest would run a module's setup()
from forgegraph.spec import documents
from forgegraph.spec.documents import name_problems, registry_for, validate

ROOT = Path(__file__).parents[1]
ACME = ROOT / "examples" / "packs" / "acme"


def graphspec(folder: Path, theme: str, fmt: str = "forgegraph_base/base_format") -> Path:
    polarization().to_parquet(folder / "p.parquet")
    doc = fg.graphspec("g", "xy", theme=theme, format=fmt, data_file="p.parquet", settings=BASE)
    path = folder / "g.yaml"
    YAML().dump(doc, path.open("w"))
    return path


def user(tmp_path: Path, monkeypatch, *listed: str) -> Path:
    """A main config listing these packs (paths from its folder)."""
    path = tmp_path / "home" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("packs = [" + ", ".join(f"'{p}'" for p in listed) + "]\n")  # literal strings
    monkeypatch.setenv(packs.MAIN_CONFIG_VARIABLE, str(path))
    return path


# --- which packs may be used --------------------------------------------------------------


def test_a_missing_main_config_is_written_listing_the_built_in_packs(tmp_path, monkeypatch, capsys):
    main = tmp_path / "home" / "forgegraph" / "config.toml"
    monkeypatch.setenv(packs.MAIN_CONFIG_VARIABLE, str(main))
    assert set(pack_setup(tmp_path).packs) == {"forgegraph_base", "forgegraph_base_2"}
    assert packs.read_config(main).packs == ("forgegraph_base", "forgegraph_base_2")
    assert f"ForgeGraph wrote its main config, {main}" in capsys.readouterr().err
    shutil.copytree(ACME, tmp_path / "acme")
    with pytest.raises(
        fg.SpecError,
        match=f"'acme/acme' is in the pack 'acme', which {re.escape(str(main))} doesn't allow",
    ):
        fg.render(graphspec(tmp_path, "acme/acme"))


def test_a_config_names_a_built_in_pack_like_a_pip_pack(tmp_path):
    allow(tmp_path, "forgegraph_base_2")
    reg = registry_for(tmp_path)
    assert reg.allowed == {"forgegraph_base_2"}
    assert reg.packs["forgegraph_base_2"].source == "built in"
    assert "forgegraph_base_2/base_theme" in reg.docs["theme"]


def test_a_main_config_that_cant_be_written_is_an_error(tmp_path, monkeypatch):
    (tmp_path / "home").write_text("a file, not a folder")
    main = tmp_path / "home" / "config.toml"
    monkeypatch.setenv(packs.MAIN_CONFIG_VARIABLE, str(main))
    with pytest.raises(PackError) as e:
        pack_setup(tmp_path)
    [problem] = e.value.problems
    assert problem.startswith(f"{main}: can't write the main config")
    assert "set FORGEGRAPH_CONFIG to a file that can be written" in problem


def test_a_folder_config_allows_its_packs(tmp_path):
    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "./acme")
    g = fg.render(graphspec(tmp_path, "acme/acme", "acme/slide"))
    assert g.values["theme"]["font.family"] == "IBM Plex Serif"
    record = g.record()
    assert record is not None and record["specs"]["theme"] == {
        "name": "acme/acme",
        "version": 0,
        "pack_version": "1.2.0",
    }


def test_under_an_acme_only_config_the_base_specs_cant_be_named(tmp_path):
    shutil.copytree(ACME, tmp_path / "acme")
    config = allow(tmp_path, "./acme")
    main = os.environ[packs.MAIN_CONFIG_VARIABLE]
    with pytest.raises(fg.SpecError) as e:
        fg.render(graphspec(tmp_path, "forgegraph_base/base_theme", "acme/slide"))
    assert e.value.problems == [
        "variable_parameters.specifications.theme: 'forgegraph_base/base_theme' is in the pack "
        f"'forgegraph_base', which {main} and {config} doesn't allow"
    ]


def test_a_packs_specs_may_extend_the_base_pack_even_when_only_it_is_allowed(tmp_path):
    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "./acme")  # acme/acme extends forgegraph_base/base_theme
    assert fg.render(graphspec(tmp_path, "acme/acme", "acme/slide")).labelling


def test_graph_types_and_layer_types_are_always_available(tmp_path):
    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "./acme")
    reg = registry_for(tmp_path)
    assert "xy" in reg.docs["graph_type"] and "reference_line" in reg.docs["layer"]


def test_a_folder_config_narrows_the_main_config(tmp_path, monkeypatch):
    shutil.copytree(ACME, tmp_path / "acme")
    user(tmp_path, monkeypatch, "forgegraph_base", str(tmp_path / "acme"))
    project = tmp_path / "work"
    project.mkdir()
    allow(project, "../acme")
    assert set(pack_setup(project).packs) == {"acme"}  # narrowed
    assert set(pack_setup(tmp_path / "elsewhere").packs) == {"forgegraph_base", "acme"}


def test_a_pack_only_a_folder_config_lists_is_nonstandard(tmp_path, monkeypatch):
    """It may be used, but whatever is drawn with it is watermarked, and its record names
    the pack."""
    shutil.copytree(ACME, tmp_path / "acme")
    user(tmp_path, monkeypatch, "forgegraph_base", str(tmp_path / "acme"))
    work = tmp_path / "work"
    _loud(work)  # house/loud extends acme/acme, which the main config lists
    allow(work, "forgegraph_base", "./house")
    assert pack_setup(work).nonstandard == {"house"}
    g = fg.render(graphspec(work, "house/loud"))
    assert g.nonstandard and g.nonstandard_packs == ["house"]
    [path] = g.save(work / "g.png")
    assert any(a.get_gid() == WATERMARK for a in g.axes.get_children())
    record = fg.load(path)
    assert record is not None
    assert record["nonstandard"] is True and record["nonstandard_packs"] == ["house"]
    standard = fg.render(graphspec(work, "forgegraph_base/base_theme"))
    assert not standard.nonstandard and standard.nonstandard_packs == []


def test_configs_are_found_from_the_drawn_file_up(tmp_path):
    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "./acme")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert [c.path for c in pack_setup(deep).configs] == [
        Path(os.environ[packs.MAIN_CONFIG_VARIABLE]),
        tmp_path / "forgegraph.toml",
    ]


def _loud(root: Path, extends: str = "acme/acme") -> Path:
    """A pack house whose theme loud extends another pack's theme."""
    house = write_pack(root)
    (house / "themes").mkdir()
    (house / "themes" / "loud.yaml").write_text(
        f"name: loud\nversion: 0\ndescription: test\nextends: {extends}\n"
        "fixed_parameters: None\nvariable_parameters: None\n"
    )
    return house


def test_a_pack_spec_builds_on_a_pack_it_may_not_use(tmp_path, monkeypatch):
    """The configs restrict use, not access: house's theme extends acme's, which the main
    config lists but the folder config doesn't allow."""
    shutil.copytree(ACME, tmp_path / "acme")
    _loud(tmp_path)
    user(tmp_path, monkeypatch, "forgegraph_base", str(tmp_path / "acme"), str(tmp_path / "house"))
    allow(tmp_path, "forgegraph_base", "./house")
    reg = registry_for(tmp_path)
    assert validate("theme", reg.docs["theme"]["house/loud"], reg) == []
    assert name_problems("theme", "house/loud", reg) == []
    assert name_problems("theme", "acme/acme", reg) == [
        f"'acme/acme' is in the pack 'acme', which {tmp_path / 'home' / 'config.toml'} and "
        f"{tmp_path / 'forgegraph.toml'} doesn't allow"
    ]
    fg.render(graphspec(tmp_path, "house/loud"))


def test_a_pack_spec_builds_on_an_installed_pip_pack(tmp_path, monkeypatch):
    shutil.copytree(ACME, tmp_path / "site" / "acme")
    monkeypatch.setattr(documents, "pip_packs", lambda: {"acme": tmp_path / "site" / "acme"})
    _loud(tmp_path)
    allow(tmp_path, "./house")
    reg = registry_for(tmp_path)
    assert "acme" in reg.packs and reg.allowed == {"house"}
    assert validate("theme", reg.docs["theme"]["house/loud"], reg) == []


def test_a_pack_spec_building_on_a_pack_that_cant_be_found_is_an_error(tmp_path):
    _loud(tmp_path, "nowhere/acme")
    allow(tmp_path, "./house")
    reg = registry_for(tmp_path)
    assert validate("theme", reg.docs["theme"]["house/loud"], reg) == [
        "extends: 'nowhere/acme' is in the pack 'nowhere', which can't be found: no config that "
        "applies lists it, and no installed pip pack has that name"
    ]


def test_a_layout_and_its_tiles_use_the_layouts_configs(tmp_path):
    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "./acme")
    graphspec(tmp_path, "acme/acme", "acme/slide")
    layout = {
        "name": "fig",
        "version": 0,
        "description": "",
        "extends": "acme/dashboard",
        "fixed_parameters": "None",
        "variable_parameters": {
            "tabs": {"T": {"grid": {"areas": [["g"]]}, "tiles": {"g": "g.yaml"}}}
        },
    }
    YAML().dump(layout, (tmp_path / "fig.layout.yaml").open("w"))
    drawn = fg.layout(tmp_path / "fig.layout.yaml")
    assert drawn.specs["layout"]["name"] == "fig" and drawn.specs["format"]["name"] == "acme/slide"


def test_a_layout_drawn_with_a_nonstandard_pack_is_watermarked(tmp_path, monkeypatch):
    shutil.copytree(ACME, tmp_path / "acme")
    user(tmp_path, monkeypatch, "forgegraph_base")  # not acme
    allow(tmp_path, "forgegraph_base", "./acme")
    graphspec(tmp_path, "acme/acme", "acme/slide")
    layout = {
        "name": "fig",
        "version": 0,
        "description": "",
        "extends": "acme/dashboard",
        "fixed_parameters": "None",
        "variable_parameters": {
            "tabs": {"T": {"grid": {"areas": [["g"]]}, "tiles": {"g": "g.yaml"}}}
        },
    }
    YAML().dump(layout, (tmp_path / "fig.layout.yaml").open("w"))
    drawn = fg.layout(tmp_path / "fig.layout.yaml")
    assert drawn.nonstandard and drawn.nonstandard_packs == ["acme"]
    [path] = drawn.save(tmp_path / "fig.png")
    record = fg.load(path)
    assert record is not None and record["nonstandard_packs"] == ["acme"]


def test_a_blank_canvas_names_its_nonstandard_packs(tmp_path, monkeypatch):
    user(tmp_path, monkeypatch)  # a main config listing no packs
    allow(tmp_path, "forgegraph_base")
    canvas = fg.blank("forgegraph_base/base_theme", "forgegraph_base/base_format", tmp_path)
    [path] = canvas.save(tmp_path / "c.png")
    record = fg.load(path)
    assert record is not None and record["nonstandard_packs"] == ["forgegraph_base"]


# --- finding packs ---------------------------------------------------------------------------


def test_a_pip_pack_is_found_by_its_entry_point_without_importing_it(tmp_path, monkeypatch):
    site = tmp_path / "site"
    package = site / "acme_forgegraph"
    shutil.copytree(ACME, package)
    (package / "__init__.py").write_text("raise RuntimeError('a pack is never imported')\n")
    info = site / "acme_forgegraph-1.2.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: acme-forgegraph\nVersion: 1.2.0\n")
    (info / "entry_points.txt").write_text("[forgegraph.packs]\nacme = acme_forgegraph\n")
    monkeypatch.syspath_prepend(str(site))
    packs.pip_packs.cache_clear()
    try:
        allow(tmp_path, "acme")
        found = pack_setup(tmp_path).packs["acme"]
        assert found.source == "pip" and found.folder == package
        assert "acme_forgegraph" not in sys.modules
    finally:
        packs.pip_packs.cache_clear()


def test_an_uninstalled_pip_pack_is_an_error(tmp_path):
    config = allow(tmp_path, "nonesuch")
    with pytest.raises(PackError, match=re.escape(f"{config}: packs: no pack 'nonesuch'")):
        pack_setup(tmp_path)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("name: house\nversion: 1\n", "description: required"),
        (
            "name: house\nversion: 1\ndescription: x\nissues: x\nrequires: None\nextra: 1\n",
            "extra: unknown field",
        ),
        (
            "name: other\nversion: 1\ndescription: x\nissues: x\nrequires: None\n",
            "name: 'other', but the pack is listed as 'house'",
        ),
        (
            "name: house\nversion: 1\ndescription: x\nissues: x\nrequires: '>=99'\n",
            "requires ForgeGraph >=99",
        ),
        (
            "name: house\nversion: 1\ndescription: x\nissues: x\nrequires: 'soon'\n",
            "'soon' isn't a version specifier",
        ),
    ],
)
def test_a_bad_pack_yaml_is_an_error(tmp_path, text, message):
    folder = tmp_path / "house"
    folder.mkdir()
    (folder / "pack.yaml").write_text(text)
    with pytest.raises(PackError, match=message):
        read_pack(folder, "folder", "house")


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('packs = ["forgegraph_base"]\ntheme = "x"\n', "theme: unknown setting"),
        ("packs = 3\n", "packs: a list of pack names or folder paths is required"),
        ("packs = [", "not TOML"),
    ],
)
def test_a_bad_config_is_an_error(tmp_path, text, message):
    (tmp_path / "forgegraph.toml").write_text(text)
    with pytest.raises(PackError, match=message):
        pack_setup(tmp_path)


def test_two_packs_with_one_name_are_an_error(tmp_path):
    write_pack(tmp_path / "a")
    write_pack(tmp_path / "b")
    allow(tmp_path, "./a/house", "./b/house")
    with pytest.raises(PackError, match="two packs named 'house'"):
        pack_setup(tmp_path)


def test_a_folder_copy_of_a_main_config_pack_is_an_error(tmp_path, monkeypatch):
    """A folder config can't swap in its own copy of a pack the main config lists: one name
    is one pack, so an edited copy can't pass as the standard one."""
    shutil.copytree(ACME, tmp_path / "acme")
    user(tmp_path, monkeypatch, "forgegraph_base", str(tmp_path / "acme"))
    work = tmp_path / "work"
    shutil.copytree(ACME, work / "acme")
    allow(work, "./acme")
    with pytest.raises(PackError, match=r"'acme' .*work[\\/]acme.*already.*[\\/]acme"):
        pack_setup(work)


@pytest.mark.parametrize("name", ["forgegraph_base", "forgegraph_base_2"])
def test_a_folder_pack_named_like_a_built_in_pack_is_an_error(tmp_path, monkeypatch, name):
    user(tmp_path, monkeypatch, "forgegraph_base")
    work = tmp_path / "work"
    write_pack(work, name)
    allow(work, f"./{name}")
    with pytest.raises(PackError, match=f"'{name}' .*already"):
        pack_setup(work)


def test_a_main_config_pack_named_like_a_built_in_pack_is_an_error(tmp_path, monkeypatch):
    write_pack(tmp_path, "forgegraph_base_2")
    user(tmp_path, monkeypatch, "forgegraph_base", str(tmp_path / "forgegraph_base_2"))
    with pytest.raises(PackError, match=r"'forgegraph_base_2' .*already"):
        pack_setup(tmp_path / "elsewhere")


def test_both_configs_may_list_the_same_pack_folder(tmp_path, monkeypatch):
    """Written differently, the same folder is the same pack: standard, not an error."""
    shutil.copytree(ACME, tmp_path / "acme")
    user(tmp_path, monkeypatch, "forgegraph_base", str(tmp_path / "acme"))
    work = tmp_path / "work"
    work.mkdir()
    allow(work, "forgegraph_base", "../acme")
    found = pack_setup(work)
    assert set(found.packs) == {"forgegraph_base", "acme"} and not found.nonstandard


def test_a_packs_fonts_are_registered_when_it_may_be_used(tmp_path):
    from matplotlib import font_manager

    house = write_pack(tmp_path)
    (house / "fonts").mkdir()
    bundled = ROOT / "src" / "forgegraph" / "fonts" / "SourceSans3-Regular.ttf"
    shutil.copy(bundled, house / "fonts" / "HouseSans.ttf")
    allow(tmp_path, "./house")
    registry_for(tmp_path)
    assert str(house / "fonts" / "HouseSans.ttf") in {
        f.fname for f in font_manager.fontManager.ttflist
    }


def test_the_reference_config_and_base_pack_are_valid():
    assert packs.read_config(ROOT / "src" / "forgegraph" / "packs" / "config.toml").packs
    base = read_pack(packs.base_folder(), "built in", "forgegraph_base")
    assert base.version == fg.__version__  # the base pack is released with ForgeGraph


# --- everything works under a pack ---------------------------------------------------------


@pytest.mark.slow
def test_the_skills_examples_render_in_acmes_theme_and_format(tmp_path):
    from forgegraph import skill

    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "forgegraph_base", "./acme")
    examples = tmp_path / "examples"
    shutil.copytree(Path(str(skill.source() / "examples")), examples)
    for path in sorted(examples.glob("*.yaml")):
        if path.name.endswith((".layout.yaml", ".schedule.yaml")):
            continue
        text = path.read_text().replace("forgegraph_base/base_theme", "acme/acme")
        path.write_text(text.replace("forgegraph_base/base_format", "acme/slide"))
        g = fg.render(path)
        assert g.values["theme"]["font.family"] == "IBM Plex Serif", path.name


def test_a_schedule_extends_a_packs_schedule(tmp_path):
    from forgegraph.jobs.run import load

    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "forgegraph_base", "./acme")
    graphspec(tmp_path, "acme/acme", "acme/slide")
    (tmp_path / "lab.schedule.yaml").write_text(
        "name: lab\nversion: 0\ndescription: test\nextends: acme/workday\n"
        "fixed_parameters: None\nvariable_parameters:\n    targets:\n        files: [g.yaml]\n"
    )
    schedule = load(tmp_path / "lab.schedule.yaml")
    assert schedule.cadence.describe().startswith("Mon")


def test_a_pack_theme_still_watermarks_a_changed_graph(tmp_path):
    from forgegraph.drawing.figure import WATERMARK

    shutil.copytree(ACME, tmp_path / "acme")
    allow(tmp_path, "./acme")
    g = fg.render(graphspec(tmp_path, "acme/acme", "acme/slide"))
    g.axes.axhline(1.0)
    [path] = g.save(tmp_path / "g.png")
    assert any(a.get_gid() == WATERMARK for a in g.axes.get_children())
    record = fg.load(path)
    assert record is not None and record["nonstandard"] is True
