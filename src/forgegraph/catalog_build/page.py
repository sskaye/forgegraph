"""The catalog page: one self-contained HTML file (architecture D6).

Tabs for each kind of specification, then for each of its files. Each file's panel has its
parameter table, in categories and subcategories that open and close (closed at first, but
open where a comment is), and its cards: the baseline graph, then the baseline with one
variable parameter changed. Every panel, table row and card has a stable id, so comments on
the page can be re-attached after a rebuild. The page holds no timestamps: the same inputs
give the same bytes.
"""

from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass, field

CSS_DPI = 96  # a CSS inch: images are shown at the figure's real size


@dataclass(frozen=True)
class Row:
    """A parameter's table row."""

    path: str
    default: str
    allowed: str
    status: str  # fixed, variable or required
    description: str


@dataclass(frozen=True)
class Card:
    id: str
    heading: str
    png: bytes
    width: int  # shown width, CSS pixels


@dataclass(frozen=True)
class Instance:
    """One specification file's panel."""

    id: str
    name: str
    heading: str  # e.g. "Theme > default"
    rows: tuple[Row, ...]
    cards: tuple[Card, ...]


@dataclass(frozen=True)
class Kind:
    id: str
    title: str  # e.g. "Themes"
    instances: tuple[Instance, ...]


STYLE = """
:root { --fg:#1f2328; --muted:#57606a; --line:#d0d7de; --soft:#f6f8fa; --bg:#fff;
        --accent:#0969da; }
body { font-family:-apple-system,"Segoe UI",system-ui,sans-serif; color:var(--fg);
       background:var(--bg); margin:0; padding:1.5rem 24px 3rem; line-height:1.5; }
body > input { position:absolute; opacity:0; pointer-events:none; }
.bar { position:sticky; top:0; z-index:10; background:var(--bg);
       border-bottom:1px solid var(--line); margin:0 -24px; padding:.2rem 24px .1rem; }
.bar h1 { margin:.4rem 0 .6rem; }
.bar .version { margin:-.5rem 0 .6rem; color:var(--muted); font-size:.9rem; }
.tabs label { display:inline-block; padding:.4rem 1rem; margin:0 .25rem .5rem 0;
              border:1px solid var(--line); border-radius:6px; cursor:pointer; }
.files, .panel { display:none; }
[id] { scroll-margin-top:11rem; }  /* a jump to a comment lands below the header */
h2 { margin:.8rem 0 .2rem; }
table { border-collapse:collapse; width:100%; font-size:.9rem; }
th, td { border-bottom:1px solid var(--line); padding:.35rem .5rem; text-align:left;
         vertical-align:top; }
table.params { table-layout:fixed; }
table.params col.path { width:25%; } table.params col.default { width:14%; }
table.params td { overflow-wrap:anywhere; }
table.params col.allowed { width:20%; } table.params col.status { width:7%; }
details.category > summary { background:var(--soft); border-bottom:1px solid var(--line);
  padding:.35rem .5rem; font-family:ui-monospace,Menlo,monospace; font-weight:600;
  cursor:pointer; }
details.category details.category > summary { font-weight:500; }
td.path { font-family:ui-monospace,Menlo,monospace; overflow-wrap:anywhere; }
.grid { display:grid; gap:1.4rem; margin-top:1.5rem;
        grid-template-columns:repeat(auto-fill, minmax(min(100%, 600px), 1fr)); }
.card { border:1px solid var(--line); border-radius:6px; padding:.6rem 1rem 1rem; }
.card h4 { margin:.3rem 0 .6rem; font-family:ui-monospace,Menlo,monospace; font-size:.95rem; }
figure { margin:0; } figure img { max-width:100%; height:auto; }
"""


def _e(text: str) -> str:
    return html.escape(text, quote=True)


COLUMNS = ("path", "default", "allowed", "status", "description")


