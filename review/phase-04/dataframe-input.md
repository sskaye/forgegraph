# Proposal: ForgeGraph's input is a DataFrame

## Contents

1. The contract
2. The GraphSpec's data fields
3. Drawing
4. Provenance
5. Command line
6. Python API
7. The skill
8. Layouts, scheduling and Studio
9. Changes to the code
10. Changes to the documents
11. Later: workbooks

## 1. The contract

ForgeGraph takes a pandas DataFrame and draws a graph from it, as the GraphSpec, theme, format and graph type say. The DataFrame comes either:

- **through the Python API**: `fg.render(spec, frame)`; or
- **from a Parquet file** named by the GraphSpec.

That is all of ForgeGraph's input. How the DataFrame was made, and where its file is kept, are up to the user and the agent.

## 2. The GraphSpec's data fields

A new category, `data`, in the GraphSpec:

| Parameter | Range | Description |
| --- | --- | --- |
| data.file | None, text | A Parquet file holding the DataFrame to draw: an absolute path, a path starting with `~` (the home folder), or a path relative to the folder of the GraphSpec file that sets it. None: the DataFrame is passed through the Python API. |
| data.preprocessing | None, text | Optional: where the code that made the data is, for whoever reads the GraphSpec later (a path, a URL, a note). ForgeGraph records it and doesn't read it. |

An example GraphSpec's data:

data:<br>
&nbsp;&nbsp;&nbsp;&nbsp;file: ../results/cycle_life.parquet<br>
&nbsp;&nbsp;&nbsp;&nbsp;preprocessing: ../scripts/prepare_cycle_life.py

The rest of the GraphSpec (graph type, theme, format, title, axes, encodings, marks, legend) is unchanged.

## 3. Drawing

1. Resolve the GraphSpec with its graph type, theme and format, as now.
2. Get the DataFrame:
   - a DataFrame passed in is drawn, whatever `data.file` says;
   - otherwise `pandas.read_parquet` on `data.file`. `~` is expanded to the home folder. A relative path is resolved against the folder of the GraphSpec file that sets it, which for a GraphSpec extending another may be the other one's; for a GraphSpec given as a Python dict, against the current folder.
3. Check it against the GraphSpec, as now: the named columns exist, axis columns are numeric or dates, a log axis has no values of 0 or below.
4. Draw, lint and save, as now.

Errors, each stopping the render with a message that names the parameter:

- `data.file` is None and no DataFrame was passed;
- `data.file` names no file, or a file that isn't Parquet;
- a column the GraphSpec names isn't in the DataFrame (the message lists the columns there are).

## 4. Provenance

The record embedded in each image holds, about its data:

| Field | Holds |
| --- | --- |
| file | `data.file` as written, or None for a DataFrame passed in |
| preprocessing | `data.preprocessing` as written |
| fingerprint | a hash of the rows drawn |
| rows read | the DataFrame's rows |
| rows plotted | the rows drawn |
| rows dropped | rows ForgeGraph left out, by reason (e.g. missing x or y) |

At `provenance: minimal`, `file` and `preprocessing` are left out, both from the data record and from the copy of the GraphSpec the image carries.

## 5. Command line

- **`forgegraph render <graphspec>`** draws from the GraphSpec's `data.file`.
- **`forgegraph catalog`** lists the graph types, themes and formats available, and the GraphSpecs to extend: ForgeGraph's own, and later packs'. A project's own GraphSpecs aren't listed.
- **`forgegraph schema <kind>`** lists a kind's parameters. `schema graphspec --theme <t> --format <f>` lists every parameter a GraphSpec can set, `data` included.
- **`forgegraph explain <graphspec>`** shows every value the graph is drawn with and which file set it.
- **`forgegraph load <image>`** shows an image's record, and `--graphspec <file>` writes its GraphSpec out, `data.file` as recorded: a relative path then resolves against the new file's folder.
- **`forgegraph skill install`** installs the skill.

## 6. Python API

- `fg.render(spec, data=None)`: `data` given, it's drawn; otherwise `data.file` is read.
- `fg.graphspec(..., data_file=None, preprocessing=None)` writes the two data fields.
- `fg.xy(frame, x, y, ...)` is unchanged.

## 7. The skill

The skill starts from a DataFrame saved as a Parquet file and covers designing, drawing, checking and changing the graph:

1. **See what's available:** `forgegraph catalog` lists the themes, formats and GraphSpecs to extend.
2. **Choose the theme and format.** If nothing points to one, use `default`.
3. **Write the GraphSpec:** `data.file` names the Parquet file; `data.preprocessing` can name the code that made it. `forgegraph schema graphspec --theme <t> --format <f>` lists every parameter it can set.
4. **Render and check:** `forgegraph render`, then the lint issues and the image.
5. **Iterate** until the graph does what was asked and shows the data well.

## 8. Layouts, scheduling and Studio

- **Layouts (phase 7):** each tile is a GraphSpec drawn from a `data.file`. A file named by several tiles is read once per render.
- **Scheduling (phase 8):** a scheduled job renders GraphSpecs and layouts. Keeping their Parquet files current is the user’s job. The in-image "data as of" stamp is the Parquet file's modification time.
- **Studio (phase 12):** opens a GraphSpec, or a Parquet file to start a new one. Its shelves map the DataFrame's columns to X, Y, color, style and series.

## 9. Changes to the code

### Removed

