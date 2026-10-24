"""The `forgegraph` command-line interface. Every command takes --json for agents."""

from __future__ import annotations

import functools
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Any

import typer
from ruamel.yaml import YAML

from forgegraph import __version__

app = typer.Typer(help="ForgeGraph: consistent, high-quality graphs.", no_args_is_help=True)
catalog_app = typer.Typer(
    help="What's available: graph types, layer types, themes, formats, layouts and GraphSpecs "
    "to extend. Also builds and checks the review catalog.",
    invoke_without_command=True,
)
app.add_typer(catalog_app, name="catalog")
skill_app = typer.Typer(help="The agent skill.", no_args_is_help=True)
app.add_typer(skill_app, name="skill")
job_app = typer.Typer(
    help="Scheduled renders: a schedule file's GraphSpecs and layouts, rendered by whatever "
    "schedules `forgegraph job run`.",
    no_args_is_help=True,
)
app.add_typer(job_app, name="job")
Json = Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")]


def _show_version(value: bool) -> None:
    if value:
        typer.echo(f"forgegraph {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", help="Show the version and exit.", callback=_show_version, is_eager=True
    ),
) -> None:
    """ForgeGraph command-line interface."""


def _fail(problems: list[str], as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps({"ok": False, "problems": problems}, indent=2))
    else:
        for p in problems:
            typer.echo(f"error: {p}", err=True)
    raise typer.Exit(1)


def _json_errors(command: Callable[..., None]) -> Callable[..., None]:
    """With --json, report any error as JSON problems rather than a traceback."""

    @functools.wraps(command)
    def run(*args: Any, **kwargs: Any) -> None:
        try:
            command(*args, **kwargs)
        except (typer.Exit, typer.Abort):
            raise
        except Exception as e:
            if not kwargs.get("as_json"):
                raise
            _fail([f"{type(e).__name__}: {e}"], True)

    return run


@app.command()
@_json_errors
def render(
    graphspec: Annotated[
        Path, typer.Argument(help="A GraphSpec file, or a layout file (.layout.yaml).")
    ],
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Where to save; a suffix picks one file type."),
    ] = None,
    as_json: Json = False,
) -> None:
    """Draw a GraphSpec or a layout and save it in its format's file types. A layout with
    several tabs saves a file per tab (name-<tab>.png), a PDF with a page per tab, and an
    HTML page with every tab."""
    import forgegraph as fg
    from forgegraph.layout import is_layout, stem
    from forgegraph.spec.documents import nonstandard_note

    drawn: Any
    try:
        drawn = fg.layout(graphspec) if is_layout(graphspec) else fg.render(graphspec)
    except fg.SpecError as e:
        _fail(e.problems, as_json)
        return
    if out is not None:
        saved = drawn.save(out)
    elif isinstance(drawn, fg.Layout):
        saved = drawn.save_all(graphspec.parent / stem(graphspec))
    else:
        saved = drawn.save_all(graphspec.parent / graphspec.stem)
    labelling = (
        {f"{t.name}.{n}": tile.labelling for t in drawn.tabs for n, tile in t.tiles.items()}
        if isinstance(drawn, fg.Layout)
        else drawn.labelling
    )
    result = {
        "ok": True,
        "saved": [str(p) for p in saved],
        "labelling": labelling,
        "lint": [i.as_dict() for i in drawn.issues],
    }
    if drawn.nonstandard_packs:
        result["nonstandard"] = nonstandard_note(drawn.nonstandard_packs)
    if as_json:
        typer.echo(json.dumps(result, indent=2))
        return
    if "nonstandard" in result:
        typer.echo(result["nonstandard"])
    for p in saved:
        typer.echo(f"saved {p}")
    for i in drawn.issues:
        typer.echo(f"lint {i.check}: {i.message}")


