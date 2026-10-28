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
SPECIFICATIONS = PACKAGE / "specifications"
# A pack's spec folders: the kind of spec each holds, as titles name it.
TITLES = {
    "themes": "Theme",
    "formats": "Format",
    "graphspecs": "GraphSpec",
    "layouts": "Layout",
    "schedules": "Schedule",
}
# Each specification file's kind, as titles name it, by its name or the start of its name.
KINDS = {
    "theme": "Theme",
    "format": "Format",
    "graphtype_": "Graph type",
    "layer_": "Layer",
    "graphspec_example": "GraphSpec",
    "layout_example": "Layout",
    "schedule": "Schedule",
    "pack": "Pack",
    "styles": "Styles",
}
# Specification files whose title says what they are, not their name.
OWN_TITLES = {
    "provenance": "Provenance specification: the record in every saved file",
    "config": "Config specification: config.toml and forgegraph.toml",
}


def _name(path: Path) -> str:
    """The name a spec file gives itself."""
    m = re.search(r"^name: (\S+)", path.read_text(encoding="utf-8"), re.MULTILINE)
    return m[1] if m else path.stem


def _specifications() -> dict[str, tuple[str, str]]:
    """A mirror page for every specification file, and every catalog file of ForgeGraph's,
    in docs/specifications/."""
    out: dict[str, tuple[str, str]] = {}
    for path in sorted([*SPECIFICATIONS.glob("*.yaml"), *SPECIFICATIONS.glob("*.toml")]):
        kind = next((t for start, t in KINDS.items() if path.stem.startswith(start)), "")
        title = OWN_TITLES.get(path.stem, f"{kind} specification: {_name(path)}")
        out[f"docs/specifications/{path.stem}"] = (title, path.relative_to(ROOT).as_posix())
    for path in sorted((SPECIFICATIONS / "catalogs").glob("*.yaml")):
        shown = _name(path) + (" layer" if path.stem.startswith("layer_") else "")
        out[f"docs/specifications/catalogs/{path.stem}"] = (
            f"Catalog specification: {shown}",
            path.relative_to(ROOT).as_posix(),
        )
    return out


def _pack(folder: Path, where: str, title: str) -> dict[str, tuple[str, str]]:
    """A mirror page for every file of a pack in folder, in where: its pack.yaml, its specs
    and its catalog files; title is how a page names it."""
    out: dict[str, tuple[str, str]] = {}

    def add(page: str, heading: str, path: Path) -> None:
        out[f"{where}/{page}"] = (heading, path.relative_to(ROOT).as_posix())

    add("pack", f"{title}: {folder.name}'s pack.yaml", folder / "pack.yaml")
    for sub, kind in TITLES.items():
        for path in sorted((folder / sub).glob("*.yaml")):
            what = kind if kind == "GraphSpec" else kind.lower()
            add(f"{sub}/{path.stem}", f"{title}: {folder.name}/{path.stem}, a {what}", path)
    for path in sorted((folder / "catalogs").glob("*/*.yaml")):
        add(
            f"catalogs/{path.parent.name}/{path.stem}",
            f"Catalog: {folder.name}'s {path.stem}",
            path,
        )
    return out


def _built_in() -> dict[str, tuple[str, str]]:
    """A mirror page for every specification file and every built-in pack's file."""
    out = _specifications()
    for pack in sorted(p for p in (PACKAGE / "packs").iterdir() if (p / "pack.yaml").is_file()):
        out.update(_pack(pack, f"docs/packs/{pack.name}", "Built-in pack"))
    return out


# Each mirror page, by its path without .md, and the title and source file it shows: every
# built-in spec file, the example pack's, and these.
MIRRORS = {
    **_built_in(),
    **_pack(ROOT / "examples" / "packs" / "acme", "docs/packs/acme", "Pack example"),
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
