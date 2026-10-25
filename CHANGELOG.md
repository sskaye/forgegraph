# Changelog

ForgeGraph follows [semantic versioning](https://semver.org). Before 1.0, a minor version may change how graphs look or how specs are written. From 0.1.0 on, each release's entry links its visual changelog: before and after images of every catalog card and regression graph that changed, made with `scripts/visual_changelog.py`.

## Unreleased

### Changed

- One name is one pack. A config can't give a built-in pack's name, or a name the main config already gives, to another folder. Before, a folder config's copy of a pack replaced the one the main config lists, and what it drew wasn't marked non-standard.
- ForgeGraph needs matplotlib 3.11.2 and typer 0.15.4 or later; earlier versions installed but didn't work.
- The package's description and classifiers say what it is now: released, in alpha.

### Fixed

- Error bars on a date axis stand on their points, and error bars of aggregated rows on a date axis draw.
- Times with a time zone are drawn at the times their clocks show. Before, they raised an error.
- A reference line at a column's sum or standard deviation counts each row once when several y columns are drawn.
- Value labels written with format auto use the value axis's tick label format when it's set, as reference lines do.
- The catalog's record of what it was built from covers every module it draws with, so a change to the drawing code marks the catalog out of date.
- The package's metadata lists the bundled fonts' licences.

## 0.2.0 (2026-10-24)

Images that changed: the [visual changelog](review/visual-changelog/0.2.0.html).

### Changed

- Error bars are black by default in both built-in themes, and their color (`layer.error_bar.color`) is a variable parameter: a GraphSpec may set `series` or any hex color.
- Three internal modules are renamed so none shares a name with the API: `forgegraph.render` is `forgegraph.drawing`, `forgegraph.layout` is `forgegraph.layouts` and `forgegraph.blank` is `forgegraph.canvas`. `import forgegraph.layouts as m` now gives the module, not `fg.layout`. The API is unchanged.

### Fixed

- `forgegraph --version` and `--help` no longer load matplotlib and pandas, so they answer at once, even on a new install. The API loads on first use.
- The README and the skill's reference say when the main config is written: the first time a command reads the configs, such as `catalog` or `render`.
- Error bars on side-by-side bars (`series.offset: side_by_side`) are drawn on their own bars. Before, every series but the middle one had its error bars drawn where they were first placed, before layout, usually off the axes.

## 0.1.0 (2026-10-24)

The first public release.

### Added

- **GraphSpecs:** a graph described in YAML or as a Python dict, drawn with `forgegraph render` or `fg.render`; `fg.xy` draws straight from a DataFrame.
- **The `xy` graph type:**
  - lines, markers and bars: grouped, stacked, 100 % stacked and horizontal;
  - dates and log axes, value labels, a benchmark series;
  - series named beside their lines or in a key.
- **Layers:** reference lines, notes and error bars, from the data or given.
- **Themes and formats:** a theme fixes what must stay the same and gives defaults for the rest; a format sets size, base font size, file types and resolution.
- **Packs and configs:**
  - every named spec comes from a pack, named `pack/name`; ForgeGraph's own is `forgegraph_base`, and `forgegraph_base_2` is a second look in this repository;
  - the main config (written on first use, or named by `FORGEGRAPH_CONFIG`) and folder configs (`forgegraph.toml`) say which packs may be used;
  - a pack only a folder config lists is non-standard: it works, and what's drawn with it is watermarked.
- **Lint on every render:** overlapping or clipped text, a key covering data, fonts too small for the format, missing fonts, dropped rows and more.
- **Provenance:** every saved file (PNG, JPEG, TIFF, SVG, PDF and HTML) records its GraphSpec and the specs it was drawn with, at the format's provenance level; `forgegraph load` reads it back.
- **Layouts:** several GraphSpecs in one figure, with spanning tiles, blank cells and set widths; tabs, and HTML dashboards.
- **Scheduled renders:** schedule files, `forgegraph job run`, a status file, `on_failure` and `on_success` hooks, a "data as of" footnote and a stale banner.
- **The themed canvas:** `forgegraph.blank(theme, format)` for what no graph type can draw, always watermarked as non-standard.
- **The agent skill** for Claude Code, installed with `forgegraph skill install`, with reference notes for themes, formats and configs, and for filing requests.
- **Commands:** `render`, `explain`, `catalog`, `schema`, `pack-notes`, `load`, `job run` and `skill install`, each with `--json`.
- **Catalogs:** a page for each pack in this repository, with a card for every parameter.

## 0.0.1 (2026-10-17)

The name, reserved on PyPI. No functionality.
