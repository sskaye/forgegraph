"""Folder packs and project configs for tests."""

from __future__ import annotations

from pathlib import Path

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


def allow(root: Path, *packs: str) -> Path:
    """A project config in root allowing these packs (names, or paths from root)."""
    path = root / "forgegraph.toml"
    path.write_text("packs = [" + ", ".join(f"'{p}'" for p in packs) + "]\n")  # literal strings
    return path
