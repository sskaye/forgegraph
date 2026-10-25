"""Running a schedule once: what `forgegraph job run` does, whatever schedules it.

1. Take a lock beside the status file, so two runs never overlap.
2. Render every target (GraphSpec or layout) into the output folder, each with the "data as
   of" footnote (when freshness.stamp.show is on) and, on HTML pages, the stale banner. A target
   that fails is recorded and the others still render.
3. Write the status file (jobs/status.py), then run on_failure if any target failed, or
   on_success, without a shell, and write the status file again with what the command did.
4. Exit 0 if every target rendered, 1 otherwise.

"Data as of" is the oldest modification time of the target's data files: the GraphSpec's
data.file, or every tile's for a layout. It's the data's time, not the clock's, so
rendering the same data twice gives the same image.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from forgegraph import __version__
from forgegraph.jobs import status as status_file
from forgegraph.jobs.status import Attempt, DataFile, HookStatus, JobStatus, TargetStatus
from forgegraph.spec.common import ProblemsError
from forgegraph.spec.loaded import Loaded, load_document, placed
from forgegraph.spec.parameters import NONE
from forgegraph.spec.schedule import Cadence
from forgegraph.spec.validate import validate

LOG_LIMIT = 1_000_000  # bytes; a longer log is moved to <name>.log.1


class ScheduleError(ProblemsError):
    """A schedule that can't be run; `problems` lists each one."""


@dataclass
class Schedule:
    """A schedule file, checked: its name, values, cadence and resolved paths."""

    path: Path
    doc: dict[str, Any]
    values: dict[str, Any]
    cadence: Cadence
    targets: list[Path]
    output_folder: Path | None
    status_path: Path

    @property
    def name(self) -> str:
        return str(self.doc["name"])

    @property
    def log_path(self) -> Path:
        return self.status_path.with_name(f"{self.name}.log")

    @property
    def stale_after_hours(self) -> float:
        value = self.values["freshness.stale_after_hours"]
        if value == "auto":
            return round(self.cadence.period() / timedelta(hours=1) * 1.25, 4)
        return float(value)


def load(path: Path) -> Schedule:
    """Read and check a schedule file."""
    path = path.resolve()
    if not path.is_file():
        raise ScheduleError([f"no schedule file at '{path}'"])
    loaded = load_document("schedule", path)
    doc = loaded.doc
    problems = validate("schedule", doc, loaded.reg)
    if problems:
        raise ScheduleError(problems)
    values = loaded.resolve().plain()
    files = values["targets.files"]
    if files in (None, NONE):
        raise ScheduleError(
            ["targets.files: must be set: the GraphSpec and layout files to render"]
        )
    here = loaded.folder_for(loaded.setter("targets.files"))
    targets = [placed(f, here).resolve() for f in files]
    problems = [f"targets.files: no file at '{t}'" for t in targets if not t.is_file()]
    if problems:
        raise ScheduleError(problems)
    cadence = Cadence.from_values(values)  # validation found that it can be built
    output = loaded.place("targets.output_folder")
    output = output.resolve() if output is not None else None
    if values["status.file"] == "auto":
        status_path = (output or path.parent) / f"{doc['name']}.status.json"
    else:
        status = loaded.place("status.file")
        assert status is not None  # its range, auto or text, has no None
        status_path = status.resolve()
    return Schedule(path, doc, values, cadence, targets, output, status_path)


# --- one run ----------------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now().astimezone()


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


class _Lock:
    """A lock file holding the running process's id. A lock left by a process that's no
    longer running is taken over."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> _Lock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if _alive(self.path):
                    raise ScheduleError(
                        [f"already running: {self.path} is held by another run"]
                    ) from None
                self.path.unlink(missing_ok=True)
                continue
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return self
        raise ScheduleError([f"couldn't take the lock {self.path}"])

    def __exit__(self, *_: Any) -> None:
        self.path.unlink(missing_ok=True)


def _alive(lock: Path) -> bool:
    try:
        pid = int(lock.read_text().strip())
    except (OSError, ValueError):
        return False
    return pid != os.getpid() and _running(pid)


def _running(pid: int) -> bool:
    """Whether a process is running. On Windows, os.kill would end it, so ask the system."""
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _log(schedule: Schedule, line: str) -> None:
    path = schedule.log_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size > LOG_LIMIT:
        os.replace(path, path.with_name(path.name + ".1"))
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{_iso(_now())} {line}\n")


def _is_layout(path: Path) -> bool:
    from forgegraph.layouts import is_layout

    return is_layout(path)


def data_files(target: Path) -> list[Path]:
    """The Parquet files a GraphSpec or layout draws from, as its files name them."""
    from forgegraph.data import data_path

    found = [data_path(graphspec) for graphspec in _graphspecs(target)]
    return list(dict.fromkeys(f.resolve() for f in found if f is not None))


def _graphspecs(target: Path) -> list[Loaded]:
    """The GraphSpecs a target draws, as its render reads them: itself, or a layout's tiles."""
    if not _is_layout(target):
        return [load_document("graphspec", target)]
    from forgegraph.layouts import tile_documents

    tiles = tile_documents(load_document("layout", target))
    return [tile for tab in tiles.values() for tile in tab.values()]


def _date_order(target: Path) -> str:
    """The theme's date order for the footnote: the GraphSpec's, or a layout's first tile's."""
    found = _graphspecs(target)
    if not found:
        return "month_day"
    try:
        return str(found[0].explain().theme["axis.tick.label.date_order"].value)
    except Exception:  # the render reports what's wrong with the GraphSpec
        return "month_day"


