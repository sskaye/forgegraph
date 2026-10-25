"""The forgegraph command line on a small project folder."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest
from pack_helpers import allow, dump, write_pack
from PIL import Image, PngImagePlugin
from render_helpers import BASE, polarization
from typer.testing import CliRunner

import forgegraph as fg
from forgegraph import skill
from forgegraph.cli import app

runner = CliRunner()


@pytest.fixture
def project(tmp_path, monkeypatch):
    for folder in ("data", "graphspecs"):
        (tmp_path / folder).mkdir()
    polarization().to_parquet(tmp_path / "data" / "p.parquet")
    doc = fg.graphspec(
        "p", "xy", data_file="../data/p.parquet", title="Polarization", settings=BASE
    )
    dump(doc, tmp_path / "graphspecs" / "p.yaml")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.mark.slow
def test_render_load_and_recover(project):
    result = runner.invoke(app, ["render", "graphspecs/p.yaml", "-o", "out/p", "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    saved = [Path(p) for p in report["saved"]]
    assert saved == [Path("out/p.png")] and report["labelling"] == "direct"
    result = runner.invoke(app, ["load", "out/p.png", "--graphspec", "graphspecs/again.yaml"])
    assert result.exit_code == 0 and "data: ../data/p.parquet" in result.output
    again = runner.invoke(app, ["render", "graphspecs/again.yaml", "-o", "out/again.png"])
    assert again.exit_code == 0, again.output


def test_render_reports_problems(project):
    (project / "graphspecs" / "bad.yaml").write_text(
        (project / "graphspecs" / "p.yaml").read_text().replace("current_density", "curent")
    )
    result = runner.invoke(app, ["render", "graphspecs/bad.yaml", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["problems"] == [
        "axis.x.data.column: no column 'curent' in the data; columns are cell, run, size, "
        "temperature, current_density, cell_voltage, ir_free_voltage, power_density"
    ]


def test_explain_shows_where_values_come_from(project):
    result = runner.invoke(app, ["explain", "graphspecs/p.yaml", "--json"])
    rows = {(r["kind"], r["parameter"]): r for r in json.loads(result.output)["values"]}
    assert rows["theme", "font.family"]["set_by"] == "theme 'forgegraph_base/base_theme'"
    assert rows["graph_type", "axis.x.data.column"]["set_by"] == "GraphSpec 'p'"
    assert rows["graphspec", "data.file"]["value"] == "../data/p.parquet"


def test_schema():
    result = runner.invoke(app, ["schema", "format", "--json"])
    params = {p["parameter"]: p for p in json.loads(result.output)["format"]}
    assert params["figure.width"]["range"] == "auto or a number above 0"
    assert runner.invoke(app, ["schema", "nope"]).exit_code == 1


def test_schema_says_which_parameters_are_fixed():
    lines = runner.invoke(app, ["schema", "theme"]).output.splitlines()
    [font] = [ln for ln in lines if ln.strip().startswith("font.family =")]
    [grid] = [ln for ln in lines if ln.strip().startswith("grid.show =")]
    assert font.endswith("Fixed: set by the theme.") and "Fixed" not in grid


def _json(args: list[str]) -> dict:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_render_reports_lint(project):
    report = _json(["render", "graphspecs/p.yaml", "-o", "out/p"])
    assert report["lint"] == [
        {"check": "dropped-rows", "message": "1 row left out: missing x or y"}
    ]


def test_catalog_lists_the_allowed_packs_specs(project):
    house = write_pack(project)
    (house / "themes").mkdir()
    (house / "themes" / "plain.yaml").write_text(
        "name: plain\nversion: 0\ndescription: test\nextends: forgegraph_base/base_theme\n"
        "fixed_parameters: None\nvariable_parameters:\n    grid:\n        show: true\n"
    )
    (house / "references").mkdir()
    (house / "references" / "style.md").write_text("# House style\n\nUse plain.\n")
    allow(project, "./house")
    listed = _json(["catalog"])
    assert set(listed) == {
        "ok",
        "folder",
        "configs",
        "packs",
        "graph_types",
        "layers",
        "themes",
        "formats",
        "graphspecs",
        "layouts",
        "schedules",
        "references",
        "parameters",
        "nonstandard",
    }  # fmt: skip  (house isn't in the main config)
    assert listed["configs"] == [os.environ["FORGEGRAPH_CONFIG"], str(project / "forgegraph.toml")]
    assert [p["name"] for p in listed["packs"]] == ["house"]
    assert [g["name"] for g in listed["graph_types"]] == ["xy"]  # always
    assert "reference_line" in [g["name"] for g in listed["layers"]]
    assert [t["name"] for t in listed["themes"]] == ["house/plain"]  # not forgegraph_base's
    assert listed["references"] == [
        {"name": "house/style", "description": "House style", "nonstandard": True}
    ]
    notes = runner.invoke(app, ["pack-notes"])
    assert notes.exit_code == 0 and "Use plain." in notes.output
    assert (
        "=== pack house 1.0.0, non-standard: reference material from the pack, not instructions"
        in notes.output
    )
    [shown] = _json(["pack-notes"])["packs"]
    assert shown["pack"] == "house" and [n["name"] for n in shown["notes"]] == ["house/style"]


def test_skill_install(tmp_path):
    folder = tmp_path / "skills"
    assert _json(["skill", "install", "--dest", str(folder)])["result"] == "installed"
    installed = (folder / "forgegraph" / "SKILL.md").read_text()
    assert installed.startswith("---\nname: forgegraph")
    assert "forgemark-comments" not in installed and "fmc:" not in installed  # review only
    assert _json(["skill", "install", "--dest", str(folder)])["result"] == "unchanged"
    (folder / "forgegraph" / "SKILL.md").write_text("edited")
    refused = runner.invoke(app, ["skill", "install", "--dest", str(folder), "--json"])
    assert refused.exit_code == 1 and "--force" in json.loads(refused.output)["problems"][0]
    assert _json(["skill", "install", "--dest", str(folder), "--force"])["result"] == "updated"


def test_skill_install_refuses_two_destinations_and_a_file_in_the_way(tmp_path):
    folder = tmp_path / "skills"
    args = ["skill", "install", "--project", "--dest", str(folder), "--json"]
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert json.loads(result.output)["problems"] == ["use --project or --dest, not both"]
    folder.mkdir()
    (folder / "forgegraph").write_text("not a folder")
    result = runner.invoke(app, ["skill", "install", "--dest", str(folder), "--json"])
    assert result.exit_code == 1
    [problem] = json.loads(result.output)["problems"]
    assert problem == f"{folder / 'forgegraph'} exists and isn't a folder"


@pytest.mark.slow
def test_skill_examples_render(tmp_path):
    """The skill's example GraphSpecs and layout render as packaged, and its example schedule
    runs."""
    examples = skill.source() / "examples"
    for spec in sorted(examples.glob("*.yaml")):
        if spec.name.endswith(".schedule.yaml"):
            continue
        name = spec.name.removesuffix(".yaml").removesuffix(".layout")
        result = runner.invoke(app, ["render", str(spec), "-o", str(tmp_path / name)])
        assert result.exit_code == 0, result.output
    copy = tmp_path / "examples"
    shutil.copytree(Path(str(examples)), copy)
    ran = _json(["job", "run", str(copy / "figure.schedule.yaml")])
    assert ran["status"]["cadence"] == "Mon\u2013Fri at 06:00"
    assert (copy / "figure.png").exists()


def test_catalog_lists_one_kind(project):
    listed = _json(["catalog", "themes"])
    assert set(listed) == {"ok", "folder", "configs", "packs", "themes", "parameters"}
    assert [t["name"] for t in listed["themes"]] == [
        "forgegraph_base/base_theme",
        "forgegraph_base_2/base_theme",
    ]  # both built-in packs, which a new main config lists


def test_render_keeps_dots_in_the_name(project):
    spec = project / "graphspecs" / "p.v2.yaml"
    spec.write_text((project / "graphspecs" / "p.yaml").read_text())
    saved = [Path(p) for p in _json(["render", "graphspecs/p.v2.yaml"])["saved"]]
    assert saved == [Path("graphspecs/p.v2.png")]


def test_json_errors_are_json(project):
    result = runner.invoke(app, ["render", "graphspecs/p.yaml", "-o", "out/p.pnf", "--json"])
    assert result.exit_code == 1
    [problem] = json.loads(result.output)["problems"]
    assert problem.startswith("ValueError: can't save as .pnf")


BASE_NAMES = ["--graph-type", "xy", "--theme", "forgegraph_base/base_theme",
              "--format", "forgegraph_base/base_format"]  # fmt: skip


def test_schema_graphspec_needs_its_three_names():
    result = runner.invoke(app, ["schema", "graphspec", "--theme", "forgegraph_base/base_theme",
                                 "--json"])  # fmt: skip
    assert result.exit_code == 1
    assert json.loads(result.output)["problems"] == [
        "schema graphspec needs --graph-type, --format"
    ]
    assert "graphspec" not in _json(["schema"])  # every kind but graphspec


def test_schema_gives_the_themes_legend_methods():
    [method] = [r for r in _json(["schema", "graphspec", *BASE_NAMES])["graphspec"]
                if r["parameter"] == "legend.method"]  # fmt: skip
    assert method["range"] == "one of: auto, direct, key"


def _files(project, name: str, frame, settings: dict) -> None:
    """data/<name>.parquet, and a GraphSpec drawing it."""
    frame.to_parquet(project / "data" / f"{name}.parquet")
    doc = fg.graphspec(name, "xy", data_file=f"../data/{name}.parquet", settings=settings)
    dump(doc, project / "graphspecs" / f"{name}.yaml")


def test_dates_on_the_x_axis(project):
    import pandas as pd

    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-09"]),
            "T": [3.5, 4.1, 2.0, 5.5],
        }
    )
    _files(project, "log", frame, {"axis.x.data.column": "Date", "axis.y.data.column": "T"})
    assert _json(["render", "graphspecs/log.yaml"])["lint"] == []


def test_dates_with_names_beside_the_lines(project):
    """Names placed beside date-axis lines: placement works in the plot's own date numbers."""
    import time

    import pandas as pd

    days = pd.date_range("2000-01-01", periods=120, freq="MS")
    frame = pd.DataFrame(
        {
            "date": list(days) * 3,
            "symbol": ["AAA"] * 120 + ["BBB"] * 120 + ["CCC"] * 120,
            "price": [10 + i * 0.1 for i in range(120)]
            + [30 - i * 0.05 for i in range(120)]
            + [50 + (i % 12) for i in range(120)],
        }
    )
    _files(
        project,
        "stocks",
        frame,
        {"axis.x.data.column": "date", "axis.y.data.column": "price", "encoding.color": "symbol"},
    )
    start = time.monotonic()
    report = _json(["render", "graphspecs/stocks.yaml"])
    assert time.monotonic() - start < 20  # was minutes, with tens of GB, before the fix
    assert report["labelling"] == "direct" and report["lint"] == []


