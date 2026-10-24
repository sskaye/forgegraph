"""Build dist/forgegraph-bundled.skill: the skill with ForgeGraph itself inside, for trying it
in Claude chat or Cowork before ForgeGraph is published.

uv run python scripts/build_bundled_skill.py

Those sessions run commands in a sandbox, without the `forgegraph` installed on this
machine, and get skills by upload. This file is the skill as `forgegraph skill install`
writes it, plus this checkout's ForgeGraph package and one line telling the agent to install
it. pip fetches ForgeGraph's dependencies in the sandbox. Once ForgeGraph is on PyPI, the
skill can name the version to install instead, and this build isn't needed.
"""

from __future__ import annotations

import subprocess
import tempfile
import zipfile
from pathlib import Path

from forgegraph.skill import NAME, contents

ROOT = Path(__file__).parents[1]
OUT = ROOT / "dist" / "forgegraph-bundled.skill"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["uv", "build", "--wheel", "-q", "-o", tmp], cwd=ROOT, check=True)
        [wheel] = Path(tmp).glob("forgegraph-*.whl")
        files = contents()
        lines = files["SKILL.md"].decode("utf-8").split("\n")
        title = next(i for i, line in enumerate(lines) if line.startswith("# "))
        install = (
            f"If the `forgegraph` command isn't available, install it: `pip install` the "
            f"`{wheel.name}` file in this skill's folder."
        )
        lines[title + 1 : title + 1] = ["", install]
        files["SKILL.md"] = "\n".join(lines).encode("utf-8")
        OUT.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
            for rel, data in files.items():
                z.writestr(f"{NAME}/{rel}", data)
            z.write(wheel, f"{NAME}/{wheel.name}")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