@dataclass
class _Node:
    """A category: its rows and subcategories, in order of first appearance."""

    path: str
    items: list[Row | _Node] = field(default_factory=list)


def _tree(rows: tuple[Row, ...]) -> _Node:
    root = _Node("")
    nodes = {"": root}
    for r in rows:
        parts = r.path.split(".")
        for depth in range(1, len(parts)):
            path = ".".join(parts[:depth])
            if path not in nodes:
                nodes[path] = _Node(path)
                nodes[".".join(parts[: depth - 1])].items.append(nodes[path])
        nodes[".".join(parts[:-1])].items.append(r)
    return root


INDENT, STEP, MARKER = 0.5, 1.25, 1.1  # rem: the first level's, each deeper one's, a ▸'s


def _indent(depth: int) -> str:
    """The left padding of a category's summary at depth (1 for a top category): each level
    STEP further in."""
    return f"padding-left:{INDENT + (depth - 1) * STEP:g}rem"


def _rows_table(inst: Instance, rows: list[Row], depth: int) -> str:
    cols = "".join(f'<col class="{c}">' for c in COLUMNS)
    body = "\n".join(_row(inst, r, depth) for r in rows)
    return f'<table class="params"><colgroup>{cols}</colgroup>\n{body}\n</table>'


def _category(inst: Instance, node: _Node) -> str:
    """A category's rows and subcategories; one that isn't the root opens and closes. Each
    is named by its own part of the path, indented by its depth."""
    depth = len(node.path.split(".")) if node.path else 0
    out, rows = [], []
    for item in node.items:
        if isinstance(item, Row):
            rows.append(item)
            continue
        if rows:
            out.append(_rows_table(inst, rows, depth))
            rows = []
        out.append(_category(inst, item))
    if rows:
        out.append(_rows_table(inst, rows, depth))
    inner = "\n".join(out)
    if not node.path:
        return inner
    cid = f"{inst.id}-category-{node.path.replace('.', '-')}"
    name = node.path.split(".")[-1]
    return (
        f'<details class="category" id="{cid}"><summary style="{_indent(depth)}" '
        f'title="{_e(node.path)}">{_e(name)}</summary>\n{inner}\n</details>'
    )


def _table(inst: Instance) -> str:
    cols = "".join(f'<col class="{c}">' for c in COLUMNS)
    head = (
        f'<table class="params"><colgroup>{cols}</colgroup>\n'
        "<tr><th>Parameter</th><th>Default</th><th>Allowed values</th><th>Status</th>"
        "<th>Description</th></tr>\n</table>"
    )
    return f'<div id="{inst.id}-params">\n{head}\n{_category(inst, _tree(inst.rows))}\n</div>'


def open_commented(page_: str) -> str:
    """The page with every category that holds a Forgemark comment marker open, so each
    comment shows where it's anchored."""
    tokens = re.finditer(r"<details class=\"category\"|</details>|<!-- fmc:\d+ -->", page_)
    stack: list[int] = []
    opened: set[int] = set()
    for t in tokens:
        if t.group().startswith("<details"):
            stack.append(t.end())
        elif t.group() == "</details>":
            stack.pop()
        else:
            opened.update(stack)
    for at in sorted(opened, reverse=True):
        if not page_.startswith(" open", at):
            page_ = page_[:at] + " open" + page_[at:]
    return page_


def _row(inst: Instance, r: Row, depth: int) -> str:
    """A parameter's row, named by its last part, lined up with its category's name."""
    cells = (r.default, r.allowed, r.status, r.description)
    pad = INDENT + (depth - 1) * STEP + MARKER if depth else INDENT
    return (
        f'<tr id="{inst.id}-param-{r.path.replace(".", "-")}">'
        f'<td class="path" style="padding-left:{pad:g}rem" title="{_e(r.path)}">'
        f"{_e(r.path.split('.')[-1])}</td>" + "".join(f"<td>{_e(c)}</td>" for c in cells) + "</tr>"
    )


