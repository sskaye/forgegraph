"""Markdown mirrors of the specification files, for review in Forgemark.

A mirror shows its YAML file as plain Markdown text rather than a code block, so every line
can be commented on. It's written in the form Forgemark itself saves: each line ends with a
hard line break, indentation and runs of spaces are non-breaking spaces, Markdown
formatting characters are escaped, and comments are in italics.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
# Each mirror page, by its path without .md, and the title and source file it shows.
MIRRORS = {
    "docs/specs/theme/base_theme": (
        "Theme specification: base_theme",
        "src/forgegraph/packs/forgegraph_base/themes/base_theme.yaml",
    ),
    "docs/specs/format/base_format": (
        "Format specification: base_format",
        "src/forgegraph/packs/forgegraph_base/formats/base_format.yaml",
    ),
    "docs/specs/format/base_layout_format": (
        "Format specification: base_layout_format",
        "src/forgegraph/packs/forgegraph_base/formats/base_layout_format.yaml",
    ),
    "docs/specs/graph_type/xy": (
        "Graph type specification: xy",
        "src/forgegraph/graph_types/xy.yaml",
    ),
    "docs/specs/graphspec/polarization": (
        "GraphSpec specification: polarization",
        "src/forgegraph/packs/forgegraph_base/graphspecs/polarization.yaml",
    ),
    "docs/specs/layout/base_layout": (
        "Layout specification: base_layout",
        "src/forgegraph/packs/forgegraph_base/layouts/base_layout.yaml",
    ),
    "docs/specs/schedule/base_schedule": (
        "Schedule specification: base_schedule",
        "src/forgegraph/packs/forgegraph_base/schedules/base_schedule.yaml",
    ),
    "docs/specs/layer/reference_line": (
        "Layer specification: reference_line",
        "src/forgegraph/layers/reference_line.yaml",
    ),
    "docs/specs/layer/note": (
        "Layer specification: note",
        "src/forgegraph/layers/note.yaml",
    ),
    "docs/specs/layer/error_bar": (
        "Layer specification: error_bar",
        "src/forgegraph/layers/error_bar.yaml",
    ),
    "docs/specs/catalog/base_theme": (
        "Catalog specification: base_theme",
        "src/forgegraph/packs/forgegraph_base/catalogs/themes/base_theme.yaml",
    ),
    "docs/specs/catalog/base_format": (
        "Catalog specification: base_format",
        "src/forgegraph/packs/forgegraph_base/catalogs/formats/base_format.yaml",
    ),
    "docs/specs/catalog/graph_type_xy": (
        "Catalog specification: xy",
        "src/forgegraph/catalogs/graph_types/xy.yaml",
    ),
    "docs/specs/catalog/layer_reference_line": (
        "Catalog specification: reference_line layer",
        "src/forgegraph/catalogs/layers/reference_line.yaml",
    ),
    "docs/specs/catalog/layer_note": (
        "Catalog specification: note layer",
        "src/forgegraph/catalogs/layers/note.yaml",
    ),
    "docs/specs/catalog/layer_error_bar": (
        "Catalog specification: error_bar layer",
        "src/forgegraph/catalogs/layers/error_bar.yaml",
    ),
    "docs/specs/provenance/provenance": (
        "Provenance specification: the record in every saved file",
        "src/forgegraph/spec/provenance.yaml",
    ),
    "docs/specs/pack/forgegraph_base": (
        "Pack specification: forgegraph_base's pack.yaml",
        "src/forgegraph/packs/forgegraph_base/pack.yaml",
    ),
    "docs/specs/config/config": (
        "Config specification: config.toml and forgegraph.toml",
        "src/forgegraph/packs/config.toml",
    ),
    "docs/specs/pack/acme/pack": (
        "Pack example: acme's pack.yaml",
        "examples/packs/acme/pack.yaml",
    ),
    "docs/specs/pack/acme/themes/acme": (
        "Pack example: acme/acme, a theme",
        "examples/packs/acme/themes/acme.yaml",
    ),
    "docs/specs/pack/acme/formats/slide": (
        "Pack example: acme/slide, a format",
        "examples/packs/acme/formats/slide.yaml",
    ),
    "docs/specs/pack/acme/graphspecs/polarization-curve": (
        "Pack example: acme/polarization-curve, a GraphSpec to extend",
        "examples/packs/acme/graphspecs/polarization-curve.yaml",
    ),
    "docs/specs/pack/acme/layouts/dashboard": (
        "Pack example: acme/dashboard, a layout to extend",
        "examples/packs/acme/layouts/dashboard.yaml",
    ),
    "docs/specs/pack/acme/schedules/workday": (
        "Pack example: acme/workday, a schedule to extend",
        "examples/packs/acme/schedules/workday.yaml",
    ),
    "review/phase-07/deliverable/paper/cell_performance.layout": (
        "Layout example: cell_performance, a paper figure",
        "review/phase-07/deliverable/paper/cell_performance.layout.yaml",
    ),
    "review/phase-07/deliverable/dashboard/lab_throughput.layout": (
        "Layout example: lab_throughput, an ops dashboard",
        "review/phase-07/deliverable/dashboard/lab_throughput.layout.yaml",
    ),
    "review/phase-07/deliverable/paper/formats/journal-double": (
        "Format example: journal-double",
        "review/phase-07/deliverable/paper/formats/journal-double.yaml",
    ),
    "review/phase-07/deliverable/dashboard/formats/dashboard": (
        "Format example: dashboard",
        "review/phase-07/deliverable/dashboard/formats/dashboard.yaml",
    ),
}
NBSP = chr(0xA0)  # non-breaking space
GAP = 10
COMMENTS = "<!-- forgemark-comments"
_REVIEW_MARK = re.compile(r"<!-- /?fmc:\d+ -->")


def mirror_path(kind: str) -> Path:
    return ROOT / f"{kind}.md"


def _split_comment(line: str) -> tuple[str, str | None]:
    quote = None
    for i, c in enumerate(line):
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'" and line[:i].rstrip()[-1:] in ("", ":", "-", "[", "{", ","):
            quote = c
        elif c == "#" and (i == 0 or line[i - 1] == " "):
            return line[:i].rstrip(), line[i:]
    return line, None


def _escape(text: str) -> str:
    out = []
    for i, c in enumerate(text):
        before, after = text[i - 1 : i], text[i + 1 : i + 2]
        if c in "\\`*[]":
            out.append("\\" + c)
        elif c == "_" and not (before.isalnum() and after.isalnum()):
            out.append("\\_")
        elif c == "<" and (after.isalpha() or after in "/!?"):
            out.append("\\<")
        elif c == "&" and re.match(r"&(#\d+|#x[0-9a-fA-F]+|\w+);", text[i:]):
            out.append("&amp;")
        else:
            out.append(c)
    return "".join(out)


def yaml_to_md(yaml_text: str) -> str:
    out = []
    for raw in yaml_text.rstrip("\n").split("\n"):
        if not raw.strip():
            out.append(NBSP)
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content, comment = _split_comment(raw[indent:])
        md = re.sub(r" {2,}", lambda m: NBSP * len(m.group(0)), _escape(content))
        if comment is not None:
            styled = "*" + _escape(comment) + "*"
            md = f"{md}{NBSP * GAP}{styled}" if content else styled
        if indent == 0 and md[:1] in "-+=>":
            md = "\\" + md
        out.append(NBSP * indent + md)
    return "\\\n".join(out)


def page(kind: str) -> str:
    """The mirror page's body for a kind, from its YAML file."""
    title, source = MIRRORS[kind]
    text = (ROOT / source).read_text(encoding="utf-8")
    return (
        f"# {title}\n\n"
        f"This page mirrors {source}, which is the specification. "
        "A test fails if they ever differ.\n\n"
        f"{yaml_to_md(text)}\n"
    )


def body(markdown: str) -> str:
    """A mirror page without Forgemark's comment markers and stored comments. Forgemark escapes
    some tildes when it saves a page, so an escaped tilde counts as a tilde."""
    page = _REVIEW_MARK.sub("", markdown.split(COMMENTS)[0]).replace("\\~", "~")
    return page.rstrip("\n") + "\n"


def write(kind: str) -> bool:
    """Regenerate a mirror, keeping any stored review comments. True if it changed."""
    path = mirror_path(kind)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    stored = old[old.index(COMMENTS) :] if COMMENTS in old else ""
    new = page(kind) + ("\n" + stored if stored else "")
    if body(old) == body(new):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return True
