# ForgeGraph — Architecture

**Owner:** Steven Kaye · **Author:** Claude (with Steven Kaye)
**Inputs:** the [initial specification](initial-specification.md) and a private set of example graphs.

---

## 0. Summary

ForgeGraph is a Python library, CLI and agent skill. They turn a short declarative **GraphSpec** into a graph styled to a house standard. A GraphSpec says which data to use, which graph type, which columns map to what, and a few options. Everything else is decided once, centrally, by a **theme** and a **format** that an organisation, a journal or a person can supply.

The core ideas, and why:

| # | Idea | Why |
| --- | --- | --- |
| 1 | **Packs**: themes, formats, GraphSpecs, layouts, schedules and reference notes can come from outside the repo (data only; graph types stay in the core); configs say which packs may be used | Organisations need their own house styles and reference notes. A public tool can't keep house style in its own repo |
| 2 | **Style has two axes, theme × format**. A theme is the look (fonts, palette, spines); a format is the destination (slide, journal column, dashboard tile: size, base font size, file type) | One graph must render correctly for a slide *and* a paper without being re-specified. Journals specify sizes, not palettes |
| 3 | **GraphSpecs to extend**: saved settings without data (graph type, columns, parameters, layers, theme, format), reused through `extends:` (e.g. `acme/polarization-curve`) | The cheapest way to get consistency for recurring graphs. No code, so orgs can write them |
| 4 | **The input is a DataFrame**: passed through the Python API, or read from a Parquet file the GraphSpec names. Preparing it is the user's and the agent's work | ForgeGraph stays about graphing, and rendering a GraphSpec never runs code |
| 5 | **Agent interface = CLI with JSON output + Agent Skill**, with a render → look → lint loop | The spec lists "AI agents via their standard interfaces", not just Claude Code. Graph quality has to be checkable by the agent itself |
| 6 | **Desktop app planned for**: a local, Tableau-like "Studio" where people make graphs without an AI, built last | It's a listed interface. Designing the schema for it now costs nothing; building it later costs less |

Also:

- Each graph type and layer type is defined by one file, which its drawing code reads.
- The review catalog is a tabbed HTML page; Forgemark supports per-tab comments.
- Company-specific material stays out of the repo: it lives in a private org pack, and `acme` is a neutral public example.

### 0.1 Decisions at a glance

