"""Every parameter changes the drawing (architecture §7).

Every parameter's card in every catalog (catalogs/, and the built-in packs' themes and
formats), fixed parameters' included, is placed by card(), as the catalog build places the
variable parameters' cards, then drawn, and must differ from the baseline it starts from.
Each parameter is its own case, so they run in parallel.
"""

from __future__ import annotations

import pytest

from forgegraph.catalog_build.cards import DENSITY, Change, Drawings, card
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
CASES = [(k, n, p.path) for k, n in FILES for p, _ in read(k, n, builtin()).cards]
_DRAWINGS: dict[tuple[str, str], tuple[Catalog, Drawings]] = {}  # this worker's, by catalog
_BEFORE: dict[str, bytes] = {}  # each start's drawing


def _drawings(kind: str, name: str) -> tuple[Catalog, Drawings]:
    if (kind, name) not in _DRAWINGS:
        reg = builtin()
        catalog = read(kind, name, reg)
        theme = name if kind == "theme" else None
        fmt = name if kind == "format" else None
        _DRAWINGS[kind, name] = catalog, Drawings(catalog, reg, theme, fmt)
    return _DRAWINGS[kind, name]


def _drawn(catalog: Catalog, *changes: Change) -> bytes:
    theme = catalog.name if catalog.kind == "theme" else None
    fmt = catalog.name if catalog.kind == "format" else None
    graph = draw(*catalog.always, *changes, spec=catalog.baseline, theme=theme, format=fmt)
    return png(graph, CSS_DPI * DENSITY)  # at the resolution of the page's cards


@pytest.mark.parametrize(("kind", "name", "path"), CASES, ids=[f"{k}:{n}:{p}" for k, n, p in CASES])
def test_changing_a_parameter_changes_the_drawing(kind, name, path):
    catalog, drawings = _drawings(kind, name)
    placed = card(catalog, path, drawings.differs)
    start = () if placed.base is None else (placed.base,)
    key = repr((kind, name, start))
    if key not in _BEFORE:
        _BEFORE[key] = _drawn(catalog, *start)
    assert _BEFORE[key] != _drawn(catalog, *start, *placed.changes), (
        f"{path} = {placed.change.value}: draws the same as the baseline it starts from"
    )