- The data source kind:
  - `src/forgegraph/data_sources/`;
  - its entries in `KINDS` and `REFERENCE`, its type word, and its mirror;
  - the data source rules in `spec/documents.py`;
  - `specifications.data_source`.
- The `forgegraph.data` package (`data/loader.py`, `describe()` included).
- CLI:
  - `forgegraph inspect`;
  - `render --snapshot` and `Graph.save(snapshot=)`;
  - data sources in `catalog`, `schema` and `explain`;
  - project GraphSpecs in `catalog`.
- Tests: `test_data_loader.py`, the data source tests in `test_specs.py`, `test_cli.py` and `test_render.py`, and the `data_source_polarization` mirror.
- Dependencies: openpyxl and xlrd.

### Changed

- **The GraphSpec definition** (`graphspecs/polarization.yaml`): the `data` category of §2 replaces `specifications.data_source`.
- **`graph.py`:**
  - the data step of §3, and the three errors, each tested;
  - `record()` at `minimal` strips the `data` fields from the embedded GraphSpec;
  - the files a GraphSpec names are checked without a data source;
  - `Graph.save` loses `snapshot`, and `Graph` the frame it kept for it.
- **`spec/documents.py`:** the GraphSpec names three other files (graph type, theme, format), in what it may set, in `explain`, and in validation; the data source rules and their file-type table go.
- **`spec/parameters.py`:** the `data source` type word and its name check go.
- **`spec/provenance.py`:** the data record of §4.
- **CLI** as in §5; `load` prints the data file and fingerprint.
- **Python API** as in §6.
- **Built-in example data:** `graphspecs/polarization.parquet` and `graphspecs/fanned.parquet`, beside the example GraphSpec, written by `scripts/build_example_data.py`. The example GraphSpec sets `data.file: polarization.parquet`. `tests/render_helpers.py` reads the same file.
- **Catalog:**
  - the theme catalog's `fanned` baseline changes `data.file`;
  - `catalog/examples.py` draws each card from a copy of its baseline GraphSpec, so it resolves the copy's `data.file`, and any `data.file` a card sets, against the baseline GraphSpec's folder before drawing;
  - the catalog's input hash covers the example Parquet files, and for a project's catalog, the Parquet files its baseline GraphSpecs name;
  - the catalog pages show nothing about data.
- **Wording:** the format's `provenance.level` description (the data file, preprocessing and fingerprint), the package description in `pyproject.toml`, and the drawing code's comments that mention snapshots.
- **Skill:** SKILL.md as in §7.
- **Evals:**
  - each run's project holds the cases' data files, as now, and the agent prepares the DataFrame however it chooses;
  - checks read the GraphSpec's `data.file` instead of a data source (`scripts/run_skill_evals.py`);
  - the messy-Excel case checks that the DataFrame drawn has the expected numeric columns.
- **Sample data** (`examples/sample-data/README.md`): describes each file and requests to try, without saying how the data should be prepared.
- **Generated files:** the spec mirrors, the catalog, the API notebook.

### Added

- **Dependency:** `pyarrow`, for Parquet.
- **Tests:**
  - drawing from `data.file` and from a DataFrame;
  - each error in §3;
  - a path relative to the GraphSpec's folder;
  - column types surviving the Parquet round trip, dates included;
  - provenance at `full` and `minimal`.

## 10. Changes to the documents

### Architecture

- **Summary, decisions at a glance, §3 pipeline:** resolve ➝ get the DataFrame ➝ validate ➝ render ➝ lint ➝ export.
- **§2 Vocabulary:** "data source" and "connection" go.
- **§3.1 What it looks like to use:** the example GraphSpec's data becomes `data.file`, and the CLI lines lose `inspect`.
- **D4 Packs:** connections and data references leave packs. Packs hold themes, formats, presets, fonts and reference notes.
- **D7** becomes **Input: a DataFrame**, stating §1–§4.
- **D9 Agent interface:** the skill's loop starts from the DataFrame (no `inspect`).
- **D11 Layouts:** as §8.
- **D12 Scheduling:** as §8.
- **D13 Provenance:** as §4; `--snapshot` goes.
- **D14 Studio:** as §8; the fields panel lists the DataFrame's columns; the filter and aggregation shelves go.
- **§7 Quality:** connector tests go.
- **§8 Phasing:** the data source specification row goes.
- **§10 Risks:** the database and connector risks go.
- **§11 Deferred:** add workbooks (§11 below).

### Build plan

- **Phase 4:** adds this change before the gate. The data contract and GraphSpec change get your review first; then the code, skill and evals.
- **Phase 5** becomes **`bar`, first layers, presets**. The `error_bar` layer draws from error columns in the DataFrame.
- **Phase 6** becomes **Packs, config, and the real-data trial**, without SQL or connections. In the trial, the agent prepares data from your sources in its own way and draws with ForgeGraph.
- **§3 Phases at a glance:** the phase 5 and 6 rows and the M2 milestone follow these names.
- **Phase 7:** layouts as in §8.
- **Phase 8:** scheduling as in §8.
- **Phase 12:** Studio as in §8.

### Decisions log

One entry stating the contract (§1).

## 11. Later: workbooks

A workbook bundles a Parquet file with the GraphSpecs and dashboards drawn from it, as one file to share or open, like Tableau's packaged workbooks. It suits Studio especially. It goes in the architecture's deferred list, to be specified when it's taken up.

