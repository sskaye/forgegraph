"""MkDocs hooks for the documentation site (mkdocs.yml): its generated pages and images.

- Commands: every `forgegraph` command, from the CLI itself.
- Specifications and the built-in pack: each definition file and each of forgegraph_default's
  specs, shown whole. The pages and their titles are the mirrors' (tests/spec_mirror.py).
- Images: every graph the guides and gallery show, drawn from its file as the site builds
  (EXAMPLES), so a page never shows a graph its spec no longer draws, and a spec that can't
  be drawn fails the build.

Build the site with:  uv run --group docs mkdocs build
"""

from __future__ import annotations

import html
import io
import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
import typer.main

sys.path.insert(0, str(Path(__file__).parents[1] / "tests"))

from spec_mirror import MIRRORS, ROOT

from forgegraph.cli import app

EXAMPLES = ROOT / "docs" / "examples"  # the guides' and gallery's GraphSpecs, layouts and pack
SAMPLE_DATA = ROOT / "examples" / "sample-data"
# The repository's own example layouts the pages show, drawn where they are.
LAYOUTS = [
    ROOT / "examples" / "layouts" / "paper" / "cell_performance.layout.yaml",
    ROOT / "examples" / "layouts" / "dashboard" / "lab_throughput.layout.yaml",
]
# The packs the examples use, all listed in the main config they're drawn with, so nothing is
# watermarked as non-standard.
PACKS = [
    "forgegraph_default",
    EXAMPLES / "packs" / "lab",
    ROOT / "examples" / "packs" / "acme",
    ROOT / "examples" / "layouts" / "paper" / "journal",
    ROOT / "examples" / "layouts" / "dashboard" / "ops",
]
IMAGE_WIDTH = 1200  # px: the images are drawn at their format's resolution, then made this wide
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
    for path, content in example_images().items():
        files.append(File.generated(config, path, content=content))
    return files


# Each sample dataset as the examples read it, where that isn't the CSV as it is: its dates as
# dates, and CO₂'s missing months, written -99.99, as missing.
PREPARE = {
    "co2_monthly": lambda d: d.assign(
        date=pd.to_datetime(d["date"]), co2_ppm=d["co2_ppm"].mask(d["co2_ppm"] < 0)
    ),
    "economics": lambda d: d.assign(date=pd.to_datetime(d["date"])),
}


def example_images() -> dict[str, bytes]:
    """Every example drawn, by its image's path in the site: images/<name>.png for each
    GraphSpec and layout in docs/examples and each of LAYOUTS, or for a layout of several
    tabs, images/<name>-<tab>.png; and each layout in docs/examples as its HTML page,
    pages/<name>.html. Each GraphSpec in docs/examples reads a sample dataset as
    Parquet (data.file: <dataset>.parquet), written from examples/sample-data as it's drawn.
    An example that can't be drawn, is non-standard or has a lint issue other than rows left
    out is an error."""
    import forgegraph as fg

    out: dict[str, bytes] = {}
    with _main_config() as folder:
        work = folder / "examples"
        work.mkdir()
        for spec in sorted(EXAMPLES.glob("*.yaml")):
            shutil.copy(spec, work / spec.name)
            for dataset in _datasets(spec):
                frame = pd.read_csv(SAMPLE_DATA / f"{dataset}.csv")
                PREPARE.get(dataset, lambda d: d)(frame).to_parquet(work / f"{dataset}.parquet")
        for spec in [*sorted(work.glob("*.yaml")), *LAYOUTS]:
            layout = spec.name.endswith(".layout.yaml")
            drawn = fg.layout(spec) if layout else fg.render(spec)
            problems = [i for i in drawn.issues if i.check != "dropped-rows"]
            if drawn.nonstandard or problems:
                raise ValueError(f"{spec.name}: non-standard, or lint issues: {problems}")
            name = spec.name.removesuffix(".yaml").removesuffix(".layout")
            for image in drawn._write(folder / "images" / name, ["png"]):
                out[f"images/{image.name}"] = _narrowed(image.read_bytes())
            if layout and spec.parent == work:  # its page, to try its tabs and readouts
                [page] = drawn._write(folder / "pages" / name, ["html"])
                out[f"pages/{page.name}"] = page.read_bytes()
    return out


def _datasets(spec: Path) -> list[str]:
    """The sample datasets a GraphSpec reads: its data.file's name, less .parquet."""
    text = spec.read_text(encoding="utf-8")
    return [
        line.split(":", 1)[1].strip().removesuffix(".parquet")
        for line in text.splitlines()
        if line.strip().startswith("file:") and line.strip().endswith(".parquet")
    ]


@contextmanager
def _main_config() -> Iterator[Path]:
    """A folder with a main config listing PACKS, in use while the examples are drawn."""
    before = os.environ.get("FORGEGRAPH_CONFIG")
    with tempfile.TemporaryDirectory() as folder:
        config = Path(folder) / "config.toml"
        config.write_text(f"packs = {[str(p) for p in PACKS]}\n".replace("'", '"'))
        os.environ["FORGEGRAPH_CONFIG"] = str(config)
        try:
            yield Path(folder)
        finally:
            if before is None:
                del os.environ["FORGEGRAPH_CONFIG"]
            else:
                os.environ["FORGEGRAPH_CONFIG"] = before


def _narrowed(png: bytes) -> bytes:
    """A PNG made IMAGE_WIDTH wide, if it's wider: the site shows it no wider."""
    from PIL import Image

    image = Image.open(io.BytesIO(png))
    if image.width > IMAGE_WIDTH:
        height = round(image.height * IMAGE_WIDTH / image.width)
        image = image.resize((IMAGE_WIDTH, height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


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
