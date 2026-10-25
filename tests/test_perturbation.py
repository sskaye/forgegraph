"""Every parameter changes the drawing (architecture §7).

Every card in ForgeGraph's catalog files (catalogs/) is drawn, and must differ from the
baseline it starts from. The catalog build refuses such a card too; this test finds one
sooner, and names it.
"""

from __future__ import annotations

import pytest

from forgegraph.catalog_build.cards import Change, place
from forgegraph.catalog_build.examples import draw, png
from forgegraph.catalog_build.files import Catalog, read
from forgegraph.spec.parameters import graph_type_files
from forgegraph.spec.registry import builtin

pytestmark = pytest.mark.slow  # the full suite only (pytest --full)

FILES = [("theme", n) for n in sorted(builtin().docs["theme"])]
FILES += [("format", n) for n in sorted(builtin().docs["format"])]
FILES += [("graph_type", n) for n in graph_type_files()]
CASES = [
    (catalog, card)
    for kind, name in FILES
    for catalog in [read(kind, name, builtin())]
    for card in place(catalog, [p.path for p, _ in catalog.variations])
    if card.start is not None
]
_BEFORE: dict[str, bytes] = {}  # each start's drawing


def _drawn(catalog: Catalog, *changes: Change) -> bytes:
    theme = catalog.name if catalog.kind == "theme" else None
    fmt = catalog.name if catalog.kind == "format" else None
    graph = draw(*catalog.always, *changes, spec=catalog.baseline, theme=theme, format=fmt)
    return png(graph, 50)


@pytest.mark.parametrize(
    ("catalog", "card"), CASES, ids=[f"{c.kind}:{c.name}:{card.id}" for c, card in CASES]
)
def test_changing_a_parameter_changes_the_drawing(catalog, card):
    assert card.start is not None
    key = repr((catalog.kind, catalog.name, card.start))
    if key not in _BEFORE:
        _BEFORE[key] = _drawn(catalog, *card.start)
    assert _BEFORE[key] != _drawn(catalog, *card.changes), (
        f"{card.heading}: draws the same as the card it starts from"
    )
