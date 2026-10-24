"""Shared helpers for rendering tests: the example data, drawn with changed values."""

from __future__ import annotations

import io
from importlib.resources import files
from typing import Any

import pandas as pd

import forgegraph as fg
from forgegraph.drawing.export import KEY
from forgegraph.drawing.style import isolated
from forgegraph.spec.documents import Registry, builtin
from forgegraph.spec.parameters import NONE, definitions, tree_set


def polarization() -> pd.DataFrame:
    """The example GraphSpec's data: three cells and a benchmark, two runs each, rows not
    in current order nor in sorted cell order, with one missing reading."""
    examples = files("forgegraph") / "packs" / "forgegraph_base" / "graphspecs"
    frame = pd.read_parquet(str(examples / "polarization.parquet"))
    return frame.rename(columns=SHORT)


# The example data's columns, by the shorter names the tests use.
SHORT = {
    "Cell": "cell",
    "Run": "run",
    "Cell Size": "size",
    "Temperature (°C)": "temperature",
    "Cell Current (mA/cm²)": "current_density",
    "Cell Voltage (V)": "cell_voltage",
    "iR-Free Voltage (V)": "ir_free_voltage",
    "Power Density (mW/cm²)": "power_density",
}


# The tests' own size, so tuning the default format doesn't change what they check.
TEST_FORMAT = {"figure.width": 150, "figure.height": 140, "figure.base_size": 12}

BASE = {
    "axis.x.data.column": "current_density",
    "axis.y.data.column": "cell_voltage",
    "encoding.color": "cell",
    "encoding.detail": "run",
    "benchmark.data_column": "cell",
    "benchmark.value": "Benchmark",
}


def _child(kind: str, name: str, changes: dict[str, Any]) -> dict[str, Any]:
    defs = definitions(kind)
    sections: dict[str, dict] = {"fixed_parameters": {}, "variable_parameters": {}}
    for path, value in changes.items():
        section = "fixed_parameters" if defs[path].fixed else "variable_parameters"
        tree_set(sections[section], path, value)
    return {
        "name": name,
        "version": 1,
        "description": "test",
        "extends": f"forgegraph_base/base_{kind}",
        **{k: (v or NONE) for k, v in sections.items()},
    }


def render(
    settings: dict[str, Any] | None = None,
    theme: dict[str, Any] | None = None,
    format: dict[str, Any] | None = None,
    data: pd.DataFrame | None = None,
    title: str | None = None,
) -> fg.Graph:
    reg: Registry = builtin().copy()
    theme_name = "forgegraph_base/base_theme"
    if theme:
        reg.add("theme", _child("theme", "changed", theme))
        theme_name = "changed"
    reg.add("format", _child("format", "changed", {**TEST_FORMAT, **(format or {})}))
    format_name = "changed"
    doc = fg.graphspec(
        "test",
        "xy",
        theme=theme_name,
        format=format_name,
        title=title,
        settings={**BASE, **(settings or {})},
    )
    return fg.render(doc, polarization() if data is None else data, reg)


def png(graph: fg.Graph, dpi: int = 50) -> bytes:
    buffer = io.BytesIO()
    with isolated(graph.style):
        graph.figure.savefig(buffer, format="png", dpi=dpi, metadata={KEY: None})  # no record
    return buffer.getvalue()
