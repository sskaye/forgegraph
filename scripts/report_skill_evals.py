"""Write the skill evals' review page from run_skill_evals.py results.

uv run python scripts/report_skill_evals.py OUT.html LABEL=results.json [LABEL=results.json ...]

Each LABEL is a column (e.g. "Opus, with skill"). A case's cell is its pass rate over that
column's runs; under the table, every failed check with its evidence. Keeps a Forgemark
comment block the page already has.
"""

from __future__ import annotations

import html
import json
import statistics
import sys
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(__file__).parents[1]
COMMENTS = "<!-- forgemark-comments"
STYLE = """
:root { --fg:#1f2328; --muted:#57606a; --line:#d0d7de; --soft:#f6f8fa; --bg:#fff;
        --good:#1a7f37; --bad:#cf222e; }
body { font-family:-apple-system,"Segoe UI",system-ui,sans-serif; color:var(--fg);
       background:var(--bg); margin:0 auto; max-width:1200px; padding:1.5rem 24px 3rem;
       line-height:1.5; }
table { border-collapse:collapse; width:100%; font-size:.9rem; margin:.5rem 0 1.5rem; }
th, td { border-bottom:1px solid var(--line); padding:.35rem .5rem; text-align:left;
         vertical-align:top; }
th { background:var(--soft); }
td.rate { white-space:nowrap; font-variant-numeric:tabular-nums; }
.all { color:var(--good); } .none { color:var(--bad); }
li { margin:.2rem 0; } .muted { color:var(--muted); }
"""


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def _rate(runs: list[dict]) -> str:
    if not runs:
        return '<td class="rate muted">not run</td>'
    passed = sum(r["passed"] for r in runs)
    cls = "all" if passed == len(runs) else "none" if passed == 0 else ""
    return f'<td class="rate {cls}">{passed}/{len(runs)}</td>'


def page(columns: list[tuple[str, list[dict]]]) -> str:
    cases = YAML(typ="safe").load((ROOT / "evals" / "skill" / "cases.yaml").read_text())["cases"]
    head = "".join(f"<th>{_e(label)}</th>" for label, _ in columns)
    rows = []
    for case in cases:
        request = " → ".join(case["turns"])
        cells = "".join(_rate([r for r in runs if r["case"] == case["id"]]) for _, runs in columns)
        cid = case["id"]
        rows.append(f'<tr id="case-{cid}"><td>{_e(cid)}</td><td>{_e(request)}</td>{cells}</tr>')
    totals = []
    for _, runs in columns:
        passed = sum(r["passed"] for r in runs)
        totals.append(f'<td class="rate">{passed}/{len(runs)}</td>')
    rows.append(f'<tr id="total"><th colspan="2">All runs</th>{"".join(totals)}</tr>')
    summary = []
    for label, runs in columns:
        if not runs:
            continue
        secs = statistics.mean(r["seconds"] for r in runs)
        cost = statistics.mean(r["cost_usd"] for r in runs)
        models = sorted({r["model"] for r in runs if r["model"]})
        summary.append(
            f"<li>{_e(label)}: {len(runs)} runs, {_e(', '.join(models))}; "
            f"{secs:.0f} s and ${cost:.2f} of usage a run on average</li>"
        )
    failures = []
    for label, runs in columns:
        items = []
        for r in sorted(runs, key=lambda r: (r["case"], r["number"])):
            if r["passed"]:
                continue
            if r["error"]:
                items.append(f"<li>{_e(r['case'])} #{r['number']}: {_e(r['error'])}</li>")
                continue
            for c in r["checks"]:
                if not c["passed"]:
                    items.append(
                        f"<li>{_e(r['case'])} #{r['number']}: {_e(c['name'])}: "
                        f'<span class="muted">{_e(c["evidence"][:300])}</span></li>'
                    )
        if items:
            failures.append(f"<h3>{_e(label)}</h3>\n<ul>\n" + "\n".join(items) + "\n</ul>")
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>Skill evals</title>\n<style>{STYLE}</style></head><body>\n"
        '<h1 id="title">Skill evals</h1>\n'
        '<p id="intro">Each case is a request (or a conversation) about a file from '
        "examples/sample-data, run through Claude Code in a fresh project folder and graded "
        "by script. A cell is the share of runs that passed every check: the graph's "
        "GraphSpec values and data, a clean lint on redrawing, a graph made with ForgeGraph "
        "and looked at, the files asked for in the folder, one GraphSpec kept across turns, "
        "no theme or format created unless asked, the data left unchanged, and for "
        "unsupported requests, what the reply says.</p>\n"
        f'<ul id="runs">\n{chr(10).join(summary)}\n</ul>\n'
        f'<table id="results">\n<tr><th>Case</th><th>Request</th>{head}</tr>\n'
        + "\n".join(rows)
        + "\n</table>\n"
        + '<h2 id="failures">Failed checks</h2>\n'
        + ("\n".join(failures) or "<p>None.</p>")
        + "\n</body></html>\n"
    )


def main() -> None:
    out = Path(sys.argv[1])
    columns = []
    for arg in sys.argv[2:]:
        label, path = arg.split("=", 1)
        columns.append((label, json.loads(Path(path).read_text())))
    text = page(columns)
    if out.exists() and COMMENTS in (old := out.read_text(encoding="utf-8")):
        text = text.rstrip("\n") + "\n\n" + old[old.index(COMMENTS) :]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
