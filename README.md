# ForgeGraph

Fast, consistent, publication-quality graphs from pandas DataFrames, usable by people and AI agents.

You describe a graph in a **GraphSpec**. ForgeGraph draws it in a house style set by a **theme** and a **format**. It checks what it drew, and records how the graph was made inside the saved file. An agent skill lets agents make and revise graphs the same way.

**<u>Key Features</u>**

- **Themes:** fixes the look of the graph (fonts, palette, lines, keys, etc.).
- **Formats:** sets the destination: figure size, base font size, file types and resolution, e.g. a slide, a journal column or a dashboard tile.
- **GraphTypes:** defines the type of graph and its parameters. E.g. `xy` (lines, markers and bars).
- **Layers:** features drawn over a graph. E.g. reference lines, notes, & error bars.
- **GraphSpecs:** specify the data, theme, format, and all customizable properties.
- **Layouts:** combine multiple graphs into a larger figure or multi-tab dashboard.
- **Scheduled renders:** re-render graphs and dashboards on a schedule set with cron, launchd, or by an agent.
- **Provenance:** every saved file contains its specifications as metadata, enabling inspection of how the graph was made and reproduction of it.
- **Packs:** collect together a set of themes and formats for different use cases. E.g. a company or lab’s standard style, journal requirements, etc.
- **Configs:** control which packs may be used, per user or folder. Used to enforce use of style pack(s) and watermark non-standard graphs.
- **Lint:** Graphs are linted on rendering, with warnings for issues including overlapping or clipped text, a key covering data, or fonts too small.

