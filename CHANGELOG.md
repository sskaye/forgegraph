# Changelog

ForgeGraph follows [semantic versioning](https://semver.org). Before 1.0, a minor version may change how graphs look or how specs are written.

## 0.5.0 (2026-10-29)

### New Features

- **Nested tabs.** A tab in a layout can now hold tabs of its own, to any depth. The HTML page shows a row of tabs for each level, and switching to another group keeps the same chart showing.
- **Tick labels per axis.** `axis.x.tick.label` and `axis.y.tick.label` set the size, weight and color of each axis's tick labels separately. Anything they don't set comes from `axis.tick.label`.
- **Tab bar style.** A layout's `tab_bar.label` and `tab_bar.line` set the look of the tab names and of the line under them on the HTML page. By default they follow the first graph's theme.

### Changes

- **Titles.** Titles now sit `title.gap` above the plot, measured from the line the letters sit on, so titles side by side line up whatever their letters. The default theme's `title.gap` is now 0.41, which keeps its titles where they were. A theme that sets its own `title.gap` will see its titles sit a little higher than in 0.4.
- **Notes above the plot.** A note placed outside the plot at the top now goes between the title and the plot, instead of above the title.
- **Tab names on the page.** The tab names are written in the theme's font and color, instead of the browser's font in dark grey.

### Bug Fixes

- Tick labels now use the theme's tick label font and weight. Before, only their size and color were applied.
- A y-axis title reading upward now sits the same distance from the tick labels whatever its letters.

## 0.4.0 (2026-10-27)

### New Features

- **Multiple Series.** GraphSpecs can now have independent Series, enabling full control over the marker, line, and bar properties and not just variation by a palette.
- **Reference bands.** The `reference_line` layer is now `reference` and has been augmented to also draw lines per element of the series and bands. It also can now compute a value plus offset (e.g. a line at mean + 3 s.d.). This enables drawing of error bands, confidence intervals of model fits, and other more complex references.
- **More aggregations.** Series, reference lines, and error bars can show the mean, median, percentile, standard deviation, standard error or confidence intervals.
- **Stepped and smooth lines.** `line.interpolate` can now be steps or a smooth curve in addition to a direct line.
- **Dates as values.** Dates, such as `2025-08-25`, can now be used directly in all relevant parameters.

### Changes

- **One built-in pack, `forgegraph_default`.** `forgegraph_base` is renamed `forgegraph_default` and its specifications have been renamed. `forgegraph_base_2` has been removed. Please update your config and any GraphSpecs or packs referencing the old packs. The default theme has been tuned slightly to fix more parameters, reducing complexity of graph design.
- **Themes, formats and GraphSpecs are written differently.** Each has one `parameters` tree, and `!fix` and `!var` tags are used to set what a GraphSpec can change, in place of the `fixed_parameters` and `variable_parameters` blocks. A theme sets the parameters of all text and all lines once, under `text` and `line`, and each category that uses them, such as the title or the tick labels, only needs to modify the parameters that are different from that default.
- **Simplified Specifications.** Numerous simplifications to the way specifications are written, making them easier to read and modify.

### Bug Fixes

- Dates on the y axis draw as they do on x: date ticks, reference lines at a date column's mean or median, and error bars in days.
- The lint no longer counts reference lines and error bars as data points outside the axis limits, or as values of 0 or below on a log axis.
- Values that differ from an axis limit only by rounding are no longer reported as outside it.
- In a theme with a light font weight, powers of ten on a log axis no longer give a `font-fallback` lint issue.
- `null` and `~` are accepted everywhere a spec can say None.

## 0.3.0 (2026-10-25)

### Added

- `fg.blank` takes `registry=`, as `fg.render` does, and a blank canvas's `save` path is optional, as a graph's is: with none, it saves `canvas.png` and the format's other file types.

### Changed

- **Breaking for existing specs:** parameters follow one naming system. `_` joins words that name one thing (`error_bar`, `plot_area`), `.` goes from a thing to its parts and properties (`line.width`), an on/off switch is the thing's `.show`, and nothing is abbreviated. A spec still using an old name is an error that suggests the new one; an old name that's now a category, such as `encoding.color`, suggests that category's parameters. The Python API's keyword arguments (`fg.xy`'s `color=`, `line_style=`, `marker_shape=`, `marker_fill=`, `detail=`) are unchanged and set the new paths. Graphs draw the same as before. The renames, old → new:
  1. `grid.line_style` → `grid.line.style`; `grid.line_width` → `grid.line.width`
  2. `plot_area.line_color` → `plot_area.line.color`; `plot_area.line_width` → `plot_area.line.width`
  3. `layer.error_bar.line_width` → `layer.error_bar.line.width`; `layer.error_bar.cap_size` → `layer.error_bar.cap.width`
  4. `layer.reference_line.line_style` → `layer.reference_line.line.style`; `layer.reference_line.line_width` → `layer.reference_line.line.width`
  5. `series.marker.edge_color`, `series.marker.edge_width` → `series.marker.edge.color`, `series.marker.edge.width`, and the same in `series.bar`, `series.benchmark.marker` and `series.benchmark.bar`
  6. `legend.key.frame_width` → `legend.key.frame.width`
  7. `legend.key.sample.marker_size` → `legend.key.sample.marker.size`
  8. `legend.key.frame` → `legend.key.frame.show`
  9. `series.value_label.total` → `series.value_label.total.show`
  10. `axis.tick.minor.num` → `axis.tick.minor.count`
  11. `encoding.color` → `encoding.color.column`; `encoding.color_type` → `encoding.color.type`; `encoding.line_style` → `encoding.line.style.column`; `encoding.marker_shape` → `encoding.marker.shape.column`; `encoding.marker_fill` → `encoding.marker.fill.column`; `encoding.detail` → `encoding.detail.column` (`encoding.order` is unchanged)
  12. Layouts: `separators.line.border` → `separators.border.show`
  13. Schedules: `freshness.stamp` → `freshness.stamp.show`; `cadence.interval` → `cadence.interval.count`; `cadence.interval_unit` → `cadence.interval.unit`
- **Breaking for packs' catalog files:** a catalog's cards are chosen by a rule, not by hand. Every parameter gets one card, its value taken from its range and the baseline's data, drawn on the first baseline where it changes the drawing; the page shows the variable parameters' cards. A catalog file lists only its baselines, and a layer's settings: `variations`, `no_card` and the `{value, from, with}` forms are gone. A pack's catalog page draws with the pack's own theme and format values.
- Drawing and saving are about 3.7 times faster. Graphs and their files are the same as before.
- A pack's fonts are registered when a file drawn uses one of its specs, not whenever a config lists the pack.
- `forgegraph --help` gives each command a one-sentence summary, and `forgegraph catalog --help` names every kind it lists.
- The internal package `forgegraph.catalog` is `forgegraph.catalog_build`. The API is unchanged.
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
- A GraphSpec naming a list as its theme, format or graph type gets the error "must be a single value", not a crash.
- A config naming a pack that can't be found, or another pack problem, stops `catalog`, `pack-notes`, `schema` and `explain` with its problems listed (`error:` lines, exit 1), not a traceback; with `--json`, one problem each, not one joined line.

## 0.2.0 (2026-10-24)

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