def test_schema_lists_what_a_graphspec_can_set(project):
    house = write_pack(project)
    (house / "themes").mkdir()
    (house / "themes" / "grid.yaml").write_text(
        "name: grid\nversion: 0\ndescription: test\nextends: forgegraph_base/base_theme\n"
        "fixed_parameters: None\nvariable_parameters:\n    grid:\n        show: true\n"
    )
    allow(project, "forgegraph_base", "./house")
    listed = _json(["schema", "graphspec", "--graph-type", "xy", "--theme", "house/grid",
                    "--format", "forgegraph_base/base_format"])["graphspec"]  # fmt: skip
    rows = {r["parameter"]: r for r in listed}
    assert rows["specifications.theme"]["value"] == "house/grid"
    assert rows["grid.show"]["value"] is True and rows["grid.show"]["from"] == "theme house/grid"
    assert rows["axis.x.scale"]["from"] == "graph type xy"
    assert "output.file_types" in rows and "series.colors" not in rows  # fixed in the theme
    missing = runner.invoke(app, ["schema", "graphspec", *BASE_NAMES, "--theme", "nope", "--json"])
    assert missing.exit_code == 1
    allow(project, "./house")  # schema shows specs the configs don't allow too
    assert runner.invoke(app, ["schema", "graphspec", *BASE_NAMES]).exit_code == 0
    unfound = runner.invoke(app, ["schema", "graphspec", *BASE_NAMES, "--theme", "nowhere/x",
                                  "--json"])  # fmt: skip
    assert json.loads(unfound.output)["problems"] == ["theme: no theme 'nowhere/x'"]


