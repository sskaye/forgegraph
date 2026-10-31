# ForgeGraph

Fast, consistent, publication-quality graphs from pandas DataFrames, usable by people and AI agents.

You describe a graph in a **GraphSpec**. ForgeGraph draws it in a house style set by a **theme** and a **format**. It checks what it drew, and records how the graph was made inside the saved file. An agent skill lets agents make and revise graphs the same way.

## Key features

- **Themes:** fixes the look of the graph (fonts, palette, lines, keys, etc.).
- **Formats:** sets the destination: figure size, base font size, file types and resolution, e.g. a slide, a journal column or a dashboard tile.
- **GraphTypes:** defines the type of graph and its parameters. E.g. `xy` (lines, markers and bars).
- **Layers:** features drawn over a graph. E.g. reference lines and bands, notes, & error bars.
- **GraphSpecs:** specify the data, theme, format, and all customizable properties.
- **Series:** each series in a graph has its own marker, line and bar properties, and can show a summary of its data, such as the mean, a percentile or a confidence interval.
- **Layouts:** combine multiple graphs into a larger figure or multi-tab dashboard.
- **Scheduled renders:** re-render graphs and dashboards on a schedule set with cron, launchd, or by an agent.
- **Provenance:** every saved file contains its specifications as metadata, enabling inspection of how the graph was made and reproduction of it.
- **Packs:** collect together a set of themes and formats for different use cases. E.g. a company or lab’s standard style, journal requirements, etc.
- **Configs:** control which packs may be used, per user or folder. Used to enforce use of style pack(s) and watermark non-standard graphs.
- **Lint:** Graphs are linted on rendering, with warnings for issues including overlapping or clipped text, a key covering data, or fonts too small.

**Status:** Until 1.0, a new minor version may change how graphs look or how specs are written; the [changelog](https://github.com/sskaye/forgegraph/blob/main/CHANGELOG.md) lists what changed in each release. `forgegraph catalog` lists the graph types, layers and packs you have. More graph types are planned. If there are specific ones you want, [open an issue](https://github.com/sskaye/forgegraph/issues).

## Packs and configs

Every named theme, format, GraphSpec, layout and schedule comes from a **pack**, a folder or pip package of specs, and is named `pack/name`. ForgeGraph's built-in pack, `forgegraph_default`, is stored in src/forgegraph/packs. It has a theme and formats, so a graph can always be drawn, and specs to extend; `forgegraph catalog` lists them, and [the Reference](reference/built-in-pack/index.md) shows each one.

A **config** lists the packs that may be used:

- The main config, `~/.config/forgegraph/config.toml` (or the file `FORGEGRAPH_CONFIG` names), applies to all work. ForgeGraph writes it, listing the built-in packs, the first time a command reads the configs, such as `catalog` or `render`.
- A folder config, `forgegraph.toml`, applies to the files in its folder and every folder below it. A file may use only the packs it lists.
- A pack that a folder config lists but the main config doesn't still works, but it's non-standard: graphs drawn with it are watermarked, and ForgeGraph's commands say so. That way you can make and try a pack without changing an organization's main config.

To write a pack, start from the example pack in [examples/packs/acme](https://github.com/sskaye/forgegraph/blob/main/examples/packs/acme); `forgegraph schema theme`, `format`, `pack` and `config` list every parameter.

## Catalogs

The built-in pack has a catalog: a page with a card for each parameter, showing what changing it does. Download it and open it in a browser.

- [forgegraph_default](https://github.com/sskaye/forgegraph/blob/main/catalog/forgegraph_default.html): its theme and formats, and ForgeGraph's graph types and layer types drawn in them.

## Your graphs are yours

ForgeGraph is [MIT-licensed](https://github.com/sskaye/forgegraph/blob/main/LICENSE). Graphs and other output you make with it are yours: no attribution or licence terms apply to them. See [TRADEMARKS.md](https://github.com/sskaye/forgegraph/blob/main/TRADEMARKS.md) for use of the name.

Feature requests and bug reports go to [GitHub issues](https://github.com/sskaye/forgegraph/issues); the skill can file them for you. [CONTRIBUTING.md](https://github.com/sskaye/forgegraph/blob/main/CONTRIBUTING.md) covers working on ForgeGraph itself.
