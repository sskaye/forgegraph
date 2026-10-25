"""`forgegraph catalog build`: the specification files -> a catalog page, keeping its comments.

The catalog shows ForgeGraph's graph types and layer types and the base pack's themes and
formats; a pack's catalog (`--pack`) shows that pack's themes and formats. A rebuild writes
a fresh page, carries the old page's Forgemark comment block over, puts
each comment back by its element's id or its text (`forgemark reattach --all`), then runs
`forgemark lint`. The page records a hash of its inputs; `current()` compares it.
"""

from __future__ import annotations

import hashlib
import io
import re
from importlib.resources import files
from pathlib import Path
from typing import Any

from PIL import Image

from forgegraph import __version__
from forgegraph.catalog_build import forgemark
from forgegraph.catalog_build.examples import NONSTANDARD, Change, draw, image
from forgegraph.catalog_build.files import CatalogError, read
from forgegraph.catalog_build.page import CSS_DPI, Card, Instance, Kind, Row, open_commented, page
from forgegraph.graph import Graph, SpecError
from forgegraph.packs import Pack
from forgegraph.spec.documents import Registry, builtin, resolve
from forgegraph.spec.parameters import BASE, NONE, Parameter, graph_type_files

COMMENTS = "<!-- forgemark-comments"
DENSITY = 1.5  # image pixels per CSS pixel: sharp on most screens, small enough to commit
COLORS = 64  # palette size: plenty for a graph's few colors and their anti-aliasing
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


def _png(graph: Graph) -> bytes:
    raw = image(graph, CSS_DPI * DENSITY).convert("RGB")
    small = raw.quantize(COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    buffer = io.BytesIO()
    small.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def _message_png(text: str, width_in: float) -> bytes:
    """A card that can't be drawn: the problem, in place of its graph."""
    import textwrap

    from matplotlib.figure import Figure

    fig = Figure(figsize=(width_in, width_in * 0.6), dpi=CSS_DPI)
    fig.text(0.05, 0.9, "\n".join(textwrap.wrap(text, 60)), va="top", fontsize=9, color="#57606a")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor="#f6f8fa")
    return buffer.getvalue()


