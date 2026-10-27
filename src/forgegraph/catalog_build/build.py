"""`forgegraph catalog build`: the specification files -> a catalog page, keeping its comments.

The catalog shows ForgeGraph's graph types and layer types and the base pack's themes and
formats; a pack's catalog (`--pack`) shows that pack's themes and formats. A rebuild writes
a fresh page, carries the old page's Forgemark comment block over, puts
each comment back by its element's id or its text (`forgemark reattach --all`), then runs
`forgemark lint`. The page records a hash of its inputs; `current()` compares it.
"""

from __future__ import annotations

import hashlib
import re
from importlib.resources import files
from pathlib import Path

from forgegraph import __version__, forgemark
from forgegraph.catalog_build.cards import Drawings, place, show
from forgegraph.catalog_build.files import Catalog, read
from forgegraph.catalog_build.page import CSS_DPI, Card, Instance, Kind, Row, open_commented, page
from forgegraph.packs import Pack
from forgegraph.spec.parameters import BASE, NONE, Parameter, graph_type_files
from forgegraph.spec.registry import Registry, builtin
from forgegraph.spec.resolve import Values, resolve

# Package files that can't change what the catalog shows. Every other file counts, so a new
# module counts without being listed; built-in packs other than the base pack count only
# for their own catalog.
UNUSED = ("__main__.py", "canvas.py", "cli", "jobs", "layouts", "skill")
# Each kind of specification: its id, tab title and heading name.
KINDS = (
    ("theme", "Themes", "Theme"),
    ("format", "Formats", "Format"),
    ("graph_type", "GraphTypes", "GraphType"),
    ("layer", "Layers", "Layer"),
)
_INPUTS_META = re.compile(r'<meta name="forgegraph-inputs" content="([0-9a-f]+)">')


def inputs_hash(pack: Pack | None = None) -> str:
    """A hash of the library version, every package file the catalog can depend on and, for a
    pack's catalog, every file in the pack (its GraphSpecs' data included)."""
    digest = hashlib.sha256(__version__.encode())
    root = Path(str(files("forgegraph")))
    sources = [(root, "", _depends_on)]
    if pack is not None:
        sources.append((pack.folder, "pack/", lambda rel: True))
    for base, prefix, counts in sources:
        # in the same order everywhere: Windows sorts paths ignoring case
        for f in sorted(base.rglob("*"), key=lambda f: f.relative_to(base).as_posix()):
            rel = f.relative_to(base)
            hidden = any(part.startswith(".") for part in rel.parts)  # .git, .DS_Store
            if not f.is_file() or hidden or "__pycache__" in rel.parts or not counts(rel):
                continue
            data = f.read_bytes()
            if b"\0" not in data:  # text, of any kind: the same on a Windows checkout
                data = data.replace(b"\r\n", b"\n")
            digest.update((prefix + rel.as_posix()).encode() + b"\0" + data + b"\0")
    return digest.hexdigest()


def _depends_on(rel: Path) -> bool:
    """Whether the catalog can depend on this package file."""
    if rel.parts[0] in UNUSED:
        return False
    return not (rel.parts[0] == "packs" and len(rel.parts) > 2 and rel.parts[1] != BASE)


def recorded_hash(page_text: str) -> str | None:
    m = _INPUTS_META.search(page_text)
    return m.group(1) if m else None


def current(path: Path, pack: Pack | None = None) -> bool:
    """True if the catalog at path was built from the current inputs."""
    if not path.exists():
        return False
    return recorded_hash(path.read_text(encoding="utf-8")) == inputs_hash(pack)


# How the catalog's Allowed values column writes each type word; a list is in [].
TYPES = {
    "text": "text",
    "int ≥ 0": "int ≥ 0",
    "int > 0": "int > 0",
    "float": "float",
    "float ≥ 0": "float ≥ 0",
    "float > 0": "float > 0",
    "floats > 0": "[floats > 0]",
    "date": "date",
    "hex color": "hex color code",
    "hex colors": "[hex color codes]",
    "two hex colors": "[two hex color codes]",
    "column": "column",
    "columns": "column | [columns]",
    "graph type": "graph type name",
    "theme": "theme name",
    "format": "format name",
    "value format": "format",
    "graphspec": "GraphSpec name",
    "layer type": "layer type name",
    "layer types": "[layer type names]",
}


