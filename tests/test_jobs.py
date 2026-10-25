"""Scheduled jobs: running a schedule (status file, footnote, hooks, lock), and the stale
banner under a simulated clock."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pack_helpers import allow, dump, needs_node, write_pack
from render_helpers import BASE, polarization

import forgegraph as fg
from forgegraph.drawing.figure import FOOTNOTE
from forgegraph.drawing.page import STALE_ID
from forgegraph.jobs import run as job_run
from forgegraph.jobs import status as status_file


def schedule_doc(name: str = "lab", **variable: Any) -> dict[str, Any]:
    return {
        "name": name,
        "version": 0,
        "description": "test",
        "extends": "forgegraph_base/base_schedule",
        "fixed_parameters": "None",
        "variable_parameters": {
            "targets": {"files": ["p.yaml"], "output_folder": "out"},
            **variable,
        },
    }


@pytest.fixture
def project(tmp_path, monkeypatch):
    polarization().to_parquet(tmp_path / "p.parquet")
    doc = fg.graphspec("p", "xy", data_file="p.parquet", settings=BASE)
    doc["variable_parameters"]["output"] = {"file_types": ["png", "html"]}
    dump(doc, tmp_path / "p.yaml")
    dump(schedule_doc(), tmp_path / "lab.schedule.yaml")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def status(project: Path, name: str = "lab") -> status_file.JobStatus:
    found = status_file.read(project / "out" / f"{name}.status.json")
    assert found is not None
    return found


# --- running ----------------------------------------------------------------------------------


def test_a_run_renders_its_targets_and_writes_its_status(project):
    assert job_run.run(project / "lab.schedule.yaml") == 0
    s = status(project)
    assert s.last_attempt.result == "success" and s.last_success == s.last_attempt.finished
    assert s.cadence == "daily at 06:00" and s.consecutive_failures == 0
    [target] = s.targets
    assert target.ok and target.rows_read == 96 and target.rows_dropped == {"missing x or y": 1}
    assert [Path(p).name for p in target.outputs] == ["p.png", "p.html"]
    modified = datetime.fromtimestamp((project / "p.parquet").stat().st_mtime).astimezone()
    assert target.data_as_of == modified.isoformat(timespec="seconds")
    assert (project / "out" / "lab.log").read_text().count("finished: success") == 1


def test_paths_a_parent_schedule_sets_are_found_from_its_folder(project):
    """A schedule extending a pack's schedule: the targets and output folder the pack's
    schedule sets are relative to its file, not to the schedule that extends it."""
    schedules = write_pack(project / "packs") / "schedules"
    (schedules / "graphs").mkdir(parents=True)
    polarization().to_parquet(schedules / "graphs" / "q.parquet")
    dump(
        fg.graphspec("q", "xy", data_file="q.parquet", settings=BASE),
        schedules / "graphs" / "q.yaml",
    )
    parent = schedule_doc("lab")
    parent["variable_parameters"]["targets"] = {"files": ["graphs/q.yaml"], "output_folder": "made"}
    dump(parent, schedules / "lab.yaml")
    work = project / "work"
    work.mkdir()
    allow(work, "forgegraph_base", "../packs/house")
    child = schedule_doc("weekly")
    child["extends"] = "house/lab"
    del child["variable_parameters"]["targets"]
    dump(child, work / "weekly.schedule.yaml")
    assert job_run.run(work / "weekly.schedule.yaml") == 0
    assert (schedules / "made" / "q.png").is_file()


def test_a_target_drawn_with_a_nonstandard_pack_says_so(project, monkeypatch):
    main = project / "main.toml"
    main.write_text("packs = []\n")
    monkeypatch.setenv("FORGEGRAPH_CONFIG", str(main))
    (project / "forgegraph.toml").write_text('packs = ["forgegraph_base"]\n')
    assert job_run.run(project / "lab.schedule.yaml") == 0
    [target] = status(project).targets
    assert target.ok and target.nonstandard_packs == ["forgegraph_base"]


@pytest.mark.slow
def test_the_footnote_says_when_the_data_is_from(project):
    when = datetime(2026, 10, 21, 5, 12)
    os.utime(project / "p.parquet", (when.timestamp(), when.timestamp()))
    job_run.run(project / "lab.schedule.yaml")
    words = job_run.stamp(when, job_run.load(project / "lab.schedule.yaml").cadence, "month_day")
    assert words == "Data as of Oct 21, 2026, 05:12 · rendered daily at 06:00"
    record = fg.load(project / "out" / "p.png")
    assert record is not None and record["graphspec"]["name"] == "p"
    g = fg.render(project / "p.yaml", footnote=words)
    [note] = [t for t in g.figure.texts if t.get_gid() == FOOTNOTE]
    renderer = g.figure.canvas.get_renderer()  # type: ignore[attr-defined]
    assert note.get_window_extent(renderer).y1 < g.axes.xaxis.label.get_window_extent(renderer).y0
    assert g.issues == fg.render(project / "p.yaml").issues  # nothing new for lint


@pytest.mark.slow
def test_no_stamp_when_freshness_stamp_is_off(project):
    dump(schedule_doc(freshness={"stamp": False}), project / "lab.schedule.yaml")
    job_run.run(project / "lab.schedule.yaml")
    plain = fg.render(project / "p.yaml")
    plain.save(project / "plain.png")
    assert (project / "out" / "p.png").stat().st_size == (project / "plain.png").stat().st_size


def test_one_target_failing_leaves_the_others_and_fires_on_failure(project):
    hook = project / "hook.txt"
    command = [
        sys.executable,
        "-c",
        f"import os; open({str(hook)!r}, 'w').write(os.environ['FORGEGRAPH_ERROR'])",
    ]
    dump(
        schedule_doc(
            targets={"files": ["p.yaml", "q.yaml"], "output_folder": "out"},
            on_failure={"command": command},
        ),
        project / "lab.schedule.yaml",
    )
    (project / "q.yaml").write_text(
        (project / "p.yaml").read_text().replace("p.parquet", "gone.parquet")
    )
    assert job_run.run(project / "lab.schedule.yaml") == 1
    s = status(project)
    assert [t.ok for t in s.targets] == [True, False]
    assert s.targets[1].problems[0].startswith("data.file: no file at")
    assert s.on_failure is not None and s.on_failure.exit_code == 0
    assert hook.read_text().startswith("q.yaml: data.file: no file at")
    assert (project / "out" / "p.png").is_file()


def test_job_run_says_what_it_saved_and_exits_1_when_a_target_fails(project):
    from typer.testing import CliRunner

    from forgegraph.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["job", "run", "lab.schedule.yaml"])
    assert result.exit_code == 0, result.output
    saved = [line.removeprefix("saved ") for line in result.output.splitlines()]
    assert [Path(p).name for p in saved] == ["p.png", "p.html"]
    targets = {"files": ["p.yaml", "q.yaml"], "output_folder": "out"}
    dump(schedule_doc(targets=targets), project / "lab.schedule.yaml")
    (project / "q.yaml").write_text(
        (project / "p.yaml").read_text().replace("p.parquet", "gone.parquet")
    )
    result = runner.invoke(app, ["job", "run", "lab.schedule.yaml"])
    assert result.exit_code == 1
    assert "error: q.yaml: data.file: no file at" in result.output
    assert "p.png" in result.output  # the other target still saved
    result = runner.invoke(app, ["job", "run", "lab.schedule.yaml", "--json"])
    assert result.exit_code == 1
    out = json.loads(result.output)
    assert not out["ok"] and [t["ok"] for t in out["status"]["targets"]] == [True, False]
    dump(schedule_doc(interval=7), project / "lab.schedule.yaml")  # 7 days: not allowed
    result = runner.invoke(app, ["job", "run", "lab.schedule.yaml", "--json"])
    assert result.exit_code == 1
    [problem] = json.loads(result.output)["problems"]
    assert problem.startswith("variable_parameters.interval: ")


@pytest.mark.slow
def test_on_success_runs_and_a_slow_command_is_stopped(project):
    slow = [sys.executable, "-c", "import time; time.sleep(5)"]
    dump(
        schedule_doc(on_success={"command": slow, "timeout_seconds": 1}),
        project / "lab.schedule.yaml",
    )
    assert job_run.run(project / "lab.schedule.yaml") == 0
    hook = status(project).on_success
    assert hook is not None and hook.exit_code is None and hook.error == "stopped after 1 s"


def test_a_missing_command_is_recorded(project):
    dump(
        schedule_doc(on_success={"command": ["no-such-program-xyz"]}), project / "lab.schedule.yaml"
    )
    job_run.run(project / "lab.schedule.yaml")
    hook = status(project).on_success
    assert hook is not None and hook.exit_code is None and hook.error


def test_two_runs_never_overlap(project):
    lock = project / "out" / ".lab.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text(str(os.getppid()))  # a process that's running
    with pytest.raises(job_run.ScheduleError, match="already running"):
        job_run.run(project / "lab.schedule.yaml")
    lock.write_text("999999999")  # one that isn't: its lock is taken over
    assert job_run.run(project / "lab.schedule.yaml") == 0 and not lock.exists()


@pytest.mark.parametrize(
    ("variable", "message"),
    [
        ({"targets": {"files": None}}, "targets.files: must be set"),
        ({"targets": {"files": ["nowhere.yaml"]}}, "targets.files: no file at"),
        ({"cadence": {"interval": 7, "interval_unit": "minute", "at": None}}, "doesn't divide 60"),
    ],
)
def test_a_schedule_that_cant_run_is_an_error(project, variable, message):
    dump(schedule_doc(**variable), project / "lab.schedule.yaml")
    with pytest.raises(job_run.ScheduleError, match=message):
        job_run.run(project / "lab.schedule.yaml")


@pytest.mark.slow
def test_a_layout_target_takes_its_oldest_tiles_time(project):
    shutil.copy(project / "p.parquet", project / "q.parquet")
    (project / "q.yaml").write_text(
        (project / "p.yaml").read_text().replace("p.parquet", "q.parquet")
    )
    old = datetime(2026, 1, 2, 3, 4).timestamp()
    os.utime(project / "q.parquet", (old, old))
    layout = {
        "name": "both",
        "version": 0,
        "description": "",
        "extends": "forgegraph_base/base_layout",
        "fixed_parameters": "None",
        "variable_parameters": {
            "tabs": {
                "T": {"grid": {"areas": [["p"], ["q"]]}, "tiles": {"p": "p.yaml", "q": "q.yaml"}}
            }
        },
    }
    dump(layout, project / "both.layout.yaml")
    dump(
        schedule_doc(targets={"files": ["both.layout.yaml"], "output_folder": "out"}),
        project / "lab.schedule.yaml",
    )
    assert job_run.run(project / "lab.schedule.yaml") == 0
    [target] = status(project).targets
    assert target.data_as_of is not None and target.data_as_of.startswith("2026-01-02T03:04")
    assert target.rows_read == 192


def test_a_layout_targets_tiles_are_read_as_its_render_reads_them(project):
    """A layout's tiles are drawn with the layout's configs, so its job finds their data
    the same way, whatever configs the tiles' own folder has."""
    tiles = project / "tiles"
    tiles.mkdir()
    shutil.copy(project / "p.yaml", tiles / "p.yaml")
    shutil.copy(project / "p.parquet", tiles / "p.parquet")
    (tiles / "forgegraph.toml").write_text("packs = ['forgegraph_base', 'not_installed']\n")
    layout = {
        "name": "tiled",
        "version": 0,
        "description": "",
        "extends": "forgegraph_base/base_layout",
        "fixed_parameters": "None",
        "variable_parameters": {
            "tabs": {"T": {"grid": {"areas": [["p"]]}, "tiles": {"p": "tiles/p.yaml"}}}
        },
    }
    dump(layout, project / "tiled.layout.yaml")
    dump(
        schedule_doc(targets={"files": ["tiled.layout.yaml"], "output_folder": "out"}),
        project / "lab.schedule.yaml",
    )
    assert job_run.run(project / "lab.schedule.yaml") == 0
    [target] = status(project).targets
    assert [Path(d.path).name for d in target.data] == ["p.parquet"]
    assert target.data_as_of is not None


