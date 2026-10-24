# ForgeGraph

Fast, consistent, publication-quality graphs from pandas DataFrames, for people and AI agents alike.

You describe a graph in a short **GraphSpec**. ForgeGraph draws it in a house style that a **theme** and a **format** set once. It checks what it drew, and records how the graph was made inside the saved file. An agent skill lets Claude Code make and revise graphs the same way.

- **One look, kept:** themes fix what must stay the same (fonts, palette, lines, keys) and leave the rest to each graph.
- **Packs and configs:** an organization keeps the specs its graphs must use in a pack, and a config says which packs may be used, for all work or for one folder.
- **Lint on every render:** overlapping or clipped text, a key covering data, fonts too small for the format, dropped rows and more.
- **Provenance:** every saved file carries its GraphSpec and the specs it was drawn with, and `forgegraph load` recovers them.
- **Layouts:** several graphs in one figure, from a two-panel paper figure to an HTML dashboard with tabs.
- **Scheduled renders:** a schedule file re-renders graphs and layouts, with a "data as of" note and a stale banner.
- **Anything else, marked:** what no graph type can draw can be drawn with matplotlib on a themed canvas, and is always watermarked as non-standard.

**Status:** 0.x. One graph type, `xy` (lines, markers and bars), with reference lines, notes and error bars as layers. More graph types come from requests: [open an issue](https://github.com/sskaye/forgegraph/issues).

## Install

ForgeGraph needs Python 3.12 or later.

```bash
pip install forgegraph
```

For the `forgegraph` command on its own, `uv tool install forgegraph` works too. To give Claude Code the skill:

```bash
forgegraph skill install
```

Then ask Claude for a graph: the skill takes it from your data to a finished graph, saving the GraphSpec beside it.

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

From the command line, with the DataFrame saved as runs.parquet and a GraphSpec, voltage.yaml:

```yaml
name: voltage
version: 0
description: Cell voltage over a test, one line per cell.
extends: None
fixed_parameters: None
variable_parameters:
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
        y:
            data:
                column: voltage
    encoding:
        color: cell
```

```bash
forgegraph render voltage.yaml
```

## How a graph is made

- **GraphSpec:** what to draw: the data, the columns on each axis, colors, titles, layers. A YAML file, or a dict in Python.
- **Graph type:** the kind of graph, such as `xy`, and the parameters it offers.
- **Theme:** the look. It fixes some parameters and gives defaults for the rest.
- **Format:** the destination: figure size, base font size, file types and resolution.
- **Layers:** what's drawn over a graph: reference lines, notes, error bars.
- **Layout:** several GraphSpecs arranged in one figure or page.
- **Schedule:** the GraphSpecs and layouts to re-render, and when.

The input is a pandas DataFrame, passed through the Python API or saved as a Parquet file that the GraphSpec's `data.file` names. How the DataFrame is made is up to you; `data.preprocessing` can record where that code is.

## Packs and configs

Every named theme, format, GraphSpec, layout and schedule comes from a **pack**, a folder or pip package of specs, and is named `pack/name`. ForgeGraph's own pack is `forgegraph_base`; a second look, `forgegraph_base_2`, is in this repository's [packs](packs/forgegraph_base_2) folder.

A **config** lists the packs that may be used:

- The main config, `~/.config/forgegraph/config.toml` (or the file `FORGEGRAPH_CONFIG` names), applies to all work. ForgeGraph writes it the first time it runs, listing the built-in packs.
- A folder config, `forgegraph.toml`, applies to the files in its folder and every folder below it. A file may use only the packs it lists.
- A pack that a folder config lists but the main config doesn't still works, but it's non-standard: graphs drawn with it are watermarked, and ForgeGraph's commands say so. That way you can make and try a pack without changing an organization's main config.

## Commands

- `forgegraph render <graphspec or layout>`: draw and save, and report lint.
- `forgegraph explain <graphspec or layout>`: every value it's drawn with, and which file set it.
- `forgegraph catalog`: the packs, graph types, layer types, themes, formats and reference notes available here.
- `forgegraph schema graphspec --graph-type <type> --theme <theme> --format <format>`: every parameter a GraphSpec can set.
- `forgegraph schema <kind>`: every parameter of a theme, format, layer, layout, schedule, pack or config.
- `forgegraph pack-notes`: the reference notes of the packs available here.
- `forgegraph load <file>`: a saved graph's record, and its GraphSpec.
- `forgegraph job run <schedule>`: render a schedule's GraphSpecs and layouts once.
- `forgegraph skill install`: install the agent skill.

Every command takes `--help`, and `--json` for agents.

## Catalogs

Each pack in this repository has a catalog: a page with a card for each parameter, showing what changing it does.

- [forgegraph_base](catalog/forgegraph_base.html): ForgeGraph's own pack, with its graph types and layer types.
- [forgegraph_base_2](catalog/forgegraph_base_2.html): its own theme and format, and the same graph types and layer types drawn in them.

## Your graphs are yours

ForgeGraph is [MIT-licensed](LICENSE). Graphs and other output you make with it are yours: no attribution or licence terms apply to them. See [TRADEMARKS.md](TRADEMARKS.md) for use of the name.

## Documentation

- [Architecture](docs/architecture.md): how ForgeGraph is designed, and why.
- [Decisions](docs/decisions.md): decisions that refine the architecture.
- [Specifications](docs/specs): every spec, a folder per kind.
- [Changelog](CHANGELOG.md).
- [Build plan](docs/build-plan.md): how ForgeGraph is being built, phase by phase.

## Contributing

Feature requests and bug reports go to [GitHub issues](https://github.com/sskaye/forgegraph/issues); the skill can file them for you. [CONTRIBUTING.md](CONTRIBUTING.md) covers working on ForgeGraph itself. In short:

```bash
uv sync && uv run pre-commit install
```

```bash
uv run pytest && uv run ruff check . && uv run pyright
```

## Repository map

- **src/forgegraph/**: the package.
  - `graph.py`: the Python API (`fg.xy`, `fg.render`, `fg.graphspec`, `fg.load`) and the `Graph` object; `blank.py`: the themed canvas.
  - **cli/**: the `forgegraph` command.
  - **spec/**: reading, checking and resolving specs, and the provenance record.
  - **render/**: drawing, layout and lint. **layout/**: layouts. **jobs/**: scheduled renders.
  - **packs/**: packs and configs, and the built-in pack `forgegraph_base`. **fonts/**: bundled fonts and their licences.
  - **graph_types/**, **layers/**: the graph type and layer type definitions. **catalog/**, **catalogs/**: the catalog builder, and each definition's catalog file.
  - **skill/forgegraph/**: the agent skill.
- **packs/forgegraph_base_2/**: a second look, as a folder pack.
- **catalog/**: the generated catalog pages.
- **examples/**: sample data, and `packs/acme`, an example pack in a deliberately different style.
- **evals/skill/**: the skill's eval cases, run by `scripts/run_skill_evals.py`.
- **tests/**, **scripts/**: tests, and build and maintenance scripts.
- **docs/**: the documents above. **review/**: each build phase's review pages.
