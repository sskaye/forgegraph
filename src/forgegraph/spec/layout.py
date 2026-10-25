"""A layout's tabs, their grids and tiles (architecture D11).

A layout lists its tabs by name, in order. Each tab is a grid: grid.areas has a list per row
naming the tile in each cell, `.` for a blank cell, and a name repeated over a rectangle of
cells makes that tile span them. grid.column_widths and grid.row_heights are the relative
sizes of the columns' and rows' plot boxes, and tiles names the GraphSpec file drawn in each
area. The nearest file in a layout's extends chain that lists tabs decides all of them: a
layout's tabs replace those it inherits, unless one of those lists them as fixed.

Every rule here is an error naming where it is; nothing is filled in or guessed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from forgegraph.spec.parameters import NONE, SECTIONS, check_parameter, tab_definitions
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import chain, resolve

BLANK = "."
TAB_KEYS = ("grid", "tiles")


@dataclass(frozen=True)
class Area:
    """Where a tile sits: its first row and column, and how many of each it spans."""

    row: int
    column: int
    rows: int = 1
    columns: int = 1

    @property
    def last_row(self) -> int:
        return self.row + self.rows - 1

    @property
    def last_column(self) -> int:
        return self.column + self.columns - 1


@dataclass(frozen=True)
class Tab:
    name: str
    areas: list[list[str]]
    tiles: dict[str, Any]  # tile name -> GraphSpec file, as written (None: unset)
    column_widths: list[float] | None
    row_heights: list[float] | None

    @property
    def rows(self) -> int:
        return len(self.areas)

    @property
    def columns(self) -> int:
        return len(self.areas[0])

    @property
    def slug(self) -> str:
        return slug(self.name)

    def places(self) -> dict[str, Area]:
        """Each tile's area, in reading order of its top-left cell."""
        found, problems = _places(self.areas)
        assert not problems, problems
        return found


def slug(name: str) -> str:
    """A tab's name as it appears in file names and page links: lowercase, with spaces as
    hyphens and only letters, digits, hyphens and underscores."""
    folded = unicodedata.normalize("NFKC", name).strip().lower()
    folded = re.sub(r"\s+", "-", folded)
    return re.sub(r"[^\w-]", "", folded)


def _listed(d: dict[str, Any]) -> tuple[str, Any] | None:
    """(section, tabs) as a file lists them, or None if it lists none."""
    for section in SECTIONS:
        tree = d.get(section)
        if isinstance(tree, dict) and "tabs" in tree:
            return section, tree["tabs"]
    return None


def tabs_source(doc: dict[str, Any], reg: Registry) -> dict[str, Any]:
    """The file in a layout's extends chain whose tabs it ends up with: the nearest listing
    any."""
    found = chain("layout", doc, reg)
    return next((d for d in found if _listed(d) is not None), found[-1])


def resolve_tabs(doc: dict[str, Any], reg: Registry) -> tuple[dict[str, Any], str]:
    """The tabs a layout ends up with, as listed, and which file lists them."""
    source = tabs_source(doc, reg)
    listed = _listed(source)
    return (listed[1], f"layout '{source.get('name')}'") if listed else ({}, "")


def tabs(doc: dict[str, Any], reg: Registry) -> list[Tab]:
    """A valid layout's tabs, in order."""
    grid, _ = tab_definitions()
    out = []
    for name, entry in resolve_tabs(doc, reg)[0].items():
        g = entry["grid"]
        widths = g.get("column_widths", grid["grid.column_widths"].default)
        heights = g.get("row_heights", grid["grid.row_heights"].default)
        out.append(
            Tab(
                str(name),
                [[str(c) for c in row] for row in g["areas"]],
                {str(k): v for k, v in entry["tiles"].items()},
                None if widths in (None, NONE) else [float(w) for w in widths],
                None if heights in (None, NONE) else [float(h) for h in heights],
            )
        )
    return out


def _places(areas: list[list[str]]) -> tuple[dict[str, Area], list[str]]:
    """Each name's area, and what's wrong with the grid's shape."""
    problems: list[str] = []
    if len({len(row) for row in areas}) > 1:
        lengths = ", ".join(str(len(row)) for row in areas)
        return {}, [f"every row needs the same number of cells; they have {lengths}"]
    cells: dict[str, list[tuple[int, int]]] = {}
    for r, row in enumerate(areas):
        for c, name in enumerate(row):
            if name != BLANK:
                cells.setdefault(name, []).append((r, c))
    places = {}
    for name, where in cells.items():
        rows = [r for r, _ in where]
        cols = [c for _, c in where]
        area = Area(min(rows), min(cols), max(rows) - min(rows) + 1, max(cols) - min(cols) + 1)
        if len(where) != area.rows * area.columns or any(
            areas[r][c] != name
            for r in range(area.row, area.last_row + 1)
            for c in range(area.column, area.last_column + 1)
        ):
            problems.append(f"'{name}' must fill a rectangle of cells to span them")
            continue
        places[name] = area
    for r, row in enumerate(areas):
        if all(name == BLANK for name in row):
            problems.append(f"row {r + 1} is all blank")
    for c in range(len(areas[0]) if areas else 0):
        if all(row[c] == BLANK for row in areas):
            problems.append(f"column {c + 1} is all blank")
    order = sorted(places.items(), key=lambda item: (item[1].row, item[1].column))
    return dict(order), problems