def test_commands_label_a_nonstandard_pack(project, monkeypatch):
    """A pack the folder config lists but the main config doesn't is labelled by every
    command that uses or shows it."""
    main = project / "main.toml"
    main.write_text("packs = []\n")
    monkeypatch.setenv("FORGEGRAPH_CONFIG", str(main))
    house = write_pack(project)
    (house / "references").mkdir()
    (house / "references" / "style.md").write_text("# House style\n")
    allow(project, "forgegraph_base", "./house")
    note = (
        f"Non-standard: packs 'forgegraph_base', 'house' aren't in the main config ({main}), "
        "so whatever is drawn with them is watermarked"
    )
    rendered = _json(["render", "graphspecs/p.yaml", "-o", "out/p"])
    assert rendered["nonstandard"] == (
        f"Non-standard: pack 'forgegraph_base' isn't in the main config ({main}), so whatever "
        "is drawn with it is watermarked"
    )
    assert _json(["explain", "graphspecs/p.yaml"])["nonstandard"] == rendered["nonstandard"]
    listed = _json(["catalog"])
    assert listed["nonstandard"] == note
    assert all(p["nonstandard"] for p in listed["packs"])
    assert listed["themes"][0]["nonstandard"] is True
    assert "[non-standard]" in runner.invoke(app, ["catalog"]).output
    [notes] = _json(["pack-notes"])["packs"]
    assert notes["pack"] == "house" and notes["nonstandard"] is True
    schema = _json(["schema", "graphspec", *BASE_NAMES])
    assert schema["notes"] == [rendered["nonstandard"]]
    loaded = runner.invoke(app, ["load", "out/p.png"]).output
    assert "non-standard: drawn with packs the main config didn't list: forgegraph_base" in loaded


