"""Markdown mirrors of the specification files, for review in Forgemark.

A mirror shows its YAML file as plain Markdown text rather than a code block, so every line
can be commented on. It's written in the form Forgemark itself saves: each line ends with a
hard line break, indentation and runs of spaces are non-breaking spaces, Markdown
formatting characters are escaped, and comments are in italics.
"""

from __future__ import annotations

import re
from pathlib import Path

from forgegraph import forgemark

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "forgegraph"
# A pack's spec folders: the kind of spec each holds, as titles name it.
TITLES = {
    "themes": "Theme",
    "formats": "Format",
    "graphspecs": "GraphSpec",
    "layouts": "Layout",
    "schedules": "Schedule",
}
BASE_PACK = "forgegraph_base"


def _built_in() -> dict[str, tuple[str, str]]:
    """A mirror page for every built-in spec file: the graph types, the layer types, every
    built-in pack's specs and pack.yaml, and every catalog file."""
    out: dict[str, tuple[str, str]] = {}

    def add(page: str, title: str, path: Path) -> None:
        out[page] = (title, path.relative_to(ROOT).as_posix())

    for path in sorted((PACKAGE / "graph_types").glob("*.yaml")):
        add(f"docs/specs/graph_type/{path.stem}", f"Graph type specification: {path.stem}", path)
    for path in sorted((PACKAGE / "layers").glob("*.yaml")):
        add(f"docs/specs/layer/{path.stem}", f"Layer specification: {path.stem}", path)
    for path in sorted((PACKAGE / "catalogs" / "graph_types").glob("*.yaml")):
        add(
            f"docs/specs/catalog/graph_type_{path.stem}",
            f"Catalog specification: {path.stem}",
            path,
        )
    for path in sorted((PACKAGE / "catalogs" / "layers").glob("*.yaml")):
        title = f"Catalog specification: {path.stem} layer"
        add(f"docs/specs/catalog/layer_{path.stem}", title, path)
    for pack in sorted(p for p in (PACKAGE / "packs").iterdir() if (p / "pack.yaml").is_file()):
        base = pack.name == BASE_PACK  # the base pack's pages are the specification's own
        where = "docs/specs" if base else f"docs/specs/pack/{pack.name}"
        page = f"docs/specs/pack/{pack.name}" if base else f"{where}/pack"
        add(page, f"Pack specification: {pack.name}'s pack.yaml", pack / "pack.yaml")
        for folder, kind in TITLES.items():
            for path in sorted((pack / folder).glob("*.yaml")):
                page = (
                    f"{where}/{kind.lower()}/{path.stem}"
                    if base
                    else f"{where}/{folder}/{path.stem}"
                )
                title = (
                    f"{kind} specification: {path.stem}"
                    if base
                    else f"{kind}: {pack.name}/{path.stem}"
                )
                add(page, title, path)
        for path in sorted((pack / "catalogs").glob("*/*.yaml")):
            page = (
                f"docs/specs/catalog/{path.stem}"
                if base
                else f"{where}/catalogs/{path.parent.name}/{path.stem}"
            )
            title = (
                f"Catalog specification: {path.stem}"
                if base
                else f"Catalog: {pack.name}'s {path.stem}"
            )
            add(page, title, path)
    return out


# Each mirror page, by its path without .md, and the title and source file it shows: every
# built-in spec file, and these.
MIRRORS = {
    **_built_in(),
    "docs/specs/provenance/provenance": (
        "Provenance specification: the record in every saved file",
        "src/forgegraph/spec/provenance.yaml",
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
    "examples/layouts/paper/cell_performance.layout": (
        "Layout example: cell_performance, a paper figure",
        "examples/layouts/paper/cell_performance.layout.yaml",
    ),
    "examples/layouts/dashboard/lab_throughput.layout": (
        "Layout example: lab_throughput, an ops dashboard",
        "examples/layouts/dashboard/lab_throughput.layout.yaml",
    ),
    "examples/layouts/paper/journal/formats/journal-double": (
        "Format example: journal/journal-double",
        "examples/layouts/paper/journal/formats/journal-double.yaml",
    ),
    "examples/layouts/dashboard/ops/formats/dashboard": (
        "Format example: ops/dashboard",
        "examples/layouts/dashboard/ops/formats/dashboard.yaml",
    ),
}
NBSP = chr(0xA0)  # non-breaking space
GAP = 10


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
    return forgemark.strip(markdown).replace("\\~", "~").rstrip("\n") + "\n"


def write(kind: str) -> bool:
    """Regenerate a mirror, keeping any stored review comments. True if it changed."""
    path = mirror_path(kind)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    new = forgemark.keep(page(kind), old)
    if body(old) == body(new):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return True
