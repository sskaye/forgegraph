"""The package's metadata: its licence files and its one-line description."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_every_licence_file_listed_exists():
    missing = [p for p in PROJECT["license-files"] if not (ROOT / p).is_file()]
    assert missing == []


def test_every_bundled_fonts_licence_is_listed():
    fonts = ROOT / "src" / "forgegraph" / "fonts"
    licences = {p.relative_to(ROOT).as_posix() for p in fonts.glob("OFL-*")}
    assert licences and licences <= set(PROJECT["license-files"])
    assert "OFL-1.1" in PROJECT["license"]


def test_one_description_everywhere():
    """pyproject's description is the README's first line, and the command's help says it."""
    from forgegraph.cli import app

    readme = (ROOT / "README.md").read_text(encoding="utf-8").split("\n\n")[1].strip()
    assert PROJECT["description"] == readme
    assert app.info.help == f"ForgeGraph: {readme[0].lower()}{readme[1:]}"
