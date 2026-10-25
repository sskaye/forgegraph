"""Regenerate the Markdown mirrors of the specification files (docs/specs/<type>/*.md, and the
deliverables' pages beside their files in review/).

Run after changing a default file:  uv run python scripts/mirror_specs.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tests"))

from spec_mirror import MIRRORS, mirror_path, write

sys.path.insert(0, str(Path(__file__).parent))
from forgegraph.catalog_build import forgemark

for kind in MIRRORS:
    changed = write(kind)
    print(("updated " if changed else "unchanged ") + str(mirror_path(kind)))
    if changed and "<!-- forgemark-comments" in mirror_path(kind).read_text(encoding="utf-8"):
        print(
            forgemark.run("reattach", str(mirror_path(kind)), "--all", check=False).stdout, end=""
        )
