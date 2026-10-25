"""Check an installed ForgeGraph, as a user would get it from pip: run from outside the
repository, in a folder of its own, with a main config of its own.

python -I scripts/smoke_installed.py   (with the environment's forgegraph installed)

Draws the README's examples from Python and the command line, reads a graph's record back,
lists the catalog, draws with the second built-in pack, installs the skill into a folder and
draws on the blank canvas. Exits non-zero, saying what failed, at the first problem.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GRAPHSPEC = """name: voltage
version: 0
description: Cell voltage over a test, one line per cell.
extends: None
fixed_parameters: None
variable_parameters:
    specifications:
        graph_type: xy
        theme: {theme}
        format: {format}
    text:
        title: Cell voltage
    data:
        file: runs.parquet
        preprocessing: None
    axis:
        x:
            data:
                column: hours
        y:
            data:
                column: voltage
    encoding:
        color:
            column: cell
"""


def forgegraph(*args: str) -> dict:
    """Run the forgegraph command with --json; its report, or exit saying why it failed."""
    done = subprocess.run(["forgegraph", *args, "--json"], capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit(f"forgegraph {' '.join(args)} failed:\n{done.stdout}{done.stderr}")
    return json.loads(done.stdout)


def main() -> None:
    import pandas as pd

    import forgegraph as fg

    folder = Path(tempfile.mkdtemp(prefix="forgegraph-smoke-"))
    os.chdir(folder)
    os.environ["FORGEGRAPH_CONFIG"] = str(folder / "main.toml")
    print(f"forgegraph {fg.__version__} from {Path(fg.__file__).parent}, in {folder}")

    runs = pd.DataFrame(
        {
            "hours": [0, 1, 2, 3, 0, 1, 2, 3],
            "voltage": [0.72, 0.71, 0.70, 0.69, 0.73, 0.73, 0.72, 0.72],
            "cell": ["A", "A", "A", "A", "B", "B", "B", "B"],
        }
    )
    [saved] = fg.xy(runs, x="hours", y="voltage", color="cell", title="Cell voltage").save("python")
    assert fg.load(saved) is not None, "the Python graph has no record"

    runs.to_parquet("runs.parquet")
    for name, theme, fmt in (
        ("base", "forgegraph_base/base_theme", "forgegraph_base/base_format"),
        ("base_2", "forgegraph_base_2/base_theme", "forgegraph_base_2/compact_format"),
    ):
        Path(f"{name}.yaml").write_text(GRAPHSPEC.format(theme=theme, format=fmt))
        report = forgegraph("render", f"{name}.yaml")
        assert report["saved"] and "nonstandard" not in report, report
        record = fg.load(report["saved"][0])
        assert record is not None and record["specs"]["theme"]["name"] == theme, record

    listed = forgegraph("catalog")
    packs = {p["name"] for p in listed["packs"]}
    assert packs == {"forgegraph_base", "forgegraph_base_2"}, packs

    installed = forgegraph("skill", "install", "--dest", str(folder / "skills"))
    assert (folder / "skills" / "forgegraph" / "SKILL.md").is_file(), installed

    canvas = fg.blank("forgegraph_base/base_theme", "forgegraph_base/base_format")
    with canvas.drawing():
        canvas.axes.plot([1, 2, 3], [2, 1, 3])
    [drawn] = canvas.save("canvas.png")
    record = fg.load(drawn)
    assert record is not None and record["nonstandard"] is True, record
    print("ok")


if __name__ == "__main__":
    main()
