"""Write the example GraphSpecs' data, into each built-in pack's graphspecs/ (polarization,
fanned, reinforced and dated .parquet), and the skill's examples/xy.parquet (the polarization
data).

uv run python scripts/build_example_data.py

Rescaled synthetic polarization curves: three cells and a benchmark, two runs each, rows
deliberately not in current order and not in sorted cell order, with one missing reading.
fanned has the same columns: four cells with long names whose curves fan out from one
point and all end at the same current, so their names fit only past the line ends.
reinforced is the polarization data with Cell A renamed Reinforced A: as a bar's tick label,
wider than the space between ticks, so it wraps, yet clear of its neighbours unwrapped.
dated is the polarization data with a Date column, a day per current step from 6 July 2026,
so a date axis's day labels show.
No real measurements are used.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PACKAGE = Path(__file__).parents[1] / "src" / "forgegraph"
PACKS = sorted(p for p in (PACKAGE / "packs").iterdir() if (p / "pack.yaml").is_file())
SKILL_EXAMPLES = PACKAGE / "skill" / "forgegraph" / "examples"


def polarization() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for cell, ocv, r, a, size, temp in [
        ("Cell C", 1.70, 0.0036, 0.060, "130 cm2", 70.0),
        ("Cell A", 1.62, 0.0030, 0.050, "6 cm2", 50.0),
        ("Cell B", 1.66, 0.0045, 0.045, "130 cm2", 60.0),
        ("Benchmark", 1.60, 0.0024, 0.040, "6 cm2", 55.0),
    ]:
        for run in (1, 2):
            i = np.linspace(2, 140 if cell == "Benchmark" else 100, 12)
            v = ocv - a * np.log1p(i / 2) - r * i - 0.01 * (run - 1) + rng.normal(0, 0.002, i.size)
            for k in rng.permutation(i.size):
                rows.append(
                    {
                        "Cell": cell,
                        "Run": run,
                        "Cell Size": size,
                        "Temperature (°C)": temp + run,
                        "Cell Current (mA/cm²)": round(float(i[k]), 3),
                        "Cell Voltage (V)": round(float(v[k]), 4),
                        "iR-Free Voltage (V)": round(float(v[k] + 0.0015 * i[k]), 4),
                        "Power Density (mW/cm²)": round(float(i[k] * v[k]), 2),
                    }
                )
    out = pd.DataFrame(rows)
    out.loc[5, "Cell Voltage (V)"] = np.nan  # one missing reading
    return out


def fanned() -> pd.DataFrame:
    rows = []
    names = ["Long-Life A", "Long-Life B", "Long-Life C", "Benchmark"]
    for k, cell in enumerate(names):
        for i in np.linspace(2, 100, 12):
            v = 1.5 - (0.0015 + 0.001 * k) * i
            rows.append(
                {
                    "Cell": cell,
                    "Run": 1,
                    "Cell Size": "6 cm2",
                    "Temperature (°C)": 60.0,
                    "Cell Current (mA/cm²)": round(float(i), 3),
                    "Cell Voltage (V)": round(float(v), 4),
                    "iR-Free Voltage (V)": round(float(v + 0.0015 * i), 4),
                    "Power Density (mW/cm²)": round(float(i * v), 2),
                }
            )
    return pd.DataFrame(rows)


def dated() -> pd.DataFrame:
    frame = polarization()
    steps = frame["Cell Current (mA/cm²)"].rank(method="dense").astype(int) - 1
    start = pd.Timestamp("2026-07-06")  # a Monday
    return frame.assign(Date=[start + pd.Timedelta(days=int(s)) for s in steps])


def reinforced() -> pd.DataFrame:
    return polarization().replace({"Cell": {"Cell A": "Reinforced A"}})


if __name__ == "__main__":
    frames = {"polarization": polarization(), "fanned": fanned(), "reinforced": reinforced()}
    frames["dated"] = dated()
    written = [
        (pack / "graphspecs" / f"{name}.parquet", frame)
        for pack in PACKS
        for name, frame in frames.items()
    ]
    for out, frame in (*written, (SKILL_EXAMPLES / "xy.parquet", polarization())):
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(out, index=False)
        print(f"wrote {out.relative_to(Path.cwd())}")
