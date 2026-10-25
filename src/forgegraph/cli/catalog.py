"""`forgegraph catalog` and `pack-notes`: what's available here, the packs' reference notes,
and building and checking the catalog pages."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any

import typer

from forgegraph.cli import Json, app, catalog_app, fail, json_errors

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
@json_errors
def catalog_list(ctx: typer.Context, folder: Folder = None, as_json: Json = False) -> None:
    """List what's available here: graph types, layer types, themes, formats and layouts
    the configs allow, and the GraphSpecs to extend."""
    if ctx.invoked_subcommand is None:
        _list(_LISTED, folder, as_json)


def _list_one(kind: str, key: str) -> None:
    def command(folder: Folder = None, as_json: Json = False) -> None:
        _list([(kind, key)], folder, as_json)

    command.__doc__ = (
        "List the GraphSpecs available here, to extend."
        if kind == "graphspec"
        else f"List the {key.replace('_', ' ')} available here."
    )
    catalog_app.command(key.replace("_", "-"))(json_errors(command))


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


@app.command(
    "pack-notes", short_help="Print the reference notes of the packs that may be used here."
)
@json_errors
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


PackFolder = Annotated[
    Path | None,
    typer.Option(
        "--pack",
        metavar="<name or path>",
        help="A built-in pack's name, or a pack's folder: its catalog.",
    ),
]


def _pack(folder: Path | None, as_json: bool) -> Any:
    """The pack --pack names: a built-in pack by name, or a pack's folder."""
    from forgegraph.packs import BUILT_IN, PackError, built_in_folder, read_pack

    if folder is None:
        return None
    try:
        if str(folder) in BUILT_IN:
            return read_pack(built_in_folder(str(folder)), "built in", str(folder))
        return read_pack(folder.resolve(), "folder")
    except PackError as e:
        fail(e.problems, as_json)


@catalog_app.command(
    "build", short_help="Build a catalog page, keeping the review comments it already has."
)
@json_errors
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
    from forgegraph.catalog_build.build import build
    from forgegraph.catalog_build.files import CatalogError
    from forgegraph.catalog_build.forgemark import ForgemarkError
    from forgegraph.spec.parameters import BASE

    chosen = _pack(pack, as_json)
    if out is None:
        out = Path("catalog") / f"{BASE if chosen is None else chosen.name}.html"
    try:
        lint = build(out, chosen)
    except CatalogError as e:
        fail(e.problems, as_json)
        return
    except ForgemarkError as e:
        fail([str(e)], as_json)
        return
    if as_json:
        typer.echo(json.dumps({"ok": True, "saved": str(out), "lint": lint}, indent=2))
        return
    typer.echo(f"saved {out}")
    if lint:
        typer.echo(lint)


@catalog_app.command("check")
@json_errors
def catalog_check(
    page: Annotated[Path, typer.Argument(help="A catalog page.")] = Path(
        "catalog/forgegraph_base.html"
    ),
    pack: PackFolder = None,
    as_json: Json = False,
) -> None:
    """Check that a catalog page was built from the current definitions and code."""
    from forgegraph.catalog_build.build import current

    if not current(page, _pack(pack, as_json)):
        fail([f"{page} is out of date; rebuild it with `forgegraph catalog build`"], as_json)
    if as_json:
        typer.echo(json.dumps({"ok": True}, indent=2))
        return
    typer.echo(f"{page} is current")
