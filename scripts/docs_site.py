"""MkDocs hooks for the documentation site (mkdocs.yml): the Reference's generated pages.

- Commands: every `forgegraph` command, from the CLI itself.
- Specifications and the built-in pack: each definition file and each of forgegraph_default's
  specs, shown whole. The pages and their titles are the mirrors' (tests/spec_mirror.py).

Build the site with:  uv run --group docs mkdocs build
"""

from __future__ import annotations

import html
import sys
import tempfile
from pathlib import Path
from typing import Any

import typer.main

sys.path.insert(0, str(Path(__file__).parents[1] / "tests"))

from spec_mirror import MIRRORS, ROOT

from forgegraph.cli import app

REPO = "https://github.com/sskaye/forgegraph/blob/main"
SPECIFICATIONS = "docs/specifications/"
PACK = "docs/packs/forgegraph_default/"
# The specifications in the order a reader meets them; any other comes after, by name.
ORDER = [
    "graphspec_example",
    "graphtype_xy",
    "layer_error_bar",
    "layer_note",
    "layer_reference",
    "theme",
    "styles",
    "format",
    "layout_example",
    "schedule",
    "pack",
    "config",
    "provenance",
]
# A pack's spec folders, in the order the navigation lists them, and their names there.
FOLDERS = {
    "themes": "Themes",
    "formats": "Formats",
    "graphspecs": "GraphSpecs",
    "layouts": "Layouts",
    "schedules": "Schedules",
}
# Options every command has, which its page leaves out.
COMMON = {"--help", "--install-completion", "--show-completion"}

INTRO_SPECIFICATIONS = """\
# Specifications

A specification is the file that defines a kind of spec: every parameter, with its default,
the values it allows (in brackets) and its description. Each page shows one, as ForgeGraph
reads it. `!var` and `!fix` set whether a GraphSpec or layout may change a parameter, and a
parameter inherits the setting of the one above it unless it sets its own.

`forgegraph schema <kind>` lists the same parameters from the command line.
"""

INTRO_PACK = """\
# The built-in pack

`forgegraph_default` is ForgeGraph's built-in pack. It has a theme and formats, so a graph can
always be drawn, and specs to extend. Each page shows one of its files.
"""


def _spec_pages() -> dict[str, tuple[str, str, str]]:
    """Each generated specification page, by its path in the site: its title, its label in the
    navigation, and its source file."""
    out: dict[str, tuple[str, str, str]] = {}
    specs = {
        k: v for k, v in MIRRORS.items() if k.startswith(SPECIFICATIONS) and "/catalogs/" not in k
    }
    stems = sorted(specs, key=lambda k: (_rank(k.removeprefix(SPECIFICATIONS)), k))
    for key in stems:
        title, source = specs[key]
        kind, _, name = title.partition(": ")
        kind = kind.removesuffix(" specification")
        label = f"{kind}: {name}" if kind in ("Graph type", "Layer") else kind
        out[f"reference/specifications/{key.removeprefix(SPECIFICATIONS)}.md"] = (
            title,
            label,
            source,
        )
    for key, (title, source) in MIRRORS.items():
        if key.startswith(PACK) and "/catalogs/" not in key:
            page = key.removeprefix(PACK)
            label = "pack.yaml" if page == "pack" else Path(page).name
            out[f"reference/built-in-pack/{page}.md"] = (title, label, source)
    return out


def _rank(stem: str) -> int:
    return ORDER.index(stem) if stem in ORDER else len(ORDER)


def _spec_page(title: str, source: str) -> str:
    text = (ROOT / source).read_text(encoding="utf-8").rstrip("\n")
    return (
        f"# {title}\n\n"
        f"This page shows [{source}]({REPO}/{source}), which is the specification.\n\n"
        f"```yaml\n{text}\n```\n"
    )


def _commands_page() -> str:
    """Every command, from the CLI: its usage, what it does, and its arguments and options."""
    parts = [
        "# Commands\n",
        "Every command takes `--help`, and most take `--json` for agents. "
        "`forgegraph --version` shows the version.\n",
    ]
    root = typer.main.get_command(app)  # Typer's own copy of Click: its classes, not click's
    with root.context_class(root, info_name="forgegraph") as ctx:
        for path, command, sub in _leaves(root, ctx):
            parts.append(f"## {path}\n")
            parts.append(f"```\n{path} {' '.join(command.collect_usage_pieces(sub))}\n```\n")
            if command.help:
                parts.append(_paragraphs(command.help) + "\n")
            params = [p for p in command.params if not (set(p.opts) & COMMON)]
            arguments = [p for p in params if p.param_type_name == "argument"]
            options = [p for p in params if p.param_type_name == "option"]
            if arguments:
                parts.append("Arguments:\n\n" + "\n".join(_item(p) for p in arguments) + "\n")
            if options:
                parts.append("Options:\n\n" + "\n".join(_item(p) for p in options) + "\n")
    return "\n".join(parts)


