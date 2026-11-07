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
- **Layers**: <!-- fmc:1 -->overlays on a graph: reference lines and bands, error bars, notes, controls that switch between views or show and hide series and layers.<!-- /fmc:1 -->
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
7. If you made a non-standard or watermarked graph or layout, or any visual not drawn by ForgeGraph, ask the user whether they'd like to file a feature request for what ForgeGraph couldn't do (see references/requests.md). Otherwise, don't mention it.
8. If the user has provided a local folder, or you were started in one, save the GraphSpec, the graph and the Parquet file (if you created it) to that folder, not a temporary one.
9. If scheduling a job, write the schedule file and schedule `forgegraph job run <schedule>` using the method of your choice.

## Examples

- [examples/xy.yaml](examples/xy.yaml): an xy graph, one line per group.
- [examples/bars.yaml](examples/bars.yaml): each group's peak value as a bar, with its value.
- [examples/layers.yaml](examples/layers.yaml): the mean of each group's runs with error bars, a reference line and a note.
- [examples/heat_map.yaml](<!-- fmc:2 -->examples/heat_map.yaml): a heat map, as an xy graph whose markers fill the grid (`marker.shape: grid_cell`).<!-- /fmc:2 -->
- [examples/controls.yaml](examples/controls.yaml): HTML controls: a dropdown that switches views, and checkboxes that show or hide series and layers.
- [examples/figure.layout.yaml](examples/figure.layout.yaml): a layout of xy.yaml above bars.yaml.
- [examples/figure.schedule.yaml](examples/figure.schedule.yaml): figure.layout.yaml rendered every weekday at 06:00.

<!-- forgemark-comments
- id: 1
  anchor_text: "overlays on a graph: reference lines and bands, error bars, notes."
  context_before: "Layers:"
  context_after: "Layout: multiple GraphSpecs can be arranged in one figure: for multi-panel"
  author: Claude
  timestamp: 2026-11-07T21:55:26Z
  resolved: false
  body: |
    Problem: the skill doesn't know about the choice and toggle layers, so an agent asked for a page where the reader picks a metric or hides a series won't look for them. The other new features (IQR limits, geometric functions, star and asterisk markers, title.max_wrap) are parameters that forgegraph schema already lists, so they need no skill text.
  suggested_edit:
    from: "overlays on a graph: reference lines and bands, error bars, notes."
    to: "overlays on a graph: reference lines and bands, error bars, notes; and controls on its HTML page that switch between views or show and hide series and layers."
  replies:
    - author: Steven
      timestamp: "2026-11-07T21:57:43.904Z"
      body: "overlays on a graph: reference lines and bands, error bars, notes, controls that switch between views or show and hide series and layers."
    - author: Claude
      timestamp: 2026-11-07T22:00:15Z
      body: |
        Done: the line is now your wording.
- id: 2
  anchor_text: "examples/heat_map.yaml): a heat map, as an xy graph whose markers fill the grid (marker.shape: grid_cell)."
  context_before: "[examples/heat_map.yaml]("
  context_after: "examples/figure.layout.yaml: a layout of xy.yaml above bars.yaml."
  author: Claude
  timestamp: 2026-11-07T21:55:26Z
  resolved: false
  body: |
    Problem: there's no example of the new layers. Proposed: add examples/controls.yaml (on this branch; it renders without lint issues beyond the data's one missing row) to the list.
  suggested_edit:
    from: "examples/heat_map.yaml): a heat map, as an xy graph whose markers fill the grid (`marker.shape: grid_cell`)."
    to: |-
      examples/heat_map.yaml): a heat map, as an xy graph whose markers fill the grid (`marker.shape: grid_cell`).
      - [examples/controls.yaml](examples/controls.yaml): an HTML page with a dropdown that switches the current axis between linear and log, and checkboxes that show or hide the series, error bars and target line.
  replies:
    - author: Steven
      timestamp: "2026-11-07T21:59:18.947Z"
      body: |-
        This is rendering funny, but I’m fine with these in the same style as the other examples.
        
        Question: Should we keep bundling examples in the skill or now that we have docs, should these be links to the relevant doc page. If it’s not inefficient for the agent to read the doc page, that gives us a single source to maintain and has a lot more detail on it.
    - author: Claude
      timestamp: 2026-11-07T22:00:15Z
      body: |
        Done: the line now reads "HTML controls: a dropdown that switches views, and checkboxes that show or hide series and layers", in the style of the others.
        
        On bundling the examples or linking to the docs:
        
        What I found:
        1. The skill is installed from the package (forgegraph skill install), so its examples always match the installed version, and they're read from disk with no network. The published docs follow the latest release, so an agent using an older ForgeGraph would read examples for features it doesn't have.
        2. Reading a docs page needs web access, which a sandboxed agent may not have, and in Claude Code a permission prompt the first time. A fetched page also usually comes back summarized, and a summary can lose the exact YAML.
        3. Size: the Layers guide is 84 KB as a web page (7.6 KB as Markdown), and an example file is 0.5 to 1.2 KB. The guide has more detail, but the agent mostly needs a working GraphSpec, and forgegraph schema already gives every parameter's description.
        4. The tests render every skill example, in the default pack and in acme's theme and format, so a broken example is caught. The docs examples are checked when the docs are built.
        
        Options:
        1. Keep bundling, as now. The two sets of examples stay separate to maintain.
        2. Link to the docs pages. One source, with more detail, but it needs web access, it may not match the installed version, and it costs the agent far more to read.
        3. Keep bundling, from one source: the package build copies the examples the skill lists from docs/examples, with their data, so the agent reads local, version-matched YAML and we maintain one set. The docs examples use the sample datasets, so the skill would bundle those few Parquet files instead of xy.parquet.
        
        Recommendation: 3. It keeps what makes the bundled examples work for agents, offline, small and version-matched, and gives us the single source you're after. I'd make it a separate change after this one.
-->
