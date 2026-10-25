"""The dashboard's data, from a LIMS run log (lab_runs.xlsx): one Parquet file per view.

python prep_lab_dashboard.py lab_runs.xlsx <output folder>
"""

import sys
from pathlib import Path

import pandas as pd

source, out = Path(sys.argv[1]), Path(sys.argv[2])
runs = pd.read_excel(source, "Runs", header=3)
runs = runs[runs["Run ID"].astype(str).str.startswith("R-")]  # no title or total rows
runs = runs.assign(Status=runs["Status"].str.strip().str.title())  # "completed", "Completed "
runs = runs[runs["Status"] != "In Progress"]
runs = runs.assign(Week=runs["Finished"].dt.to_period("W-SUN").dt.start_time)
instruments = ["HPLC-01", "HPLC-02", "GC-MS-01", "ICP-OES-01"]
done = runs[runs["Status"] == "Completed"]

weekly = done.pivot_table(
    index="Week", columns="Instrument", values="Run ID", aggfunc="count", fill_value=0
)[instruments]
for name in instruments:  # one file per instrument's tile
    one = weekly[name].rename("Completed runs").reset_index()
    one.to_parquet(out / f"weekly_{name.lower().replace('-', '_')}.parquet", index=False)
long = weekly.reset_index().melt(id_vars="Week", var_name="Instrument", value_name="Completed runs")
long.to_parquet(out / "weekly_runs.parquet", index=False)

failed = runs.assign(Lost=runs["Status"].isin(["Failed", "Aborted"]))
share = failed.groupby("Instrument")["Lost"].mean().mul(100).reindex(instruments)
share = share.rename("Failed or aborted (%)").reset_index()
share.to_parquet(out / "lost_runs.parquet", index=False)

samples = done.groupby("Week")["Samples"].sum().rename("Samples").reset_index()
samples.to_parquet(out / "weekly_samples.parquet", index=False)

hours = (done["Finished"] - done["Started"]).dt.total_seconds() / 3600
duration = hours.groupby(done["Instrument"]).median().reindex(instruments)
duration = duration.rename("Median run time (h)").reset_index()
duration.to_parquet(out / "run_time.parquet", index=False)