@app.command()
@_json_errors
def explain(
    graphspec: Annotated[
        Path, typer.Argument(help="A GraphSpec file, or a layout file (.layout.yaml).")
    ],
    as_json: Json = False,
) -> None:
    """Show every value a graph is drawn with, whether it's fixed, and which file set it. For
    a layout: its own values, then each tile's, under tabs.<tab>.tiles.<tile>."""
    import forgegraph as fg
    from forgegraph.layout import explain_layout, is_layout, nonstandard_packs_of
    from forgegraph.spec.documents import explain as explain_values
    from forgegraph.spec.documents import load as load_yaml
    from forgegraph.spec.documents import nonstandard_note, packs_used, registry_for, validate

    if is_layout(graphspec):
        try:
            values = explain_layout(graphspec)
        except fg.SpecError as e:
            _fail(e.problems, as_json)
            return
        packs = nonstandard_packs_of(graphspec)
    else:
        doc = load_yaml(graphspec)
        reg = registry_for(graphspec.parent)
        if isinstance(doc, dict) and "name" in doc:
            reg.add("graphspec", doc, graphspec)
        problems = validate("graphspec", doc, reg)
        if problems:
            _fail(problems, as_json)
        values = explain_values(doc, reg)
        packs = sorted(packs_used("graphspec", doc, reg) & reg.nonstandard)
    note = nonstandard_note(packs) if packs else None
    rows = [
        {"kind": kind, "parameter": path, "value": value, "fixed": r.fixed, "set_by": r.origin}
        for kind, params in values.items()
        for name, r in params.items()
        for path, value in (
            [(f"{name}.{p}", v) for p, v in r.value.items()]  # a layer: each of its parameters
            if kind == "layers" or kind.endswith(".layers")
            else [(name, r.value)]
        )
    ]
    if as_json:
        shown: dict[str, Any] = {"ok": True, "values": rows}
        if note:
            shown["nonstandard"] = note
        typer.echo(json.dumps(shown, indent=2, default=str))
        return
    if note:
        typer.echo(note)
    for kind in values:
        typer.echo(kind)
        for row in (r for r in rows if r["kind"] == kind):
            mark = "fixed" if row["fixed"] else "variable"
            typer.echo(f"  {row['parameter']} = {row['value']!r}  ({mark}, {row['set_by']})")


@app.command("load")
@_json_errors
def load_cmd(
    file: Annotated[
        Path, typer.Argument(help="A graph or layout file (png, jpg, tiff, svg, pdf or html).")
    ],
    graphspec: Annotated[
        Path | None, typer.Option("--graphspec", help="Write the recovered GraphSpec here.")
    ] = None,
    as_json: Json = False,
) -> None:
    """Show a graph file's provenance record, and recover its GraphSpec."""
    import forgegraph as fg

    record = fg.load(file)
    if record is None:
        _fail([f"{file.name} has no ForgeGraph record"], as_json)
        return
    if graphspec is not None and "layout" in record:
        _fail([f"{file.name} records a layout, not one GraphSpec"], as_json)
        return
    if graphspec is not None and "graphspec" not in record:
        _fail([f"{file.name} records no GraphSpec (its format's provenance is off)"], as_json)
        return
    if graphspec is not None:
        yaml = YAML()
        yaml.indent(mapping=4, sequence=6, offset=4)
        with graphspec.open("w", encoding="utf-8") as f:
            yaml.dump(record["graphspec"], f)
    if as_json:
        typer.echo(json.dumps(record, indent=2))
        return
    typer.echo(
        f"drawn by forgegraph {record['forgegraph_version']} at {record['created']} "
        f"({record['provenance_level']} record)"
    )
    for kind, spec in record.get("specs", {}).items():
        if kind != "layers":
            typer.echo(f"{kind.replace('_', ' ')}: {spec['name']}, version {spec['version']}")
    if record.get("nonstandard_packs"):
        listed = ", ".join(record["nonstandard_packs"])
        typer.echo(f"non-standard: drawn with packs the main config didn't list: {listed}")
    elif record.get("nonstandard"):
        typer.echo("non-standard: drawn on after ForgeGraph finished")
    if "layout" in record:
        typer.echo(f"layout: {record['layout'].get('name')}")
        for tab, tiles in record.get("tabs", {}).items():
            listed = ", ".join(f"{n} ({t['file']})" for n, t in tiles.items())
            typer.echo(f"  tab {tab}: {listed}")
    if "data" in record:
        typer.echo(f"data: {record['data']}")
    if graphspec is not None:
        typer.echo(f"GraphSpec written to {graphspec}")


