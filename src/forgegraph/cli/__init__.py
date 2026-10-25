"""The `forgegraph` command-line interface. Every command takes --json for agents."""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer

from forgegraph import __version__

app = typer.Typer(
    help="ForgeGraph: fast, consistent, publication-quality graphs from pandas DataFrames, "
    "usable by people and AI agents.",
    no_args_is_help=True,
)
catalog_app = typer.Typer(
    help="What's available here: graph types, layer types, themes, formats, GraphSpecs, "
    "layouts, schedules, packs and their reference notes. Also builds and checks the catalog "
    "pages.",
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
Folder = Annotated[
    Path | None, typer.Option("--folder", help="The folder whose configs apply (default: here).")
]


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


class Failed(Exception):
    """A command's problems, which json_errors reports."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


def fail(problems: list[str]) -> NoReturn:
    """Stop the command with these problems."""
    raise Failed(problems)


def _show(problems: list[str], as_json: bool) -> NoReturn:
    if as_json:
        typer.echo(json.dumps({"ok": False, "problems": problems}, indent=2))
    else:
        for p in problems:
            typer.echo(f"error: {p}", err=True)
    raise typer.Exit(1)


def _problems(e: Exception) -> list[str] | None:
    """The problems an error lists or names, if it's one of ForgeGraph's that does."""
    from forgegraph.forgemark import ForgemarkError
    from forgegraph.skill import InstallError
    from forgegraph.spec.common import ProblemsError

    if isinstance(e, ProblemsError):
        return e.problems
    if isinstance(e, (InstallError, ForgemarkError)):
        return [str(e)]
    return None


def json_errors(command: Callable[..., None]) -> Callable[..., None]:
    """Report a command's problems, and the problems of any error that lists them, as
    problems (error: lines, or JSON with --json), exiting 1; with --json, any other error
    too, rather than a traceback."""

    @functools.wraps(command)
    def run(*args: Any, **kwargs: Any) -> None:
        as_json = bool(kwargs.get("as_json"))
        try:
            command(*args, **kwargs)
        except (typer.Exit, typer.Abort):
            raise
        except Failed as e:
            _show(e.problems, as_json)
        except Exception as e:
            problems = _problems(e)
            if problems is None and not as_json:
                raise
            _show(problems if problems is not None else [f"{type(e).__name__}: {e}"], as_json)

    return run


def report(
    result: dict[str, Any],
    as_json: bool,
    text: Callable[[], None],
    default: Callable[[Any], Any] | None = None,
) -> None:
    """Print a command's result: as JSON with --json (default: json.dumps's), otherwise as
    text() prints it."""
    if as_json:
        typer.echo(json.dumps(result, indent=2, default=default))
    else:
        text()


# Each command group's module registers its commands on the app above.
# isort: off
from forgegraph.cli import graphs  # noqa: E402, F401  (in --help's order)
from forgegraph.cli import schema  # noqa: E402, F401
from forgegraph.cli import catalog  # noqa: E402, F401
from forgegraph.cli import skill  # noqa: E402, F401
from forgegraph.cli import jobs  # noqa: E402, F401
# isort: on