def stamp(as_of: datetime, cadence: Cadence, order: str) -> str:
    """The "data as of" footnote: e.g. "Data as of Oct 21, 2026, 05:12 · rendered daily
    at 06:00"."""
    from forgegraph.drawing.dates import MONTHS

    month = MONTHS[as_of.month - 1][:3]
    day = (
        f"{as_of.day} {month} {as_of.year}"
        if order == "day_month"
        else f"{month} {as_of.day}, {as_of.year}"
    )
    return f"Data as of {day}, {as_of:%H:%M} · rendered {cadence.describe()}"


def _render_target(schedule: Schedule, target: Path) -> TargetStatus:
    import forgegraph as fg
    from forgegraph.drawing.page import Freshness
    from forgegraph.layouts import draw_file, stem

    shown = os.path.relpath(target, schedule.path.parent)
    found: list[DataFile] = []
    try:
        files = data_files(target)
    except Exception:  # a GraphSpec that can't be read: the render below reports why
        files = []
    times = []
    for f in files:
        if f.is_file():
            moment = datetime.fromtimestamp(f.stat().st_mtime).astimezone()
            times.append(moment)
            found.append(DataFile(path=str(f), modified=_iso(moment)))
        else:
            found.append(DataFile(path=str(f)))
    as_of = min(times) if times and len(times) == len(files) else None
    footnote = None
    if as_of is not None and schedule.values["freshness.stamp.show"]:
        footnote = stamp(as_of, schedule.cadence, _date_order(target))
    result = TargetStatus(
        file=shown, ok=False, data=found, data_as_of=_iso(as_of) if as_of else None
    )
    try:
        drawn = draw_file(target, footnote=footnote)
    except fg.SpecError as e:
        result.problems = list(e.problems)
        return result
    except Exception as e:
        result.problems = [f"{type(e).__name__}: {e}"]
        return result
    if as_of is not None:
        drawn.freshness = Freshness(
            _iso(as_of), schedule.stale_after_hours, schedule.cadence.describe()
        )
    folder = schedule.output_folder or target.parent
    try:
        saved = drawn.save_all(folder / stem(target))
    except Exception as e:
        result.problems = [f"saving: {type(e).__name__}: {e}"]
        return result
    records = drawn.data_records
    dropped: dict[str, int] = {}
    for r in records:
        for reason, n in r.rows_dropped.items():
            dropped[reason] = dropped.get(reason, 0) + n
    result.ok = True
    result.outputs = [str(p) for p in saved]
    result.rows_read = sum(r.rows_read or 0 for r in records)
    result.rows_plotted = sum(r.rows_plotted or 0 for r in records)
    result.rows_dropped = dropped
    result.lint_issues = len(drawn.issues)
    result.nonstandard_packs = list(drawn.nonstandard_packs)
    return result


def _hook(schedule: Schedule, which: str, error: str | None) -> HookStatus | None:
    command = schedule.values[f"{which}.command"]
    if command in (None, NONE):
        return None
    command = [str(c) for c in command]
    env = {
        **os.environ,
        "FORGEGRAPH_JOB": schedule.name,
        "FORGEGRAPH_STATUS_FILE": str(schedule.status_path),
        "FORGEGRAPH_ERROR": error or "",
    }
    ran = _iso(_now())
    timeout = float(schedule.values[f"{which}.timeout_seconds"])
    try:
        done = subprocess.run(command, env=env, timeout=timeout, capture_output=True, check=False)
    except subprocess.TimeoutExpired:
        return HookStatus(
            command=command, ran=ran, exit_code=None, error=f"stopped after {timeout:g} s"
        )
    except OSError as e:
        return HookStatus(command=command, ran=ran, exit_code=None, error=str(e))
    return HookStatus(command=command, ran=ran, exit_code=done.returncode)


def run(path: Path) -> int:
    """Run a schedule once: render its targets, write its status file, run its hook. Returns
    the exit code: 0 if every target rendered, 1 otherwise."""
    os.environ.setdefault("MPLBACKEND", "Agg")
    schedule = load(path)
    with _Lock(schedule.status_path.with_name(f".{schedule.name}.lock")):
        started = _now()
        clock = time.monotonic()
        _log(schedule, f"started {schedule.path}")
        targets = [_render_target(schedule, t) for t in schedule.targets]
        for t in targets:
            _log(
                schedule,
                f"{'rendered' if t.ok else 'failed'} {t.file}"
                + (f": {t.problems[0]}" if t.problems else ""),
            )
        ok = all(t.ok for t in targets)
        finished = _now()
        before = status_file.read(schedule.status_path)
        failures = 0 if ok else (before.consecutive_failures if before else 0) + 1
        record = JobStatus(
            name=schedule.name,
            schedule=str(schedule.path),
            cadence=schedule.cadence.describe(),
            forgegraph=__version__,
            computer=platform.node(),
            last_attempt=Attempt(
                run=uuid.uuid4().hex,
                started=_iso(started),
                finished=_iso(finished),
                seconds=round(time.monotonic() - clock, 3),
                result="success" if ok else "failure",
                exit_code=0 if ok else 1,
            ),
            last_success=_iso(finished) if ok else (before.last_success if before else None),
            consecutive_failures=failures,
            targets=targets,
        )
        status_file.write(schedule.status_path, record)
        error = next((f"{t.file}: {t.problems[0]}" for t in targets if t.problems), None)
        hook = _hook(schedule, "on_success" if ok else "on_failure", error)
        if hook is not None:
            setattr(record, "on_success" if ok else "on_failure", hook)
            status_file.write(schedule.status_path, record)
            _log(schedule, f"{'on_success' if ok else 'on_failure'} exited {hook.exit_code}")
        _log(schedule, f"finished: {'success' if ok else 'failure'}")
    return 0 if ok else 1
