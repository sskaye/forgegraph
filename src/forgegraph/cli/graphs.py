"""`forgegraph render`, `explain` and `load`: drawing a GraphSpec or layout, saying what it's
drawn with, and reading a saved file's record."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from ruamel.yaml import YAML

from forgegraph.cli import Json, app, fail, json_errors, report


@app.command(short_help="Draw a GraphSpec or layout and save it in its format's file types.")
@json_errors
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
    from forgegraph.layouts import draw_file, stem
    from forgegraph.spec.access import nonstandard_note

    drawn: Any = draw_file(graphspec)
    if out is not None:
        saved = drawn.save(out)
    else:
        saved = drawn.save_all(graphspec.parent / stem(graphspec))
    result: dict[str, Any] = {
        "ok": True,
        "saved": [str(p) for p in saved],
        "labelling": drawn.labelling_by_name,
        "lint": [i.as_dict() for i in drawn.issues],
    }
    if drawn.nonstandard_packs:
        result["nonstandard"] = nonstandard_note(drawn.nonstandard_packs)

    def text() -> None:
        if "nonstandard" in result:
            typer.echo(result["nonstandard"])
        for p in saved:
            typer.echo(f"saved {p}")
        for i in drawn.issues:
            typer.echo(f"lint {i.check}: {i.message}")

    report(result, as_json, text)


@app.command(
    short_help="Show every value a graph is drawn with, whether it's fixed, and which file set it."
)
@json_errors
def explain(
    graphspec: Annotated[
        Path, typer.Argument(help="A GraphSpec file, or a layout file (.layout.yaml).")
    ],
    as_json: Json = False,
) -> None:
    """Show every value a graph is drawn with, whether it's fixed, and which file set it. For
    a layout: its own values, then each tile's, under tabs.<tab>.tiles.<tile>."""
    from forgegraph.layouts import explain_layout, is_layout, nonstandard_packs_of
    from forgegraph.spec.access import nonstandard_note, packs_used
    from forgegraph.spec.loaded import load_document
    from forgegraph.spec.resolve import Values
    from forgegraph.spec.validate import validate

    values: dict[str, Values]  # by kind; a tile's as tabs.<tab>.tiles.<tile>.<kind>
    if is_layout(graphspec):
        own, tiles = explain_layout(graphspec)
        values = {"layout": own}
        for (tab, tile), explained in tiles.items():
            where = f"tabs.{tab}.tiles.{tile}"
            values.update({f"{where}.{kind}": v for kind, v in explained.kinds().items()})
        packs = nonstandard_packs_of(graphspec)
    else:
        loaded = load_document("graphspec", graphspec)
        doc, reg = loaded.doc, loaded.reg
        problems = validate("graphspec", doc, reg)
        if problems:
            fail(problems)
        values = loaded.explain().kinds()
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
    shown: dict[str, Any] = {"ok": True, "values": rows}
    if note:
        shown["nonstandard"] = note

    def text() -> None:
        if note:
            typer.echo(note)
        for kind in values:
            typer.echo(kind)
            for row in (r for r in rows if r["kind"] == kind):
                mark = "fixed" if row["fixed"] else "variable"
                typer.echo(f"  {row['parameter']} = {row['value']!r}  ({mark}, {row['set_by']})")

    report(shown, as_json, text, default=str)


@app.command("load")
@json_errors
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
        fail([f"{file.name} has no ForgeGraph record"])
    if graphspec is not None and "layout" in record:
        fail([f"{file.name} records a layout, not one GraphSpec"])
    if graphspec is not None and "graphspec" not in record:
        fail([f"{file.name} records no GraphSpec (its format's provenance is off)"])
    if graphspec is not None:
        yaml = YAML()
        yaml.indent(mapping=4, sequence=6, offset=4)
        with graphspec.open("w", encoding="utf-8") as f:
            yaml.dump(record["graphspec"], f)

    def text() -> None:
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

    report(record, as_json, text)
