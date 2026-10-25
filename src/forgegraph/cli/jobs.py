"""`forgegraph job run`: one run of a schedule file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from forgegraph.cli import Json, fail, job_app, json_errors

ScheduleFile = Annotated[Path, typer.Argument(help="A schedule file (.schedule.yaml).")]


@job_app.command(
    "run", short_help="Run a schedule once: render its targets and write its status file."
)
@json_errors
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
        fail(e.problems, as_json)
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
