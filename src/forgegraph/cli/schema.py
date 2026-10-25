"""`forgegraph schema`: every parameter of a kind, with its range, default and description."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from forgegraph.cli import Json, app, fail, json_errors


@app.command()
@json_errors
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
            fail([f"unknown kind '{k}'; kinds are {', '.join(known)}"], as_json)
    out: dict[str, Any] = {}
    for k in kinds:
        if k in ("pack", "config"):
            out[k] = _pack_fields(k)
            continue
        if k == "graphspec":
            if graph_type is None or theme is None or format is None:
                missing = [f for f, v in (("--graph-type", graph_type), ("--theme", theme),
                                          ("--format", format)) if v is None]  # fmt: skip
                fail([f"schema graphspec needs {', '.join(missing)}"], as_json)
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
        fail(problems, as_json)
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
