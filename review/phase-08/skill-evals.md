# Skill evals for phase 8

These cases test what phases 7 and 8 added: layouts, date axes and scheduled jobs, and questions about them. They join the 44 cases of phases 4 and 5. As before, each case gives a fresh Claude Code session an empty folder holding its sample data from `examples/sample-data`, the installed skill and ForgeGraph, then sends the request. Requests are written as expert users write them, worded the way different scientists word things. Every graph request's final turn ends with "After you finish, please share the graph and any notes on issues that came up or you had to work around." A question's turn is sent as written, with nothing added.

A case is graded two ways:

- **By script:** as before (the final GraphSpec's values, the lint on redrawing it, the files made, the data unchanged, what a question's reply names), and now also the final layout (it draws, its tabs and tiles, a spanning tile, a blank cell, its column widths, its lint) and the final schedule (it loads, when it runs, whether it was run once).
- **By me:** I look at every graph and read every reply, and report anything the script can't judge.

**No jobs are installed.** In the eval sessions, `launchctl`, `crontab`, `systemctl` and `schtasks` are stand-ins that record each call and refuse it, so nothing can be registered on this machine. A scheduling case asks for a schedule file, and is graded on that file.

## Models

Each case runs once on Opus, once on Sonnet and once on Haiku. A case passes on Opus and Sonnet or it fails: those are the results that decide changes to the skill. Haiku's results are reported beside them. The 44 earlier cases run again too, with the changed skill and the new date axes.

## Coverage

| Case | Data | What it tests |
| --- | --- | --- |
| 45 | cell_durability, cell_polarization | Two panels side by side, from two files |
| 46 | cell_durability, cell_polarization | Three panels, one spanning the right column |
| 47 | iris | A 2×2 grid with a blank cell |
| 48 | economics | A dashboard page: a full-width top row, two below, as HTML |
| 49 | lab_runs | A dashboard with two tabs, from a messy export |
| 50 | tips | Two panels, then a follow-up changing their widths |
| 51 | lab_runs | Weekly bars on a date axis |
| 52 | seaice | A weekly tick step |
| 53 | co2_monthly | A weekday schedule |
| 54 | seaice | An every-two-hours schedule at a quarter past |
| 55 | dose_response | A monthly schedule into a folder, run once |
| 56–57 | none | Questions about layouts and scheduling |

## Layouts

### 45. Two panels

- **Data:** cell_durability.csv, cell_polarization.csv
- **Request:** "For the paper, put two panels side by side: cell voltage over the durability test on the left (cell_durability.csv) and the polarization curves on the right (cell_polarization.csv), each cell in its own color."
- **A good result:** two GraphSpecs, each from its own Parquet file, and a layout with one tab of two tiles side by side; clean lint, or dropped-rows for blank rows that break the line at Cell C's gap.
- **Why:** the basic multi-panel figure.

### 46. Three panels, one spanning

- **Data:** cell_durability.csv, cell_polarization.csv
- **Request:** "Three-panel figure: voltage vs. hours and HFR vs. hours stacked in the left column (cell_durability.csv), and the polarization plot from cell_polarization.csv filling the whole right column."
- **A good result:** a layout of three tiles, the polarization tile spanning both rows; clean lint, or dropped-rows for blank rows that break the line at Cell C's gap.
- **Why:** a spanning tile.

### 47. A blank cell

- **Data:** iris.csv
- **Request:** "iris.csv as a 2×2 grid of scatter plots colored by species: sepal length vs sepal width, petal length vs petal width, and sepal length vs petal length, with the fourth cell left empty."
- **A good result:** a layout of three tiles and a blank cell; clean lint.
- **Why:** blank cells.

### 48. A dashboard page

- **Data:** economics.csv
- **Request:** "Dashboard from economics.csv, as an HTML page: unemployment over time across the full top row; below it, the personal savings rate and median unemployment duration side by side."
- **A good result:** a layout of three tiles, the top one spanning both columns, saved as HTML (a format listing html, or `--out` with `.html`); clean lint.
- **Why:** a dashboard, and HTML output.

### 49. A dashboard with tabs

- **Data:** lab_runs.xlsx
- **Request:** "lab_runs.xlsx is our LIMS export. I'd like a dashboard with two tabs: Overview, with completed runs per week for each instrument, and Failures, with failed or aborted runs per week for each instrument."
- **A good result:** the runs counted per instrument and week from the messy export (as in the phase 5 deliverable), and a layout with two tabs; clean lint.
- **Why:** tabs, and preparing data from a real-looking export.

### 50. Widths, as a follow-up

- **Data:** tips.csv
- **Request:** "Two plots side by side from tips.csv: tip vs. total bill as points on the left, average tip per day as bars on the right." Then: "Make the left panel twice as wide as the right."
- **A good result:** a layout of two tiles whose `column_widths` are 2:1 after the second turn; the image looked at after each turn; clean lint.
- **Why:** a layout parameter, set in a follow-up.

## Date axes

### 51. Weekly bars

- **Data:** lab_runs.xlsx
- **Request:** "Weekly throughput from lab_runs.xlsx: one bar per week, the number of completed runs across all instruments."
- **A good result:** weeks as dates on x, bars, clean lint (bars that fit their weeks).
- **Why:** bars on a date axis, and the new date labels.

### 52. A weekly tick step

- **Data:** seaice.csv
- **Request:** "Sea-ice extent for January 2019 from seaice.csv, with an x tick every week."
- **A good result:** January 2019 only, dates on x, `axis.x.tick.algorithm: manual` with `tick.step: "1 week"` (or "7 day"); clean lint.
- **Why:** the new week unit for tick steps.

## Scheduled jobs

### 53. Every weekday

- **Data:** co2_monthly.csv
- **Request:** "Line chart of the monthly CO₂ record in co2_monthly.csv, plus a schedule file that re-renders it every weekday at 7am."
- **A good result:** the graph, and a schedule that runs Monday to Friday at 07:00 (a week unit with five times).
- **Why:** a cadence that needs a list of times.

### 54. Every two hours

- **Data:** seaice.csv
- **Request:** "Chart of sea-ice extent from seaice.csv, and write me a schedule file to refresh it every two hours, at a quarter past."
- **A good result:** the graph, and a schedule of `interval: 2`, `interval_unit: hour`, `at: ":15"`.
- **Why:** an interval, and a time within the unit.

### 55. Monthly, run once

- **Data:** dose_response.csv
- **Request:** "Dose-response curves from dose_response.csv (log dose axis, one line per compound), with a schedule file for 06:00 on the 1st of every month, the output going to a reports folder. Do one run now so I can check it works."
- **A good result:** the graph, a schedule for the 1st at 06:00 with `output_folder` reports, run once with `forgegraph job run` (its outputs in reports/ and a successful status file).
- **Why:** an output folder, and running a schedule once.

## Questions

### 56. Several graphs in one figure

- **Request:** "Can ForgeGraph put several graphs into one figure, like a multi-panel figure in a paper?"
- **A good result:** no graph; the reply says yes, with a layout.

### 57. Re-rendering every morning

- **Request:** "Can a ForgeGraph dashboard re-render by itself every morning?"
- **A good result:** no graph; the reply names a schedule and `forgegraph job run`.