# --- the stale banner, under a simulated clock ------------------------------------------------


def _stale(page: Path, now: datetime) -> str | None:
    """What the page's banner says at `now`, by running its own script's staleMessage."""
    text = page.read_text()
    script = re.search(rf'<script id="{STALE_ID}-script">(.*?)</script>', text, re.S)
    data = re.search(
        rf'<script type="application/json" id="{STALE_ID}-data">(.*?)</script>', text, re.S
    )
    assert script and data
    function = script[1].split("(function ()")[0]
    values = json.loads(data[1])
    call = (
        f"console.log(JSON.stringify(staleMessage(Date.parse({json.dumps(values['as_of'])}), "
        f"{int(now.timestamp() * 1000)}, {values['stale_after_hours']}, "
        f"{json.dumps(values['cadence'])})))"
    )
    node = shutil.which("node")
    assert node is not None
    done = subprocess.run([node, "-e", function + call], capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


@needs_node
def test_failure_injection_status_hook_and_banner(project):
    """The data file disappears: the status file records the error, on_failure fires, and
    the last good page's banner turns stale on schedule."""
    hook = project / "fired.txt"
    command = [sys.executable, "-c", f"open({str(hook)!r}, 'w').write('fired')"]
    dump(schedule_doc(on_failure={"command": command}), project / "lab.schedule.yaml")
    made = datetime(2026, 10, 19, 5, 0).astimezone()  # Monday
    os.utime(project / "p.parquet", (made.timestamp(), made.timestamp()))
    assert job_run.run(project / "lab.schedule.yaml") == 0
    good = status(project)
    page = project / "out" / "p.html"
    assert _stale(page, made + timedelta(hours=29)) is None  # daily: stale after 30 hours
    (project / "p.parquet").unlink()
    assert job_run.run(project / "lab.schedule.yaml") == 1
    s = status(project)
    assert s.last_attempt.result == "failure" and s.consecutive_failures == 1
    assert s.last_success == good.last_success
    assert s.targets[0].problems[0].startswith("data.file: no file at")
    assert hook.read_text() == "fired"
    late = _stale(page, made + timedelta(hours=31))
    assert late == "This page's data is 31 hours old; it should update daily at 06:00."
    assert _stale(page, made + timedelta(days=3)) == (
        "This page's data is 3 days old; it should update daily at 06:00."
    )


@needs_node
def test_a_weekday_job_isnt_stale_over_the_weekend(project):
    weekdays = ["mon 06:00", "tue 06:00", "wed 06:00", "thu 06:00", "fri 06:00"]
    dump(
        schedule_doc(cadence={"interval_unit": "week", "at": weekdays}),
        project / "lab.schedule.yaml",
    )
    friday = datetime(2026, 10, 23, 5, 30).astimezone()
    os.utime(project / "p.parquet", (friday.timestamp(), friday.timestamp()))
    job_run.run(project / "lab.schedule.yaml")
    page = project / "out" / "p.html"
    assert _stale(page, friday + timedelta(days=3, hours=1)) is None  # Monday morning
    assert _stale(page, friday + timedelta(days=4)) is not None
