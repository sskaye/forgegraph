"""Every parameter changes the drawing (architecture §7).

Every card in ForgeGraph's catalog files (catalogs/) is drawn, and must differ from the
baseline it starts from. The catalog build refuses such a card too; this test finds one
sooner, and names it.
"""

from __future__ import annotations

import pytest

from forgegraph.catalog.examples import Change, draw, png
from forgegraph.catalog.files import read
from forgegraph.spec.documents import builtin
from forgegraph.spec.parameters import graph_type_files

pytestmark = pytest.mark.slow  # the full suite only (pytest --full)

FILES = [("theme", n) for n in sorted(builtin().docs["theme"])]
FILES += [("format", n) for n in sorted(builtin().docs["format"])]
FILES += [("graph_type", n) for n in graph_type_files()]
CASES = [
    (kind, name, catalog.baseline, v)
    for kind, name in FILES
    for catalog in [read(kind, name, builtin())]
    for _, v in catalog.variations
    if v is not None
]
_BEFORE: dict[str, bytes] = {}  # each baseline's drawing


def _drawn(kind: str, name: str, spec: str, *changes: Change) -> bytes:
    theme = name if kind == "theme" else None
    fmt = name if kind == "format" else None
    return png(draw(*changes, spec=spec, theme=theme, format=fmt), 50)


@pytest.mark.parametrize(
    ("kind", "name", "spec", "v"), CASES, ids=[f"{k}:{n}:{v.change.path}" for k, n, _, v in CASES]
)
def test_changing_a_parameter_changes_the_drawing(kind, name, spec, v):
    key = repr((kind, name, v.base))
    if key not in _BEFORE:
        _BEFORE[key] = _drawn(kind, name, spec, *([v.base] if v.base else []))
    after = _drawn(kind, name, spec, *([v.base] if v.base else []), *v.changes)
    assert _BEFORE[key] != after, (
        f"{v.change.path}: changing it to {v.change.value!r} changed nothing"
    )
