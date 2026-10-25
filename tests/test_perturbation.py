"""Every parameter changes the drawing (architecture §7).

Every parameter's card in every catalog (catalogs/, and the built-in packs' themes and
formats), fixed parameters' included, is placed, drawn, and must differ from the baseline
it starts from. The catalog build places the variable parameters' cards the same way; this
test also covers those the page doesn't show, and names a card that draws the same.
"""

from __future__ import annotations

import pytest

from forgegraph.catalog_build.cards import DENSITY, Change, Drawings, place
from forgegraph.catalog_build.examples import draw, png
from forgegraph.catalog_build.files import Catalog, read
from forgegraph.catalog_build.page import CSS_DPI
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
    return png(graph, CSS_DPI * DENSITY)  # at the resolution of the page's cards


@pytest.mark.parametrize(("kind", "name"), FILES, ids=[f"{k}:{n}" for k, n in FILES])
def test_changing_a_parameter_changes_the_drawing(kind, name):
    reg = builtin()
    catalog = read(kind, name, reg)
    theme = name if kind == "theme" else None
    fmt = name if kind == "format" else None
    drawings = Drawings(catalog, reg, theme, fmt)
    before: dict[str, bytes] = {}  # each start's drawing
    for card in place(catalog, drawings.differs, every=True):
        if card.start is None or card.numbered:
            continue
        key = repr(card.start)
        if key not in before:
            before[key] = _drawn(catalog, *card.start)
        assert before[key] != _drawn(catalog, *card.changes), (
            f"{card.heading}: draws the same as the card it starts from"
        )
