# Phase 7 deliverable: a paper figure and an ops dashboard

Two layouts made from the sample data in `examples/sample-data`, for judging whether layouts format the way you want. Each folder is a small project: the data preparation, the Parquet files it writes, one GraphSpec per graph, the layout, the format it uses (in `formats/`), and what `forgegraph render` saved.

## The paper figure: `paper/`

`cell_performance.layout.yaml` puts three graphs of three fuel cells on one journal-width figure: voltage over a 200-hour durability test (top left), resistance over the same test (bottom left), and the polarization curves after it, spanning both rows on the right.

| File | What it is |
| --- | --- |
| prep_cells.py | Writes `cell_durability.csv` and `cell_polarization.csv` (sample data) as Parquet, unchanged. |
| voltage_time.yaml, hfr_time.yaml, polarization.yaml | The three GraphSpecs. Each also renders alone, in the default format. |
| cell_performance.layout.yaml | The layout: a 2 × 2 grid with polarization in both right-hand cells, the right column 1.3 times as wide. |
| formats/journal-double.yaml | 183 mm wide, height auto, 7 pt base size; saves PDF and PNG. |
| cell_performance.pdf, cell_performance.png | The figure. |

**What to look at:**
- The left plot boxes line up, although their tick labels differ in width.
- The polarization plot box runs from the top of the voltage plot to the bottom of the resistance plot.
- The height comes from the format's auto height: each row is as tall as its graphs' aspect asks.
- Each graph names its cells directly, in the same colors in all three, since each lists the same cells in the same order.

## The ops dashboard: `dashboard/`

`lab_throughput.layout.yaml` has two tabs, drawn from the LIMS run log `lab_runs.xlsx`.
- **Overview:** completed runs per week by instrument (spanning two columns), the share of each instrument's runs that failed or were aborted, samples per week, and median run time, with a blank cell.
- **By instrument:** one graph of completed runs per week for each instrument.

| File | What it is |
| --- | --- |
| prep_lab_dashboard.py | Reads the run log and writes one Parquet file per graph. Run it as `python prep_lab_dashboard.py lab_runs.xlsx .` |
| throughput_weekly.yaml, lost_runs.yaml, samples_weekly.yaml, run_time.yaml | The Overview tab's GraphSpecs. |
| runs_hplc_01.yaml and three more | The By instrument tab's GraphSpecs. |
| lab_throughput.layout.yaml | The layout, with lines between tiles (a blank cell counts as a tile) and a border around them. |
| formats/dashboard.yaml | 420 × 236 mm (16:9) at 300 dpi, 14 pt base size; saves PNG and HTML. |
| lab_throughput-overview.png, lab_throughput-by-instrument.png | One image per tab. |
| lab_throughput.html | One page with both tabs: a tab bar at the top, and a link per tab (`#by-instrument`). |

**What to look at:**
- The lines run between tiles, the blank cell included, but not through the spanning tile, and a border runs around the outside.
- HPLC-02's two weeks of downtime in August show as zeros.
- The page opened in a browser.

## Recreations: `recreations/`

The two side-by-side example slides (Ex1 p3 and Ex2 p7), redrawn from rescaled synthetic data as layouts. They're also image-regression tests (`tests/test_regression.py`).
- **layout_screening_and_rate:** a scatter of many runs beside two bars with their values. The original's fitted curve waits for fits (phase 11).
- **layout_anode_layers:** voltage and power from the same runs, colored by anode, with the test conditions in a note. The original's arrow and its "maximum to maximum" annotation wait for annotations (phase 9).

## With your own data

Copy one of these folders outside the repository, put your export beside it, and ask the agent (with the installed skill) to adapt the preparation and GraphSpecs to it. To re-render after the data changes, run the preparation script, then:

```bash
forgegraph render lab_throughput.layout.yaml
```

## What layouts don't do yet

These are deferred, as decided in the spec review:
- panel labels (a, b, c);
- axes shared between tiles, with tick labels drawn once;
- one legend for several tiles.

In the paper figure, each tile still has its own time-axis labels and names its own cells.
