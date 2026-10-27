"""The phase 2 recreation set: the example graphs' kinds, rebuilt from rescaled synthetic data.

Each recreation is a GraphSpec's settings plus the DataFrame it draws. The same set feeds the
review page (scripts/build_recreations.py) and the image-regression baselines
(tests/test_regression.py), each baseline and its check drawn by baseline_image(). No real
measurements are used.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest import mock

import numpy as np
import pandas as pd
from pack_helpers import allow, doc, dump, write_config, write_pack
from render_helpers import with_series

import forgegraph as fg
from forgegraph.drawing.export import KEY
from forgegraph.drawing.style import isolated
from forgegraph.layouts import Layout
from forgegraph.packs import MAIN_CONFIG_VARIABLE
from forgegraph.spec.parameters import NONE
from forgegraph.spec.registry import Registry, builtin

BASELINE_DPI = 72


@dataclass
class Recreation:
    name: str
    caption: str
    data: pd.DataFrame
    settings: dict[str, Any]
    title: str | None = None
    format: dict[str, Any] = field(default_factory=dict)

    def graphspec(self) -> dict[str, Any]:
        fmt = "changed" if self.format else "forgegraph_default/compact_format"
        settings = with_series(self.settings)
        return fg.graphspec(self.name, "xy", format=fmt, title=self.title, settings=settings)

    def registry(self) -> Registry:
        reg = builtin().copy()
        if self.format:
            fmt = doc(
                "forgegraph_default/compact_format", "changed", fixed=self.format, description=""
            )
            reg.add("format", fmt)
        return reg

    def render(self) -> fg.Graph:
        return fg.render(self.graphspec(), self.data, self.registry())


def _polarization() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    rows = []
    for cell, ocv, r, a in [
        ("Cell A", 1.62, 0.0030, 0.050),
        ("Cell B", 1.66, 0.0045, 0.045),
        ("Cell C", 1.70, 0.0036, 0.060),
        ("Benchmark", 1.60, 0.0024, 0.040),
    ]:
        for i in np.linspace(0, 140 if cell == "Benchmark" else 100, 12):
            v = ocv - a * np.log1p(i / 2) - r * i + rng.normal(0, 0.002)
            rows.append({"cell": cell, "current_density": i, "cell_voltage": v})
    return pd.DataFrame(rows)


POLARIZATION_SETTINGS = {
    "axis.x.data.column": "current_density",
    "axis.y.data.column": "cell_voltage",
    "axis.x.title": "Cell Current (mA/cm^2)",
    "axis.y.title": "Cell Voltage (V)",
    "series.color": "cell",
    "benchmark.data_column": "cell",
    "benchmark.value": "Benchmark",
}


def _screening() -> pd.DataFrame:
    rng = np.random.default_rng(2)
    v = rng.uniform(1.30, 1.62, 300)
    icorr = np.exp(-12 * (v - 1.3)) * 4 + rng.lognormal(0, 0.35, 300)
    return pd.DataFrame({"cell_voltage_100ma": v, "icorr_ma": icorr})


def _replicates() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    rows = []
    for acd, shift in [("1 mm", 0.00), ("2 mm", 0.04), ("3 mm", 0.08)]:
        for cell in range(3):
            for i in np.linspace(0, 120, 10):
                v = 1.75 - shift - 0.055 * np.log1p(i / 3) - 0.0022 * i + rng.normal(0, 0.006)
                rows.append(
                    {
                        "acd": acd,
                        "cell_id": f"{acd}-{cell}",
                        "current_density": i,
                        "cell_voltage": v,
                    }
                )
    return pd.DataFrame(rows)


def _scale_up() -> pd.DataFrame:
    rows = []
    for fuel, ocv in [("Al", 1.80), ("Zn", 1.45)]:
        for area, loss in [("6 cm2", 1.0), ("130 cm2", 1.35)]:
            for i in np.linspace(0, 400 if fuel == "Al" else 600, 12):
                v = ocv - 0.20 * np.log1p(i / 30) * loss - 0.0012 * i * loss
                rows.append(
                    {"fuel": fuel, "active_area": area, "current_density": i, "cell_voltage": v}
                )
    return pd.DataFrame(rows)


def _precipitation() -> pd.DataFrame:
    rng = np.random.default_rng(4)
    rows = []
    for process, k in [("Batch", 1.0), ("Continuous", 3.2), ("Seeded", 9.5)]:
        rate = np.logspace(-5, -2, 9)
        for r in rate:
            rows.append(
                {
                    "process": process,
                    "rate": r,
                    "volume_l": k * 1e6 * r**0.85 * rng.lognormal(0, 0.1),
                }
            )
    return pd.DataFrame(rows)


def _separators() -> pd.DataFrame:
    rng = np.random.default_rng(5)
    area = rng.uniform(20, 70, 40)
    thickness = rng.uniform(80, 400, 40)
    power = 180 + 3.1 * area - 0.35 * thickness + rng.normal(0, 12, 40)
    return pd.DataFrame({"open_area_pct": area, "thickness_um": thickness, "max_power": power})


def _flow_sweep() -> pd.DataFrame:
    flow = np.linspace(0.5, 4.0, 8)
    return pd.DataFrame(
        {
            "flow_lpm": flow,
            "al_no_header": 1.32 + 0.050 * np.log(flow),
            "al_5_hole": 1.36 + 0.040 * np.log(flow),
            "zn_no_header": 1.10 + 0.030 * np.log(flow),
            "zn_5_hole": 1.13 + 0.024 * np.log(flow),
        }
    )


def _crowded() -> pd.DataFrame:
    x = np.linspace(0, 100, 10)
    return pd.DataFrame(
        [
            {"run": f"Run {k}", "current_density": xi, "cell_voltage": 1.5 - 0.004 * xi + 0.004 * k}
            for k in range(5)
            for xi in x
        ]
    )


RECREATIONS = [
    Recreation(
        "polarization",
        "Polarization curves, black benchmark, interior labels (lines with markers, color_by).",
        _polarization(),
        POLARIZATION_SETTINGS,
        "Polarization, 60 °C",
    ),
    Recreation(
        "polarization_narrow",
        "The same GraphSpec in an 89 mm format with an 8 pt base font and an auto height: "
        "every size scales with the base font.",
        _polarization(),
        POLARIZATION_SETTINGS,
        "Polarization, 60 °C",
        {"figure.width": 89, "figure.height": "auto", "figure.base_size": 8},
    ),
    Recreation(
        "screening_scatter",
        "Many points, markers only (a scatter plot), one group: no series names needed.",
        _screening(),
        {
            "axis.x.data.column": "cell_voltage_100ma",
            "axis.y.data.column": "icorr_ma",
            "axis.x.title": "Cell Voltage (V @ 100 mA)",
            "axis.y.title": "Icorr (mA)",
            "series.line.show": False,
        },
    ),
    Recreation(
        "replicates",
        "Replicates: three cells per ACD, one color per ACD, one line per cell (line_path_by).",
        _replicates(),
        {
            "axis.x.data.column": "current_density",
            "axis.y.data.column": "cell_voltage",
            "axis.x.title": "Current Density (mA/cm^2)",
            "axis.y.title": "Cell Voltage (V)",
            "series.color": "acd",
            "series.split": "cell_id",
            "legend.key.title.text": "ACD",
        },
    ),
    Recreation(
        "fuel_by_size",
        "Color by fuel, line style by cell size: fuels named in the plot, sizes in a style key.",
        _scale_up(),
        {
            "axis.x.data.column": "current_density",
            "axis.y.data.column": "cell_voltage",
            "axis.x.title": "Cell Current (mA/cm^2)",
            "axis.y.title": "Cell Voltage (V)",
            "series.color": "fuel",
            "series.line.style": "active_area",
        },
    ),
    Recreation(
        "precipitation_loglog",
        "Log-log axes with markers only and unit markup in the axis titles.",
        _precipitation(),
        {
            "axis.x.data.column": "rate",
            "axis.y.data.column": "volume_l",
            "axis.x.scale": "log",
            "axis.y.scale": "log",
            "axis.x.title": "ATH Precipitation Rate (mol ATH L^-1 s^-1)",
            "axis.y.title": "Volume (L)",
            "series.color": "process",
            "series.line.show": False,
        },
    ),
    Recreation(
        "separator_colorbar",
        "A numeric color_by: each point colored by its value, with a color bar.",
        _separators(),
        {
            "axis.x.data.column": "open_area_pct",
            "axis.y.data.column": "thickness_um",
            "axis.x.title": "Open Area (%)",
            "axis.y.title": "Thickness (µm)",
            "series.color": "max_power",
            "legend.color_bar.title.text": "Max Power (mW/cm^2)",
            "series.line.show": False,
        },
    ),
    Recreation(
        "flow_sweep_wide",
        "Wide data: four y columns, one series each, colored by series (color: series).",
        _flow_sweep(),
        {
            "axis.x.data.column": "flow_lpm",
            "axis.y.data.column": ["al_no_header", "al_5_hole", "zn_no_header", "zn_5_hole"],
            "axis.x.title": "Electrolyte Flow Rate (LPM)",
            "axis.y.title": "Cell Voltage (V)",
            "series.color": "series",
            "legend.key.title.text": NONE,
        },
    ),
    Recreation(
        "crowded_runs",
        "Five nearly identical runs: no interior position clearly belongs to one run, so auto "
        "falls back to the legend. At a 12 pt base font: at 18 pt no corner is clear for it.",
        _crowded(),
        {
            "axis.x.data.column": "current_density",
            "axis.y.data.column": "cell_voltage",
            "axis.x.title": "Cell Current (mA/cm^2)",
            "axis.y.title": "Cell Voltage (V)",
            "series.color": "run",
        },
        format={"figure.base_size": 12},
    ),
]


def _corrosion() -> pd.DataFrame:
    return pd.DataFrame({"period": ["Prev. best", "Today"], "Corrosion Rate (mA/cm²)": [290, 48]})


def _anode_layers() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for layers, loss in [("1 layer anode", 1.25), ("2 layer anode", 1.0)]:
        for cell in range(3):
            spread = 1 + 0.06 * cell
            for i in [
                0,
                10,
                25,
                50,
                100,
                150,
                200,
                250,
                300,
                350,
                400,
                450,
                500,
                550,
                600,
                650,
                700,
            ]:
                v = 1.52 - 0.12 * np.log1p(i / 40) - 0.0010 * i * loss * spread
                v -= 0.07 * loss * spread * max(0.0, (i - 520) / 180) ** 2
                v += rng.normal(0, 0.004)
                rows.append(
                    {
                        "anode": layers,
                        "cell": f"{layers}-{cell}",
                        "current_density": i,
                        "cell_voltage": v,
                        "power_density": v * i,
                    }
                )
    return pd.DataFrame(rows)


ANODE = {
    "axis.x.data.column": "current_density",
    "axis.x.title": "Current Density (mA/cm^2)",
    "series.color": "anode",
    "series.split": "cell",
}


@dataclass
class LayoutRecreation:
    """A side-by-side example: GraphSpecs on a grid, drawn from their DataFrames."""

    name: str
    caption: str
    tiles: dict[str, Recreation]
    areas: list[list[str]]
    format: dict[str, Any]

    def render(self, folder: Path) -> Layout:
        """Write the tiles' GraphSpecs, the format (in a folder pack, house) and the layout
        into folder, and draw it, with a main config of its own allowing house, so it's
        standard."""
        write_pack(folder)
        allow(folder, "forgegraph_default", "./house")
        main = write_config(folder / "main.toml", "forgegraph_default", "./house")
        fmt = doc(
            "forgegraph_default/compact_format",
            "slide",
            fixed={"figure": self.format},
            description="",
        )
        dump(fmt, folder / "house" / "formats" / "slide.yaml")
        for name, r in self.tiles.items():
            dump(r.graphspec(), folder / f"{name}.yaml")
        tiles = {name: f"{name}.yaml" for name in self.tiles}
        layout = doc(
            "forgegraph_default/layout",
            self.name,
            variable={
                "specifications.format": "house/slide",
                "tabs": {"Slide": {"grid": {"areas": self.areas}, "tiles": tiles}},
            },
            description=self.caption,
        )
        path = dump(layout, folder / f"{self.name}.layout.yaml")
        with mock.patch.dict(os.environ, {MAIN_CONFIG_VARIABLE: str(main)}):
            return fg.layout(path, data={name: r.data for name, r in self.tiles.items()})


SLIDE = {"width": 254, "height": 110, "base_size": 12}

LAYOUT_RECREATIONS = [
    LayoutRecreation(
        "layout_screening_and_rate",
        "Two panels side by side: many runs as a scatter, then two bars with their values; "
        "each panel titled, plot boxes aligned top and bottom.",
        {
            "previously": Recreation(
                "previously",
                "",
                _screening().rename(columns={"icorr_ma": "Icorr (mA)"}),
                {
                    "axis.x.data.column": "cell_voltage_100ma",
                    "axis.y.data.column": "Icorr (mA)",
                    "axis.x.title": "Cell Voltage (V @ 100 mA)",
                    "series.line.show": False,
                },
                "Previously",
            ),
            "recent": Recreation(
                "recent",
                "",
                _corrosion(),
                {
                    "axis.x.data.column": "period",
                    "axis.x.title": NONE,
                    "axis.x.tick.algorithm": "all",
                    "axis.y.data.column": "Corrosion Rate (mA/cm²)",
                    "series.bar.show": True,
                    "series.line.show": False,
                    "series.marker.show": False,
                    "series.value_label.show": True,
                },
                "Last 3 Months",
            ),
        },
        [["previously", "recent"]],
        SLIDE,
    ),
    LayoutRecreation(
        "layout_anode_layers",
        "Two panels from the same runs: voltage and power against current density, colored "
        "by anode, one line per cell, test conditions in a note.",
        {
            "voltage": Recreation(
                "voltage",
                "",
                _anode_layers(),
                {
                    **ANODE,
                    "axis.y.data.column": "cell_voltage",
                    "axis.y.title": "Cell Voltage (V)",
                    "layers": {
                        "conditions": {
                            "type": "note",
                            "text": "6 cm^2, 60 °C\nGas: 200 sccm, 3 psi",
                            "position": "bottom_left",
                        }
                    },
                },
            ),
            "power": Recreation(
                "power",
                "",
                _anode_layers(),
                {
                    **ANODE,
                    "axis.y.data.column": "power_density",
                    "axis.y.title": "Power (mW/cm^2)",
                },
            ),
        },
        [["voltage", "power"]],
        SLIDE,
    ),
]


def baseline_image(r: Recreation | LayoutRecreation, path: Path, folder: Path) -> Path:
    """Draw a recreation at path as a PNG with no record, at the baselines' resolution; a
    layout recreation's first tab, its files written in folder."""
    if isinstance(r, LayoutRecreation):
        tab = r.render(folder).tabs[0]
        with tab.saving():
            tab.figure.savefig(path, format="png", dpi=BASELINE_DPI, metadata={KEY: None})
        return path
    graph = r.render()
    with isolated(graph.style):
        graph.figure.savefig(path, format="png", dpi=BASELINE_DPI, metadata={KEY: None})
    return path
