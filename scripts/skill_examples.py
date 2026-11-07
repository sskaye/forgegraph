"""Copy the skill's examples from the documentation's (docs/examples), with their data.

uv run python scripts/skill_examples.py           # write them into the skill
uv run python scripts/skill_examples.py --check   # exit 1 if the skill's copies differ

The documentation's examples are the one source: the skill bundles the ones its SKILL.md
lists (SKILL), so an agent reads small files that match the installed version, without web
access. A layout brings the GraphSpecs its tiles name, and a schedule its targets. Each
GraphSpec's data.file is written from examples/sample-data as the documentation site draws it
(scripts/docs_site.py). tests/test_skill_examples.py fails while the copies are stale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from forgegraph.spec.registry import load_yaml

sys.path.insert(0, str(Path(__file__).parent))

import docs_site

ROOT = Path(__file__).parents[1]
DOCS = ROOT / "docs" / "examples"
SKILL = ROOT / "src" / "forgegraph" / "skill" / "forgegraph" / "examples"
LISTED = (  # the examples SKILL.md lists, in its order
    "polarization.yaml",
    "tips_stacked.yaml",
    "dose_response.yaml",
    "savings.yaml",
    "plate_spectra.yaml",
    "penguin_measures.yaml",
    "passenger_toggles.yaml",
    "cells.layout.yaml",
    "cells.schedule.yaml",
)


def specs() -> list[str]:
    """Every file the listed examples need: each one, a layout's tiles' GraphSpecs and a
    schedule's targets, in the order first needed."""
    out: list[str] = []

    def add(name: str) -> None:
        if name in out:
            return
        out.append(name)
        doc = load_yaml(DOCS / name)
        tree = doc.get("parameters") or {}
        if name.endswith(".schedule.yaml"):
            for target in tree["targets"]["files"]:
                add(target)
        elif name.endswith(".layout.yaml"):
            for tab in _tabs(tree["tabs"]):
                for tile in tab["tiles"].values():
                    add(tile)

    for name in LISTED:
        add(name)
    return out


def _tabs(tabs: dict) -> list[dict]:
    """Every tab with tiles, inside tabs that hold tabs too."""
    out = []
    for tab in tabs.values():
        out += _tabs(tab["tabs"]) if "tabs" in tab else [tab]
    return out


def data() -> dict[str, pd.DataFrame]:
    """Each Parquet file the GraphSpecs read, as the documentation site writes it."""
    out = {}
    for name in specs():
        for dataset in docs_site._datasets(DOCS / name):
            frame = pd.read_csv(docs_site.SAMPLE_DATA / f"{dataset}.csv")
            out[f"{dataset}.parquet"] = docs_site.PREPARE.get(dataset, lambda d: d)(frame)
    return out


def stale() -> list[str]:
    """What differs between the skill's examples and their sources: a file missing,
    changed or extra."""
    found = []
    wanted = set(specs()) | set(data())
    for name in specs():
        theirs = SKILL / name
        if not theirs.exists() or theirs.read_bytes() != (DOCS / name).read_bytes():
            found.append(name)
    for name, frame in data().items():
        theirs = SKILL / name
        if not theirs.exists() or not pd.read_parquet(theirs).equals(frame):
            found.append(name)
    found += sorted(p.name for p in SKILL.iterdir() if p.name not in wanted)
    return found


def write() -> None:
    for p in SKILL.iterdir():
        if p.name not in set(specs()) | set(data()):
            p.unlink()
            print(f"removed {p.relative_to(ROOT)}")
    for name in specs():
        (SKILL / name).write_bytes((DOCS / name).read_bytes())
    for name, frame in data().items():
        frame.to_parquet(SKILL / name, index=False)
    print(
        f"wrote {len(specs())} examples and {len(data())} data files to {SKILL.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the copies differ")
    if parser.parse_args().check:
        if problems := stale():
            sys.exit(f"stale: {', '.join(problems)}; run scripts/skill_examples.py")
    else:
        write()