@app.command()
@_json_errors
def schema(
    kind: Annotated[
        str | None,
        typer.Argument(
            help="theme, format, graph_type, graphspec, layer, layout, schedule, pack or config."
        ),
    ] = None,
    graph_type: Annotated[
        str | None, typer.Option("--graph-type", help="graphspec: the graph type it draws.")
    ] = None,
    theme: Annotated[
        str | None, typer.Option("--theme", help="graphspec: the theme it uses.")
    ] = None,
    format: Annotated[
        str | None, typer.Option("--format", help="graphspec: the format it uses.")
    ] = None,
    folder: Annotated[
        Path | None,
        typer.Option("--folder", help="The folder whose configs apply (default: here)."),
    ] = None,
    as_json: Json = False,
) -> None:
    """Show every parameter of a kind: its default, range and description. For graphspec,
    every parameter a GraphSpec can set: its own, and the variable parameters of the graph
    type, theme and format named by --graph-type, --theme and --format, each with the value
    it has unless the GraphSpec sets it; with no kind, every kind but graphspec.
    For layer, every layer type's parameters, as type.parameter: what a GraphSpec's layers
    set, under a name of its choosing. For layout, its parameters, its format's variable
    parameters, then a tab's, as tabs.<tab>.<parameter>, and a tile's, tabs.<tab>.tiles.<tile>."""
    from forgegraph.spec.documents import builtin
    from forgegraph.spec.parameters import KINDS, definitions, tab_definitions

    def builtin_layers() -> list[str]:
        return list(builtin().docs["layer"])

    known = [*KINDS, "pack", "config"]
    kinds = [kind] if kind else [k for k in known if k != "graphspec"]
    for k in kinds:
        if k not in known:
            _fail([f"unknown kind '{k}'; kinds are {', '.join(known)}"], as_json)
    out: dict[str, Any] = {}
    for k in kinds:
        if k in ("pack", "config"):
            out[k] = _pack_fields(k)
            continue
        if k == "graphspec":
            if graph_type is None or theme is None or format is None:
                missing = [f for f, v in (("--graph-type", graph_type), ("--theme", theme),
                                          ("--format", format)) if v is None]  # fmt: skip
                _fail([f"schema graphspec needs {', '.join(missing)}"], as_json)
                return
            out[k], notes = _settable(graph_type, theme, format, folder or Path.cwd(), as_json)
            if notes:
                out["notes"] = notes
            continue
        if k == "layer":
            out[k] = [
                {
                    "parameter": f"{t}.{p.path}",
                    "default": p.default,
                    "range": p.range.describe(),
                    "required": p.required,
                    "description": p.description,
                }
                for t in sorted(builtin_layers())
                for p in definitions("layer", t).values()
            ]
            continue
        out[k] = [
            {
                "parameter": p.path,
                "default": p.default,
                "range": p.range.describe(),
                "fixed": p.fixed,
                "required": p.required,
                "description": p.description,
            }
            for p in definitions(k).values()
        ]
        if k == "layout":
            grid, tile = tab_definitions()
            out[k] += [
                {
                    "parameter": p.path,
                    "default": p.default,
                    "range": p.range.describe(),
                    "fixed": False,
                    "required": False,
                    "description": f"{p.description} The format's value unless the layout sets it.",
                }
                for p in definitions("format").values()
                if not p.fixed
            ]
            out[k] += [
                {
                    "parameter": f"tabs.<tab>.{p.path}"
                    if p is not tile
                    else "tabs.<tab>.tiles.<tile>",
                    "default": p.default,
                    "range": p.range.describe(),
                    "fixed": False,
                    "required": p is tile or p.path == "grid.areas",
                    "description": p.description,
                }
                for p in [*grid.values(), tile]
            ]
    if as_json:
        typer.echo(json.dumps(out, indent=2, default=str))
        return
    for note in out.pop("notes", []):
        typer.echo(note)
    for k, params in out.items():
        typer.echo(k)
        for p in params:
            value = p.get("value", p.get("default"))
            fixed = f" Fixed: set by the {k.replace('_', ' ')}." if p.get("fixed") else ""
            typer.echo(f"  {p['parameter']} = {value!r}: {p['range']}. {p['description']}{fixed}")