def _leaves(command: Any, ctx: Any) -> list[tuple[str, Any, Any]]:
    """Each command that runs something, with its full name and context, in the CLI's order. A
    group that runs on its own, as `forgegraph catalog` does, is one too."""
    if not hasattr(command, "list_commands"):
        return [(ctx.command_path, command, ctx)]
    out = []
    if getattr(command, "invoke_without_command", False) and ctx.parent is not None:
        out.append((ctx.command_path, command, ctx))
    for name in command.list_commands(ctx):
        sub = command.get_command(ctx, name)
        if sub is None or sub.hidden:
            continue
        out += _leaves(sub, sub.context_class(sub, info_name=name, parent=ctx))
    return out


def _item(param: Any) -> str:
    """An argument or option as a list item: its name or flags, and its help."""
    if param.param_type_name == "argument":
        name = f"`{param.human_readable_name}`"
    else:
        name = ", ".join(f"`{o}`" for o in [*param.opts, *param.secondary_opts])
    text = _paragraphs(str(getattr(param, "help", None) or "")).replace("\n\n", " ")
    required = " Required." if param.required and param.param_type_name == "option" else ""
    return f"- {name}: {text}{required}".rstrip(": ")


def _paragraphs(text: str) -> str:
    """Help text as Markdown paragraphs: its line breaks within a paragraph joined, and its
    placeholders, such as <tab>, kept as text rather than read as HTML tags."""
    blocks = [html.escape(" ".join(b.split()), quote=False) for b in text.strip().split("\n\n")]
    return "\n\n".join(b for b in blocks if b and b != "\b")


def on_config(config: Any) -> Any:
    """Add the generated pages to the Reference in the navigation."""
    pages = _spec_pages()
    specs = [{label: path} for path, (_, label, _) in pages.items() if "/specifications/" in path]
    pack: list[Any] = [{"Overview": "reference/built-in-pack/index.md"}]
    pack += [{label: path} for path, (_, label, _) in pages.items() if path.endswith("/pack.md")]
    for folder, name in FOLDERS.items():
        within = [
            {label: path}
            for path, (_, label, _) in pages.items()
            if path.startswith(f"reference/built-in-pack/{folder}/")
        ]
        if within:
            pack.append({name: within})
    reference = next(s for s in config["nav"] if "Reference" in s)["Reference"]
    reference += [
        {"Commands": "reference/commands.md"},
        {"Specifications": [{"Overview": "reference/specifications/index.md"}, *specs]},
        {"The built-in pack": pack},
    ]
    return config


def on_files(files: Any, config: Any) -> Any:
    """Add the generated pages."""
    from mkdocs.structure.files import File  # pyright: ignore[reportMissingImports]  # docs group

    generated = {
        "reference/commands.md": _commands_page(),
        "reference/specifications/index.md": INTRO_SPECIFICATIONS,
        "reference/built-in-pack/index.md": INTRO_PACK,
    }
    for path, (title, _, source) in _spec_pages().items():
        generated[path] = _spec_page(title, source)
    for path, content in generated.items():
        files.append(File.generated(config, path, content=content))
    files.append(File.generated(config, "get-started/voltage.png", content=_quickstart_image()))
    return files


def _quickstart_image() -> bytes:
    """The Quickstart's graph, drawn by its own code, so the page shows what it gives."""
    import pandas as pd

    import forgegraph as fg

    runs = pd.DataFrame(
        {
            "hours": [0, 1, 2, 3, 0, 1, 2, 3],
            "voltage": [0.72, 0.71, 0.70, 0.69, 0.73, 0.73, 0.72, 0.72],
            "cell": ["A", "A", "A", "A", "B", "B", "B", "B"],
        }
    )
    g = fg.xy(runs, x="hours", y="voltage", color="cell", title="Cell voltage")
    with tempfile.TemporaryDirectory() as folder:
        return g.save(Path(folder) / "voltage")[0].read_bytes()
