"""Files for tests: folder packs, configs and YAML documents; and needs_node, for tests that
run a page's script or Forgemark."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

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