| Area | Decision |
| --- | --- |
| Renderer (D1) | matplotlib only; no interactivity in the MVP |
| Core API (D2) | Spec-first: `render(spec)`; Python functions build specs. The definition files are the source; `forgegraph schema`, the catalog pages and the docs/specs mirrors are generated from them |
| Style (D3) | Theme × format, layered and explainable; themes tag parameters !fix (graphs can't change them) or !var, with defaults (graphs can change them) |
| Extension (D4) | Packs, data only, are the only source of named specs; the main and folder configs say which may be used, and a pack only a folder config lists is non-standard; graph types and layers stay in the core |
| Graph types (D5) | Each graph type's and layer type's definition file (graph_types/xy.yaml, layers/<type>.yaml) is the source of truth |
| Review (D6) | Tabbed HTML catalog with Forgemark comments |
| Input (D7) | A pandas DataFrame, from the Python API or a Parquet file named by the GraphSpec; an optional reference to the code that made it |
| Labels (D8) | Lightweight sub/superscript markup, applied to explicit labels only |
| Agents (D9) | CLI + Agent Skill; MCP server deferred |
| Non-standard (D10) | Agent draws it with an always-on watermark; requests as GitHub issues, filed by the agent as the skill's reference file says |
| Layouts (D11) | One layout engine for multi-panel figures and dashboards, in PNG, PDF and HTML |
| Scheduling (D12) | A schedule file, rendered by `forgegraph job run`, which the agent schedules by the environment's own means; freshness stamped in the image and shown at view time |
| Provenance (D13) | Embedded in every output via matplotlib's built-in metadata; full, minimal or off |
| Studio (D14) | Tableau-like drag and drop plus a house-style editor; built after everything else works |
| Stability (D15) | Versioned specs, library-level semver, visual changelog, pinning via lockfiles |
| Licence and name (§9) | MIT; the name kept by Steven Kaye via `TRADEMARKS.md` |
| What's planned | [To do](todo.md) |

---

## 1. Design principles

1. **The GraphSpec is the product.** Skill, notebooks, CLI, scheduler, dashboards and the future desktop app all produce or consume the same document. Python function calls build GraphSpecs; they are not a second code path.
2. **Three tiers of control, no fourth.**
   - **Fixed style**: house style, set by the theme and format (by the org, journal or user), never by an individual graph. Each value is a **parameter**, e.g. `plot_area.sides` or `series.colors`; a theme may also leave some parameters variable, for graphs to change.
   - **Options**: what an individual graph may vary. Each is documented with a default, except the data itself (the data file and the required mappings such as `x` and `y`), which every graph must specify.
   - **Escape hatch**: raw matplotlib on a themed figure, always marked non-standard.
3. **One source per fact; everything else is generated.** Each kind of document is defined by its definition file (§8): every parameter with its default, range and description. The code reads them; `forgegraph schema`, the catalog pages and the docs/specs mirrors are generated from them, and the skill reads them at run time. Nothing generated is edited by hand.
4. **Renderer code holds no style constants.** Every visual value is read from the resolved spec. Editing a default in YAML changes the output without editing code, and tests check that each value actually changes something (§7).
5. **Extensible without forking.** Anything an organisation would want to customise can be supplied by a pack.
6. **Reproducible by default.** A rendered file carries its own spec and provenance. A saved spec plus a data reference re-renders the same graph tomorrow, or with tomorrow's data.
7. **Opinionated defaults, deliberate exceptions.** Anything outside the catalog is allowed but visibly labelled, and it feeds a request flow, so the catalog grows from real need.

---

## 2. Vocabulary

| Term | What it is | Where it lives |
| --- | --- | --- |
| **GraphSpec** | One specific graph: data, graph type, column mappings, parameters, layers | a YAML file, embedded in the saved graph |
| **Graph type** | A kind of graph (`xy`): the parameters a GraphSpec chooses, in its definition file, drawn by its module in drawing/ | `src/forgegraph/graph_types/<type>.yaml` (core only) |
| **Layer** | An addition drawn on a graph (`reference_line`, `note`, `error_bar`), defined by its own file | `src/forgegraph/layers/<type>.yaml` (core only) |
| **GraphSpec to extend** | A GraphSpec without data, reused by others through `extends:`. E.g. "polarization curve" = `xy` + its columns + axis titles | a pack's `graphspecs/` |
| **Theme** | The look: fixed style (fonts, palettes, spines, ticks, legend style), plus defaults for options | a pack's `themes/` |
| **Format** | The destination: figure size, base font size, file types, dpi, provenance level | a pack's `formats/` |
| **Layout** | Several graphs on one canvas, used for both multi-panel figures and dashboards | `*.layout.yaml` |
| **Pack** | A folder or pip package that bundles themes, formats, GraphSpecs, layouts, schedules, fonts and reference notes. Data only, no code | anywhere; listed in the main config or a folder config |
| **Scheduled render** | A schedule file's GraphSpecs and layouts, rendered by `forgegraph job run`, which whatever the environment offers runs on a schedule | a `*.schedule.yaml`; outputs wherever it says |

---

## 3. Architecture

```
 Interfaces   Python API · CLI (forgegraph) · Agent Skill · Studio desktop app (later) · OS scheduler
                    │ all build / read
 Documents    GraphSpec · Layout · Schedule    (YAML, each spec versioned)
                    │
 Pipeline     resolve ──► read ──► validate ──► render ──► lint ──► export
               │           │          │             │          │         │
               │       DataFrame   data        matplotlib  overlap,  PNG/SVG/PDF/HTML
               │       or Parquet  contract    engine      clipping, + provenance
               │       file        check                   palette…
               │
 Registry     graph types · layer types · packs (themes · formats · GraphSpecs · layouts · schedules · notes)
               ▲
               ├── which packs may be used: the main config, then the folder config
               └── values: graph type  ◄  theme  ◄  format  ◄  extends  ◄  the spec itself
```

**Resolve** merges, in order: the graph type's defaults, then the theme, the format, any spec named in `extends:`, and finally the spec itself. Each field has a defined merge rule (replace by default; `layers` merge by name, so a GraphSpec adds layers or changes an inherited one by naming it), set in the GraphSpec specification. Resolve records where each value came from. `forgegraph explain my.yaml` prints the resolved spec with an origin for every value (like `git config --show-origin`). When someone asks "why is my legend frameless?", the answer is one command away.

**Read** takes the DataFrame passed in, or reads the Parquet file the GraphSpec's `data.file` names. **Validate** checks the frame against the graph type's columns and fails with messages an agent can act on ("axis.y.data.column: no column 'Voltage' in the data; columns are …"). **Lint** inspects the rendered figure as part of every render (D9). **Export** writes the files and embeds provenance.

### 3.1 What it looks like to use

**GraphSpec** (docs/specs/graphspec/graphspec_example.md lists every parameter):

```yaml
name: voltage
version: 0
description: Cell voltage over a test, one line per cell.
extends: None
parameters: !var
    specifications:
        graph_type: xy
        theme: forgegraph_base/base_theme      # from a pack the configs allow
        format: forgegraph_base/base_format
    text:
        title: Cell voltage
    data:
        file: runs.parquet      # or a DataFrame passed through the Python API
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
    layers:
        target:
            type: reference_line
            axis: y
            value: 0.7
            label:
                text: Target
```

**Python:**

```python
import forgegraph as fg

g = fg.xy(df, x="current_density", y="cell_voltage", color="cell")
g                                  # renders inline in Jupyter
g.save("polarization.png")         # PNG with its GraphSpec embedded
record = fg.load("polarization.png")
record["graphspec"]                # the GraphSpec, recovered from the image
```

**CLI** (every command has `--json` for agents):

```
forgegraph catalog                     # what the configs allow: graph types, themes, formats, ...
forgegraph catalog themes              # one kind: graph-types, layers, themes, formats, graphspecs, layouts or schedules
forgegraph schema graphspec --graph-type xy --theme acme/acme --format acme/slide   # what a GraphSpec can set
forgegraph render polarization.yaml    # lint warnings come back with every render
forgegraph explain polarization.yaml
forgegraph load out/polarization.png   # print the spec embedded in an image
```

---

## 4. Key decisions

### D1. Renderer: matplotlib, one engine

**matplotlib is the single renderer.** Everything in the examples is a static, typographically precise figure, and real graphs will go to many static destinations: papers, reports, slides, posters, dashboards, model-validation outputs. That covers mathtext units (cm², L⁻¹ s⁻¹, P<sub>max</sub>), log axes with 10ⁿ ticks, braces, ellipses, leader lines and colorbars, and every one of these is native to matplotlib. It installs light and renders headless with no browser, which matters for scheduled and cloud runs. Plotly's static export now needs a local Chrome install. Scientists also already know matplotlib, which makes the escape hatch (D10) genuinely useful.

The GraphSpec stays renderer-agnostic, so the choice is contained. If interactive dashboards with hover and live filters become a priority, add an *optional* second backend for a subset of graph types (Plotly or Vega-Lite), held to the same gallery-conformance tests. Until then, HTML dashboards are pages of crisp SVG.

Interactivity is not part of the MVP. If it becomes a requirement later, the optional-backend route above is the plan.

### D2. Spec-first core, Python sugar

`fg.render(spec, data=None) → Graph` is the real API. `fg.xy(df, …)` builds a spec and calls it. A `Graph` holds `.spec`, `.figure` and `.axes` (the escape hatch), `.issues` (lint; `.warnings` as messages) and `.record()` (provenance), and shows itself as an image in notebooks.

**Where the definitions come from.** Each kind of document is defined by its definition file (§8); spec/parameters.py reads every parameter, range and description from it, and validation, `forgegraph schema` and the catalog all use what it reads. A GraphSpec is checked against the graph type it names, so an error names only that graph type's parameters. The provenance record and a job's status file are pydantic models.

**Rendering is isolated from the user's matplotlib state.**

- Chart renderers draw into an Axes they are given. They never create figures and never use `pyplot`, so layouts (D11) can place any chart in any panel, notebooks don't show a graph twice, and servers can render concurrently.
- Every render runs inside an rc context that starts from matplotlib's defaults plus the theme. A user's `matplotlibrc` or an earlier `plt.style.use(…)` in the notebook can't leak in.

### D3. Style resolution: theme × format, layered, explainable

**One structure for every specification.** Themes, formats, graph types and GraphSpecs are written the same way, and each kind is defined by one file: the base pack's `themes/base_theme.yaml` and `formats/base_format.yaml` (in `src/forgegraph/packs/forgegraph_base/`), each graph type's own file (`graph_types/xy.yaml`) and an example GraphSpec that sets every parameter (the base pack's `graphspecs/graphspec_example.yaml`). Every file has a header (`name`, `version`, `description`, `extends`) and `parameters`, one tree of categories of parameters. In a definition file every line, header included, gives its value and a comment `[RANGE]; DESCRIPTION`, and the code reads every definition, range included, from those files.

- **!fix:** a GraphSpec can't change it (principle 2). A different look needs a different theme, typically one that extends the house theme.
- **!var:** a GraphSpec may change it, under the same category; the file gives the value it has otherwise.
- A tag goes before a value (`width: !var 0.15`) or on a category (`output: !var`), where it applies to everything inside unless a tag further in says otherwise. A tag with no value (`width: !var`) changes only the status.
- **extends:** every parameter a file doesn't list is inherited, with its status. The nearest file that tags a parameter, or a category above it, decides its status. With `extends: None` the file lists every parameter and tags each, itself or through a category.
- In a theme or format, a graph type's name used as a heading holds parameters for that graph type only.

Every size in a theme is a multiple of the format's base font ("tick labels = 0.9 × base"), so a theme renders correctly in any format. That matters because graphs go to many destinations, not mainly slides (so no `.pptx` export: the examples were collected on slides only for convenience).

**The base theme** (forgegraph_base/base_theme): Roboto, a full box, outward ticks, the Okabe–Ito palette, a frameless key, direct labels where they fit. The `acme` example pack has a *deliberately different* house style (IBM Plex Serif, two sides of the box, a grid, Paul Tol's muted palette), so it shows that a pack can change the look completely.

**Fonts and PDFs:**

- Fonts are bundled as static TTF instances; matplotlib can't use variable-font axes.
- Maths in labels uses the theme font, upright rather than italic.
- PDF and PostScript output embed TrueType (Type 42) fonts rather than matplotlib's default Type 3, which many journal submission checks reject.

*The base pack's files are the specification (§8).*

### D4. Packs: extension without forking

```
acme-forgegraph/
├── pack.yaml                 # name, version, description, issues, requires
├── themes/house.yaml
├── formats/slide.yaml
├── graphspecs/polarization-curve.yaml
├── layouts/dashboard.yaml
├── schedules/workday.yaml
├── references/house.md       # notes for the agent
└── fonts/
```

- **Packs are the only source of named specs.** Every theme, format, GraphSpec, layout or schedule that a file names, under specifications or in extends, comes from a pack and is named `pack/name`. ForgeGraph's own specs are the pack `forgegraph_base`: `base_theme`, `base_format`, `base_layout_format`, `base_layout`, `base_schedule` and example GraphSpecs. Specs of your own are a folder pack. The files you draw (GraphSpecs, layouts and schedules, a layout's tiles and a schedule's targets) are given by path.
- **Graph types and layer types** are ForgeGraph's code, not pack data, so they're named without a prefix (`xy`) and can always be used.
- **The config says which packs may be used** (packs/__init__.py has the rules): the main config for all work, and a folder config, `forgegraph.toml`, for the files below it.
  - A pack only a folder config lists is non-standard: it works, but whatever is drawn with it is watermarked and its record names the pack. That way someone who can't change an organization's main config can still make and try a pack, and nothing drawn with it passes as standard.
  - Configs are found from the drawn file and the user, not the working folder, so a scheduled run is checked the same way.
- **Configs restrict use, not access.** A drawn file may name only the allowed packs' specs, but a pack's specs may build on any spec ForgeGraph can find, so a pack can extend another without every user allowing both.
- **Extending** creates a new spec, so it isn't narrowing: a spec is usable only if its own pack is allowed. The narrowing always allowed is a GraphSpec setting the variable parameters of the theme and format it names.
- **No defaults.** Every GraphSpec names its graph type, theme and format, itself or through the GraphSpec it extends; a layout names its format. The base specs are what other specs extend.
- **Distribution:** a local folder, or a pip package that declares a `forgegraph.packs` entry point. Pip already handles git URLs (`pip install git+https://…`) and versions, so ForgeGraph has no fetching or caching of its own.
- **Pinning:** pip packs are pinned like any dependency, in the project's lockfile; folder packs by git commit. Scheduled dashboards therefore don't change looks by surprise.
- **Skill integration:** `forgegraph catalog` lists the allowed packs' specs, `forgegraph pack-notes` prints their reference notes, each under its pack, and requests about a pack's specs go to the address in its pack.yaml's `issues`.
- **Data only, never executed.** Packs hold YAML, Markdown and fonts, never Python. Graph types and layers live only in the core library. An org that needs a new graph type requests it upstream (D10); an org-specific variant of an existing type is a GraphSpec to extend.
  - **Loading:** ForgeGraph finds a pip pack's files through package metadata without importing it, and loads YAML with a safe loader.
  - **Reference notes:** the skill treats them as reference data, not as instructions.
  - **Trust:** installing a pip package is still a trust decision, as for any package.

### D5. Graph types and layer types: one definition file each

A graph type is defined by its own file in `src/forgegraph/graph_types/`, starting with `xy.yaml`, and drawn by drawing/xy.py; a layer type by its file in `src/forgegraph/layers/`, drawn by drawing/layers.py. Its parameters are what a GraphSpec chooses for one graph: the data column for each axis, the encodings, the marks and the legend. Things drawn on top of the graph, including those computed from its data (error bars, a reference line at the mean, a fitted curve), are layers. A parameter defined as None with no None in its range is required: a GraphSpec must set it. Style values never live in a graph type: the renderer reads them from the theme, so the theme stays the single place where style values live. The graph code receives a DataFrame; loading and preparing data happens before it.

**Series labels come from a set of labelling methods.** Each method either places every label cleanly or reports that it can't. The theme lists the methods it allows, in order of preference, and a graph's `legend.method: auto` uses the first that fits. A method chosen by name that doesn't fit, or `auto` with nothing that fits, is an error that says what to change: ForgeGraph never draws labels over data as a fallback. The first methods are:

- `direct`: labels inside the plot, each beside its own series, touching no line, marker or other label;
- `key`: a key at the first of the GraphSpec's legend.key.positions that covers no data, or outside the plot area (legend.key.inside: false);
- `none`.

A single series is named too, unless its name is the y-axis title's text, which already names it. A numeric `encoding.color.column` is drawn on a color scale with a color bar, or with palette colors and labels when `encoding.color.type` is `categorical`; with lines shown, a line joins only points of one color.

Placement is deterministic. A direct label sits inside the plot, beside its own series, touching nothing; drawing/labels.py lists the rules. A key, and the style key that explains encoding.line.style.column, sits inside the plot area at the first position that covers no data, or outside it, with the figure laid out again around it; drawing/key.py places it. Existing labelling libraries (matplotlib-label-lines, adjustText) don't meet these rules.

### D6. Review surface: tabbed HTML catalog, Forgemark comments

- `forgegraph catalog build` generates one **HTML catalog** per pack, with a tab per kind (themes, formats, graph types, layers). Each spec shows its generated table, its baseline, and one image per variable parameter, with that parameter changed. A rule chooses each image's value and the baseline it's drawn on, not a hand-picked list, so the catalog files hold only generic baselines. Every parameter gets such a card, fixed ones included, and the perturbation tests draw them all; a format's output and provenance parameters, which change only the saved files, and a graph type's layer.types, which only permits layers, get none. Forgemark supports per-tab comments in HTML.
- **Comments survive rebuilds.**
  - The build gives every section, table row and figure a stable `id` (`#xy-param-labels`, `#xy-example-labels-direct`), and carries the trailing `forgemark-comments` block across verbatim.
  - It then re-attaches each comment by its recorded anchor text, using Forgemark's own `reattach`. Only comments whose text actually changed stay orphaned.
  - `forgemark lint` reports any orphans.
- **Size and freshness.**
  - Catalog images are embedded at screen resolution, which keeps the file small enough to commit.
  - The page records a hash of its inputs (the package's files and the library version). CI checks that hash rather than comparing pixels, which differ slightly between machines.
- **Packs build their own catalog.** An org reviews its house style the same way the project reviews the core. A pack's catalog draws every card with its own theme's and format's values, not those its GraphSpecs set.
- **GitHub:** a PR shows definition-file diffs as text and changed baseline PNGs as image diffs, which is enough for code review. There are no separate per-chart README files to keep in sync.
- **Requests don't need a PR.** PRs are for contributors who write code. Anyone else asks for a new graph type through a GitHub issue, which the agent can file for them (D10).

**Why HTML, not another format.** Alternatives considered:

- **Markdown has no tabs.** Neither CommonMark nor GitHub's flavour has them. MkDocs, Docusaurus, Quarto and Obsidian each add their own incompatible tab syntax, which shows up as raw text anywhere else.
- **A docs site** (MkDocs, Quarto) means many pages, a build step and somewhere to host it, with no built-in commenting.
- **Notebooks** review poorly.
- **PDF** is static, and its comments don't map back to the source.

A single self-contained HTML file opens anywhere offline, embeds its images, supports tabs, and Forgemark can comment on it.

### D7. Input: a DataFrame

ForgeGraph takes a pandas DataFrame and draws a graph from it, as the GraphSpec, theme, format and graph type say. The DataFrame comes either through the Python API (`fg.render(spec, df)`, `fg.xy(df, …)`) or from a Parquet file the GraphSpec names. How the DataFrame was made, and where its file is kept, are up to the user and the agent.

The GraphSpec's `data` category:

- **`data.file`**: the Parquet file: an absolute path, a path starting with `~`, or a path relative to the folder of the GraphSpec file that sets it. None: the DataFrame is passed through the Python API. A DataFrame passed in is drawn whatever `data.file` says.
- **`data.preprocessing`**: optional; where the code that made the data is (a path, a URL, a note). ForgeGraph records it in provenance and never reads it.

Drawing reads the DataFrame and checks it against the GraphSpec: the named columns exist, axis columns are numeric or dates, a log axis has no values of 0 or below. A missing data file, a file that isn't Parquet, or a GraphSpec with no data file and no DataFrame is an error naming the parameter.

### D8. Text: lightweight markup for scientific labels

Every example uses units with super- and subscripts. **Explicit labels** (`text.title`, `axis.x.title`, `axis.y.title`, key titles and layers' text) accept a small markup, rendered in the theme font:

- **Superscripts** with braces, or `^` followed directly by an optional minus sign and digits: `mA/cm^2`, `L^-1 s^-1`, `10^{-3}`.
- **Subscripts** only with braces: `P_{max}`, `KOH_{aq}`, `ΔV_{Al}`.
- Only the script fragments are typeset as maths, so spaces between units survive.

Labels default to the column name, and those defaults are shown **literally**: `current_density` keeps its underscore, and a `$` in a column name is just a dollar sign.

### D9. Agent interface: CLI + Skill; render → look → lint

- **CLI with `--json` is the universal agent interface.** Any agent with a shell can use it: Claude Code, Codex, Claude or ChatGPT desktop with code execution, CI.
- **The skill** is an Agent Skill folder (`SKILL.md` and example GraphSpecs), a format several agent platforms now read.
  - **It ships inside the Python package:** `forgegraph skill install` copies it into the agent's skills folder.
  - **`SKILL.md` is a short workflow.** Everything that depends on the installed version is fetched at run time with `forgegraph catalog` and `forgegraph schema`: graph types, themes, formats, every parameter with its range and description, GraphSpecs to extend, packs and reference notes. The skill therefore always matches the installed library and packs, and nothing needs regenerating.
- **MCP server: deferred** (§11).
- **The loop the skill follows** is SKILL.md's workflow: choose, write the GraphSpec, render, look, lint, and iterate until the graph meets the request.
- **Lint** runs as part of every render and catches what an agent often misses, such as overlapping or clipped text, a key covering data and fonts too small for the format; drawing/lint.py lists every check.

### D10. Non-standard graphs and the request flow

When a request isn't in the catalog, the agent says so plainly, then:

1. **Compose first** when the request is a variation of something supported: the closest graph type + layers.
2. **Draw it anyway** when nothing is close, e.g. a violin plot when only `xy` exists. The *agent* writes raw matplotlib on a themed canvas (`fg.blank(theme, format)`), so the result is at least on-style. The requester never writes code.
3. **Watermark it.** Every non-standard output gets a prominent diagonal, semi-transparent "NON-STANDARD" watermark across the plot area, plus `nonstandard: true` in provenance, and a warning to the user. The watermark is **always on**, and a GraphSpec can't change it: its parameters are fixed in the theme. A theme's author can restyle it, even out of sight, so an organisation that wants it required keeps it in its own theme. This also covers changes made after rendering: whatever draws or saves the figure, ForgeGraph or matplotlib directly, first checks that it still has the artists it had when rendering finished, drawing the same pixels. If anything was drawn or changed through `.axes` or `.figure`, the output is marked non-standard, because its embedded spec no longer reproduces it, and it stays non-standard.
4. **Offer a request.** With the user's OK, the agent files a feature request or bug report as a GitHub issue, as the skill's reference file says. Graph types live only in the core (D4), so every request goes upstream, where the maintainer handles it.

### D11. Layouts: multi-panel figures and dashboards are one feature

```yaml
name: lab_throughput
version: 0
description: Daily operations view of lab throughput.
extends: forgegraph_base/layout_example
parameters:
    specifications:
        format: ops/dashboard
    separators:
        line:
            show: true
    tabs:
        Overview:
            grid:
                areas: [[weekly,  weekly,   lost],
                        [samples, run_time, .   ]]
                row_heights: [1.2, 1]
            tiles:
                weekly: throughput_weekly.yaml
                lost: lost_runs.yaml
                samples: samples_weekly.yaml
                run_time: run_time.yaml
        By instrument:
            grid:
                areas: [[hplc_01,  hplc_02   ],
                        [gc_ms_01, icp_oes_01]]
            tiles:
                hplc_01: runs_hplc_01.yaml
                hplc_02: runs_hplc_02.yaml
                gc_ms_01: runs_gc_ms_01.yaml
                icp_oes_01: runs_icp_oes_01.yaml
```

**A layout arranges GraphSpecs.** A layout file (`*.layout.yaml`, docs/specs/layout/layout_example.md) holds only what's particular to several graphs together: the arrangement, and what separates the graphs. Text, colors, fonts and the look of each graph stay in each tile's GraphSpec and its theme, so a tile drawn alone and in a layout is the same graph. A layout has no per-tile settings and no text of its own.

- **Format, no theme.** The layout's format (by default the base pack's base_layout_format: the base format at 300 mm) sets the size and output of the whole figure, and replaces each tile's own format, so every tile is drawn at one base size. The layout can set the format's variable parameters, such as its file types. Each tile keeps its own theme.
- **The grid.** grid.areas draws the grid as rows of tile names, as CSS `grid-template-areas`, matplotlib's `subplot_mosaic` and patchwork do: a name repeated over a rectangle of cells spans it, and `.` is a blank cell. column_widths and row_heights are ratios of plot boxes.
- **Aligned plot boxes.** A tab's tiles are laid out together, as patchwork, egg and cowplot do: each column's and row's margins are the most room any of its tiles needs around its plot box, measured to the letters, so plot boxes line up across tiles whatever their tick labels. A spanning tile's plot box runs across the margins and gaps inside it. With the format's height auto, each row is as tall as its tiles' aspects need. Tiles are never shrunk to fit; a figure too small for them is an error naming them.
- **Separators.** The gap between tiles, its color, and optionally a line along the middle of each gap between two tiles.
- **Tabs.** Each tab is a figure of its own, at the format's size. html saves one page with a tab bar, each tab with its own link (#by-instrument); pdf, a page per tab; other file types, a file per tab (lab_throughput-overview.png). A layout's tabs replace those it inherits.
- **Data:** each tile draws from its own data.file.
- **HTML** is each figure as SVG, its text as outlines, in a minimal page; a figure shrinks to fit a narrow window without reflowing. A GraphSpec can be saved as a page too. Scheduled runs add the "data as of" stamp and the stale-banner script (D12).
- **Rendering:** each tab renders as one matplotlib figure, each tile drawn into its own Axes in its own theme's settings.
- **What's given up:** pages don't reflow on phones. Panel labels, shared axes and one legend for several tiles aren't drawn yet.

Paper figures and ops dashboards differ only in their format and defaults; examples/layouts has one of each.

### D12. Scheduled graphs and dashboards

A scheduled job is a **schedule file** (`*.schedule.yaml`, docs/specs/schedule/base_schedule.md): the GraphSpec and layout files to render, where to save them, and when. It extends the base schedule like any other spec, so it can be reviewed, kept in version control and checked like any parameter.

- **Cadence.** `interval.count` counts `interval.unit` (minute, hour, day, week, month or year), and `at` says when in each unit, one time or a list: ":30", "06:00", "mon 06:00", "1 06:00", "Jan 1 06:00". `interval.count` divides 60, 24 and 12 for minutes, hours and months, and is 1 otherwise, so every form maps exactly onto every scheduler. Times are the machine's local time.
- **`forgegraph job run lab.schedule.yaml`** runs a schedule once. Whatever the environment offers schedules that command: the machine's scheduler (launchd, systemd, cron, Task Scheduler), a GitHub Actions workflow, a Claude scheduled task. ForgeGraph writes no scheduler entries itself, so every user's path is the same.
- **Each run** takes a lock, renders every target (a failing one is recorded and the others still render), writes the status file, and runs `on_failure` or `on_success` without a shell.
- **Run status.** Every run writes `<name>.status.json` beside its outputs, whole: last attempt, last success, consecutive failures, and for each target its outputs, rows, data files and their times, lint count and errors. `job run` also writes a log, rotated so it can't grow without limit.
- **Freshness without a monitor.** Every output shows a "data as of" footnote **in the image itself** (the oldest data file's modification time, and the cadence in words), drawn in the theme's footnote look. It's the data's time, not the clock's, so the same data gives the same image.
  - **HTML pages** show a stale banner on their own when the data is older than `freshness.stale_after_hours` (by default, the longest gap between runs plus 25 %), so a job that silently stopped can't look current. This works where the page's script runs (a local browser or a web host). File-sharing previews often don't run scripts, so the in-image footnote is what always shows.
- **The skill** has the agent write the schedule file and schedule `forgegraph job run <schedule>` by the method of its choice.
- **Data:** the job renders; keeping the targets' Parquet files current is the user's job.
- **macOS:** a background job that writes into a cloud-synced folder needs Full Disk Access.

### D13. Provenance and reproducibility

Every output embeds a provenance record, at its format's provenance.level (full, minimal or off), so a graph can be traced and redrawn; docs/specs/provenance/provenance.md lists what each level records.

- **Carriers.** Provenance is one JSON record written through matplotlib's own metadata support: a PNG text chunk, a JPEG comment, the TIFF image description, the SVG Dublin Core `Description` field, and the PDF Info dictionary. HTML pages carry it in `<script type="application/json">`. drawing/export.py writes it.
- **Layouts.** A layout's files record the layout as written and, for each tab they show, each tile's GraphSpec file and the same entries as a GraphSpec's.
- **Privacy.** The built-in formats use `full`, so published figures stay reproducible and traceable; `minimal` is for formats whose files must not reveal where their data is.
- **Determinism.** Exports honour `SOURCE_DATE_EPOCH` and a fixed SVG hash salt, so tests can produce stable files.
- **Recovery.** `forgegraph load image.png` recovers the spec. Because PowerPoint and Slack strip metadata, the skill also saves the GraphSpec beside the graph, in the user's folder.

### D14. Desktop app: "Studio"

**Purpose:** let a person make a graph without an AI, through a Tableau-like interface.

```
┌ Data ──────────┐ ┌ Graph: [xy ▾]  Extends: [— ▾] Theme: [acme ▾]  Format: [slide-double ▾] ┐ ┌ Options ──────────┐
│ # current_dens │ │  X      [ current_density            ]                               │ │ mode  [lines+mk ▾]│
│ # cell_voltage │ │  Y      [ cell_voltage               ]                               │ │ labels [direct ▾] │
│ A cell         │ │  Color  [ cell                       ]                               │ │ x scale [linear ▾]│
│ A cell_size    │ │  Style  [ cell_size                  ]                               │ │ grid  [ ]         │
│ ◷ test_date    │ │                                                                      │ │ x label [ … ]     │
│                │ │ ┌──────────────── live preview ────────────────┐                     │ │ (set by theme:    │
│ (from data)    │ │ │                                               │                     │ │  spines, font)    │
└────────────────┘ └─────────────────────────────────────────────────────────────────────┘ └───────────────────┘
```

- **Data:** Studio opens a GraphSpec, or a Parquet file to start a new one.
- **Fields panel:** the DataFrame's columns, typed as numeric, categorical or date.
- **Shelves:** drag fields onto X, Y, Color, Style, Series and Error. These write the GraphSpec's mappings.
- **Options panel:** generated from the graph type's definition file, so every new parameter appears automatically. Values that the theme controls are shown read-only, with the reason.
- **Live preview:** each change re-renders through the same pipeline.
- **Theme and format editor**, for whoever owns the house style. It edits a pack's `themes/` and `formats/` files and previews the result across the whole gallery.
- **Round trip with the AI:** Studio opens any GraphSpec, or any ForgeGraph PNG via its embedded spec, so a graph the agent made can be tweaked by hand and vice versa. Saving writes the spec, keeping the user's comments and key order.
- **Later:** a layout editor for dashboards and multi-panel figures, and a catalog browser.

**Build:** a local web app (`forgegraph studio`: a Python server running the library, plus a frontend with drag-and-drop), packaged as a desktop app. The UI framework is chosen in its UI plan, trying a Python UI framework (e.g. NiceGUI) first before committing to a separate TypeScript frontend. It's still a GUI over specs: schema-described options are what make it feasible.

**When:** after everything else works (see [to do](todo.md)).

- **Ready for it from the start:** options are described by the schema.
- **Built with Studio:** the shelf-mapping code and its round-trip tests.
- **Not mappable:** a spec using something shelves can't show opens with that part shown read-only.
- **Validation:** once built, it gets a hands-on trial to judge whether it's sufficient.

### D15. Stability for a public library

- **Specs are versioned.** Every spec file has a `version`, and provenance records it, with a pack spec's pack version. `forgegraph migrate` is written when a spec change needs it.
- **One version number: the library's**, using semver. The built-in packs are released with it and carry its version; other packs have their own, like any package.
  - **Major:** a breaking change to a spec format.
  - **Minor:** releases may change how graphs look.
- **Visual changelog:** each release lists every appearance change, with before and after images of every catalog card and regression graph that changed.
- **Pinning:** projects and scheduled renders pin versions through their lockfile, so a dashboard can't change appearance overnight.
- **No telemetry.** Feature requests come from the request flow and GitHub issues.

---

## 5. Scope and coverage of the examples

**Graph types:** `xy` draws lines, markers and bars: grouped, stacked, 100 % stacked and horizontal, with value labels.

**Layers:** `reference_line` (horizontal or vertical, labelled), `note` (the "conditions" text block) and `error_bar`. Error bars are a layer, drawn from DataFrame columns or the spread of aggregated rows: the specification names their absence as a failing of Tableau.

| Capability | Status |
| --- | --- |
| lines and markers, color by a column, direct labels, a benchmark series | built |
| markers-only scatter with many points | built |
| replicates: several lines per color group (encoding.detail.column) | built |
| line style by a column, with a key for the styles | built |
| log axes, unit markup | built |
| color by a numeric column, with a color bar | built |
| wide data (several y columns) | built |
| bars: grouped, stacked, horizontal, with value labels | built |
| reference lines, notes and error bars | built |
| multi-panel figures and dashboards (layouts) | built |
| target regions, fill between, stacked decomposition | on request |
| annotations: arrows, braces, highlights, leader callouts | on request |
| the distribution graph type (box plus strip, categorical x) | planned |
| iso-curves (x·y = c) and a fit layer | planned |

**Annotations** aren't in the first release; they're built when someone asks for them. Producing them deterministically at good quality is hard, so the problem is split in two. The *drawing* is deterministic: `arrow`, `brace`, `ellipse`, `text` and `delta` would be layers anchored in data coordinates, stored in the spec, and re-render identically. The *judgement* — what to call out and where to put it — is the agent's, checked by lint for overlaps. That makes annotations reproducible and reviewable while still using the agent for what it's good at.

---

## 6. Repository layout

Repo `sskaye/forgegraph`; distribution, import and CLI `forgegraph`. The README's repository map describes each folder.

**Dependencies:**

- **Core:** matplotlib, pandas, pyarrow (Parquet), pydantic, ruamel.yaml, packaging, and typer for the CLI.
- **ruamel.yaml instead of PyYAML:** it follows YAML 1.2, so `18:00` stays a time string rather than becoming `1080`, `1.10` isn't read as `1.1`, and `NO` isn't read as false. It also keeps comments and key order when Studio or `forgegraph` rewrites a file.
- **Python ≥ 3.12.** It's the default on current long-term-support Linux (Ubuntu 24.04) and widely supported across the scientific stack. The minimum is reviewed at each release.

---

## 7. Quality and testing

- **Image regression, in two tiers.**
  - On the same platform and lockfile, output must be pixel-identical.
  - Across platforms, it must be within a tolerance: anti-aliasing and compression differ slightly between Linux CI and a Mac.
  - Baselines are drawn with `scripts/build_recreations.py --baselines`; changes show as image diffs in the PR.
- **Contract tests:** every parameter a definition file lists is read by the code, its range's edges are checked, and the reference GraphSpec sets every variable parameter.
- **Perturbation tests:** for every option and style parameter a graph type declares, render with a changed value, in its declared active state, and check that the effect appears. Checks assert on the figure's artists where possible, e.g. tick-label font size equals the resolved value. Those checks are exact and platform-independent; otherwise images are compared in-process at exact pixel equality.
- **"Hostile style" test:** render a graph under an extreme matplotlib style, and assert that nothing changes. This catches style values the theme forgot to set, which perturbation tests can't, and proves the isolation in D2.
- **PDF font test:** PDFs embed TrueType fonts with the expected name, and no Type 3 fonts.
- **Resolution tests:** layering order, merge rules, `extends`, and the `explain` origins.
- **Input tests:** drawing from a DataFrame and from a Parquet file; absolute, `~` and relative paths, including one set by a GraphSpec extended; column types through Parquet; each input error.
- **Skill evals:** natural-language requests over sample datasets → check the produced spec (graph type, mappings) and that lint passes. Each case runs several times and is scored on its pass rate, because single runs are noisy.
- **Catalog round trip:** build → comments made on prose and on table cells survive → `forgemark lint` is clean.

---

## 8. Specifications

Each kind of document is specified by its definition file: every parameter with its default, range and description. The code reads it, and tests check the code against it, including the edges of every range. docs/specs/ mirrors each file for review.

| Specification | Definition file |
| --- | --- |
| **Theme** | src/forgegraph/packs/forgegraph_base/themes/base_theme.yaml |
| **Format** | src/forgegraph/packs/forgegraph_base/formats/base_format.yaml |
| **Graph type** | src/forgegraph/graph_types/xy.yaml |
| **GraphSpec** | src/forgegraph/packs/forgegraph_base/graphspecs/graphspec_example.yaml |
| **Layer type** | src/forgegraph/layers/, a file per type |
| **Layout** | src/forgegraph/packs/forgegraph_base/layouts/layout_example.yaml |
| **Schedule** | src/forgegraph/packs/forgegraph_base/schedules/base_schedule.yaml |
| **Pack and config** | src/forgegraph/packs/forgegraph_base/pack.yaml, src/forgegraph/packs/config.toml |
| **Provenance record** | src/forgegraph/spec/provenance.yaml |
| **Catalog** | src/forgegraph/catalogs/, and each pack's catalogs/ |

---

## 9. Licence and name

- **Licence: MIT.** Anyone may use, change, embed, fork and sell the code, provided copies keep the copyright notice ("Copyright (c) Steven Kaye") and the licence text. That notice is the attribution. MIT was chosen for least hassle; Apache-2.0's explicit patent grant matters little for a graphing library.
- **Graphs are free.** The README and docs say, outside the licence text: *"Graphs and other output you make with ForgeGraph are yours. No attribution or licence terms apply to them."* Graphs carry no visible ForgeGraph credit, and provenance metadata can be switched off (D13).
- **The name stays Steven Kaye's.** The licence covers the code, not the name.
  - A `TRADEMARKS.md` states that "ForgeGraph" is owned by Steven Kaye. Forks and products may say "based on ForgeGraph", but must use their own name.
  - The namespaces are held: `forgegraph` on PyPI and `sskaye/forgegraph` on GitHub.
  - Trademark registration is optional. It makes enforcement much easier.
- **Dependencies:** matplotlib, pandas and the bundled OFL fonts are compatible with MIT; the fonts keep their own licence file.

---

## 10. Risks

| Risk | Mitigation |
| --- | --- |
| Spec and code drift | Definition files are the single source, read by the code; contract, comment and perturbation tests |
| Option sprawl in `xy` | Three-tier rule; new options only via the request flow; prefer layers and GraphSpecs to extend over flags |
| House-style changes silently alter scheduled outputs | Version pinning through lockfiles; visual changelog |
| Someone else ships a product called ForgeGraph | `TRADEMARKS.md`; held namespaces; optional registration |
| A pack is malicious or compromised | Packs are data only and never imported; YAML loaded safely; reference notes treated as data by the skill |
| Real data leaks into public requests | The skill's reference file says to leave out the user's data, and the agent shows the request before filing |
| Studio and the agent drift into incompatible specs | Options described by the schema; round-trip tests when Studio is built |
| Internal details leak in published figures | `minimal` provenance leaves out the data file and preprocessing reference |
| Confidential material enters the repo | Example PDFs gitignored; synthetic data rescaled; a deny-list of internal terms checked on every commit |
| Rebuilds orphan review comments | Stable ids, verbatim block carry-over, re-attachment by anchor text, `forgemark lint` in the build |
| A scheduled render stops and nobody notices | "Data as of" stamp in the image; stale banner; status file; `on_failure` hook |
| Fonts differ between machines | Bundled static fonts; fallback reported as a lint warning |
| User matplotlib settings change the output | Rendering isolated from rc settings and pyplot; hostile-style test |
| Agent picks the wrong chart or mapping | `catalog`, `schema` and org reference notes; render → look → lint loop; skill evals |

---

## 11. Deferred

- interactive backend and live-filter dashboards (post-MVP)
- responsive HTML dashboards (D11); `forgegraph migrate` (until a spec change needs it)
- in layouts: panel labels, axes shared between tiles, and one legend for several tiles (D11)
- stat or KPI tiles for ops dashboards
- MCP server, for agents that can't run `forgegraph` themselves (e.g. cloud chat apps)
- further graph types: histogram, heatmap/contour, area, waterfall/loss breakdown; added through the request flow as needed
- workbooks: a Parquet file bundled with the GraphSpecs and dashboards drawn from it, as one file to share or open (like Tableau's packaged workbooks), especially for Studio


---

## Appendix: the reasons behind smaller decisions

Decisions made while building whose reasons aren't given above.

### Drawing

- **Invalid requests are errors, never silent substitutes.** If what's asked is logically invalid or impossible, ForgeGraph stops and names the parameter and what to do, rather than defaulting to other behaviour or only warning: a warning can go unseen by an agent. Behaviour a spec defines isn't a fallback: colors repeating past the last, as series.colors says, stays a warning.
- **Drawing checks every file it uses.** A GraphSpec's graph type, theme and format, and each file they extend, are validated, so a theme with a problem stops the graph rather than being drawn with substitutes.
- **A missing font weight is an error.** A theme's weights are font-file weights (light 300 to bold 700). A theme whose font lacks a weight it uses is an error naming the weights the font has, rather than matplotlib substituting the nearest.
- **Bundled italics.** matplotlib's maths typesetting needs an italic face even when labels are upright, so Roboto and Source Sans 3 are bundled with their italics. Every bundled family has every weight a theme can name.
- **Text is measured to its letters.** matplotlib spaces text by a box sized for the font's tallest letters and deepest descenders, so its gaps aren't the gaps you see. Following CSS's `text-box: trim-both cap alphabetic`, Figma's vertical trim and D3's axis offsets, a text's edges run from its capital height to its baseline, growing only where its letters reach further. ForgeGraph lays the figure out itself, with no matplotlib layout engine.
- **No font hinting.** Text has the same width at every resolution, so what's laid out is what's saved.
- **Roboto is the base font,** chosen from a comparison of 13 open fonts.
- **Ticks come from published algorithms** (drawing/ticks.py), which a theme chooses: the base theme's are extended Wilkinson for linear axes and R's scales::breaks_log for log axes. A rule of ForgeGraph's own let labels run together on short axes. On every axis the labels must fit: the algorithm is asked for one tick fewer while they would overlap.
- **The layout always fits its tick labels.** Tick labels can keep a layout from settling: a taller plot box gets more, wider labels, which make it shorter again. After 6 unsettled passes it lays out once more with, on each side, the most room either of the last two passes needed, so whichever labels the final draw has fit.
- **Date axes use one calendar unit per axis.** matplotlib's automatic date ticks mix units (the 1st and 15th, labelled "Aug" and "15") and name the shared context in a corner. As in d3 and Vega-Lite, ticks are a calendar unit's boundaries, never finer than the data's spacing, with the next unit up on a second line where it changes, as Plotly and Datawrapper do. Weekly ticks fall on Mondays even when the data starts on another day, which reads more naturally than counting from the data's first day. ForgeGraph writes %-d, %-m and %-H itself, since strftime's differ by platform.
- **The default palette is Okabe–Ito.** With 4 or more groups, color_blind's colors ran together in the skill evals: two blues and two greys. Okabe and Ito's palette keeps its first four colors distinct for color-blind readers.
- **The base theme leaves line widths and marker sizes to the GraphSpec.** Agents in the skill evals needed smaller markers and thinner lines for dense data. Key samples have their own marker size, so shrinking the plot's markers leaves the key readable.
- **forgegraph_base_2 follows matplotlib's output, not its style sheet's numbers.** matplotlib draws the style's font weight 350 with Source Sans 3 Light, so the theme uses light. Its gaps were measured from matplotlib's output and set to match, since matplotlib measures from text boxes and ForgeGraph from letters.

### Names

- **Parameter names follow Vega-Lite where a standard term exists** (encoding, mark, detail), keeping ForgeGraph's nesting, snake_case and units. A third of the parameters have no Vega-Lite equivalent, so its names weren't adopted wholesale. "Legend" is the umbrella for every way of naming what colors and styles mean, as in Vega-Lite.
- **Every size is × figure.base_size,** so a theme draws correctly in any format.
- **The command is `forgegraph`.** `fg` is a built-in command in bash and zsh, and a shell runs its built-in before any program of that name.
- **A tab's name is what its tab shows.** File names and links use it lowercased, with spaces as hyphens, so there's no separate label to keep in step.

### Layouts

- **The grid is a list of tile names per row,** written one row under the other so it reads as a picture of the figure, as CSS grids, matplotlib's subplot_mosaic and patchwork do. A list of tiles with spans can't express a tile spanning rows.
- **A layout's tabs replace those it inherits,** rather than merging by name as a GraphSpec's layers do: a set of tabs is one design.
- **Spacing between tiles is the layout's,** not the theme's: it exists only in layouts, and a layout has no theme. A pack sets its house spacing in a base layout that its others extend.
- **The layout's format is twice the base format's width,** so two columns are each as wide as one base graph at the same text size. At the base width, two columns were too small for their labels in the skill evals.
- **A layout can set its format's variable parameters,** as a GraphSpec can, so a dashboard can be saved as HTML without a format of its own.
- **html is a file type for any graph,** not only dashboards: a graph linked from a wiki, or a scheduled graph whose page shows the stale banner. Figures are SVG with their text as outlines, so pages look the same in every browser.
- **Example formats stay examples.** Journal and dashboard sizes differ by journal and screen, and organizations keep their formats in packs.

### Schedules

- **A scheduled job is a file,** so it can be reviewed, kept in version control and checked like any other spec.
- **The cadence has one unit.** launchd's calendar intervals, cron and Task Scheduler's repetition count whole minutes, and can't run every 2 weeks or 3 days exactly, so `interval.count` divides 60, 24 or 12 for minutes, hours and months and is 1 otherwise. A list of times replaces separate weekday settings.
- **ForgeGraph writes no scheduler entries.** That would reach only the local machine, so one user's path would differ from everyone else's and couldn't be tested as theirs, and each operating system's rules made it the brittle part.
- **on_success as well as on_failure.** on_success lets a check-in service notice a job that stopped running, which on_failure can't.
- **Stale data isn't a failure.** A run that succeeds on old data isn't a failed run, so stale data shows in the banner, the footnote and the status file's data times, not through on_failure. "Data as of" is a target's oldest data file, so one stale tile makes a layout stale.

### Packs and configs

- **Packs are the only source of named specs,** so the specs a person or organization requires are kept in one place, and a folder can't pick up stray themes and formats beside a GraphSpec.
- **A pack only a folder config lists is non-standard, not an error,** so someone who can't change their organization's main config can still make and try a pack, while a pack used by accident is labelled, not silent. A folder config can't replace the main one, which would let a folder drop an organization's pack.
- **The main config is ~/.config/forgegraph/config.toml on every platform,** Windows included: one path is the easiest to document. `FORGEGRAPH_CONFIG` names another file, which keeps evals and tests away from the machine's own and lets an organization point at a managed one.
- **The main config is written on first use,** listing the built-in packs, since pip can't run code when it installs a package. It's never overwritten.
- **forgegraph.toml is a folder config,** and the CLI's option is `--folder`: calling it a project's would assume how the folder is used.
- **The record names each pack spec's pack version,** so a file shows which release of a house style drew it.
- **`schema graphspec` shows any spec ForgeGraph can find,** while `catalog` and `pack-notes` show only the allowed packs, so an agent can see how a spec it builds on is written.
- **Specs made in code keep plain names.** A theme or format added to a registry through the Python API has no pack; only names written pack/name are checked against the configs.

### Requests and the repository

- **The first release is small.** Features come from specific requests, not from guessing what users will want; annotations are built when someone asks for them.
- **Requests go through the skill,** which points to references/requests.md: agents already know how to write a feature request or bug report, so there's no issue form.
- **The public repository starts from one commit.** The earlier history held a confidential term, so it's kept privately.
- **Forgemark's tool is pinned,** downloaded once and checked by SHA-256. Problems found in Forgemark are reported to its maintainer, not worked around.
- **Review pages and catalog pages are exempt from the large-file check,** since they embed their images, and the deny-list check skips base64 image data, which can hold a short deny-listed term by chance.
