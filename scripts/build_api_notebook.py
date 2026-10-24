"""Build review/phase-02/api.ipynb: a short tour of the Python API, with outputs filled in.

uv run python scripts/build_api_notebook.py
"""

from __future__ import annotations

import ast
import base64
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[1]

CELLS: list[tuple[str, str]] = [
    (
        "markdown",
        "# ForgeGraph: the Python API\n\nA short tour for the phase 3 review. All data here is synthetic.",
    ),
    (
        "code",
        """import numpy as np
import pandas as pd

import forgegraph as fg

rng = np.random.default_rng(1)
rows = []
for cell, ocv, r, a in [("Cell A", 1.62, 0.0030, 0.050), ("Cell B", 1.66, 0.0045, 0.045),
                        ("Cell C", 1.70, 0.0036, 0.060), ("Benchmark", 1.60, 0.0024, 0.040)]:
    for i in np.linspace(0, 140 if cell == "Benchmark" else 100, 12):
        rows.append({"cell": cell, "current_density": i,
                     "cell_voltage": ocv - a * np.log1p(i / 2) - r * i + rng.normal(0, 0.002)})
df = pd.DataFrame(rows)
df.head()""",
    ),
    (
        "markdown",
        "## One call draws a graph\n\n`fg.xy` takes a DataFrame and the columns. Any other parameter is set by its path in `parameters`. A notebook shows the result directly.",
    ),
    (
        "code",
        """g = fg.xy(
    df, x="current_density", y="cell_voltage", color="cell", title="Polarization, 60 °C",
    parameters={
        "benchmark.data_column": "cell", "benchmark.value": "Benchmark",
        "axis.x.title": "Cell Current (mA/cm^2)", "axis.y.title": "Cell Voltage (V)",
    },
)
g""",
    ),
    (
        "markdown",
        "## What it did\n\nThe graph records how its series were named, any warnings, and the data it plotted.",
    ),
    (
        "code",
        """print("series named by:", g.labelling)
print("warnings:", g.warnings)
print(g.data)""",
    ),
    (
        "markdown",
        "## Saving, and getting the GraphSpec back\n\nSaving writes the format's file types, each carrying an invisible record. `fg.load` reads it back, GraphSpec included.",
    ),
    (
        "code",
        """saved = g.save("polarization")
record = fg.load(saved[0])
print(saved)
print(record["level"], record["created"], record["data"]["rows_plotted"], "rows plotted")
record["graphspec"]["variable_parameters"]["specifications"]""",
    ),
    (
        "markdown",
        "## A GraphSpec as data\n\n`fg.graphspec` builds the same document a GraphSpec file holds; `fg.render` draws it. Here: markers only, on log axes.",
    ),
    (
        "code",
        """spec = fg.graphspec(
    "scatter", "xy", title="Markers only, log x",
    settings={"axis.x.data.column": "current_density", "axis.y.data.column": "cell_voltage",
              "encoding.color": "cell", "mark.line.show": False, "axis.x.scale": "log",
              "axis.x.min": 1.0},
)
fg.render(spec, df[df["current_density"] > 0])""",
    ),
    (
        "markdown",
        "## Mistakes name the parameter\n\nValidation runs before drawing, and every problem says where it is.",
    ),
    (
        "code",
        """try:
    fg.xy(df, x="current", y="cell_voltage", parameters={"axis.x.scale": "logarithmic"})
except fg.SpecError as e:
    print(e)""",
    ),
    (
        "markdown",
        "## The escape hatch\n\nDrawing on the figure with plain matplotlib is allowed, but the graph is then non-standard: saving watermarks it and says so in its record.",
    ),
    (
        "code",
        """g2 = fg.xy(df, x="current_density", y="cell_voltage", color="cell")
g2.axes.axhline(1.3, color="red")
print("non-standard:", g2.nonstandard)
g2.save("annotated.png")
print(fg.load("annotated.png")["nonstandard"])
g2""",
    ),
]


def _run(source: str, namespace: dict) -> list[dict]:
    tree = ast.parse(source)
    last = tree.body[-1] if tree.body and isinstance(tree.body[-1], ast.Expr) else None
    body = tree.body[:-1] if last is not None else tree.body
    out = io.StringIO()
    outputs: list[dict] = []
    with contextlib.redirect_stdout(out):
        exec(compile(ast.Module(body=body, type_ignores=[]), "<cell>", "exec"), namespace)
        value = (
            eval(compile(ast.Expression(last.value), "<cell>", "eval"), namespace) if last else None
        )
    if out.getvalue():
        outputs.append(
            {
                "output_type": "stream",
                "name": "stdout",
                "text": out.getvalue().splitlines(keepends=True),
            }
        )
    if value is not None:
        data = {"text/plain": [repr(value)[:300]]}
        if hasattr(value, "_repr_png_"):
            data = {
                "image/png": base64.b64encode(value._repr_png_()).decode(),
                "text/plain": ["<Graph>"],
            }
        elif hasattr(value, "_repr_html_"):
            data["text/html"] = value._repr_html_().splitlines(keepends=True)
        outputs.append(
            {"output_type": "execute_result", "execution_count": None, "data": data, "metadata": {}}
        )
    return outputs


def build() -> dict:
    namespace: dict = {}
    cells = []
    count = 0
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            for kind, source in CELLS:
                lines = source.splitlines(keepends=True)
                if kind == "markdown":
                    cells.append({"cell_type": "markdown", "metadata": {}, "source": lines})
                    continue
                count += 1
                outputs = _run(source, namespace)
                for o in outputs:
                    if o["output_type"] == "execute_result":
                        o["execution_count"] = count
                cells.append(
                    {
                        "cell_type": "code",
                        "execution_count": count,
                        "metadata": {},
                        "outputs": outputs,
                        "source": lines,
                    }
                )
        finally:
            os.chdir(cwd)
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    out = ROOT / "review" / "phase-02" / "api.ipynb"
    out.write_text(json.dumps(build(), indent=1), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
