"""Run the skill evals: each case in evals/skill/cases.yaml through Claude Code in print mode,
in a fresh project folder holding the case's data from examples/sample-data. Scored by script.

uv run python scripts/run_skill_evals.py --models opus,sonnet,haiku   # every case on each model
uv run python scripts/run_skill_evals.py --without-skill              # the baseline
uv run python scripts/run_skill_evals.py --cases iris-scatter,stocks --runs 2
uv run python scripts/run_skill_evals.py --models opus --out <folder> --resume   # finish a set
uv run python scripts/run_skill_evals.py --models opus --out <folder> --regrade  # grade again

The agent can't add jobs to this machine's scheduler: launchctl, crontab, systemctl and
schtasks are stand-ins on its PATH that record each call and refuse, and any LaunchAgent left
afterwards that runs something in the case's folder is removed and reported.

Runs use the Claude Code login on this machine: no API key, no separate API charges. Each
run's transcripts and files are kept under --out (in the system's temporary folder, outside
the repository). Each run's result is saved as it finishes, as run-<n>.result.json beside
its folder, so a crash or an interrupted set keeps what's done, and --resume runs only what
isn't; results-<config>.json, written at the end, holds every check's result and evidence.
The agent runs a non-editable copy of ForgeGraph built from this checkout, and the run warns
if the repository changes while it goes.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ruamel.yaml import YAML

ROOT = Path(__file__).parents[1]
EVALS = ROOT / "evals" / "skill"
DATA = ROOT / "examples" / "sample-data"
PACKS = (ROOT / "examples" / "packs",)  # where a case's folder packs are copied from
IMAGES = (".png", ".pdf", ".svg", ".jpg", ".jpeg", ".tif", ".tiff", ".html")  # .html: a page
TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"]
TURN_TIMEOUT_S = 900  # a turn that takes longer than 15 minutes has gone wrong
REPORTED_ONLY = ("haiku",)  # models whose results are reported but don't decide changes
SCHEDULERS = ("launchctl", "crontab", "systemctl", "schtasks")  # stand-ins: see the docstring
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
MAIN_CONFIG_VARIABLE = "FORGEGRAPH_CONFIG"  # each case's main config (forgegraph.packs)
_GRADING = threading.Lock()


@dataclass
class Check:
    name: str
    passed: bool
    evidence: str


@dataclass
class Run:
    case: str
    config: str  # with_skill or without_skill
    number: int
    model_asked: str = ""  # the --models entry this run used; "" for Claude Code's default
    checks: list[Check] = field(default_factory=list)
    reply: str = ""
    model: str = ""
    seconds: float = 0.0
    cost_usd: float = 0.0
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.error and all(c.passed for c in self.checks)


def _result_path(out: Path, config: str, model: str | None, case_id: str, number: int) -> Path:
    """Where a run's result is saved as soon as it finishes."""
    return out / config / (model or "default") / case_id / f"run-{number}.result.json"


def _save(run: Run, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(run) | {"passed": run.passed}, indent=1), encoding="utf-8")


def _load(path: Path) -> Run:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("passed", None)
    data["checks"] = [Check(**c) for c in data["checks"]]
    return Run(**data)


def _hashes(folder: Path, names: list[str]) -> dict[str, str]:
    """The case's data files' hashes in the folder, to show they weren't changed."""
    return {
        n: hashlib.sha256((folder / n).read_bytes()).hexdigest()
        if (folder / n).exists()
        else "missing"
        for n in names
    }


def _project_files(ws: Path) -> list[Path]:
    return [p for p in ws.rglob("*") if p.is_file() and ".claude" not in p.relative_to(ws).parts]


