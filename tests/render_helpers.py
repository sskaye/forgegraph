"""Shared helpers for rendering tests: the example data, drawn with changed values."""

from __future__ import annotations

import copy
import io
from importlib.resources import files
from typing import Any

import pandas as pd
from pack_helpers import BUILT_IN, child

import forgegraph as fg
from forgegraph.drawing.export import KEY
from forgegraph.drawing.style import isolated
from forgegraph.spec.parameters import series_definitions, tree_set
from forgegraph.spec.registry import Registry, builtin
from forgegraph.spec.series import look_definitions


def polarization() -> pd.DataFrame:
    """The example GraphSpec's data: three cells and a benchmark, two runs each, rows not
    in current order nor in sorted cell order, with one missing reading."""
    examples = files("forgegraph") / "packs" / "forgegraph_default" / "graphspecs"
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
    "series.color": "cell",
    "series.split": "run",
    "benchmark.data_column": "cell",
    "benchmark.value": "Benchmark",
}


def with_series(settings: dict[str, Any]) -> dict[str, Any]:
    """GraphSpec settings with the value axis's data.column as a series per column, named
    after it, each taking every series parameter given under series (as fg.xy does)."""
    out = dict(settings)
    base = out.get("arrangement.base_axis", "x")
    columns = out.pop(f"axis.{'y' if base == 'x' else 'x'}.data.column", None)
    if columns is None:
        return out
    own = {*series_definitions(), *look_definitions()}
    entry: dict[str, Any] = {}
    for path in [p for p in out if p.startswith("series.") and p[len("series.") :] in own]:
        tree_set(entry, path[len("series.") :], out.pop(path))
    names = [columns] if isinstance(columns, str) else columns
    return {"series": {name: copy.deepcopy(entry) for name in names}, **out}


def _child(kind: str, changes: dict[str, Any]) -> dict[str, Any]:
    return child(kind, BUILT_IN[kind], changes, name="changed", version=1)


def render(
    settings: dict[str, Any] | None = None,
    theme: dict[str, Any] | None = None,
    format: dict[str, Any] | None = None,
    data: pd.DataFrame | None = None,
    title: str | None = None,
) -> fg.Graph:
    reg: Registry = builtin().copy()
    theme_name = "forgegraph_default/light_theme"
    if theme:
        reg.add("theme", _child("theme", theme))
        theme_name = "changed"
    reg.add("format", _child("format", {**TEST_FORMAT, **(format or {})}))
    format_name = "changed"
    doc = fg.graphspec(
        "test",
        "xy",
        theme=theme_name,
        format=format_name,
        title=title,
        settings=with_series({**BASE, **(settings or {})}),
    )
    return fg.render(doc, polarization() if data is None else data, reg)


def png(graph: fg.Graph, dpi: int = 50) -> bytes:
    buffer = io.BytesIO()
    with isolated(graph.style):
        graph.figure.savefig(buffer, format="png", dpi=dpi, metadata={KEY: None})  # no record
    return buffer.getvalue()


def painted_draws(monkeypatch: Any) -> list[Any]:
    """Every drawing of a ForgeGraph figure that paints pixels, as it happens. A draw made
    only to measure has its painting switched off: matplotlib puts no-ops on the renderer."""
    from forgegraph.drawing.figure import GraphFigure

    painted: list[Any] = []
    original = GraphFigure.draw

    def counting_draw(self: Any, renderer: Any) -> None:
        if "draw_path" not in vars(renderer):
            painted.append(renderer)
        original(self, renderer)

    monkeypatch.setattr(GraphFigure, "draw", counting_draw)
    return painted
