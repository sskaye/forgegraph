"""`forgegraph skill install`: the agent skill, into Claude Code's skills folder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from forgegraph.cli import Json, fail, json_errors, skill_app


@skill_app.command("install", short_help="Install the ForgeGraph skill for agents.")
@json_errors
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
        fail(["use --project or --dest, not both"], as_json)
    folder = (
        dest
        if dest is not None
        else (Path.cwd() / ".claude" / "skills" if here else Path.home() / ".claude" / "skills")
    )
    try:
        target, what = install(folder, force)
    except InstallError as e:
        fail([str(e)], as_json)
        return
    if as_json:
        typer.echo(json.dumps({"ok": True, "skill": str(target), "result": what}, indent=2))
        return
    typer.echo(f"{what}: {target}")