def _events(transcript: Path) -> list[dict[str, Any]]:
    out = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _tool_uses(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    uses = []
    for e in events:
        if e.get("type") != "assistant":
            continue
        for block in e.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                uses.append(block)
    return uses


def _renders(use: dict[str, Any], ws: Path) -> bool:
    """`forgegraph render <file>` for a file in the project: not --help, a copy elsewhere or
    `job run`, which redraws a GraphSpec without changing it."""
    if use.get("name") != "Bash":
        return False
    command = str(use.get("input", {}).get("command", ""))
    for args in re.findall(r"forgegraph render([^;&|\n]*)", command):
        files = [a.strip("\"'") for a in args.split() if not a.startswith("-")]
        if not files:
            continue
        path = Path(files[0])
        if path.is_absolute():
            if path.is_relative_to(ws):
                return True
        elif any(p.name == path.name for p in _project_files(ws)):
            return True
    return False


def _job_runs(use: dict[str, Any]) -> bool:
    """`forgegraph job run`, which draws a schedule's targets."""
    command = str(use.get("input", {}).get("command", ""))
    return (
        use.get("name") == "Bash" and "forgegraph job run " in command and "--help" not in command
    )


def _draws(use: dict[str, Any], ws: Path, expect: dict[str, Any]) -> bool:
    """A render, or for a drawing on a blank canvas (which a Python script makes), a run of
    Python."""
    if _renders(use, ws):
        return True
    command = str(use.get("input", {}).get("command", ""))
    return bool(expect.get("nonstandard")) and use.get("name") == "Bash" and "python" in command


def _looks(use: dict[str, Any]) -> bool:
    path = str(use.get("input", {}).get("file_path", ""))
    return use.get("name") == "Read" and path.lower().endswith(IMAGES)


def _given(ws: Path) -> set[str]:
    """The files the case put in its folder (its data, packs and config), by relative path."""
    listed = ws.parent / f"{ws.name}.setup.txt"
    return set(listed.read_text().splitlines()) if listed.is_file() else set()


def _specs(ws: Path) -> list[tuple[Path, str, dict[str, Any]]]:
    """The spec files the agent wrote, each with its kind: layout or schedule by its suffix;
    theme or format by its pack folder; GraphSpec if it names a graph type or extends a
    GraphSpec; otherwise "style", a theme or format outside a pack."""
    from forgegraph.spec.documents import registry_for

    yaml = YAML(typ="safe")
    given, out = _given(ws), []
    for p in _project_files(ws):
        if p.suffix not in (".yaml", ".yml") or str(p.relative_to(ws)) in given:
            continue
        try:
            doc = yaml.load(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict) or "fixed_parameters" not in doc or "name" not in doc:
            continue
        variable = doc.get("variable_parameters")
        chosen = variable.get("specifications") if isinstance(variable, dict) else None
        if p.name.endswith(".layout.yaml"):
            kind = "layout"
        elif p.name.endswith(".schedule.yaml"):
            kind = "schedule"
        elif p.parent.name in ("themes", "formats"):
            kind = p.parent.name[:-1]
        elif isinstance(chosen, dict) and "graph_type" in chosen:
            kind = "graphspec"
        else:
            try:
                extends_graphspec = (
                    str(doc.get("extends")) in registry_for(p.parent).docs["graphspec"]
                )
            except Exception:
                extends_graphspec = False
            kind = "graphspec" if extends_graphspec else "style"
        out.append((p, kind, doc))
    return out


def _graphspecs(ws: Path) -> list[Path]:
    """The GraphSpecs the agent wrote, the last one written last."""
    found = [p for p, kind, _ in _specs(ws) if kind == "graphspec"]
    return sorted(found, key=lambda p: p.stat().st_mtime)


def _resolved(spec: Path) -> dict[str, dict[str, Any]]:
    from forgegraph.spec.documents import explain, registry_for
    from forgegraph.spec.documents import load as load_yaml

    doc = load_yaml(spec)
    reg = registry_for(spec.parent).copy()
    reg.add("graphspec", doc, spec)
    return {kind: {p: r.value for p, r in v.items()} for kind, v in explain(doc, reg).items()}


def _matches(actual: Any, expected: Any) -> bool:
    def norm(v: Any) -> Any:
        if isinstance(v, float) and v.is_integer():
            return int(v)
        if isinstance(v, list):
            return [norm(x) for x in v]
        return v

    if isinstance(expected, dict) and "in" in expected:
        return any(norm(actual) == norm(e) for e in expected["in"])
    if isinstance(expected, dict) and "contains" in expected:
        items = actual if isinstance(actual, list) else [actual]
        return expected["contains"] in items
    if isinstance(expected, dict) and "matches" in expected:
        items = actual if isinstance(actual, list) else [actual]
        return any(re.search(expected["matches"], str(i), re.IGNORECASE) for i in items)
    if isinstance(expected, dict) and "lt" in expected:
        return isinstance(actual, int | float) and actual < expected["lt"]
    return norm(actual) == norm(expected)


def _created_styles(ws: Path) -> list[str]:
    """Themes and formats the agent made, in a pack or not, by name (a pack's without its
    pack)."""
    return sorted(
        str(doc["name"]) for _, kind, doc in _specs(ws) if kind in ("theme", "format", "style")
    )


def _drawn(final: Path) -> tuple[Any, pd.DataFrame | None, str]:
    """The final GraphSpec drawn, its Parquet data, and why either failed."""
    import forgegraph as fg
    from forgegraph.graph import data_path
    from forgegraph.spec.documents import load as load_yaml
    from forgegraph.spec.documents import registry_for

    try:
        graph = fg.render(final)
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"
    where = data_path(load_yaml(final), registry_for(final.parent), final.parent)
    frame = pd.read_parquet(where) if where is not None and where.is_file() else None
    return graph, frame, ""


def _named(ws: Path, suffix: str) -> list[Path]:
    """The project's files ending with suffix, oldest first."""
    found = [p for p in _project_files(ws) if p.name.endswith(suffix)]
    return sorted(found, key=lambda p: p.stat().st_mtime)


def _layout_checks(want: dict[str, Any], ws: Path, allowed: list[str]) -> list[Check]:
    """The final layout: it draws, its tabs and tiles, a spanning tile, a blank cell, its
    column widths, and its lint."""
    import forgegraph as fg
    from forgegraph.layout import _load
    from forgegraph.spec.layout import BLANK, tabs

    layouts = _named(ws, ".layout.yaml")
    if not layouts:
        return [Check("layout written", False, "no .layout.yaml in the project")]
    final = layouts[-1]
    try:
        drawn = fg.layout(final)
        doc, reg, _ = _load(final, None)
        listed = tabs(doc, reg)
    except Exception as e:
        return [Check("layout draws", False, f"{final.name}: {type(e).__name__}: {e}")]
    checks = [Check("layout draws", True, final.name)]
    places = [area for t in listed for area in t.places().values()]
    if "tabs" in want:
        checks.append(Check(f"{want['tabs']} tabs", len(listed) == want["tabs"], str(len(listed))))
    if "tiles" in want:
        checks.append(
            Check(f"{want['tiles']} tiles", len(places) == want["tiles"], str(len(places)))
        )
    if want.get("span"):
        spans = [a for a in places if a.rows > 1 or a.columns > 1]
        checks.append(Check("a tile spans cells", bool(spans), str(len(spans))))
    if want.get("blank"):
        blank = any(c == BLANK for t in listed for row in t.areas for c in row)
        checks.append(Check("a blank cell", blank, str([t.areas for t in listed])))
    if "widths" in want:
        got = listed[0].column_widths
        a, b = want["widths"]
        ok = got is not None and len(got) == 2 and abs(got[0] / got[1] - a / b) < 0.05
        checks.append(Check(f"column widths {a}:{b}", ok, str(got)))
    extra = [i for i in drawn.issues if i.check not in allowed]
    checks.append(
        Check(
            "layout lint clean",
            not extra,
            "; ".join(f"{i.check}: {i.message}" for i in drawn.issues) or "no issues",
        )
    )
    return checks


def _schedule_checks(want: dict[str, Any], ws: Path) -> list[Check]:
    """The final schedule: it loads, its runs over a week (or day), and whether it was run."""
    from datetime import datetime as moment

    from forgegraph.jobs import status as status_file
    from forgegraph.jobs.run import ScheduleError, load

    schedules = _named(ws, ".schedule.yaml")
    if not schedules:
        return [Check("schedule written", False, "no .schedule.yaml in the project")]
    final = schedules[-1]
    try:
        schedule = load(final)
    except ScheduleError as e:
        return [Check("schedule loads", False, f"{final.name}: {'; '.join(e.problems)}")]
    checks = [Check("schedule loads", True, final.name)]
    if "runs" in want:
        start = moment(2026, 10, 19)  # a Monday
        span = {"day": 1, "week": 7, "year": 366}[want.get("over", "week")]
        runs = list(schedule.cadence.runs(start, start + timedelta(days=span, seconds=-1)))
        fmt = "%b %d %H:%M" if want.get("over") == "year" else "%a %H:%M"
        got = [r.strftime(fmt) for r in runs]
        checks.append(Check(f"runs {want['runs']}", got == want["runs"], str(got)))
    if want.get("ran"):
        record = status_file.read(schedule.status_path)
        ok = record is not None and record.last_attempt.result == "success"
        checks.append(
            Check("ran once", ok, str(schedule.status_path) if record else "no status file")
        )
    return checks


def grade(case: dict[str, Any], ws: Path, transcripts: list[Path], before: dict) -> list[Check]:
    expect = case["expect"]
    after = _hashes(ws, case["data"])
    checks = [Check("data unchanged", after == before, json.dumps(after))]
    allowed = expect.get("themes", [])
    created = _created_styles(ws)
    checks.append(
        Check(
            "no theme or format created" if not allowed else f"only themes {allowed} created",
            all(n in allowed for n in created) and all(n in created for n in allowed),
            ", ".join(created) or "none",
        )
    )
    files = _project_files(ws)
    images = [p for p in files if p.suffix.lower() in IMAGES]
    turns = [_events(t) for t in transcripts]
    reply = ""
    for e in turns[-1] if turns else []:
        if e.get("type") == "result":
            reply = str(e.get("result", ""))
    if expect.get("graph"):
        import forgegraph as fg

        made = [p for p in images if p.suffix.lower() != ".jpeg"]
        records = {p.name: fg.load(p) is not None for p in made}
        checks.append(
            Check(
                "made with ForgeGraph",
                bool(made) and all(records.values()),
                json.dumps(records) if made else "no image in the project",
            )
        )
        if expect.get("nonstandard"):  # drawn on a blank canvas: recorded as non-standard
            marked = {p.name: bool((fg.load(p) or {}).get("nonstandard")) for p in made}
            checks.append(Check("drawn non-standard", any(marked.values()), json.dumps(marked)))
        if expect.get("nonstandard_pack"):  # drawn with a pack the main config doesn't list
            named = {p.name: (fg.load(p) or {}).get("nonstandard_packs", []) for p in made}
            checks.append(
                Check("drawn with a non-standard pack", any(named.values()), json.dumps(named))
            )
        looked, evidence = True, []
        must_look = expect.get("look_turns", list(range(1, len(turns) + 1)))
        for i, events in enumerate(turns, start=1):
            if i not in must_look:
                continue
            uses = _tool_uses(events)
            last = max((k for k, u in enumerate(uses) if _draws(u, ws, expect)), default=None)
            if last is None:  # drawn only by running the schedule, then each run is a draw
                last = max((k for k, u in enumerate(uses) if _job_runs(u)), default=None)
            if last is None:
                continue
            seen = any(_looks(u) for u in uses[last + 1 :])
            looked &= seen
            evidence.append(f"turn {i}: {'looked' if seen else 'rendered without looking'}")
        checks.append(Check("looked at the image", looked and bool(evidence), "; ".join(evidence)))
    specs = _graphspecs(ws)
    if expect.get("graph") and not expect.get("nonstandard"):  # a canvas drawing has none
        where = "no GraphSpec in the folder"
        ok = bool(specs) and bool(images)
        if specs:
            from forgegraph.graph import data_path
            from forgegraph.spec.documents import load as load_yaml
            from forgegraph.spec.documents import registry_for

            try:
                data = data_path(
                    load_yaml(specs[-1]), registry_for(specs[-1].parent), specs[-1].parent
                )
            except Exception as e:
                data, where = None, f"{type(e).__name__}: {e}"
            inside = (  # resolved both sides: macOS's temporary folder is a link
                data is not None and data.is_file() and ws.resolve() in data.resolve().parents
            )
            ok = ok and inside
            where = f"{specs[-1].relative_to(ws)}, data {data}, {len(images)} images"
        checks.append(Check("GraphSpec, data and graph in the folder", ok, where))
    if "lint" in expect or "values" in expect:
        if not specs:
            checks.append(Check("GraphSpec written", False, "no GraphSpec in the project"))
        else:
            final = specs[-1]
            if "lint" in expect:
                import forgegraph as fg

                try:
                    issues = fg.render(final).issues
                    extra = [i for i in issues if i.check not in expect["lint"]]
                    checks.append(
                        Check(
                            "lint clean",
                            not extra,
                            "; ".join(f"{i.check}: {i.message}" for i in issues) or "no issues",
                        )
                    )
                except Exception as e:  # a GraphSpec that doesn't draw fails the check
                    checks.append(Check("lint clean", False, f"{type(e).__name__}: {e}"))
            if "values" in expect:
                try:
                    values = _resolved(final)
                except Exception as e:
                    values = None
                    checks.append(Check("values", False, f"{type(e).__name__}: {e}"))
                if values is not None:
                    for key, want in expect["values"].items():
                        kind, path = key.split(":", 1)
                        found = values.get(kind, {})
                        if "*" in path:  # axis.*.x: either axis's value that matches
                            options = [found.get(path.replace("*", a)) for a in ("x", "y")]
                            actual = next((o for o in options if _matches(o, want)), options)
                        else:
                            actual = found.get(path, "<not a parameter>")
                        checks.append(
                            Check(
                                f"{key} = {want}",
                                _matches(actual, want),
                                f"{final.name}: {actual!r}",
                            )
                        )
    for want in expect.get("layers", []):
        layers: dict[str, dict[str, Any]] = {}
        evidence = "no GraphSpec in the project"
        if specs:
            try:
                layers = _resolved(specs[-1]).get("layers", {})
                evidence = json.dumps(layers, default=str)
            except Exception as e:
                evidence = f"{type(e).__name__}: {e}"
        ok = any(
            all(_matches(layer.get(k), v) for k, v in want.items()) for layer in layers.values()
        )
        checks.append(Check(f"a layer {want}", ok, evidence))
    data_checks = (
        "lines",
        "rows_plotted",
        "x_dates",
        "x_between",
        "y_above",
        "only",
        "tick_labels",
    )
    if specs and (any(k in expect for k in data_checks) or expect.get("categorical_color")):
        graph, frame, problem = _drawn(specs[-1])
        x = y = None
        if graph is not None:
            values = graph.values["graph_type"]
            x, y = values["axis.x.data.column"], values["axis.y.data.column"]
        if "lines" in expect:
            lines = [] if graph is None else graph.axes.lines
            series = sum(len(np.asarray(line.get_xdata())) > 0 for line in lines)
            checks.append(
                Check(
                    f"at least {expect['lines']} series",
                    series >= expect["lines"],
                    problem or f"{series} drawn",
                )
            )
        if "rows_plotted" in expect:
            rows = None if graph is None else graph.data.rows_plotted
            want = expect["rows_plotted"]
            ok = rows is not None and (
                rows <= want["max"] if isinstance(want, dict) else rows == want
            )
            checks.append(Check(f"rows plotted {want}", ok, problem or str(rows)))
        if expect.get("x_dates") or "x_between" in expect:
            ok, evidence = False, problem or "no data"
            if frame is not None and isinstance(x, str) and x in frame:
                ok = pd.api.types.is_datetime64_any_dtype(frame[x])
                evidence = f"{x}: {frame[x].dtype}"
                if ok and "x_between" in expect:
                    lo, hi = (pd.Timestamp(v) for v in expect["x_between"])
                    ok = bool(frame[x].dropna().between(lo, hi + pd.Timedelta(days=1)).all())
                    evidence += f", {frame[x].min()} to {frame[x].max()}"
            checks.append(
                Check("x is dates" + (" in range" if "x_between" in expect else ""), ok, evidence)
            )
        if "y_above" in expect:
            ok, evidence = False, problem or "no data"
            if frame is not None:
                cols = [y] if isinstance(y, str) else list(y or [])
                lows = {
                    c: float(np.nanmin(np.asarray(frame[c], dtype=float)))
                    for c in cols
                    if c in frame
                }
                ok = bool(lows) and all(v > expect["y_above"] for v in lows.values())
                evidence = json.dumps(lows)
            checks.append(Check(f"y above {expect['y_above']}", ok, evidence))
        for name, want in expect.get("tick_labels", {}).items():
            got: list[str] = []
            if graph is not None:
                axis = graph.axes.xaxis if name == "x" else graph.axes.yaxis
                got = [t.get_text() for t in axis.get_majorticklabels() if t.get_text()]
            checks.append(Check(f"{name} tick labels {want}", got == want, problem or str(got)))
        for column, allowed_values in expect.get("only", {}).items():
            ok, evidence = frame is not None, problem or "no data"
            if frame is not None:
                seen = sorted(map(str, frame[column].dropna().unique())) if column in frame else []
                ok = all(v in allowed_values for v in seen)
                evidence = f"{column}: {seen or 'not in the data'}"
            checks.append(Check(f"only {column} {allowed_values}", ok, evidence))
        if expect.get("categorical_color"):
            ok, evidence = False, problem or "no data"
            if graph is not None:
                values = graph.values["graph_type"]
                color = values["encoding.color"]
                kind = values["encoding.color_type"]
                text = (
                    frame is not None
                    and color in frame
                    and not pd.api.types.is_numeric_dtype(frame[color])
                )
                ok = kind == "categorical" or bool(text)
                evidence = f"encoding.color {color!r}, color_type {kind}"
            checks.append(Check("color is categorical", ok, evidence))
    if "numeric_columns" in expect:
        evidence, ok = "no GraphSpec in the project", False
        if specs:
            from forgegraph.graph import data_path
            from forgegraph.spec.documents import load as load_yaml
            from forgegraph.spec.documents import registry_for

            final = specs[-1]
            where = data_path(load_yaml(final), registry_for(final.parent), final.parent)
            if where is not None and where.is_file():
                frame = pd.read_parquet(where)
                kinds = {
                    c: str(frame[c].dtype) if c in frame else "missing"
                    for c in expect["numeric_columns"]
                }
                ok = all(c in frame and pd.api.types.is_numeric_dtype(frame[c]) for c in kinds)
                evidence = f"{where.name}: {kinds}"
            else:
                evidence = f"{final.name}: data.file names no file ({where})"
        checks.append(Check(f"numeric columns {expect['numeric_columns']}", ok, evidence))
    for pattern in expect.get("files", []):
        hits = [
            str(p.relative_to(ws))
            for p in files
            if fnmatch.fnmatch(str(p.relative_to(ws)), pattern)
            or fnmatch.fnmatch(p.name, pattern.split("/")[-1])
        ]
        checks.append(Check(f"file {pattern}", bool(hits), ", ".join(hits) or "none"))
    if expect.get("one_graphspec"):
        checks.append(
            Check(
                "kept one GraphSpec",
                len(specs) == 1,
                ", ".join(str(p.relative_to(ws)) for p in specs) or "none",
            )
        )
    if expect.get("no_other_tool"):
        import forgegraph as fg

        others = [p.name for p in images if p.suffix.lower() != ".jpeg" and fg.load(p) is None]
        checks.append(
            Check("no graph made without ForgeGraph", not others, ", ".join(others) or "none")
        )
    if expect.get("no_graph"):
        checks.append(
            Check("no graph made", not images, ", ".join(p.name for p in images) or "none")
        )
    if "layout" in expect:
        checks += _layout_checks(expect["layout"], ws, expect.get("lint", []))
    if "schedule" in expect:
        checks += _schedule_checks(expect["schedule"], ws)
    for words in expect.get("says", []):
        found = [w for w in words if w.lower() in reply.lower()]
        checks.append(Check(f"says one of {words}", bool(found), ", ".join(found) or "none"))
    return checks


def _install_copy(out: Path) -> Path:
    """A non-editable install of ForgeGraph from this checkout, in its own environment under
    out: the agent runs this copy, so nothing it does can change the repository's files.
    Returns the environment's bin folder."""
    subprocess.run(["uv", "build", "--wheel", "-q", "-o", str(out / "dist")], cwd=ROOT, check=True)
    [wheel] = sorted((out / "dist").glob("forgegraph-*.whl"))
    venv = out / "venv"
    subprocess.run(["uv", "venv", "-q", "--python", "3.12", str(venv)], check=True)
    subprocess.run(
        ["uv", "pip", "install", "-q", "--python", str(venv / "bin" / "python"), str(wheel)],
        check=True,
    )
    return venv / "bin"


def _repo_state() -> str:
    """The repository's uncommitted changes, to catch a run that edits it."""
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    diff = subprocess.run(["git", "diff"], cwd=ROOT, capture_output=True, check=True).stdout
    return status + hashlib.sha256(diff).hexdigest()


def run_one(
    case: dict[str, Any],
    config: str,
    number: int,
    out: Path,
    model: str | None,
    bin_: Path,
    closing: str,
) -> Run:
    """One case, one model, its result saved as soon as it's known: a run the runner itself
    fails on is saved with that error, and doesn't stop the others."""
    try:
        run = _run_one(case, config, number, out, model, bin_, closing)
    except Exception as e:
        run = Run(case["id"], config, number, model_asked=model or "")
        run.error = f"runner: {type(e).__name__}: {e}"
    _save(run, _result_path(out, config, model, case["id"], number))
    return run


def _run_one(
    case: dict[str, Any],
    config: str,
    number: int,
    out: Path,
    model: str | None,
    bin_: Path,
    closing: str,
) -> Run:
    """One case, one model: closing ends the last turn unless the case sets closing: false."""
    run = Run(case["id"], config, number, model_asked=model or "")
    ws = out / config / (model or "default") / case["id"] / f"run-{number}"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    for name in case["data"]:
        shutil.copy2(DATA / name, ws / name)
    for name in case.get("packs", []):  # folder packs, and the project config allowing them
        source = next(base / name for base in PACKS if (base / name).is_dir())
        shutil.copytree(source, ws / name, ignore=shutil.ignore_patterns("catalogs"))
    if "config" in case:
        listed = ", ".join(f'"{p}"' for p in case["config"])
        (ws / "forgegraph.toml").write_text(f"packs = [{listed}]\n")
    main = ws.parent / f"{ws.name}.main.toml"  # the case's own, never this machine's
    from forgegraph.packs import BUILT_IN

    named = case.get("main", [*BUILT_IN, *(str(ws / n) for n in case.get("packs", []))])
    main.write_text("packs = [" + ", ".join(f"'{p}'" for p in named) + "]\n")  # literal strings
    setup = [str(p.relative_to(ws)) for p in _project_files(ws)]
    (ws.parent / f"{ws.name}.setup.txt").write_text("\n".join(setup))
    if config == "with_skill":  # the installed copy's skill, as a user would get it
        subprocess.run(
            [
                str(bin_ / "forgegraph"),
                "skill",
                "install",
                "--dest",
                str(ws / ".claude" / "skills"),
            ],
            check=True,
            capture_output=True,
        )
    before = _hashes(ws, case["data"])
    shims = ws.parent / f"{ws.name}.shims"
    shims.mkdir(exist_ok=True)
    log = ws.parent / f"{ws.name}.schedulers.log"
    for name in SCHEDULERS:  # stand-ins that record each call and refuse it
        shim = shims / name
        shim.write_text(
            f'#!/bin/sh\necho "{name} $*" >> "{log}"\necho "{name}: not in evals" >&2\nexit 1\n'
        )
        shim.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{shims}{os.pathsep}{bin_}{os.pathsep}{env.get('PATH', '')}"
    env.pop("VIRTUAL_ENV", None)
    env[MAIN_CONFIG_VARIABLE] = str(main)
    transcripts = []
    start = time.monotonic()
    for i, turn in enumerate(case["turns"]):
        if i == len(case["turns"]) - 1 and case.get("closing", True):
            turn += closing
        cmd = [
            "claude", "-p", turn,
            "--output-format", "stream-json", "--verbose",
            "--permission-mode", "dontAsk", "--allowedTools", *TOOLS,
            "--setting-sources", "project", "--strict-mcp-config",
        ]  # fmt: skip
        if i:
            cmd.append("--continue")
        if model:
            cmd += ["--model", model]
        transcript = ws.parent / f"run-{number}.turn-{i + 1}.jsonl"
        try:
            done = subprocess.run(
                cmd, cwd=ws, env=env, capture_output=True, text=True, timeout=TURN_TIMEOUT_S
            )
        except subprocess.TimeoutExpired:
            run.error = f"turn {i + 1} timed out"
            break
        transcript.write_text(done.stdout, encoding="utf-8")
        transcripts.append(transcript)
        for e in _events(transcript):
            if e.get("type") == "system" and e.get("model"):
                run.model = e["model"]
            if e.get("type") == "result":
                run.cost_usd += float(e.get("total_cost_usd") or 0)
                run.reply = str(e.get("result", ""))
        if done.returncode != 0 and not run.reply:
            run.error = f"turn {i + 1}: claude exited {done.returncode}: {done.stderr[-300:]}"
            break
    run.seconds = round(time.monotonic() - start, 1)
    left = _left_agents(ws)
    if not run.error:
        with _GRADING:  # grading reads the case's main config; runs share this process
            earlier = os.environ.get(MAIN_CONFIG_VARIABLE)
            os.environ[MAIN_CONFIG_VARIABLE] = str(main)
            try:
                run.checks = grade(case, ws, transcripts, before)
            except Exception as e:  # a grading bug fails this run, not the whole set
                run.checks = [Check("graded", False, f"{type(e).__name__}: {e}")]
            finally:
                if earlier is None:
                    del os.environ[MAIN_CONFIG_VARIABLE]
                else:
                    os.environ[MAIN_CONFIG_VARIABLE] = earlier
        if left:
            run.checks.append(Check("no LaunchAgent left", False, ", ".join(left)))
    return run


def _left_agents(ws: Path) -> list[str]:
    """Remove any LaunchAgent that runs something in ws; return their names."""
    import plistlib

    found = []
    for plist in LAUNCH_AGENTS.glob("*.plist"):
        try:
            args = plistlib.loads(plist.read_bytes()).get("ProgramArguments", [])
        except Exception:
            continue
        if any(str(ws.resolve()) in str(Path(a).resolve()) for a in args if "/" in str(a)):
            subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(plist)], check=False)
            plist.unlink(missing_ok=True)
            found.append(plist.name)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--runs", type=int, default=1, help="Runs of each case on each model.")
    parser.add_argument("--cases", help="Comma-separated case ids (default: all).")
    parser.add_argument("--without-skill", action="store_true", help="The baseline.")
    parser.add_argument(
        "--models", help="Comma-separated Claude Code --model values (default: its own)."
    )
    parser.add_argument("--jobs", type=int, default=4, help="Runs at a time.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep the runs --out already has a result for, except the runner's own failures.",
    )
    parser.add_argument(
        "--regrade",
        action="store_true",
        help="Grade the runs --out holds again, with the current checks, without running them.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(tempfile.gettempdir())  # outside the repo: the agent mustn't find its code
        / "forgegraph-skill-evals"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%S"),
    )
    args = parser.parse_args()
    spec = YAML(typ="safe").load((EVALS / "cases.yaml").read_text(encoding="utf-8"))
    cases, closing = spec["cases"], str(spec.get("closing", ""))
    if args.cases:
        wanted = args.cases.split(",")
        unknown = [c for c in wanted if c not in {x["id"] for x in cases}]
        if unknown:
            sys.exit(f"unknown cases: {', '.join(unknown)}")
        cases = [c for c in cases if c["id"] in wanted]
    config = "without_skill" if args.without_skill else "with_skill"
    models: list[str | None] = list(args.models.split(",")) if args.models else [None]
    jobs = [(c, m, n) for m in models for c in cases for n in range(1, args.runs + 1)]
    if args.regrade:
        held = [
            (c, m, n) for c, m, n in jobs if _result_path(args.out, config, m, c["id"], n).is_file()
        ]
        for c, m, n in jobs:
            if (c, m, n) not in held:
                print(f"skipped {m or 'default'} {c['id']} #{n}: no result in {args.out}")
        _report([_regrade(c, config, n, args.out, m) for c, m, n in held], models, args, config)
        return
    args.out.mkdir(parents=True, exist_ok=True)
    bin_ = _install_copy(args.out)
    repo = _repo_state()
    done: dict[tuple[str, str, int], Run] = {}
    if args.resume:
        for c, m, n in jobs:
            saved = _result_path(args.out, config, m, c["id"], n)
            if saved.is_file():
                kept = _load(saved)
                if not kept.error.startswith("runner:"):  # the runner's own failures run again
                    done[c["id"], m or "", n] = kept
    todo = [(c, m, n) for c, m, n in jobs if (c["id"], m or "", n) not in done]
    kept = f" ({len(done)} kept from before)" if done else ""
    print(f"{len(jobs)} runs{kept}, {config}, into {args.out}", flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [
            pool.submit(run_one, c, config, n, args.out, m, bin_, closing) for c, m, n in todo
        ]
        for f in as_completed(futures):  # each is saved already; this reports it
            r = f.result()
            done[r.case, r.model_asked, r.number] = r
            mark = "pass" if r.passed else "FAIL"
            failed = [c.name for c in r.checks if not c.passed]
            print(
                f"{mark} {r.model_asked or 'default'} {r.case} #{r.number} ({r.seconds:.0f}s) "
                f"{r.error or ', '.join(failed)}",
                flush=True,
            )
    results = [done[c["id"], m or "", n] for c, m, n in jobs]  # in the cases' order
    if _repo_state() != repo:
        print("\nTHE REPOSITORY CHANGED DURING THE RUNS: check `git status` before trusting them")
    _report(results, models, args, config)


def _regrade(case: dict[str, Any], config: str, number: int, out: Path, model: str | None) -> Run:
    """A finished run graded again from its folder and transcripts, with the current checks;
    one that ended in an error stays as it was."""
    saved = _result_path(out, config, model, case["id"], number)
    run = _load(saved)
    if run.error:
        return run
    ws = saved.with_name(f"run-{number}")
    transcripts = sorted(ws.parent.glob(f"run-{number}.turn-*.jsonl"))
    with _GRADING:
        earlier = os.environ.get(MAIN_CONFIG_VARIABLE)
        os.environ[MAIN_CONFIG_VARIABLE] = str(ws.parent / f"{ws.name}.main.toml")
        try:
            run.checks = grade(case, ws, transcripts, _hashes(DATA, case["data"]))
        except Exception as e:
            run.checks = [Check("graded", False, f"{type(e).__name__}: {e}")]
        finally:
            if earlier is None:
                del os.environ[MAIN_CONFIG_VARIABLE]
            else:
                os.environ[MAIN_CONFIG_VARIABLE] = earlier
    _save(run, saved)
    mark = "pass" if run.passed else "FAIL"
    failed = [c.name for c in run.checks if not c.passed]
    print(f"{mark} {run.model_asked or 'default'} {run.case} #{number} {', '.join(failed)}")
    return run


def _report(results: list[Run], models: list[str | None], args: Any, config: str) -> None:
    path = args.out / f"results-{config}.json"
    path.write_text(json.dumps([asdict(r) | {"passed": r.passed} for r in results], indent=1))
    by_case: dict[str, list[Run]] = {}
    for r in results:
        by_case.setdefault(r.case, []).append(r)
    passed = sum(r.passed for r in results)
    print(f"\n{passed}/{len(results)} runs passed; results in {path}")
    for model in models:
        mine = [r for r in results if r.model_asked == (model or "")]
        note = " (reported only)" if model in REPORTED_ONLY else ""
        print(f"  {model or 'default'}{note}: {sum(r.passed for r in mine)}/{len(mine)} passed")
    for case_id, runs in by_case.items():
        marks = ", ".join(
            f"{r.model_asked or 'default'} {'pass' if r.passed else 'FAIL'}" for r in runs
        )
        print(f"  {case_id}: {marks}")


if __name__ == "__main__":
    main()
