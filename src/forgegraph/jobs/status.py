"""A scheduled job's status file: what its last run did (docs/specs/schedule/base_schedule.md).

The file is written whole at the end of every run, to a temporary file that's then renamed
over the old one, so a reader never sees half of one. Times are ISO 8601 with their UTC
offset.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from forgegraph.spec.common import Model


class DataFile(Model):
    path: str
    modified: str | None = None  # None: the file was missing


class TargetStatus(Model):
    file: str  # the GraphSpec or layout file, as the schedule names it
    ok: bool
    outputs: list[str] = Field(default_factory=list)
    rows_read: int | None = Field(default=None, ge=0)
    rows_plotted: int | None = Field(default=None, ge=0)
    rows_dropped: dict[str, int] = Field(default_factory=dict)
    data: list[DataFile] = Field(default_factory=list)
    data_as_of: str | None = None  # the oldest data file's modification time
    lint_issues: int = 0
    nonstandard_packs: list[str] = Field(default_factory=list)  # used, not in the main config
    problems: list[str] = Field(default_factory=list)  # as `forgegraph render --json` reports them


class HookStatus(Model):
    command: list[str]
    ran: str  # when it started
    exit_code: int | None  # None: stopped after its timeout, or couldn't start
    error: str | None = None


class Attempt(Model):
    run: str  # a unique id for each run
    started: str
    finished: str
    seconds: float
    result: Literal["success", "failure"]
    exit_code: int


class JobStatus(Model):
    name: str
    schedule: str  # the schedule file, absolute
    cadence: str  # in words
    forgegraph: str
    computer: str
    last_attempt: Attempt
    last_success: str | None = None  # when the last successful run finished
    consecutive_failures: int = 0
    targets: list[TargetStatus] = Field(default_factory=list)
    on_failure: HookStatus | None = None
    on_success: HookStatus | None = None


def write(path: Path, status: JobStatus) -> None:
    """Write the status file whole: to a temporary file, then renamed over the old one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(status.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read(path: Path) -> JobStatus | None:
    """The status file, or None if there's none yet."""
    if not path.is_file():
        return None
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    return JobStatus.model_validate(data)
