"""`forgegraph job run`: one run of a schedule file."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from forgegraph.cli import Json, job_app, json_errors, report

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
    from forgegraph.jobs import status as status_file
    from forgegraph.jobs.run import load, run

    code = run(schedule)
    record = status_file.read(load(schedule).status_path)

    def text() -> None:
        for t in record.targets if record is not None else []:
            if t.ok:
                for p in t.outputs:
                    typer.echo(f"saved {p}")
            for p in t.problems:
                typer.echo(f"error: {t.file}: {p}", err=True)

    out = {"ok": code == 0, "status": record.model_dump() if record else None}
    report(out, as_json, text)
    if code:
        raise typer.Exit(code)
