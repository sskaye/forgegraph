"""The `forgegraph` command-line interface. Every command takes --json for agents."""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import Annotated, Any

import typer

from forgegraph import __version__

app = typer.Typer(
    help="ForgeGraph: fast, consistent, publication-quality graphs from pandas DataFrames, "
    "usable by people and AI agents.",
    no_args_is_help=True,
)
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


def fail(problems: list[str], as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps({"ok": False, "problems": problems}, indent=2))
    else:
        for p in problems:
            typer.echo(f"error: {p}", err=True)
    raise typer.Exit(1)


def json_errors(command: Callable[..., None]) -> Callable[..., None]:
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
            fail([f"{type(e).__name__}: {e}"], True)

    return run


# Each command group's module registers its commands on the app above.
# isort: off
from forgegraph.cli import graphs  # noqa: E402, F401  (in --help's order)
from forgegraph.cli import schema  # noqa: E402, F401
from forgegraph.cli import catalog  # noqa: E402, F401
from forgegraph.cli import skill  # noqa: E402, F401
from forgegraph.cli import jobs  # noqa: E402, F401
# isort: on