def allowed(p: Parameter) -> str:
    """A parameter's range as the catalog writes it: the alternatives separated by |, types
    and number ranges first and None last; a list in []."""
    rng = p.range
    parts = [TYPES[t] for t in rng.types]
    parts += [f"float, {show(i.low)}-{show(i.high)}" for i in rng.intervals]
    parts += sorted(rng.literals, key=lambda v: v == NONE)
    if not p.takes_list:
        return " | ".join(parts)
    items = " | ".join(x for x in parts if x != NONE)  # None stands for no list, not an item
    return f"[{items}]" + (f" | {NONE}" if NONE in rng.literals else "")


def _status(p: Parameter, fixed: bool) -> str:
    if p.required:
        return "required"
    return "fixed" if fixed else "variable"


def _own_values(kind: str, name: str, reg: Registry) -> Values:
    """The values a theme, format or graph type is drawn with, and whether each is fixed,
    by parameter: its own, not the definition's defaults (a pack's theme isn't the base's)."""
    if kind not in ("theme", "format", "graph_type"):
        return Values()
    return resolve(kind, reg.docs[kind][name], reg)


def instance(
    catalog: Catalog,
    heading: str,
    reg: Registry,
    theme: str | None = None,
    fmt: str | None = None,
) -> Instance:
    """One specification file's panel: its table, and its catalog's cards. A graph type's or
    layer type's cards are drawn in theme and fmt when given (a pack's), and placed in them;
    a card that can't be placed in them is placed as in ForgeGraph's catalog, and one that
    then can't be drawn in them, or draws the same as the card it starts from, says so on
    the card instead of stopping the page, since a pack can't change those cards."""
    kind, name = catalog.kind, catalog.name
    lenient = kind in ("graph_type", "layer") and (theme is not None or fmt is not None)
    theme = name if kind == "theme" else theme
    fmt = name if kind == "format" else fmt
    iid = f"{kind.replace('_', '')}-{name.replace('/', '-')}"
    drawings = Drawings(catalog, reg, theme, fmt, lenient)
    drawings.png()  # the baseline itself must draw
    own = _own_values(kind, name, reg)

    rows = tuple(
        Row(
            p.path,
            show(own.value(p.path, p.default)),
            allowed(p),
            _status(p, own.fixed(p.path, p.fixed)),
            p.description,
        )
        for p in catalog.parameters
    )
    fallback = Drawings(catalog, reg).differs if lenient else None
    cards = []
    for planned in place(catalog, drawings.differs, fallback):
        png_ = drawings.png(*planned.changes)
        heading_ = planned.heading
        checked = lenient and planned.start is not None and not planned.numbered
        if checked and png_ == drawings.png(*(planned.start or ())):
            heading_ += f" (draws the same as {planned.start_name} in this theme and format)"
        size = round(drawings.width(*planned.changes) * CSS_DPI)
        cards.append(Card(f"{iid}-{planned.id}", heading_, png_, size))
    return Instance(iid, name, heading, rows, tuple(cards))


def kinds(pack: Pack | None = None) -> list[Kind]:
    """A pack's themes and formats (the base pack's by default), and ForgeGraph's graph types
    and layer types, drawn in the pack's first theme and format, so a pack's catalog shows
    how each looks in it. Each with its cards."""
    reg = builtin()
    shown = BASE
    if pack is not None:
        reg.add_pack(pack)
        reg.allowed = frozenset({BASE, pack.name})
        shown = pack.name
    own = {
        k: sorted(n for n in reg.docs[k] if reg.pack_of(k, n) == shown) for k in ("theme", "format")
    }
    theme = own["theme"][0] if pack is not None and own["theme"] else None
    fmt = own["format"][0] if pack is not None and own["format"] else None
    out = []
    for kind, title, heading in KINDS:
        if kind == "graph_type":
            names = list(graph_type_files())
        elif kind == "layer":
            names = sorted(reg.docs["layer"])
        else:
            names = own[kind]
        if not names:
            continue
        instances = tuple(
            instance(read(kind, n, reg), f"{heading} > {n}", reg, theme, fmt) for n in names
        )
        out.append(Kind(kind.replace("_", ""), title, instances))
    return out


def html(pack: Pack | None = None) -> str:
    """The catalog page, without comments."""
    title = f"{BASE if pack is None else pack.name} Catalog"
    version = __version__ if pack is None else pack.version
    return page(kinds(pack), inputs_hash(pack), title, version)


def build(path: Path, pack: Pack | None = None) -> str:
    """Build the catalog at path: ForgeGraph's, or a pack's. Returns Forgemark's lint report
    ("" with no comments)."""
    return forgemark.rewrite(path, html(pack), reopen=open_commented)