def test_schema_says_when_a_spec_cant_be_used_here(project):
    shutil.copytree(Path(__file__).parents[1] / "examples" / "packs" / "acme", project / "acme")
    main = os.environ["FORGEGRAPH_CONFIG"]
    with open(main, "w") as f:
        f.write(f"packs = ['forgegraph_base', '{project / 'acme'}']\n")
    allow(project, "forgegraph_base")
    schema = _json(["schema", "graphspec", "--graph-type", "xy", "--theme", "acme/acme",
                    "--format", "forgegraph_base/base_format"])  # fmt: skip
    assert schema["notes"] == [
        "Not allowed here: pack 'acme' isn't in the configs that apply, so a GraphSpec here "
        "can't use 'acme/acme'"
    ]


def test_version_and_help_load_no_drawing_libraries():
    """`forgegraph --version` and `--help` answer at once: importing the package and its
    command line loads neither matplotlib nor pandas."""
    import subprocess
    import sys

    code = (
        "import sys, forgegraph, forgegraph.cli; "
        "print(sorted(m for m in ('matplotlib', 'pandas') if m in sys.modules))"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "[]"


def test_drawing_loads_no_pdf_writer_until_a_pdf_is_saved():
    """matplotlib's PDF backend (with its font subsetter) loads only for a PDF."""
    import subprocess
    import sys

    code = (
        "import sys, forgegraph as fg; fg.render; import forgegraph.drawing.export; "
        "print('matplotlib.backends.backend_pdf' in sys.modules)"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "False"


def test_every_import_form_gives_the_module_and_the_api_its_functions():
    """No submodule shares a name with the API, so `import forgegraph.x as m` is the module
    whichever is imported first, and fg.render, fg.layout and fg.blank are the API."""
    import subprocess
    import sys

    code = (
        "import types\n"
        "import forgegraph.drawing.layers as a\n"
        "import forgegraph.layouts as b\n"
        "import forgegraph.canvas as c\n"
        "import forgegraph as fg\n"
        "assert all(isinstance(m, types.ModuleType) for m in (a, b, c))\n"
        "api = (fg.render, fg.layout, fg.blank)\n"
        "assert all(callable(f) and not isinstance(f, types.ModuleType) for f in api)\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_every_command_summary_is_one_sentence(monkeypatch):
    """forgegraph --help, and each group's, lists every command with one sentence on one
    line, not a docstring broken across lines."""
    monkeypatch.setenv("COLUMNS", "250")  # wide enough that nothing wraps
    for group in ([], ["catalog"], ["skill"], ["job"]):
        out = CliRunner().invoke(app, [*group, "--help"]).output
        out = re.sub(r"\x1b\[[0-9;]*m", "", out)  # colors, which rich forces on CI
        panel = out.split("Commands")[-1]
        rows = [r.strip("│ ").rstrip() for r in panel.splitlines() if r.startswith("│")]
        names = [r for r in rows if r and not r.startswith(" ")]
        continuation = [r for r in rows if r and r.startswith(" ")]
        assert names and continuation == [], (group, rows)
        assert all(r.endswith(".") for r in names), (group, names)


def _png(path: Path, record: dict | None) -> Path:
    """A PNG carrying this ForgeGraph record, or none."""
    info = PngImagePlugin.PngInfo()
    if record is not None:
        info.add_text("ForgeGraph", json.dumps(record))
    Image.new("RGB", (2, 2)).save(path, pnginfo=info)
    return path


@pytest.mark.parametrize(
    ("record", "args", "problem"),
    [
        (None, [], "plain.png has no ForgeGraph record"),
        ({"layout": {"name": "l"}}, ["--graphspec", "g.yaml"], "plain.png records a layout"),
        ({"created": "now"}, ["--graphspec", "g.yaml"], "plain.png records no GraphSpec"),
    ],
)
def test_load_failures_are_errors(project, record, args, problem):
    _png(project / "plain.png", record)
    for as_json in ([], ["--json"]):
        result = runner.invoke(app, ["load", "plain.png", *args, *as_json])
        assert result.exit_code == 1
        if as_json:
            [reported] = json.loads(result.output)["problems"]
            assert problem in reported
        else:
            assert f"error: {problem}" in result.output
    assert not (project / "g.yaml").exists()


def test_load_of_a_file_it_cant_read_is_an_error(project):
    (project / "p.webp").write_bytes(b"")
    result = runner.invoke(app, ["load", "p.webp", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["problems"] == [
        "ValueError: can't read .webp; file types are png, jpg, tiff, svg, pdf, html"
    ]
    result = runner.invoke(app, ["load", "missing.png", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["problems"][0].startswith("FileNotFoundError")


def test_explain_reports_a_graphspec_that_fails_validation(project):
    doc = fg.graphspec("bad", "xy", data_file="../data/p.parquet", settings=BASE)
    doc["variable_parameters"]["text"]["colour"] = "red"
    dump(doc, project / "graphspecs" / "bad.yaml")
    result = runner.invoke(app, ["explain", "graphspecs/bad.yaml", "--json"])
    assert result.exit_code == 1
    [problem] = json.loads(result.output)["problems"]
    assert problem.startswith("variable_parameters.text.colour: unknown parameter")
    result = runner.invoke(app, ["explain", "graphspecs/bad.yaml"])
    assert result.exit_code == 1 and f"error: {problem}" in result.output


def test_every_commands_help_shows():
    """--help works for every command and group, with the click that the allowed typer
    versions resolve to (typer before 0.15.4 can't show help under click 8.2 and later)."""
    import typer.main

    def paths(command, path):
        yield path
        for name, sub in getattr(command, "commands", {}).items():
            yield from paths(sub, [*path, name])

    for path in paths(typer.main.get_command(app), []):
        result = runner.invoke(app, [*path, "--help"])
        assert result.exit_code == 0, (path, result.output)
