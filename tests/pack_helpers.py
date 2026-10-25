"""Files for tests: folder packs, configs, documents and GraphSpecs; the CLI's JSON output;
and needs_node, for tests that run a page's script or Forgemark."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

import forgegraph as fg
from forgegraph.cli import app
from forgegraph.spec.parameters import NONE, definitions, tree_set

needs_node = pytest.mark.skipif(
    shutil.which("node") is None and not os.environ.get("FORGEGRAPH_REQUIRE_NODE"),
    reason="needs Node 18 or later",
)

PACK_YAML = (
    "name: {name}\nversion: 1.0.0\ndescription: Test pack.\n"
    "issues: https://example.com/{name}/issues\nrequires: {requires}\n"
)


def write_pack(root: Path, name: str = "house", requires: str = "None") -> Path:
    """An empty folder pack, root/name, with its pack.yaml."""
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "pack.yaml").write_text(PACK_YAML.format(name=name, requires=requires))
    return folder


def write_config(path: Path, *packs: str) -> Path:
    """A config allowing these packs (names, or paths from its folder)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("packs = [" + ", ".join(f"'{p}'" for p in packs) + "]\n")  # literal strings
    return path


def allow(root: Path, *packs: str) -> Path:
    """A folder config in root allowing these packs (names, or paths from root)."""
    return write_config(root / "forgegraph.toml", *packs)


def dump(doc: dict[str, Any], path: Path) -> Path:
    """Write a YAML document, making its folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        YAML().dump(doc, f)
    return path


def doc(
    extends: str,
    name: str = "t",
    *,
    fixed: dict[str, Any] | None = None,
    variable: dict[str, Any] | None = None,
    description: str = "test",
    version: int = 0,
) -> dict[str, Any]:
    """A document extending another, with these fixed and variable parameters (by dotted
    path, or as categories); an empty section is written as None."""
    sections: dict[str, Any] = {}
    for section, values in (("fixed_parameters", fixed), ("variable_parameters", variable)):
        tree: dict[str, Any] = {}
        for path, value in (values or {}).items():
            tree_set(tree, path, value)
        sections[section] = tree or NONE
    return {
        "name": name,
        "version": version,
        "description": description,
        "extends": extends,
        **sections,
    }


def child(kind: str, parent: str, values: dict[str, Any], **header: Any) -> dict[str, Any]:
    """A document extending parent that sets these values (by dotted path), each in the
    section its definition has it in. header: doc()'s name, description and version."""
    defs = definitions(kind)
    fixed = {path: value for path, value in values.items() if defs[path].fixed}
    variable = {path: value for path, value in values.items() if not defs[path].fixed}
    return doc(parent, fixed=fixed, variable=variable, **header)


def graphspec_file(
    folder: Path, name: str = "p", data: str = "p.parquet", **graphspec_kw: Any
) -> Path:
    """folder/<name>.yaml: a GraphSpec drawing the example data from data (a path from
    folder), written there if it isn't yet, with the tests' settings unless graphspec_kw
    (fg.graphspec's) gives its own."""
    from render_helpers import BASE, polarization

    where = folder / data
    if not where.exists():
        where.parent.mkdir(parents=True, exist_ok=True)
        polarization().to_parquet(where)
    graphspec_kw.setdefault("settings", BASE)
    return dump(fg.graphspec(name, "xy", data_file=data, **graphspec_kw), folder / f"{name}.yaml")


def cli(*args: str) -> dict[str, Any]:
    """A command's JSON output; the command must succeed."""
    result = CliRunner().invoke(app, [*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def cli_problems(*args: str) -> list[str]:
    """The problems a command reports, in JSON; the command must fail."""
    result = CliRunner().invoke(app, [*args, "--json"])
    assert result.exit_code == 1, result.output
    return json.loads(result.output)["problems"]
