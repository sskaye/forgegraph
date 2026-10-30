---
name: forgegraph
description: Creates a graph from a DataFrame with the ForgeGraph library. Select a graph type, theme and format; design the graph, render it, then iterate until it meets the request and is a good visualization of the data. Use this skill whenever the user asks you to make a graph, plot, multi-panel graph, or dashboard, or asks a question about ForgeGraph.
allowed-tools: Bash(forgegraph *)
---

# ForgeGraph

ForgeGraph is a library and agent skill for making high-quality graphs quickly and consistently. A ForgeGraph graph consists of:

- **GraphSpec**: the data and the graph's customizable features.
- **Graph type**: the type of graph, e.g. xy drawn with lines, markers, or bars.
- **Theme**: the look: fixed styles (fonts, palettes, spines, ticks, legend style), plus defaults for options.
- **Format**: destination-specific features: figure size, base font size, file type, dpi, etc.
- **Layers**: overlays on a graph: reference lines, error bars, notes.
- **Layout**: multiple GraphSpecs can be arranged in one figure: for multi-panel figures, dashboards.

The input is a pandas DataFrame saved as a Parquet file, named by the GraphSpec's `data.file`.

## Commands

- `forgegraph catalog`: lists the packs available, with each of their graph types, layer types, themes, formats, layouts, schedules, GraphSpecs, and reference notes.
- `forgegraph pack-notes`: prints the reference notes from the available packs, labelled by pack.
- `forgegraph schema graphspec --graph-type <type> --theme <theme> --format <format>`: lists every parameter a GraphSpec can set (its own, and the variable ones of the graph type, theme and format), with default, allowed values and description.
- `forgegraph schema theme`, `forgegraph schema format`, `forgegraph schema layer`, `forgegraph schema graph_type`, `forgegraph schema layout`, `forgegraph schema schedule`, `forgegraph schema pack`, `forgegraph schema config`: lists every parameter of the schema with their type, description, and default value. Does not show whether a parameter is fixed or variable.
- `forgegraph render <graphspec or layout> --json`: saves the graph or layout files and lists lint issues. A layout file ends in `.layout.yaml`.
- `forgegraph explain <graphspec or layout>`: lists every value the graph or layout is drawn with, whether it's fixed or variable, and which file set it.
- `forgegraph job run <schedule>`: renders the GraphSpecs and layouts a schedule file names.

Every command takes `--help`.

## Workflow

1. Select or prepare the DataFrame as a Parquet file.
2. Select the graph type, theme, format, and layers. If unclear, consult the reference notes or ask the user. If a fixed parameter or a missing graph type prevents you from fulfilling the user's request, say so and offer to make a request to ForgeGraph (instructions at references/requests.md). You can also ask if the user wants it drawn anyway. If so, draw it with matplotlib on `forgegraph.blank(theme, format)`, which is watermarked. If and only if the user explicitly asks, you can create or change a theme or format (see references/themes_formats_configs.md). Don't use other graphing libraries, or write charts by hand.
3. Write the GraphSpec (see examples below). It can set any parameter shown by `forgegraph schema graphspec`.
4. Render and check the output for issues: the lint and the image itself. On an error, use the error message and `forgegraph explain` to debug. If a command reports a non-standard pack, tell the user.
5. Iterate until the graph or layout meets the request and is a good visualization of the data. Check the image after each iteration, including follow-up requests.
6. Do a final inspection of the graph or layout to confirm everything before sharing with the user.
7. If you made a non-standard graph or layout, or any visual not drawn by ForgeGraph, ask the user whether they'd like to file a feature request for what ForgeGraph couldn't do (see references/requests.md).
8. If the user has provided a local folder, or you were started in one, save the GraphSpec, the graph and the Parquet file (if you created it) to that folder, not a temporary one.
9. If scheduling a job, write the schedule file and schedule `forgegraph job run <schedule>` using the method of your choice.

## Examples

- [examples/xy.yaml](examples/xy.yaml): an xy graph, one line per group.
- [examples/bars.yaml](examples/bars.yaml): each group's peak value as a bar, with its value.
- [examples/layers.yaml](examples/layers.yaml): the mean of each group's runs with error bars, a reference line and a note.
- [examples/figure.layout.yaml](examples/figure.layout.yaml): a layout of xy.yaml above bars.yaml.
- [examples/figure.schedule.yaml](examples/figure.schedule.yaml): figure.layout.yaml rendered every weekday at 06:00.