**Status:** 0.x.  `xy` graph type (lines, markers, & bars), reference lines, error bars, and notes layers, initial style packs. More graph types are planned. If there’s specific ones you want, [open an issue](https://github.com/sskaye/forgegraph/issues).

## Install

ForgeGraph needs Python 3.12 or later.

```bash
pip install forgegraph
```

For the `forgegraph` command on its own, `uv tool install forgegraph` works too. To install the skill for Claude Code:

```bash
forgegraph skill install
```

For another agent, give the folder it reads skills from:

```bash
forgegraph skill install --dest <skills folder>
```

Then ask your agent for a graph: the skill takes it from your data to a finished graph, saving the GraphSpec beside it.

## Quick start

In Python:

```python
import pandas as pd
import forgegraph as fg

runs = pd.DataFrame({
    "hours": [0, 1, 2, 3, 0, 1, 2, 3],
    "voltage": [0.72, 0.71, 0.70, 0.69, 0.73, 0.73, 0.72, 0.72],
    "cell": ["A", "A", "A", "A", "B", "B", "B", "B"],
})
g = fg.xy(runs, x="hours", y="voltage", color="cell", title="Cell voltage")
g.save("voltage")  # voltage.png, with its GraphSpec inside
```

The Python API (each function has a docstring):

- `fg.xy(df, x, y, ...)`: draw y against x from a DataFrame.
- `fg.render(spec, data=None)`: draw a GraphSpec, given as a file or a document.
- `fg.graphspec(name, graph_type, ...)`: write a GraphSpec document.
- `fg.layout(spec, data=None)`: draw a layout.
- `fg.load(path)`: a saved graph's record; its GraphSpec is under `"graphspec"`.
- `fg.blank(theme, format)`: a themed canvas for drawing with matplotlib what no graph type can; what's drawn on it is watermarked.
- A `Graph` has `.save(path)`, `.figure` and `.axes` (matplotlib's), `.issues` (the lint) and `.check()`.

From the command line, with the DataFrame saved as runs.parquet and a GraphSpec, voltage.yaml:

```yaml
name: voltage
version: 0
description: Cell voltage over a test, one line per cell.
extends: None
parameters: !var
    specifications:
        graph_type: xy
        theme: forgegraph_base/base_theme
        format: forgegraph_base/base_format
    text:
        title: Cell voltage
    data:
        file: runs.parquet
        preprocessing: None
    axis:
        x:
            data:
                column: hours
    series:
        voltage:
            color: cell
```

```bash
forgegraph render voltage.yaml
```

## Packs and configs

Every named theme, format, GraphSpec, layout and schedule comes from a **pack**, a folder or pip package of specs, and is named `pack/name`. The initial built-in packs are `forgegraph_base` and `forgegraph_base_2`, stored in src/forgegraph/packs.

A **config** lists the packs that may be used:

- The main config, `~/.config/forgegraph/config.toml` (or the file `FORGEGRAPH_CONFIG` names), applies to all work. ForgeGraph writes it, listing the built-in packs, the first time a command reads the configs, such as `catalog` or `render`.
- A folder config, `forgegraph.toml`, applies to the files in its folder and every folder below it. A file may use only the packs it lists.
- A pack that a folder config lists but the main config doesn't still works, but it's non-standard: graphs drawn with it are watermarked, and ForgeGraph's commands say so. That way you can make and try a pack without changing an organization's main config.

To write a pack, start from the example pack in [examples/packs/acme](https://github.com/sskaye/forgegraph/blob/main/examples/packs/acme); `forgegraph schema theme`, `format`, `pack` and `config` list every parameter.

On macOS, a scheduled render that writes into a cloud-synced folder needs Full Disk Access.

## Commands

- `forgegraph render <graphspec or layout>`: draw and save, and report lint.
- `forgegraph explain <graphspec or layout>`: every value it's drawn with, and which file set it.
- `forgegraph catalog`: the packs, graph types, layer types, themes, formats, GraphSpecs, layouts, schedules and reference notes available here.
- `forgegraph schema graphspec --graph-type <type> --theme <theme> --format <format>`: every parameter a GraphSpec can set.
- `forgegraph schema <kind>`: every parameter of a theme, format, layer, layout, schedule, pack or config.
- `forgegraph pack-notes`: the reference notes of the packs available here.
- `forgegraph load <file>`: a saved graph's record, and its GraphSpec.
- `forgegraph job run <schedule>`: render a schedule's GraphSpecs and layouts once.
- `forgegraph skill install`: install the agent skill.

Every command takes `--help`, and `--json` for agents.

## Catalogs

Each pack in this repository has a catalog: a page with a card for each parameter, showing what changing it does. Download a page and open it in a browser.

- [forgegraph_base](https://github.com/sskaye/forgegraph/blob/main/catalog/forgegraph_base.html): ForgeGraph's own pack, with its graph types and layer types.
- [forgegraph_base_2](https://github.com/sskaye/forgegraph/blob/main/catalog/forgegraph_base_2.html): its own theme and format, and the same graph types and layer types drawn in them.

## Your graphs are yours

ForgeGraph is [MIT-licensed](https://github.com/sskaye/forgegraph/blob/main/LICENSE). Graphs and other output you make with it are yours: no attribution or licence terms apply to them. See [TRADEMARKS.md](https://github.com/sskaye/forgegraph/blob/main/TRADEMARKS.md) for use of the name.

## Documentation

- [Specifications](https://github.com/sskaye/forgegraph/blob/main/docs/specs): every spec, a folder per kind.
- [Changelog](https://github.com/sskaye/forgegraph/blob/main/CHANGELOG.md).
- [Contributing](https://github.com/sskaye/forgegraph/blob/main/CONTRIBUTING.md): working on ForgeGraph itself.
- Design record, in [docs/design](https://github.com/sskaye/forgegraph/blob/main/docs/design):
  - [Architecture](https://github.com/sskaye/forgegraph/blob/main/docs/design/architecture.md): how ForgeGraph is designed, and why.
  - [To do](https://github.com/sskaye/forgegraph/blob/main/docs/design/todo.md): what's still planned.

## Contributing

Feature requests and bug reports go to [GitHub issues](https://github.com/sskaye/forgegraph/issues); the skill can file them for you. [CONTRIBUTING.md](https://github.com/sskaye/forgegraph/blob/main/CONTRIBUTING.md) covers working on ForgeGraph itself: setup, the checks to run, and regenerating the catalogs.

## Repository map

- **src/forgegraph/**: the package.
  - `graph.py`: the Python API (`fg.xy`, `fg.render`, `fg.graphspec`, `fg.load`) and the `Graph` object; `canvas.py`: `fg.blank`, the themed canvas; `drawn.py`: what they and layouts share once drawn; `data.py`: reading a GraphSpec's data.
  - **cli/**: the `forgegraph` command.
  - **spec/**: reading, checking and resolving specs, and the provenance record.
  - **drawing/**: drawing, layout and lint. **layouts/**: `fg.layout` and layouts. **jobs/**: scheduled renders.
  - **packs/**: packs and configs, and the built-in packs `forgegraph_base` and `forgegraph_base_2`. **fonts/**: bundled fonts and their licences.
  - **graph_types/**, **layers/**: the graph type and layer type definitions. **catalog_build/**: the catalog builder. **catalogs/**: each definition's catalog file.
  - **skill/forgegraph/**: the agent skill. `forgemark.py`: Forgemark's review-comment format, and its pinned tool.
- **catalog/**: the generated catalog pages.
- **examples/**: sample data; `packs/acme`, an example pack in a deliberately different style; and `layouts/`, a paper figure and a dashboard.
- **evals/skill/**: the skill's eval cases, run by `scripts/run_skill_evals.py`.
- **tests/**, **scripts/**: tests, and build and maintenance scripts.
- **docs/**: the specifications, the design record and the visual changelogs. **review/**: each build phase's review pages.

