"""Every parameter changes the drawing (architecture §7).

Every catalog's cards (catalogs/, and the built-in packs' themes and formats) are placed,
each drawn, and each must differ from the baseline it starts from. The catalog build places
them the same way; this test names a card that draws the same sooner.
"""

from __future__ import annotations

import pytest

from forgegraph.catalog_build.cards import Change, Drawings, place
from forgegraph.catalog_build.examples import draw, png
from forgegraph.catalog_build.files import Catalog, read
from forgegraph.spec.parameters import graph_type_files
from forgegraph.spec.registry import builtin

pytestmark = pytest.mark.slow  # the full suite only (pytest --full)

FILES = [("theme", n) for n in sorted(builtin().docs["theme"])]
FILES += [("format", n) for n in sorted(builtin().docs["format"])]
FILES += [("graph_type", n) for n in graph_type_files()]
FILES += [("layer", n) for n in sorted(builtin().docs["layer"])]


def _drawn(catalog: Catalog, *changes: Change) -> bytes:
    theme = catalog.name if catalog.kind == "theme" else None
    fmt = catalog.name if catalog.kind == "format" else None
    graph = draw(*catalog.always, *changes, spec=catalog.baseline, theme=theme, format=fmt)
    return png(graph, 50)


@pytest.mark.parametrize(("kind", "name"), FILES, ids=[f"{k}:{n}" for k, n in FILES])
def test_changing_a_parameter_changes_the_drawing(kind, name):
    reg = builtin()
    catalog = read(kind, name, reg)
    theme = name if kind == "theme" else None
    fmt = name if kind == "format" else None
    drawings = Drawings(catalog, reg, theme, fmt)
    for card in place(catalog, drawings.differs):
        if card.start is None or card.numbered:
            continue
        assert _drawn(catalog, *card.start) != _drawn(catalog, *card.changes), (
            f"{card.heading}: draws the same as the card it starts from"
        )
