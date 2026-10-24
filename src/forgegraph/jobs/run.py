"""Running a schedule once: what `forgegraph job run` does, whatever schedules it.

1. Take a lock beside the status file, so two runs never overlap.
2. Render every target (GraphSpec or layout) into the output folder, each with the "data as
   of" footnote (when freshness.stamp is on) and, on HTML pages, the stale banner. A target
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
from forgegraph.spec.documents import Registry, explain, registry_for, resolve, setter, validate
from forgegraph.spec.documents import load as load_yaml
from forgegraph.spec.schedule import Cadence, CadenceError

NONE = "None"
LOG_LIMIT = 1_000_000  # bytes; a longer log is moved to <name>.log.1


class ScheduleError(ValueError):
    """A schedule that can't be run; `problems` lists each one."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


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


def _from(doc: dict[str, Any], reg: Registry, path: str, folder: Path) -> Path:
    """The folder a path parameter's relative values are found from: that of the schedule
    file that sets it (`folder` for doc itself)."""
    depth = setter("schedule", doc, reg, path) or 0
    parent = doc
    for _ in range(depth):
        parent = reg.docs["schedule"][parent["extends"]]
    known = reg.paths["schedule"].get(parent["name"])
    return known.parent if depth and known is not None else folder


def _place(value: str, folder: Path) -> Path:
    where = Path(value).expanduser()
    return (where if where.is_absolute() else folder / where).resolve()


def load(path: Path) -> Schedule:
    """Read and check a schedule file."""
    path = path.resolve()
    if not path.is_file():
        raise ScheduleError([f"no schedule file at '{path}'"])
    doc = load_yaml(path)
    reg = registry_for(path.parent)
    if isinstance(doc, dict) and "name" in doc:
        reg.add("schedule", doc, path)
    problems = validate("schedule", doc, reg)
    if problems:
        raise ScheduleError(problems)
    values = {p: v for p, (v, _) in resolve("schedule", doc, reg).items()}
    files = values["targets.files"]
    if files in (None, NONE):
        raise ScheduleError(
            ["targets.files: must be set: the GraphSpec and layout files to render"]
        )
    here = _from(doc, reg, "targets.files", path.parent)
    targets = [_place(str(f), here) for f in files]
    problems = [f"targets.files: no file at '{t}'" for t in targets if not t.is_file()]
    if problems:
        raise ScheduleError(problems)
    try:
        cadence = Cadence.from_values(values)
    except CadenceError as e:
        raise ScheduleError([str(e)]) from None
    folder_value = values["targets.output_folder"]
    output = (
        None
        if folder_value in (None, NONE)
        else _place(str(folder_value), _from(doc, reg, "targets.output_folder", path.parent))
    )
    file_value = values["status.file"]
    if file_value == "auto":
        status_path = (output or path.parent) / f"{doc['name']}.status.json"
    else:
        status_path = _place(str(file_value), _from(doc, reg, "status.file", path.parent))
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
    from forgegraph.layout import is_layout

    return is_layout(path)


def data_files(target: Path) -> list[Path]:
    """The Parquet files a GraphSpec or layout draws from, as its files name them."""
    from forgegraph.graph import data_path

    def of_graphspec(path: Path) -> list[Path]:
        doc = load_yaml(path)
        reg = registry_for(path.parent)
        if isinstance(doc, dict) and "name" in doc:
            reg.add("graphspec", doc, path)
        found = data_path(doc, reg, path.parent)
        return [found.resolve()] if found is not None else []

    if not _is_layout(target):
        return of_graphspec(target)
    from forgegraph.layout import _load, _tile_files

    doc, reg, folder = _load(target, None)
    files, _ = _tile_files(doc, reg, folder)
    found = [p for tab in files.values() for path in tab.values() for p in of_graphspec(path)]
    return list(dict.fromkeys(found))


def _date_order(target: Path) -> str:
    """The theme's date order for the footnote: the GraphSpec's, or a layout's first tile's."""
    path = target
    if _is_layout(target):
        from forgegraph.layout import _load, _tile_files

        doc, reg, folder = _load(target, None)
        files, _ = _tile_files(doc, reg, folder)
        first = next((p for tab in files.values() for p in tab.values()), None)
        if first is None:
            return "month_day"
        path = first
    doc = load_yaml(path)
    reg = registry_for(path.parent)
    if isinstance(doc, dict) and "name" in doc:
        reg.add("graphspec", doc, path)
    try:
        return str(explain(doc, reg)["theme"]["axis.tick.label.date_order"].value)
    except Exception:  # the render reports what's wrong with the GraphSpec
        return "month_day"


def stamp(as_of: datetime, cadence: Cadence, order: str) -> str:
    """The "data as of" footnote: e.g. "Data as of Oct 21, 2026, 05:12 · rendered daily
    at 06:00"."""
    from forgegraph.render.axes import MONTHS

    month = MONTHS[as_of.month - 1][:3]
    day = (
        f"{as_of.day} {month} {as_of.year}"
        if order == "day_month"
        else f"{month} {as_of.day}, {as_of.year}"
    )
    return f"Data as of {day}, {as_of:%H:%M} · rendered {cadence.describe()}"


def _render_target(schedule: Schedule, target: Path) -> TargetStatus:
    import forgegraph as fg
    from forgegraph.layout import stem
    from forgegraph.render.page import Freshness

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
    if as_of is not None and schedule.values["freshness.stamp"]:
        footnote = stamp(as_of, schedule.cadence, _date_order(target))
    result = TargetStatus(
        file=shown, ok=False, data=found, data_as_of=_iso(as_of) if as_of else None
    )
    try:
        drawn: Any = (
            fg.layout(target, footnote=footnote)
            if _is_layout(target)
            else fg.render(target, footnote=footnote)
        )
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
    name = stem(target) if _is_layout(target) else target.stem
    try:
        saved = drawn.save_all(folder / name)
    except Exception as e:
        result.problems = [f"saving: {type(e).__name__}: {e}"]
        return result
    records = (
        [tile.data for t in drawn.tabs for tile in t.tiles.values()]
        if _is_layout(target)
        else [drawn.data]
    )
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
