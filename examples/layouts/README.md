# Example layouts

Two small projects made from the sample data in `examples/sample-data`. Each folder holds the data preparation, the Parquet files it writes, one GraphSpec per graph, the layout, and the layout's format, in a folder pack that the folder's `forgegraph.toml` allows.

- `paper/`: `cell_performance.layout.yaml` puts three graphs of three fuel cells on one journal-width figure, in the format `journal/journal-double`.
- `dashboard/`: `lab_throughput.layout.yaml` is an ops dashboard with two tabs, in the format `ops/dashboard`.

Draw one from its folder, for example `forgegraph render cell_performance.layout.yaml`. Its pack is listed only in the folder's config, so what it draws is watermarked as non-standard; list the pack in your main config to draw it as standard.

The data comes from `prep_cells.py <sample-data folder> <output folder>` and `prep_lab_dashboard.py <lab_runs.xlsx> <output folder>`.