def _pack_fields(kind: str) -> list[dict[str, Any]]:
    """A pack.yaml's fields, from the base pack's, or a config's settings, from the reference
    config: each with its example value, range and description."""
    import re

    from forgegraph.packs import base_folder

    source = base_folder() / "pack.yaml" if kind == "pack" else base_folder().parent / "config.toml"
    rows = []
    for line in source.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\w+)\s*[:=]\s*(.*?)\s{2,}# \[(.*?)\]; (.*)$", line)
        if m:
            rows.append({"parameter": m[1], "default": m[2], "range": m[3], "fixed": False,
                         "required": True, "description": m[4]})  # fmt: skip
    return rows


def _settable(
    graph_type: str, theme: str, format: str, root: Path, as_json: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    """Every parameter a GraphSpec can set, with the value it has unless the GraphSpec sets
    it, and which file gives that value; and notes on any spec named whose pack is
    non-standard here, or may not be used here."""
    from forgegraph.spec.documents import found_problems, nonstandard_note, registry_for, resolve
    from forgegraph.spec.parameters import NONE, definitions

    reg = registry_for(root)
    chosen_names = (("graph_type", graph_type), ("theme", theme), ("format", format))
    problems = [
        f"{k.replace('_', ' ')}: {p}" for k, n in chosen_names for p in found_problems(k, n, reg)
    ]
    if problems:
        _fail(problems, as_json)
    notes = []
    named = {reg.pack_of(k, n): n for k, n in chosen_names if reg.pack_of(k, n) is not None}
    nonstandard = sorted(p for p in named if p in reg.nonstandard)
    if nonstandard:
        notes.append(nonstandard_note(nonstandard))
    notes += [
        f"Not allowed here: pack '{p}' isn't in the configs that apply, so a GraphSpec here "
        f"can't use '{n}'"
        for p, n in sorted(named.items())
        if p not in reg.allowed
    ]
    chosen = {
        "specifications.graph_type": graph_type,
        "specifications.theme": theme,
        "specifications.format": format,
    }
    rows = [
        {
            "parameter": p.path,
            "value": chosen.get(p.path, NONE),  # not the example GraphSpec's own values
            "range": p.range.describe(),
            "required": p.required,
            "description": p.description,
            "from": "graphspec",
        }
        for p in definitions("graphspec").values()
    ]
    methods = resolve("theme", reg.docs["theme"][theme], reg, graph_type)["legend.methods"][0]
    for kind, name in chosen_names:
        params = definitions(kind, graph_type if kind == "graph_type" else None)
        values = resolve(kind, reg.docs[kind][name], reg, graph_type)
        for path, (value, fixed) in values.items():
            if fixed or path not in params:
                continue
            p = params[path]
            allowed = p.range.describe()
            if path == "legend.method":  # the theme's methods, which the check allows
                allowed = "one of: " + ", ".join(methods)
            rows.append(
                {
                    "parameter": path,
                    "value": value,
                    "range": allowed,
                    "required": p.required,
                    "description": p.description,
                    "from": f"{kind.replace('_', ' ')} {name}",
                }
            )
    return rows, notes


_LISTED = (
    ("graph_type", "graph_types"),
    ("layer", "layers"),
    ("theme", "themes"),
    ("format", "formats"),
    ("graphspec", "graphspecs"),
    ("layout", "layouts"),
    ("schedule", "schedules"),
)


Folder = Annotated[
    Path | None, typer.Option("--folder", help="The folder whose configs apply (default: here).")
]


@catalog_app.callback()
@_json_errors
def catalog_list(ctx: typer.Context, folder: Folder = None, as_json: Json = False) -> None:
    """List what's available here: graph types, layer types, themes, formats and layouts
    the configs allow, and the GraphSpecs to extend."""
    if ctx.invoked_subcommand is None:
        _list(_LISTED, folder, as_json)


def _list_one(kind: str, key: str) -> None:
    def command(folder: Folder = None, as_json: Json = False) -> None:
        _list([(kind, key)], folder, as_json)

    command.__doc__ = (
        "List ForgeGraph's GraphSpecs, to extend."
        if kind == "graphspec"
        else f"List the {key.replace('_', ' ')} available here."
    )
    catalog_app.command(key.replace("_", "-"))(_json_errors(command))


for _kind, _key in _LISTED:
    _list_one(_kind, _key)


def _list(kinds: Sequence[tuple[str, str]], folder: Path | None, as_json: bool) -> None:
    from forgegraph.packs import references
    from forgegraph.spec.documents import nonstandard_note, registry_for
    from forgegraph.spec.parameters import CORE_KINDS, graph_type_files

    root = (folder or Path.cwd()).resolve()
    reg = registry_for(root)
    out: dict[str, Any] = {
        "ok": True,
        "folder": str(root),
        "configs": [str(c.path) for c in reg.configs],
        "packs": [
            {"name": p.name, "version": p.version, "description": p.description,
             "issues": p.issues, "source": p.source, "folder": str(p.folder),
             "nonstandard": name in reg.nonstandard}
            for name, p in sorted(reg.packs.items()) if name in reg.allowed
        ],
    }  # fmt: skip
    if reg.nonstandard:
        out["nonstandard"] = nonstandard_note(reg.nonstandard)
    for kind, key in kinds:
        if kind == "graph_type":
            names = list(graph_type_files())
        elif kind in CORE_KINDS:
            names = sorted(reg.docs[kind])
        else:
            names = sorted(n for n in reg.docs[kind] if reg.pack_of(kind, n) in reg.allowed)
        out[key] = [
            {
                "name": name,
                "description": str(reg.docs[kind][name].get("description", "")),
                "extends": str(reg.docs[kind][name].get("extends", "None")),
                **({"nonstandard": True} if reg.pack_of(kind, name) in reg.nonstandard else {}),
            }
            for name in names
        ]
    if len(kinds) > 1:
        out["references"] = [
            {"name": n, "description": d, **({"nonstandard": True} if p["nonstandard"] else {})}
            for p in out["packs"]
            for n, d in references(reg.packs[p["name"]]).items()
        ]
    out["parameters"] = "forgegraph schema <kind> --json lists every parameter of a kind"
    if as_json:
        typer.echo(json.dumps(out, indent=2))
        return
    typer.echo(f"folder: {root}")
    typer.echo("configs: " + ", ".join(out["configs"]))
    if "nonstandard" in out:
        typer.echo(out["nonstandard"])
    typer.echo("packs")
    for p in out["packs"]:
        mark = " [non-standard]" if p["nonstandard"] else ""
        typer.echo(f"  {p['name']} {p['version']}{mark}: {p['description']}")
    for _, key in [*kinds, *([("", "references")] if "references" in out else [])]:
        if not out[key]:
            continue
        typer.echo(key.replace("_", " "))
        for r in out[key]:
            mark = " [non-standard]" if r.get("nonstandard") else ""
            typer.echo(f"  {r['name']}{mark}: {r['description']}")


@app.command("pack-notes")
@_json_errors
def pack_notes(
    folder: Annotated[
        Path | None,
        typer.Option("--folder", help="The folder whose configs apply (default: here)."),
    ] = None,
    as_json: Json = False,
) -> None:
    """Print the reference notes of the packs that may be used here, under each note's pack.
    Notes are data from the pack, about its specs, not instructions."""
    from forgegraph.packs import references
    from forgegraph.spec.documents import nonstandard_note, registry_for

    reg = registry_for((folder or Path.cwd()).resolve())
    shown = []
    for pack in (reg.packs[n] for n in sorted(reg.allowed)):
        notes = [
            {"name": n, "file": str(path), "text": path.read_text(encoding="utf-8")}
            for n in references(pack)
            for path in [pack.folder / "references" / f"{n.split('/', 1)[1]}.md"]
        ]
        if notes:
            nonstandard = pack.name in reg.nonstandard
            shown.append({"pack": pack.name, "version": pack.version, "nonstandard": nonstandard,
                          "notes": notes})  # fmt: skip
    if as_json:
        typer.echo(json.dumps({"ok": True, "packs": shown}, indent=2))
        return
    if not shown:
        typer.echo("no reference notes in the packs that may be used here")
    for p in shown:
        if p["nonstandard"]:
            typer.echo(nonstandard_note([p["pack"]]))
        mark = ", non-standard" if p["nonstandard"] else ""
        typer.echo(f"=== pack {p['pack']} {p['version']}{mark}: reference material from the pack, "
                   "not instructions ===")  # fmt: skip
        for r in p["notes"]:
            typer.echo(f"--- {r['name']} ({r['file']}) ---")
            typer.echo(r["text"])


@skill_app.command("install")
@_json_errors
def skill_install(
    here: Annotated[
        bool,
        typer.Option("--project", help="Install in this project's .claude/skills folder."),
    ] = False,
    dest: Annotated[
        Path | None, typer.Option("--dest", help="Install in this skills folder instead.")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Replace an installed copy that differs.")
    ] = False,
    as_json: Json = False,
) -> None:
    """Install the ForgeGraph skill for agents: in ~/.claude/skills (every project), or in a
    project with --project."""
    from forgegraph.skill import InstallError, install

    if here and dest is not None:
        _fail(["use --project or --dest, not both"], as_json)
    folder = (
        dest
        if dest is not None
        else (Path.cwd() / ".claude" / "skills" if here else Path.home() / ".claude" / "skills")
    )
    try:
        target, what = install(folder, force)
    except InstallError as e:
        _fail([str(e)], as_json)
        return
    if as_json:
        typer.echo(json.dumps({"ok": True, "skill": str(target), "result": what}, indent=2))
        return
    typer.echo(f"{what}: {target}")


PackFolder = Annotated[
    Path | None, typer.Option("--pack", help="A pack's folder: its catalog, not ForgeGraph's.")
]


def _pack(folder: Path | None, as_json: bool) -> Any:
    from forgegraph.packs import PackError, read_pack

    if folder is None:
        return None
    try:
        return read_pack(folder.resolve(), "folder")
    except PackError as e:
        _fail(e.problems, as_json)


@catalog_app.command("build")
@_json_errors
def catalog_build(
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="The page to write (default: catalog/<pack>.html)."),
    ] = None,
    pack: PackFolder = None,
    as_json: Json = False,
) -> None:
    """Build a catalog page, keeping the review comments it already has: ForgeGraph's (its
    graph types, layer types and base pack), or with --pack, that pack's themes and formats."""
    from forgegraph.catalog.build import build
    from forgegraph.catalog.files import CatalogError
    from forgegraph.catalog.forgemark import ForgemarkError
    from forgegraph.packs import BASE

    chosen = _pack(pack, as_json)
    if out is None:
        out = Path("catalog") / f"{BASE if chosen is None else chosen.name}.html"
    try:
        lint = build(out, chosen)
    except CatalogError as e:
        _fail(e.problems, as_json)
        return
    except ForgemarkError as e:
        _fail([str(e)], as_json)
        return
    if as_json:
        typer.echo(json.dumps({"ok": True, "saved": str(out), "lint": lint}, indent=2))
        return
    typer.echo(f"saved {out}")
    if lint:
        typer.echo(lint)