def layout_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems with a layout's tabs, and with the tabs it ends up with."""
    errors: list[str] = []
    listed = _listed(doc)
    for d in chain("layout", doc, reg)[1:]:
        inherited = _listed(d)
        if listed is not None and inherited is not None and inherited[0] == SECTIONS[0]:
            errors.append(f"{listed[0]}.tabs: fixed by layout '{d.get('name')}'")
            return errors
        if inherited is not None:
            break
    if listed is None:
        return errors
    section, entries = listed
    where = f"{section}.tabs"
    if not isinstance(entries, dict) or not entries:
        return [f"{where}: must be one or more tabs, each under its name"]
    grid_defs, tile_def = tab_definitions()
    names: dict[str, str] = {}  # tile name -> the tab it's in
    slugs: dict[str, str] = {}
    for tab_name, entry in entries.items():
        at = f"{where}.{tab_name}"
        tab_slug = slug(str(tab_name))
        if not tab_slug:
            errors.append(f"{at}: a tab's name needs a letter or digit, for file names and links")
        elif tab_slug in slugs:
            errors.append(
                f"{at}: gives the same file names and links as tab '{slugs[tab_slug]}' "
                f"({tab_slug}); rename one"
            )
        else:
            slugs[tab_slug] = str(tab_name)
        before = len(errors)  # the tab's own problems, after its name's
        if not isinstance(entry, dict):
            errors.append(f"{at}: must be a tab: its grid and tiles")
            continue
        errors += [
            f"{at}.{k}: unknown; a tab has only {', '.join(TAB_KEYS)}"
            for k in entry
            if k not in TAB_KEYS
        ]
        grid, tiles = entry.get("grid"), entry.get("tiles")
        if not isinstance(grid, dict):
            errors.append(f"{at}.grid: required: the grid's areas, and optionally its sizes")
            continue
        for key, value in grid.items():
            p = grid_defs.get(f"grid.{key}")
            if p is None:
                known = ", ".join(k.split(".")[1] for k in grid_defs)
                errors.append(f"{at}.grid.{key}: unknown; a grid has only {known}")
                continue
            errors += [f"{at}.grid.{key}{s}: {m}" for s, m in check_parameter(p, value)]
        if "areas" not in grid:
            errors.append(f"{at}.grid.areas: required: a list of tiles per row")
        if not isinstance(tiles, dict) or not tiles:
            errors.append(f"{at}.tiles: required: the GraphSpec file drawn in each area")
            continue
        for tile, file in tiles.items():  # None: unset, see drawing_problems
            errors += [f"{at}.tiles.{tile}{s}: {m}" for s, m in check_parameter(tile_def, file)]
        if len(errors) > before:
            continue
        areas = [[str(c) for c in row] for row in grid["areas"]]
        places, problems = _places(areas)
        errors += [f"{at}.grid.areas: {p}" for p in problems]
        in_grid = {name for row in areas for name in row if name != BLANK}
        listed_tiles = {str(t) for t in tiles}
        errors += [
            f"{at}.tiles: no tile for '{n}', which grid.areas names"
            for n in sorted(in_grid - listed_tiles)
        ]
        errors += [
            f"{at}.tiles.{t}: not in grid.areas; add it there or remove it"
            for t in sorted(listed_tiles - in_grid)
        ]
        for n in places:
            if n in names:
                errors.append(f"{at}.tiles.{n}: also a tile in tab '{names[n]}'; names are unique")
            names[n] = str(tab_name)
        for key, count in (("column_widths", len(areas[0])), ("row_heights", len(areas))):
            sizes = grid.get(key)
            if isinstance(sizes, list) and len(sizes) != count:
                what = "column" if key == "column_widths" else "row"
                errors.append(
                    f"{at}.grid.{key}: {len(sizes)} sizes, but the grid has {count} "
                    f"{what}{'s' if count != 1 else ''}"
                )
    if not errors:
        errors += _sizes_problems(doc, reg, entries, where)
    return errors


def drawing_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """What a valid layout still lacks before it can be drawn: a GraphSpec file for each
    tile."""
    entries, _ = resolve_tabs(doc, reg)
    return [
        f"tabs.{name}.tiles.{tile}: must be set before the layout can be drawn: a GraphSpec file"
        for name, entry in entries.items()
        for tile, file in entry["tiles"].items()
        if file in (None, NONE)
    ]


def _sizes_problems(
    doc: dict[str, Any], reg: Registry, entries: dict[str, Any], where: str
) -> list[str]:
    """With the format's height (or width) auto, rows (columns) take the size their tiles
    need, so row_heights (column_widths) can't also be set."""
    chosen = resolve("layout", doc, reg).get("specifications.format", (None,))[0]
    fmt = reg.docs["format"].get(chosen) if chosen is not None else None
    if fmt is None:
        return []
    values = resolve("format", fmt, reg)
    errors = []
    for size, key in (("height", "row_heights"), ("width", "column_widths")):
        if values.get(f"figure.{size}", (None,))[0] != "auto":
            continue
        for tab_name, entry in entries.items():
            if entry["grid"].get(key) not in (None, NONE):
                errors.append(
                    f"{where}.{tab_name}.grid.{key}: format '{chosen}' has figure.{size} auto, "
                    f"so the tiles set each {'row' if key == 'row_heights' else 'column'}'s "
                    f"size; give the format a {size}, or remove {key}"
                )
    return errors
