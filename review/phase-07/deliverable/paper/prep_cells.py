"""The paper figure's data: the sample CSVs as Parquet, unchanged."""

import sys
from pathlib import Path

import pandas as pd

source, out = Path(sys.argv[1]), Path(sys.argv[2])
for name in ("cell_durability", "cell_polarization"):
    pd.read_csv(source / f"{name}.csv").to_parquet(out / f"{name}.parquet", index=False)