def _card(card: Card) -> str:
    data = base64.b64encode(card.png).decode()
    return (
        f'<section class="card" id="{card.id}">\n<h4>{_e(card.heading)}</h4>\n'
        f'<figure id="{card.id}-figure"><img alt="{_e(card.heading)}" width="{card.width}" '
        f'src="data:image/png;base64,{data}"></figure>\n</section>'
    )


_FIGURE = re.compile(r'<figure id="([^"]+)"><img [^>]*src="data:image/png;base64,([^"]+)"')


def figures(page_text: str) -> dict[str, bytes]:
    """A catalog page's card images, as _card writes them, by their figure's id."""
    return {fid: base64.b64decode(data) for fid, data in _FIGURE.findall(page_text)}


def _instance(inst: Instance) -> str:
    cards = "\n".join(_card(c) for c in inst.cards)
    return (
        f'<section class="panel" id="{inst.id}">\n'
        f'<h2 id="{inst.id}-heading">{_e(inst.heading)}</h2>\n'
        f'<h3 id="{inst.id}-parameters">Parameters</h3>\n{_table(inst)}\n'
        f'<div class="grid" id="{inst.id}-cards">\n{cards}\n</div>\n</section>'
    )


def _switch(group: str, id_: str, checked: bool) -> str:
    return f'<input type="radio" name="{group}" id="tab-{id_}"{" checked" if checked else ""}>'


def _labels(id_: str, cls: str, items: list[tuple[str, str]]) -> str:
    labels = "".join(f'<label for="tab-{i}">{_e(label)}</label>' for i, label in items)
    return f'<div class="{cls}" id="{id_}">\n{labels}\n</div>'


def page(
    kinds: list[Kind], inputs: str, title: str = "ForgeGraph Catalog", version: str = ""
) -> str:
    """The catalog page. `inputs` is the hash of what it was built from.

    Every tab is a radio button at the top of the body, so one CSS rule per tab can show
    its label as chosen, its row of file tabs (in the header, which stays in place while
    the page scrolls) and its panel."""
    switches = [_switch("kinds", k.id, n == 0) for n, k in enumerate(kinds)]
    switches += [
        _switch(f"{k.id}-files", i.id, n == 0) for k in kinds for n, i in enumerate(k.instances)
    ]
    rows = [_labels("kinds", "tabs", [(k.id, k.title) for k in kinds])]
    rows += [
        _labels(f"{k.id}-files", "tabs files", [(i.id, i.name) for i in k.instances]) for k in kinds
    ]
    rules = []
    for k in kinds:
        chosen = f"#tab-{k.id}:checked"
        rules.append(f"{chosen} ~ .bar #{k.id}-files, {chosen} ~ #{k.id} {{ display:block; }}")
        for i in k.instances:
            rules.append(f"#tab-{i.id}:checked ~ #{k.id} #{i.id} {{ display:block; }}")
    chosen_label = ", ".join(
        f"#tab-{x}:checked ~ .bar label[for=tab-{x}]"
        for x in [k.id for k in kinds] + [i.id for k in kinds for i in k.instances]
    )
    rules.append(
        f"{chosen_label} {{ background:var(--accent); border-color:var(--accent); color:#fff; }}"
    )
    panels = "\n".join(
        f'<section class="panel" id="{k.id}">\n'
        + "\n".join(_instance(i) for i in k.instances)
        + "\n</section>"
        for k in kinds
    )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="forgegraph-inputs" content="{inputs}">\n'
        f"<title>{_e(title)}</title>\n<style>{STYLE}{chr(10).join(rules)}\n</style></head><body>\n"
        + "\n".join(switches)
        + f'\n<header class="bar">\n<h1 id="title">{_e(title)}</h1>\n'
        + (f'<p id="version" class="version">version {_e(version)}</p>\n' if version else "")
        + "\n".join(rows)
        + f"\n</header>\n{panels}\n</body></html>\n"
    )
