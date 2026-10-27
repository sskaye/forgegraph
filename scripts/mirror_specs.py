"""Regenerate the Markdown mirrors of the specification files (docs/specifications/), the
packs' files (docs/packs/<pack>/), and the example layouts' pages beside their files in
examples/.

Run after changing a default file:  uv run python scripts/mirror_specs.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tests"))

from spec_mirror import MIRRORS, mirror_path, write

from forgegraph import forgemark

for kind in MIRRORS:
    changed = write(kind)
    print(("updated " if changed else "unchanged ") + str(mirror_path(kind)))
    if changed and forgemark.COMMENTS in mirror_path(kind).read_text(encoding="utf-8"):
        print(
            forgemark.run("reattach", str(mirror_path(kind)), "--all", check=False).stdout, end=""
        )