def show(value: Any) -> str:
    """A parameter value as the specification files write it."""
    if isinstance(value, list):
        return "[" + ", ".join(show(v) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return NONE
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("\n", "\\n")  # a line break, as YAML writes it in quotes


# How the catalog's Allowed values column writes each type word; a list is in [].
TYPES = {
    "text": "text",
    "int": "int ≥ 0",
    "positive int": "int > 0",
    "float": "float",
    "positive float": "float > 0",
    "hex color": "hex color code",
    "hex colors": "[hex color codes]",
    "two hex colors": "[two hex color codes]",
    "column": "column",
    "columns": "column | [columns]",
    "graph type": "graph type name",
    "theme": "theme name",
    "format": "format name",
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


def _own_values(kind: str, name: str, reg: Registry) -> dict[str, tuple[Any, bool]]:
    """The values a theme, format or graph type is drawn with, and whether each is fixed,
    by parameter: its own, not the definition's defaults (a pack's theme isn't the base's)."""
    if kind not in ("theme", "format", "graph_type"):
        return {}
    return resolve(kind, reg.docs[kind][name], reg)


def _change(c: Change) -> str:
    if c.parts:
        return ", ".join(_change(p) for p in c.parts)
    return "non-standard drawing" if c.path == NONSTANDARD else f"{c.path} = {show(c.value)}"


def _id(change: Change) -> str:
    return change.path.replace(".", "-")


def instance(
    kind: str,
    name: str,
    heading: str,
    reg: Registry,
    theme: str | None = None,
    fmt: str | None = None,
) -> Instance:
    """One specification file's panel: its table, and the cards its catalog file lists. A
    graph type's or layer type's cards are drawn in theme and fmt when given (a pack's); one
    that can't be drawn in them, or draws the same as the card it starts from, says so on the
    card instead of stopping the page, since a pack can't change those cards."""
    catalog = read(kind, name, reg)
    lenient = kind in ("graph_type", "layer") and (theme is not None or fmt is not None)
    theme = name if kind == "theme" else theme
    fmt = name if kind == "format" else fmt
    iid = f"{kind.replace('_', '')}-{name.replace('/', '-')}"
    images: dict[str, bytes] = {}  # each drawing, by its changes

    def drawn(*changes: Change) -> tuple[Graph | None, bytes]:
        key = " + ".join(_change(c) for c in changes)
        try:
            graph = draw(
                *catalog.always, *changes, spec=catalog.baseline, theme=theme, format=fmt, reg=reg
            )
        except SpecError as e:
            card_ = " + ".join(["Baseline", *(_change(c) for c in changes)])
            if lenient and changes:
                width = baseline.figure.get_size_inches()[0]
                images[key] = _message_png(
                    f"Can't be drawn in this theme and format: {e.problems[0]}", width
                )
                return None, images[key]
            raise CatalogError(
                [f"{kind.replace('_', ' ')} {name}: {card_}: {p}" for p in e.problems]
            ) from None
        images[key] = _png(graph)
        return graph, images[key]

    first_drawn, image = drawn()
    assert first_drawn is not None  # the baseline itself must draw
    baseline: Graph = first_drawn
    own = _own_values(kind, name, reg)

    def value(p: Parameter) -> tuple[Any, bool]:
        return own.get(p.path, (p.default, p.fixed))

    rows = tuple(
        Row(
            p.path,
            show(value(p)[0]),
            allowed(p),
            _status(p, value(p)[1]),
            p.description,
        )
        for p, _ in catalog.variations
    )

    def card(cid: str, heading: str, graph: Graph | None, png_: bytes) -> Card:
        size = round((graph or baseline).figure.get_size_inches()[0] * CSS_DPI)
        return Card(f"{iid}-{cid}", heading, png_, size)

    first = "Baseline"
    if catalog.always:  # a layer's catalog: say what every card adds to the GraphSpec
        first = " + ".join([f"Baseline: {catalog.baseline}", *(_change(c) for c in catalog.always)])
    cards = [card("baseline", first, baseline, image)]
    # Only a variable parameter's card is shown; every card is still drawn by the
    # perturbation test.
    variations = [v for p, v in catalog.variations if v is not None and not value(p)[1]]
    numbers: dict[str, int] = {}  # each numbered baseline's number, by the change that makes it
    problems = []
    for v in variations:
        single = len(v.changes) == 1
        if single and _change(v.change) in numbers:
            continue  # already shown, as a numbered baseline
        if v.base is not None and _change(v.base) not in numbers:
            numbers[_change(v.base)] = len(numbers) + 2
            heading_ = f"Baseline {numbers[_change(v.base)]}: Baseline + {_change(v.base)}"
            cards.append(card(f"baseline-{_id(v.base)}", heading_, *drawn(v.base)))
        if single and v.base is None and any(w.base == v.change for w in variations):
            numbers[_change(v.change)] = len(numbers) + 2
            heading_ = f"Baseline {numbers[_change(v.change)]}: Baseline + {_change(v.change)}"
            cards.append(card(f"baseline-{_id(v.change)}", heading_, *drawn(v.change)))
            continue
        start = "Baseline" if v.base is None else f"Baseline {numbers[_change(v.base)]}"
        changes = v.changes if v.base is None else (v.base, *v.changes)
        graph, png_ = drawn(*changes)
        before = images["" if v.base is None else _change(v.base)]
        heading_ = " + ".join([start, *(_change(c) for c in v.changes)])
        if png_ == before and lenient:
            heading_ += f" (draws the same as {start} in this theme and format)"
        elif png_ == before:
            problems.append(
                f"{kind.replace('_', ' ')} {name}: {heading_} draws the same as {start}"
            )
        cards.append(card(f"card-{_id(v.change)}", heading_, graph, png_))
    if problems:
        raise CatalogError(problems)
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
        instances = tuple(instance(kind, n, f"{heading} > {n}", reg, theme, fmt) for n in names)
        out.append(Kind(kind.replace("_", ""), title, instances))
    return out


def html(pack: Pack | None = None) -> str:
    """The catalog page, without comments."""
    title = f"{BASE if pack is None else pack.name} Catalog"
    version = __version__ if pack is None else pack.version
    return page(kinds(pack), inputs_hash(pack), title, version)


def keep_comments(new: str, old: str) -> str:
    """The new page with the old page's Forgemark comment block carried over."""
    if COMMENTS not in old:
        return new
    return new.rstrip("\n") + "\n\n" + old[old.index(COMMENTS) :]


def write(path: Path, text: str) -> str:
    """Write a rebuilt page, keeping the comments the old one had. Returns Forgemark's lint
    report, or "" when the page has no comments."""
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if COMMENTS in old:
        forgemark.ready()  # fail before writing if the comments couldn't be put back
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(keep_comments(text, old), encoding="utf-8", newline="\n")
    if COMMENTS not in old:
        return ""
    forgemark.run("reattach", str(path), "--all", check=False)
    path.write_text(
        open_commented(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n"
    )
    lint = forgemark.run("lint", str(path), check=False)
    return (lint.stdout + lint.stderr).strip()


def build(path: Path, pack: Pack | None = None) -> str:
    """Build the catalog at path: ForgeGraph's, or a pack's. Returns Forgemark's lint report
    ("" with no comments)."""
    return write(path, html(pack))