@catalog_app.command("check")
@_json_errors
def catalog_check(
    page: Annotated[Path, typer.Argument(help="A catalog page.")] = Path(
        "catalog/forgegraph_base.html"
    ),
    pack: PackFolder = None,
    as_json: Json = False,
) -> None:
    """Check that a catalog page was built from the current definitions and code."""
    from forgegraph.catalog.build import current

    if not current(page, _pack(pack, as_json)):
        _fail([f"{page} is out of date; rebuild it with `forgegraph catalog build`"], as_json)
    if as_json:
        typer.echo(json.dumps({"ok": True}, indent=2))
        return
    typer.echo(f"{page} is current")


ScheduleFile = Annotated[Path, typer.Argument(help="A schedule file (.schedule.yaml).")]


@job_app.command("run")
@_json_errors
def job_run(
    schedule: ScheduleFile,
    as_json: Json = False,
) -> None:
    """Run a schedule once: render its targets, write its status file and run on_failure or
    on_success. Exits 1 if any target failed. Schedule this command to render on a schedule."""
    from forgegraph.jobs import ScheduleError
    from forgegraph.jobs import status as status_file
    from forgegraph.jobs.run import load, run

    try:
        code = run(schedule)
    except ScheduleError as e:
        _fail(e.problems, as_json)
        return
    record = status_file.read(load(schedule).status_path)
    if as_json:
        out = {"ok": code == 0, "status": record.model_dump() if record else None}
        typer.echo(json.dumps(out, indent=2))
    elif record is not None:
        for t in record.targets:
            if t.ok:
                for p in t.outputs:
                    typer.echo(f"saved {p}")
            for p in t.problems:
                typer.echo(f"error: {t.file}: {p}", err=True)
    if code:
        raise typer.Exit(code)
